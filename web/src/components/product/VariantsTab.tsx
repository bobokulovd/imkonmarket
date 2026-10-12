"use client";
import clsx from "clsx";
import { Check, ImageOff, Layers, Plus, Trash2, Wand2 } from "lucide-react";
import { useMemo, useState } from "react";
import { Badge, Button, Empty, Input, Spinner } from "@/components/ui";
import { api } from "@/lib/api";
import { useApp } from "@/lib/store";
import type { AttributeDef, GalleryImage, SellerProduct, SellerVariant } from "@/lib/types";
import { decimalOnly, digitsOnly, eanCheck, ErrorBox, numStr, type ProductChange, errMsg } from "./shared";

type Row = {
  key: string; id?: number; sku: string; attributes: Record<string, string | number>; barcode: string; price: string;
  stock: string; image: number | null; is_active: boolean; reserved: number; sold: number;
};

let seq = 0;
const comboKey = (a: Record<string, string | number>) => JSON.stringify(Object.keys(a).sort().map((k) => [k, String(a[k])]));
const rowOf = (v: SellerVariant): Row => ({
  key: `v${v.id}`, id: v.id, sku: v.sku, attributes: v.attributes || {}, barcode: v.barcode || "", price: numStr(v.own_price),
  stock: v.stock === null ? "" : String(v.stock), image: v.image, is_active: v.is_active, reserved: v.reserved, sold: v.sold,
});

