// IKPU (MXIK) qidiruvi. tasnif.soliq.uz CORS'ga ruxsat beradi, foydalanuvchi esa O'zbekistonda —
// shuning uchun avval brauzerdan to'g'ridan-to'g'ri so'raymiz (xorijdagi server ulana olmasligi mumkin),
// bo'lmasa backend proksisi.
import { api } from "./api";
import type { IkpuItem } from "./types";

const TASNIF = "https://tasnif.soliq.uz/api/cls-api/elasticsearch/search";

async function direct(q: string, lang: string, size: number): Promise<IkpuItem[]> {
  const ctl = new AbortController();
  const timer = setTimeout(() => ctl.abort(), 9000);
  try {
    const u = `${TASNIF}?${new URLSearchParams({ search: q, page: "0", size: String(size), lang })}`;
    const r = await fetch(u, { signal: ctl.signal, headers: { Accept: "application/json" } });
    if (!r.ok) throw new Error(`tasnif ${r.status}`);
    const d = await r.json();
    return ((d?.data || []) as any[])
      .filter((x) => String(x?.mxikCode || "").length === 17)
      .map((x) => ({
        code: String(x.mxikCode), name: x.name || "", group: x.groupName || "", class: x.className || "",
        position: x.positionName || "", subposition: x.subPositionName || "", brand: x.brandName || "",
      }));
  } finally { clearTimeout(timer); }
}

export async function searchIkpu(q: string, lang = "ru", size = 20): Promise<{ items: IkpuItem[]; error?: string }> {
  try {
    return { items: await direct(q, lang, size) };
  } catch (e1) {
    try {
      return await api<{ items: IkpuItem[]; error?: string }>(`/seller/ikpu/search/?q=${encodeURIComponent(q)}&lang=${lang}`, { authed: true });
    } catch (e2: any) {
      const msg = e2?.data?.error || (e1 as Error)?.message || "tasnif.soliq.uz";
      return { items: [], error: String(msg) };
    }
  }
}

/** Kodsiz mahsulotlarga avtomatik tavsiya: har bir nom bo'yicha brauzerda qidirib, backend eng mosini yozadi. */
export async function suggestMissing(onProgress: (done: number, total: number, updated: number) => void, signal?: { stop: boolean }) {
  const m = await api<{ groups: { name_ru: string; name_uz: string; ids: number[] }[]; products: number }>("/seller/ikpu/missing/", { authed: true });
  let updated = 0, done = 0, failed = 0;
  for (const g of m.groups) {
    if (signal?.stop) break;
    let picked = false;
    for (const [q, lang] of [[g.name_ru, "ru"], [g.name_uz, "uz"]] as const) {
      if (!q || picked) continue;
      const short = (q.match(/[^\W\d_]{3,}/gu) || []).slice(0, 2).join(" ");
      for (const query of Array.from(new Set([q, short])).filter(Boolean)) {
        const r = await searchIkpu(query, lang);
        if (r.error && !r.items.length) { failed++; continue; }
        const res = await api<{ picked: unknown; updated: number }>("/seller/ikpu/apply/", { method: "POST", json: { ids: g.ids, query: q, items: r.items }, authed: true });
        if (res.picked) { updated += res.updated; picked = true; break; }
      }
    }
    done++;
    onProgress(done, m.groups.length, updated);
    if (failed >= 3 && updated === 0) throw new Error("tasnif.soliq.uz javob bermayapti");
  }
  return { updated, groups: m.groups.length, products: m.products };
}
