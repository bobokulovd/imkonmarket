"use client";
import clsx from "clsx";
import { Eye, EyeOff, ImagePlus, Pencil, Plus, Search } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useMe } from "@/components/CabinetShell";
import BulkImages from "@/components/BulkImages";
import { Badge, Button, Empty, Field, Input, Modal, ProductImage, Select, Spinner, Textarea, Toast } from "@/components/ui";
import { api, auth, API_URL, errText, qs, ApiError } from "@/lib/api";
import { LANGS, useApp } from "@/lib/store";
import { toCyrl, toNew } from "@/lib/translit";
import type { I18n, Lang, Paged, SellerProduct } from "@/lib/types";

const UNITS = ["dona", "juft", "kg", "m²", "m³", "p/m", "to'plam", "tonna", "xizmat"];

type Form = {
  id?: number; name: I18n; spec: I18n; description: I18n; category: string; unit: string; price: string; stock: string;
  daily_capacity: string; lead_days: string; min_order: string; delivery: boolean; is_active: boolean; note: string; seller?: string;
};
const emptyForm = (cat: string): Form => ({
  name: {}, spec: {}, description: {}, category: cat, unit: "dona", price: "", stock: "", daily_capacity: "", lead_days: "3",
  min_order: "1", delivery: true, is_active: true, note: "",
});

