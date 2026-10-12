"use client";
import { CheckCircle2, Search } from "lucide-react";
import { useEffect, useState } from "react";
import { Badge, Button, Input, Spinner } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { useApp } from "@/lib/store";
import type { IkpuItem, SellerProduct } from "@/lib/types";
import { digitsOnly, ErrorBox, type ProductChange, errMsg } from "./shared";

/** IKPU (MXIK) — 17 raqamli soliq tasniflagichi kodi. Tanlash darhol saqlanadi (PATCH). */
export default function IkpuPicker({ product, onChange }: { product: SellerProduct; onChange: ProductChange }) {
  const { t, p, meta, lang } = useApp();
  const cat = meta?.categories.find((c) => c.slug === product.category);
  const [q, setQ] = useState("");
  const [items, setItems] = useState<IkpuItem[] | null>(null);
  const [searching, setSearching] = useState(false);
  const [searchErr, setSearchErr] = useState("");
  const [manual, setManual] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    const s = q.trim();
    if (s.length < 2) { setItems(null); setSearchErr(""); return; }
    let alive = true;
    const id = setTimeout(() => {
      setSearching(true); setSearchErr("");
      // so'rov kirillchada bo'lsa — ruscha tasnif, lotinchada — o'zbekcha
      const l = /[а-яё]/i.test(s) || lang === "ru" ? "ru" : "uz";
      api<{ items: IkpuItem[]; error?: string }>(`/seller/ikpu/search/?q=${encodeURIComponent(s)}&lang=${l}`, { authed: true })
        .then((d) => { if (alive) { setItems(d.items || []); if (d.error) setSearchErr(d.error); } })
        .catch((e) => {
          if (!alive) return;
          setItems([]);
          setSearchErr(e instanceof ApiError && e.data?.error ? String(e.data.error) : errMsg(e));
        })
        .finally(() => alive && setSearching(false));
    }, 450);
    return () => { alive = false; clearTimeout(id); };
  }, [q, lang]);

  const patch = async (json: Record<string, unknown>) => {
    setBusy(true); setErr("");
    try {
      const saved = await api<SellerProduct>(`/seller/products/${product.id}/`, { method: "PATCH", json, authed: true });
      onChange(saved); setQ(""); setManual("");
    } catch (e) { setErr(errMsg(e)); } finally { setBusy(false); }
  };

  return (
    <div className="space-y-3">
      <div className="rounded-xl border border-ink-100 p-3">
        {product.ikpu ? (
          <div className="flex flex-wrap items-start gap-3 justify-between">
            <div className="min-w-0">
              <div className="font-mono font-semibold tabular-nums tracking-wide">{product.ikpu}</div>
              {product.ikpu_name && <div className="text-xs text-ink-500 mt-0.5">{product.ikpu_name}</div>}
            </div>
            {product.ikpu_confirmed ? (
              <Badge tone="green"><CheckCircle2 className="w-3.5 h-3.5" />{t("pe_ikpu_confirmed")}</Badge>
            ) : (
              <div className="flex items-center gap-2">
                <Badge tone="amber">{t("pe_ikpu_suggested")}</Badge>
                <Button size="sm" variant="soft" loading={busy} onClick={() => patch({ ikpu_confirmed: true })}>{t("pe_ikpu_confirm")}</Button>
              </div>
            )}
          </div>
        ) : (
          <div className="text-sm text-ink-500">{t("pe_ikpu_none")}</div>
        )}
        {cat?.ikpu_default && cat.ikpu_default !== product.ikpu && (
          <div className="mt-2 pt-2 border-t border-ink-100 flex flex-wrap items-center gap-2 justify-between text-xs text-ink-500">
            <span>{t("pe_ikpu_cat_default", { c: p(cat.name) })}: <b className="font-mono text-ink-700">{cat.ikpu_default}</b>{cat.ikpu_name ? ` — ${cat.ikpu_name}` : ""}</span>
            <Button size="sm" variant="outline" disabled={busy} onClick={() => patch({ ikpu: cat.ikpu_default, ikpu_name: cat.ikpu_name || "", ikpu_confirmed: true })}>{t("pe_ikpu_use")}</Button>
          </div>
        )}
      </div>

      <div className="relative">
        <Search className="w-4 h-4 absolute left-3 top-3.5 text-ink-500" />
        <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder={t("pe_ikpu_search_ph")} className="pl-9" />
        {searching && <Spinner className="w-4 h-4 absolute right-3 top-3.5" />}
      </div>
      {searchErr && <div className="text-xs text-amber-800 bg-amber-50 rounded-lg p-2">{searchErr}<br />{t("pe_ikpu_manual_hint")}</div>}
      {items && items.length > 0 && (
        <div className="max-h-64 overflow-y-auto rounded-xl border border-ink-100 divide-y divide-ink-100">
          {items.map((it) => (
            <button key={it.code} type="button" disabled={busy} onClick={() => patch({ ikpu: it.code, ikpu_name: it.name.slice(0, 255), ikpu_confirmed: true })}
              className="w-full text-left px-3 py-2 hover:bg-brand-50 disabled:opacity-50">
              <div className="flex gap-2 items-baseline">
                <span className="font-mono text-xs font-semibold text-brand-700 tabular-nums shrink-0">{it.code}</span>
                <span className="text-sm">{it.name}</span>
              </div>
              {(it.subposition || it.position || it.class) && <div className="text-xs text-ink-500 mt-0.5 truncate">{[it.class, it.position, it.subposition].filter(Boolean).join(" › ")}</div>}
            </button>
          ))}
        </div>
      )}
      {items && items.length === 0 && !searching && !searchErr && <div className="text-xs text-ink-500">{t("pe_ikpu_nothing")}</div>}

      <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); if (manual.length === 17) patch({ ikpu: manual, ikpu_name: "", ikpu_confirmed: true }); }}>
        <Input value={manual} onChange={(e) => setManual(digitsOnly(e.target.value).slice(0, 17))} inputMode="numeric" placeholder={t("pe_ikpu_manual_ph")} className="font-mono" />
        <Button type="submit" variant="outline" disabled={manual.length !== 17 || busy}>{t("save")}</Button>
      </form>
      {manual.length > 0 && manual.length !== 17 && <div className="text-xs text-ink-500">{t("pe_ikpu_len", { n: manual.length })}</div>}
      <ErrorBox text={err} />
    </div>
  );
}