export default function VariantsTab({ product, defs, onChange }: { product: SellerProduct; defs: AttributeDef[] | null; onChange: ProductChange }) {
  const { t, p, money } = useApp();
  const axes = useMemo(() => (defs || []).filter((d) => d.variant), [defs]);
  const [rows, setRows] = useState<Row[]>(() => (product.variants || []).map(rowOf));
  const [pick, setPick] = useState<Record<string, string[]>>({});
  const [numDraft, setNumDraft] = useState<Record<string, string>>({});
  const [bulk, setBulk] = useState({ price: "", stock: "" });
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [ok, setOk] = useState(false);

  if (!defs) return <div className="py-12 grid place-items-center"><Spinner /></div>;
  if (!axes.length) {
    return <Empty icon={<Layers className="w-7 h-7" />} title={t("pe_var_none_title")} sub={t("pe_var_none_sub")} />;
  }

  const edit = (fn: (rs: Row[]) => Row[]) => { setRows(fn); setDirty(true); setOk(false); };
  const setRow = (key: string, patch: Partial<Row>) => edit((rs) => rs.map((r) => (r.key === key ? { ...r, ...patch } : r)));
  const optName = (d: AttributeDef, v: string | number) => p(d.options.find((o) => o.v === String(v))?.name) || `${v}${d.unit ? ` ${d.unit}` : ""}`;
  const label = (r: Row) => axes.filter((d) => r.attributes[d.code] !== undefined).map((d) => optName(d, r.attributes[d.code])).join(" · ");

  const toggle = (code: string, v: string) => setPick((s) => {
    const cur = s[code] || [];
    return { ...s, [code]: cur.includes(v) ? cur.filter((x) => x !== v) : [...cur, v] };
  });
  const addNum = (d: AttributeDef) => {
    const vals = (numDraft[d.code] || "").split(/[,;\s]+/).map((x) => x.replace(",", ".")).filter((x) => x && Number.isFinite(Number(x)));
    if (!vals.length) return;
    setPick((s) => ({ ...s, [d.code]: Array.from(new Set([...(s[d.code] || []), ...vals.map((x) => String(Number(x)))])) }));
    setNumDraft((s) => ({ ...s, [d.code]: "" }));
  };

  const generate = () => {
    const used = axes.filter((d) => (pick[d.code] || []).length);
    if (!used.length) return;
    let combos: Record<string, string | number>[] = [{}];
    for (const d of used) {
      combos = combos.flatMap((c) => pick[d.code].map((v) => ({ ...c, [d.code]: d.type === "number" ? Number(v) : v })));
    }
    const have = new Set(rows.map((r) => comboKey(r.attributes)));
    const add = combos.filter((c) => !have.has(comboKey(c))).map<Row>((c) => ({
      key: `n${++seq}`, sku: "", attributes: c, barcode: "", price: bulk.price || numStr(product.has_variants ? null : product.price),
      stock: bulk.stock, image: null, is_active: true, reserved: 0, sold: 0,
    }));
    if (add.length) edit((rs) => [...rs, ...add]);
    setPick({});
  };

  const applyBulk = () => edit((rs) => rs.map((r) => ({ ...r, ...(bulk.price ? { price: bulk.price } : {}), ...(bulk.stock ? { stock: bulk.stock } : {}) })));

  const images = product.images || [];
  const badEan = rows.find((r) => eanCheck(r.barcode) !== "ok");
  const save = async () => {
    setBusy(true); setErr(""); setOk(false);
    const body = rows.map((r) => ({
      ...(r.id ? { id: r.id } : {}), sku: r.sku, attributes: r.attributes, barcode: r.barcode, price: r.price === "" ? null : r.price,
      stock: r.stock === "" ? null : Number(r.stock), is_active: r.is_active,
      image: r.image !== null && images.some((i) => i.id === r.image) ? r.image : null, // galereyadan o'chirilgan bo'lsa
    }));
    try {
      const res = await api<{ variants: SellerVariant[]; product: SellerProduct }>(`/seller/products/${product.id}/variants/`, { method: "PUT", json: body, authed: true });
      setRows(res.variants.map(rowOf)); setDirty(false); setOk(true);
      onChange(res.product);
    } catch (e) { setErr(errMsg(e)); } finally { setBusy(false); }
  };

  return (
    <div className="space-y-5">
      <section className="rounded-2xl border border-ink-100 p-4 bg-ink-50/40 space-y-3">
        <div>
          <h3 className="font-bold text-ink-900 flex items-center gap-2"><Wand2 className="w-4 h-4 text-brand-600" />{t("pe_var_gen")}</h3>
          <p className="text-xs text-ink-500 mt-0.5">{t("pe_var_gen_hint")}</p>
        </div>
        {axes.map((d) => (
          <div key={d.code}>
            <div className="text-sm font-medium text-ink-700 mb-1.5">{p(d.name)}{d.unit ? `, ${d.unit}` : ""}</div>
            {d.type === "number" || !d.options.length ? (
              <div className="space-y-2">
                <form className="flex gap-2 max-w-sm" onSubmit={(e) => { e.preventDefault(); addNum(d); }}>
                  <Input value={numDraft[d.code] || ""} onChange={(e) => setNumDraft((s) => ({ ...s, [d.code]: e.target.value }))} placeholder={t("pe_var_num_ph")} />
                  <Button type="submit" variant="outline"><Plus className="w-4 h-4" /></Button>
                </form>
                <div className="flex flex-wrap gap-1.5">
                  {(pick[d.code] || []).map((v) => <Chip key={v} on onClick={() => toggle(d.code, v)}>{v}{d.unit ? ` ${d.unit}` : ""} ×</Chip>)}
                </div>
              </div>
            ) : (
              <div className="flex flex-wrap gap-1.5">
                {d.options.map((o) => <Chip key={o.v} on={(pick[d.code] || []).includes(o.v)} onClick={() => toggle(d.code, o.v)}>{p(o.name) || o.v}</Chip>)}
              </div>
            )}
          </div>
        ))}
        <div className="flex flex-wrap gap-2 items-end pt-1">
          <Button variant="soft" onClick={generate} disabled={!axes.some((d) => (pick[d.code] || []).length)}><Wand2 className="w-4 h-4" />{t("pe_var_generate")}</Button>
        </div>
      </section>

      {rows.length === 0 ? (
        <div className="text-center text-sm text-ink-500 py-6">{t("pe_var_empty")}</div>
      ) : (
        <>
          <div className="flex flex-wrap gap-2 items-center text-sm">
            <span className="text-ink-500">{t("pe_var_bulk")}:</span>
            <input className="h-9 w-32 rounded-lg border border-ink-300 px-2 text-sm" inputMode="decimal" placeholder={t("price")} value={bulk.price} onChange={(e) => setBulk({ ...bulk, price: decimalOnly(e.target.value) })} />
            <input className="h-9 w-24 rounded-lg border border-ink-300 px-2 text-sm" inputMode="numeric" placeholder={t("stock")} value={bulk.stock} onChange={(e) => setBulk({ ...bulk, stock: digitsOnly(e.target.value) })} />
            <Button size="sm" variant="outline" onClick={applyBulk} disabled={!bulk.price && !bulk.stock}>{t("pe_var_apply_all")}</Button>
          </div>
          <div className="overflow-x-auto rounded-xl border border-ink-100">
            <table className="w-full text-sm min-w-[860px]">
              <thead className="bg-ink-100/60 text-ink-500 text-left text-xs">
                <tr>
                  <th className="px-3 py-2">{t("pe_var_variant")}</th>
                  <th className="px-3 py-2">{t("pe_var_photo")}</th>
                  <th className="px-3 py-2">{t("price")}, {t("sum")}</th>
                  <th className="px-3 py-2">{t("stock")}</th>
                  <th className="px-3 py-2">{t("mp_barcode")}</th>
                  <th className="px-3 py-2 text-right">{t("reserved")} / {t("pe_sold")}</th>
                  <th className="px-3 py-2 text-center">{t("active")}</th>
                  <th className="px-3 py-2" />
                </tr>
              </thead>
              <tbody className="divide-y divide-ink-100">
                {rows.map((r) => {
                  const ean = eanCheck(r.barcode);
                  return (
                    <tr key={r.key} className={clsx(!r.is_active && "opacity-60")}>
                      <td className="px-3 py-2">
                        <div className="font-medium">{label(r)}</div>
                        <div className="text-[11px] text-ink-500 font-mono">{r.sku || t("pe_var_sku_auto")}</div>
                      </td>
                      <td className="px-3 py-2"><ImagePick images={images} value={r.image} onChange={(v) => setRow(r.key, { image: v })} /></td>
                      <td className="px-3 py-2">
                        <input className="h-9 w-28 rounded-lg border border-ink-300 px-2 text-right tabular-nums" inputMode="decimal" value={r.price}
                          placeholder={product.price && !product.has_variants ? String(Number(product.price)) : "—"} onChange={(e) => setRow(r.key, { price: decimalOnly(e.target.value) })} />
                      </td>
                      <td className="px-3 py-2">
                        <input className="h-9 w-20 rounded-lg border border-ink-300 px-2 text-right tabular-nums" inputMode="numeric" value={r.stock} placeholder="∞"
                          onChange={(e) => setRow(r.key, { stock: digitsOnly(e.target.value) })} />
                      </td>
                      <td className="px-3 py-2">
                        <input className={clsx("h-9 w-36 rounded-lg border px-2 font-mono text-xs", ean === "ok" ? "border-ink-300" : "border-red-400 bg-red-50")} inputMode="numeric"
                          value={r.barcode} title={ean === "ok" ? "" : ean === "len" ? t("pe_ean_len") : t("pe_ean_bad", { d: ean })}
                          onChange={(e) => setRow(r.key, { barcode: digitsOnly(e.target.value).slice(0, 13) })} />
                      </td>
                      <td className="px-3 py-2 text-right tabular-nums text-ink-500">{r.reserved} / {r.sold}</td>
                      <td className="px-3 py-2 text-center"><input type="checkbox" className="w-4 h-4 accent-brand-600" checked={r.is_active} onChange={(e) => setRow(r.key, { is_active: e.target.checked })} /></td>
                      <td className="px-3 py-2 text-right">
                        <button type="button" className="p-2 rounded-lg text-red-600 hover:bg-red-50" title={t("remove")} onClick={() => edit((rs) => rs.filter((x) => x.key !== r.key))}><Trash2 className="w-4 h-4" /></button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <p className="text-xs text-ink-500">{t("pe_var_note")}</p>
        </>
      )}

      {product.has_variants && (
        <div className="text-sm text-ink-700">
          <Badge tone="blue">{t("pe_var_count", { n: product.variants?.length ?? rows.length })}</Badge>{" "}
          {t("price")}: {product.price ? t("pe_from", { v: money(product.price) }) : "—"} · {t("stock")}: {product.stock ?? "∞"}
        </div>
      )}
      {badEan && <p className="text-xs text-red-600">{t("pe_var_bad_ean", { v: label(badEan) })}</p>}
      <ErrorBox text={err} />
      <div className="flex items-center gap-3 justify-end">
        {ok && <span className="text-sm text-emerald-700 flex items-center gap-1"><Check className="w-4 h-4" />{t("saved")}</span>}
        {dirty && <span className="text-xs text-amber-700">{t("pe_unsaved")}</span>}
        <Button loading={busy} disabled={!dirty || !!badEan} onClick={save}>{t("save")}</Button>
      </div>
    </div>
  );
}

function Chip({ on, children, onClick }: { on?: boolean; children: React.ReactNode; onClick: () => void }) {
  return (
    <button type="button" onClick={onClick}
      className={clsx("px-3 h-8 rounded-full text-sm border transition", on ? "bg-brand-600 border-brand-600 text-white" : "bg-white border-ink-300 text-ink-700 hover:bg-ink-100")}>
      {children}
    </button>
  );
}

function ImagePick({ images, value, onChange }: { images: GalleryImage[]; value: number | null; onChange: (v: number | null) => void }) {
  const { t } = useApp();
  const [open, setOpen] = useState(false);
  const cur = images.find((i) => i.id === value);
  return (
    <div className="relative">
      <button type="button" onClick={() => setOpen(!open)} title={t("pe_var_photo")}
        className="w-10 h-10 rounded-lg border border-ink-300 overflow-hidden grid place-items-center bg-ink-50 hover:border-brand-500">
        {cur ? <img src={cur.url} alt="" className="w-full h-full object-cover" /> : <ImageOff className="w-4 h-4 text-ink-500" />}
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute z-20 left-0 top-11 w-64 rounded-xl border border-ink-100 bg-white shadow-pop p-2">
            {images.length === 0 ? <div className="text-xs text-ink-500 p-2">{t("pe_var_no_photos")}</div> : (
              <div className="grid grid-cols-5 gap-1.5">
                <button type="button" onClick={() => { onChange(null); setOpen(false); }} className={clsx("aspect-square rounded-lg border grid place-items-center", value === null ? "border-brand-500" : "border-ink-100")}>
                  <ImageOff className="w-4 h-4 text-ink-500" />
                </button>
                {images.map((i) => (
                  <button key={i.id} type="button" onClick={() => { onChange(i.id); setOpen(false); }}
                    className={clsx("aspect-square rounded-lg border-2 overflow-hidden", value === i.id ? "border-brand-500" : "border-transparent")}>
                    <img src={i.url} alt="" className="w-full h-full object-cover" />
                  </button>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