function Editor({ initial, onSaved, onClose }: { initial: Form & { image_url?: string | null }; onSaved: () => void; onClose: () => void }) {
  const { t, p, meta, unit } = useApp();
  const { me } = useMe();
  const [f, setF] = useState<Form>(initial);
  const [tab, setTab] = useState<Lang>("uz");
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const setI = (k: "name" | "spec" | "description", v: string) => {
    const cur: I18n = { ...f[k] };
    if (tab === "uz") {
      // avtomatik to'ldirilgan (uz dan olingan) qiymatlarni tozalaymiz — backend qayta hosil qiladi
      const old = cur.uz || "";
      (Object.keys(cur) as Lang[]).forEach((l) => {
        if (l === "uz") return;
        if (cur[l] === old || (l === "uz_cyrl" && cur[l] === toCyrl(old)) || (l === "uz_new" && cur[l] === toNew(old))) cur[l] = "";
      });
    }
    cur[tab] = v;
    setF({ ...f, [k]: cur });
  };

  const save = async () => {
    setBusy(true); setErr("");
    const body = new FormData();
    const json: Record<string, any> = {
      name: f.name, spec: f.spec, description: f.description, category: f.category, unit: f.unit,
      price: f.price || null, stock: f.stock === "" ? null : f.stock, daily_capacity: f.daily_capacity || null,
      lead_days: f.lead_days || 3, min_order: f.min_order || 1, delivery: f.delivery, is_active: f.is_active, note: f.note,
    };
    if (f.seller) json.seller = f.seller;
    try {
      const url = f.id ? `/seller/products/${f.id}/` : "/seller/products/";
      const method = f.id ? "PATCH" : "POST";
      const saved = await api<SellerProduct>(url, { method, json, authed: true });
      if (file) {
        body.append("image", file);
        const res = await fetch(`${API_URL}/api/seller/products/${saved.id}/`, { method: "PATCH", body, headers: { Authorization: `Bearer ${auth.token}` } });
        if (!res.ok) throw new ApiError(res.status, await res.json().catch(() => ({})));
      }
      onSaved();
    } catch (e) { setErr(errText(e)); } finally { setBusy(false); }
  };

  return (
    <div className="space-y-5">
      <div className="flex gap-4 items-start">
        <label className="w-28 h-28 rounded-xl overflow-hidden border border-dashed border-ink-300 shrink-0 cursor-pointer relative group">
          {file ? <img src={URL.createObjectURL(file)} className="w-full h-full object-cover" alt="" /> : <ProductImage src={initial.image_url} category={f.category} icon={meta?.categories.find((c) => c.slug === f.category)?.icon} />}
          <span className="absolute inset-0 bg-ink-900/40 text-white text-xs font-semibold grid place-items-center opacity-0 group-hover:opacity-100 transition"><ImagePlus className="w-6 h-6" /></span>
          <input type="file" accept="image/*" className="hidden" onChange={(e) => setFile(e.target.files?.[0] || null)} />
        </label>
        <div className="flex-1 text-xs text-ink-500">{t("upload_image")} · JPG/PNG<br /><br />{t("tr_hint")}</div>
      </div>
      <div>
        <div className="flex gap-1 overflow-x-auto no-scrollbar border-b border-ink-100">
          {LANGS.map((l) => (
            <button key={l.code} type="button" onClick={() => setTab(l.code)} className={clsx("px-3 py-2 text-sm font-semibold border-b-2 -mb-px whitespace-nowrap", tab === l.code ? "border-brand-600 text-brand-700" : "border-transparent text-ink-500")}>
              {l.short}{f.name[l.code] ? " ✓" : ""}
            </button>
          ))}
        </div>
        <div className="grid gap-3 mt-3">
          <Field label={`${t("name")} (${LANGS.find((l) => l.code === tab)?.label})${tab === "uz" ? " *" : ""}`}><Input value={f.name[tab] || ""} onChange={(e) => setI("name", e.target.value)} placeholder={tab !== "uz" ? f.name.uz : ""} /></Field>
          <Field label={t("spec")}><Input value={f.spec[tab] || ""} onChange={(e) => setI("spec", e.target.value)} placeholder={tab !== "uz" ? f.spec.uz : ""} /></Field>
          <Field label={t("description")}><Textarea rows={3} value={f.description[tab] || ""} onChange={(e) => setI("description", e.target.value)} /></Field>
        </div>
      </div>
      <div className="grid sm:grid-cols-3 gap-3">
        {me.seller.role === "operator" && !f.id && (
          <Field label={t("seller")} className="sm:col-span-3"><Select value={f.seller || ""} onChange={(e) => setF({ ...f, seller: e.target.value })}>
            <option value="">—</option>{meta?.sellers.map((s) => <option key={s.code} value={s.code}>{p(s.name)}</option>)}</Select></Field>
        )}
        <Field label={t("category")} className="sm:col-span-2"><Select value={f.category} onChange={(e) => setF({ ...f, category: e.target.value })}>{meta?.categories.map((c) => <option key={c.slug} value={c.slug}>{p(c.name)}</option>)}</Select></Field>
        <Field label={t("unit")}><Select value={f.unit} onChange={(e) => setF({ ...f, unit: e.target.value })}>{UNITS.map((u) => <option key={u} value={u}>{unit(u)}</option>)}</Select></Field>
        <Field label={`${t("price")}, ${t("sum")}`} hint={`∅ = ${t("price_on_request")}`}><Input inputMode="decimal" value={f.price} onChange={(e) => setF({ ...f, price: e.target.value.replace(/[^\d.]/g, "") })} /></Field>
        <Field label={t("stock")} hint={t("stock_hint")}><Input inputMode="numeric" value={f.stock} onChange={(e) => setF({ ...f, stock: e.target.value.replace(/\D/g, "") })} /></Field>
        <Field label={t("daily_capacity")}><Input inputMode="numeric" value={f.daily_capacity} onChange={(e) => setF({ ...f, daily_capacity: e.target.value.replace(/\D/g, "") })} /></Field>
        <Field label={t("lead_days", { n: "" }).replace(/[:\s]+$/, "")}><Input inputMode="numeric" value={f.lead_days} onChange={(e) => setF({ ...f, lead_days: e.target.value.replace(/\D/g, "") })} /></Field>
        <Field label={t("min_order", { n: "" }).replace(/[:\s]+$/, "")}><Input inputMode="numeric" value={f.min_order} onChange={(e) => setF({ ...f, min_order: e.target.value.replace(/\D/g, "") })} /></Field>
        <Field label={t("notes")}><Input value={f.note} onChange={(e) => setF({ ...f, note: e.target.value })} /></Field>
      </div>
      <div className="flex flex-wrap gap-5 text-sm">
        <label className="flex items-center gap-2"><input type="checkbox" className="w-4 h-4 accent-brand-600" checked={f.delivery} onChange={(e) => setF({ ...f, delivery: e.target.checked })} /> {t("delivery_yes")}</label>
        <label className="flex items-center gap-2"><input type="checkbox" className="w-4 h-4 accent-brand-600" checked={f.is_active} onChange={(e) => setF({ ...f, is_active: e.target.checked })} /> {t("published")}</label>
      </div>
      {err && <div className="text-sm text-red-700 bg-red-50 rounded-lg p-3">{err}</div>}
      <div className="flex gap-2 justify-end">
        <Button variant="ghost" onClick={onClose}>{t("cancel")}</Button>
        <Button loading={busy} disabled={!f.name.uz?.trim()} onClick={save}>{t("save")}</Button>
      </div>
    </div>
  );
}

