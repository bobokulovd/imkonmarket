"use client";
import clsx from "clsx";
import { Eye, EyeOff, ImagePlus, Pencil, Plus, Search, Receipt } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useMe } from "@/components/CabinetShell";
import BulkImages from "@/components/BulkImages";
import IkpuBulk from "@/components/product/IkpuBulk";
import ProductEditor from "@/components/product/ProductEditor";
import { Badge, Button, Empty, Input, Modal, ProductImage, Select, Spinner, Toast } from "@/components/ui";
import { api, qs } from "@/lib/api";
import { useApp } from "@/lib/store";
import type { Paged, SellerProduct } from "@/lib/types";

/** Mahsulot kartochkasi muharriri — tablar: Asosiy, Rasmlar, Xususiyatlar, Variantlar, Marketplace. */
function Editor({ edit, onSaved, onCreated, onClose }: { edit: EditState; onSaved: () => void; onCreated: (id: number) => void; onClose: () => void }) {
  return <ProductEditor productId={edit.id} defaultCategory={edit.category} onSaved={onSaved} onCreated={onCreated} onClose={onClose} />;
}
type EditState = { id?: number; category: string };

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
  const [ikpu, setIkpu] = useState(false);
  const [page, setPage] = useState(1);
  const [edit, setEdit] = useState<EditState | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  const load = useCallback(() => {
    api<Paged<SellerProduct>>(`/seller/products/${qs({ q, category: cat, image: img, page, page_size: 50 })}`, { authed: true }).then(setData).catch(() => {});
  }, [q, cat, img, page]);
  useEffect(() => { const id = setTimeout(load, 250); return () => clearTimeout(id); }, [load]);

  const openEdit = (pr: SellerProduct) => setEdit({ id: pr.id, category: pr.category });
  const toggle = async (pr: SellerProduct) => {
    await api(`/seller/products/${pr.id}/`, { method: "PATCH", json: { is_active: !pr.is_active }, authed: true });
    load();
  };

  return (
    <div>
      <div className="flex flex-wrap gap-3 items-center justify-between">
        <h1 className="text-2xl font-extrabold">{t("my_products")} {data && <span className="text-ink-500 text-lg">· {data.count}</span>}</h1>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => setIkpu(true)}><Receipt className="w-4 h-4" /> {t("ik_bulk")}</Button>
          <Button variant="outline" onClick={() => setBulk(true)}><ImagePlus className="w-4 h-4" /> {t("bulk_images")}</Button>
          <Button onClick={() => setEdit({ category: meta?.categories[0]?.slug || "mebel" })}><Plus className="w-4 h-4" /> {t("add_product")}</Button>
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
                          {pr.has_variants && <Badge tone="blue" className="mt-0.5">{t("pe_list_variants", { n: pr.variants?.length ?? 0 })}</Badge>}
                          {pr.note && <div className="text-xs text-amber-700 truncate max-w-[280px]">{pr.note}</div>}
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-2.5 text-ink-500 text-xs">{p(meta?.categories.find((c) => c.slug === pr.category)?.name)}</td>
                    <td className="px-4 py-2.5 text-right tabular-nums whitespace-nowrap">{pr.price ? money(pr.price) : <Badge tone="amber">{t("price_on_request")}</Badge>}<div className="text-xs text-ink-500">/ {unit(pr.unit)}</div></td>
                    <td className="px-4 py-2.5">{pr.has_variants
                      ? <span className="inline-flex items-center gap-1 h-8 px-2 rounded-lg bg-ink-100/70 text-ink-700 tabular-nums text-sm" title={t("pe_list_stock_variants_hint")}>Σ {pr.stock ?? "∞"}</span>
                      : <StockCell pr={pr} onSaved={() => { load(); setToast(t("saved")); }} />}</td>
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
        {edit && <Editor edit={edit} onClose={() => setEdit(null)} onSaved={() => { load(); setToast(t("saved")); }}
          onCreated={(id) => setEdit((e) => (e ? { ...e, id } : e))} />}
      </Modal>
      <Modal open={ikpu} onClose={() => setIkpu(false)} title={t("ik_bulk")}>
        <IkpuBulk onDone={() => load()} />
      </Modal>
      <Modal open={bulk} onClose={() => setBulk(false)} title={t("bulk_images")}>
        <BulkImages onDone={() => load()} />
      </Modal>
      <Toast text={toast} onDone={() => setToast(null)} />
    </div>
  );
}