function StockCell({ pr, onSaved }: { pr: SellerProduct; onSaved: () => void }) {
  const [v, setV] = useState(pr.stock === null ? "" : String(pr.stock));
  const [busy, setBusy] = useState(false);
  useEffect(() => setV(pr.stock === null ? "" : String(pr.stock)), [pr.stock]);
  const dirty = v !== (pr.stock === null ? "" : String(pr.stock));
  const save = async () => {
    setBusy(true);
    try { await api(`/seller/products/${pr.id}/stock/`, { method: "POST", json: { stock: v === "" ? null : v }, authed: true }); onSaved(); } finally { setBusy(false); }
  };
  return (
    <form onSubmit={(e) => { e.preventDefault(); save(); }} className="flex items-center gap-1">
      <input value={v} onChange={(e) => setV(e.target.value.replace(/\D/g, ""))} placeholder="∞" inputMode="numeric"
        className={clsx("w-20 h-8 rounded-lg border px-2 text-right tabular-nums text-sm outline-none", dirty ? "border-accent-500 bg-orange-50" : "border-ink-300")} />
      {dirty && <button className="h-8 px-2 rounded-lg bg-brand-600 text-white text-xs font-semibold" disabled={busy}>OK</button>}
    </form>
  );
}

export default function ProductsPage() {
  const { t, p, money, unit, meta } = useApp();
  const { me } = useMe();
  const [data, setData] = useState<Paged<SellerProduct> | null>(null);
  const [q, setQ] = useState("");
  const [cat, setCat] = useState("");
  const [img, setImg] = useState("");
  const [bulk, setBulk] = useState(false);
  const [page, setPage] = useState(1);
  const [edit, setEdit] = useState<(Form & { image_url?: string | null }) | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  const load = useCallback(() => {
    api<Paged<SellerProduct>>(`/seller/products/${qs({ q, category: cat, image: img, page, page_size: 50 })}`, { authed: true }).then(setData).catch(() => {});
  }, [q, cat, img, page]);
  useEffect(() => { const id = setTimeout(load, 250); return () => clearTimeout(id); }, [load]);

  const openEdit = (pr: SellerProduct) => setEdit({
    id: pr.id, name: pr.name, spec: pr.spec, description: pr.description || {}, category: pr.category, unit: pr.unit,
    price: pr.price ? String(Number(pr.price)) : "", stock: pr.stock === null ? "" : String(pr.stock),
    daily_capacity: pr.daily_capacity ? String(pr.daily_capacity) : "", lead_days: String(pr.lead_days), min_order: String(pr.min_order),
    delivery: pr.delivery, is_active: pr.is_active, note: pr.note, image_url: pr.image_url,
  });
  const toggle = async (pr: SellerProduct) => {
    await api(`/seller/products/${pr.id}/`, { method: "PATCH", json: { is_active: !pr.is_active }, authed: true });
    load();
  };

  return (
    <div>
      <div className="flex flex-wrap gap-3 items-center justify-between">
        <h1 className="text-2xl font-extrabold">{t("my_products")} {data && <span className="text-ink-500 text-lg">· {data.count}</span>}</h1>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => setBulk(true)}><ImagePlus className="w-4 h-4" /> {t("bulk_images")}</Button>
          <Button onClick={() => setEdit(emptyForm(meta?.categories[0]?.slug || "mebel"))}><Plus className="w-4 h-4" /> {t("add_product")}</Button>
        </div>
      </div>
      <div className="flex flex-wrap gap-2 mt-4">
        <div className="relative flex-1 min-w-[220px]">
          <Search className="w-4 h-4 absolute left-3 top-3.5 text-ink-500" />
          <Input value={q} onChange={(e) => { setQ(e.target.value); setPage(1); }} placeholder={t("search_ph")} className="pl-9" />
        </div>
        <Select value={cat} onChange={(e) => { setCat(e.target.value); setPage(1); }} className="w-auto">
          <option value="">{t("all_categories")}</option>
          {meta?.categories.map((c) => <option key={c.slug} value={c.slug}>{p(c.name)}</option>)}
        </Select>
        <Select value={img} onChange={(e) => { setImg(e.target.value); setPage(1); }} className="!w-auto">
          <option value="">{t("img_filter")}: {t("all")}</option>
          <option value="none">{t("img_none")}</option><option value="sample">{t("img_sample")}</option><option value="real">{t("img_real")}</option>
        </Select>
      </div>
      <div className="card mt-4 overflow-hidden">
        {!data ? <div className="py-16 grid place-items-center"><Spinner /></div> : data.results.length === 0 ? <Empty title={t("no_data")} /> : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm min-w-[860px]">
              <thead className="bg-ink-100/60 text-ink-500 text-left">
                <tr><th className="px-4 py-3">{t("name")}</th><th className="px-4 py-3">{t("category")}</th><th className="px-4 py-3 text-right">{t("price")}</th><th className="px-4 py-3">{t("stock")}</th><th className="px-4 py-3 text-right">{t("reserved")}</th><th className="px-4 py-3 text-right">{t("available")}</th><th className="px-4 py-3" /></tr>
              </thead>
              <tbody className="divide-y divide-ink-100">
                {data.results.map((pr) => (
                  <tr key={pr.id} className={clsx(!pr.is_active && "opacity-50")}>
                    <td className="px-4 py-2.5">
                      <div className="flex items-center gap-3">
                        <div className="w-11 h-11 rounded-lg overflow-hidden shrink-0 relative"><ProductImage src={pr.image_url} category={pr.category} icon={meta?.categories.find((c) => c.slug === pr.category)?.icon} />
                          {pr.image_url && pr.image_is_sample && <span title={t("sample_image_hint")} className="absolute bottom-0 inset-x-0 bg-ink-900/60 text-white text-[8px] text-center font-bold">AI</span>}</div>
                        <div className="min-w-0">
                          <div className="font-medium truncate max-w-[280px]">{p(pr.name)}</div>
                          <div className="text-xs text-ink-500 truncate max-w-[280px]">{p(pr.spec)} · {pr.sku}{me.seller.role === "operator" ? ` · ${p(pr.seller.name)}` : ""}</div>
                          {pr.note && <div className="text-xs text-amber-700 truncate max-w-[280px]">{pr.note}</div>}
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-2.5 text-ink-500 text-xs">{p(meta?.categories.find((c) => c.slug === pr.category)?.name)}</td>
                    <td className="px-4 py-2.5 text-right tabular-nums whitespace-nowrap">{pr.price ? money(pr.price) : <Badge tone="amber">{t("price_on_request")}</Badge>}<div className="text-xs text-ink-500">/ {unit(pr.unit)}</div></td>
                    <td className="px-4 py-2.5"><StockCell pr={pr} onSaved={() => { load(); setToast(t("saved")); }} /></td>
                    <td className="px-4 py-2.5 text-right tabular-nums">{pr.reserved}</td>
                    <td className="px-4 py-2.5 text-right tabular-nums font-semibold">{pr.available ?? "∞"}</td>
                    <td className="px-4 py-2.5 text-right whitespace-nowrap">
                      <button onClick={() => toggle(pr)} className="p-2 rounded-lg hover:bg-ink-100" title={pr.is_active ? t("active") : t("hidden")}>{pr.is_active ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}</button>
                      <button onClick={() => openEdit(pr)} className="p-2 rounded-lg hover:bg-ink-100" title={t("edit")}><Pencil className="w-4 h-4" /></button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      {data && data.count > 50 && (
        <div className="flex justify-center gap-2 mt-4">
          <Button size="sm" variant="outline" disabled={!data.previous} onClick={() => setPage(page - 1)}>{t("prev")}</Button>
          <span className="text-sm text-ink-500 self-center">{page} / {Math.ceil(data.count / 50)}</span>
          <Button size="sm" variant="outline" disabled={!data.next} onClick={() => setPage(page + 1)}>{t("next")}</Button>
        </div>
      )}
      <Modal open={!!edit} onClose={() => setEdit(null)} wide title={edit?.id ? t("edit") : t("add_product")}>
        {edit && <Editor initial={edit} onClose={() => setEdit(null)} onSaved={() => { setEdit(null); load(); setToast(t("saved")); }} />}
      </Modal>
      <Modal open={bulk} onClose={() => setBulk(false)} title={t("bulk_images")}>
        <BulkImages onDone={() => load()} />
      </Modal>
      <Toast text={toast} onDone={() => setToast(null)} />
    </div>
  );
}
