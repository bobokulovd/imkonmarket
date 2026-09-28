"use client";
import clsx from "clsx";
import { ChevronLeft, ChevronRight, SlidersHorizontal, X } from "lucide-react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useState } from "react";
import { ProductGrid, ProductSkeleton } from "@/components/ProductCard";
import { Button, CatIcon, Empty, Select } from "@/components/ui";
import { api, qs } from "@/lib/api";
import { useApp } from "@/lib/store";
import type { Facets, Paged, Product } from "@/lib/types";

const PAGE = 24;

function Check({ checked, onChange, label, count }: { checked: boolean; onChange: (v: boolean) => void; label: React.ReactNode; count?: number }) {
  return (
    <label className="flex items-center gap-2.5 py-1.5 cursor-pointer group">
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} className="w-4 h-4 rounded accent-brand-600" />
      <span className="flex-1 text-sm text-ink-700 group-hover:text-ink-900 leading-tight">{label}</span>
      {count !== undefined && <span className="text-xs text-ink-500 tabular-nums">{count}</span>}
    </label>
  );
}

function Filters({ params, set, facets }: { params: URLSearchParams; set: (k: string, v: string | null) => void; facets?: Facets }) {
  const { t, p, meta } = useApp();
  const list = (k: string) => (params.get(k) || "").split(",").filter(Boolean);
  const toggle = (k: string, v: string, on: boolean) => {
    const cur = new Set(list(k));
    on ? cur.add(v) : cur.delete(v);
    set(k, Array.from(cur).join(",") || null);
  };
  const [minP, setMinP] = useState(params.get("min_price") || "");
  const [maxP, setMaxP] = useState(params.get("max_price") || "");
  useEffect(() => { setMinP(params.get("min_price") || ""); setMaxP(params.get("max_price") || ""); }, [params]);
  const sellersWith = (meta?.sellers || []).filter((s) => (facets?.sellers?.[s.code] ?? s.product_count) > 0);
  return (
    <div className="space-y-6">
      <div>
        <div className="font-bold text-ink-900 mb-2">{t("categories")}</div>
        {meta?.categories.map((c) => (
          <Check key={c.slug} checked={list("category").includes(c.slug)} onChange={(v) => toggle("category", c.slug, v)}
            label={<span className="inline-flex items-center gap-2"><CatIcon icon={c.icon} className="w-4 h-4 text-ink-500" />{p(c.name)}</span>}
            count={facets?.categories?.[c.slug] ?? c.count} />
        ))}
      </div>
      <div>
        <div className="font-bold text-ink-900 mb-2">{t("price")}, {t("sum")}</div>
        <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); set("min_price", minP || null); set("max_price", maxP || null); }}>
          <input value={minP} onChange={(e) => setMinP(e.target.value.replace(/\D/g, ""))} placeholder={t("price_from")} inputMode="numeric"
            className="w-full h-10 rounded-lg border border-ink-300 px-3 text-sm outline-none focus:border-brand-500" />
          <input value={maxP} onChange={(e) => setMaxP(e.target.value.replace(/\D/g, ""))} placeholder={t("price_to")} inputMode="numeric"
            className="w-full h-10 rounded-lg border border-ink-300 px-3 text-sm outline-none focus:border-brand-500" />
          <button className="h-10 px-3 rounded-lg bg-ink-100 font-semibold text-sm">OK</button>
        </form>
      </div>
      <div>
        <Check checked={params.get("in_stock") === "1"} onChange={(v) => set("in_stock", v ? "1" : null)} label={t("only_in_stock")} />
        <Check checked={params.get("delivery") === "1"} onChange={(v) => set("delivery", v ? "1" : null)} label={t("with_delivery")} />
        <Check checked={params.get("priced") === "1"} onChange={(v) => set("priced", v ? "1" : null)} label={t("only_priced")} />
      </div>
      <div>
        <div className="font-bold text-ink-900 mb-2">{t("region")}</div>
        {meta?.regions.filter((r) => (facets?.regions?.[r.key] ?? 1) > 0).map((r) => (
          <Check key={r.key} checked={list("region").includes(r.key)} onChange={(v) => toggle("region", r.key, v)} label={p(r.name)} count={facets?.regions?.[r.key]} />
        ))}
      </div>
      <div>
        <div className="font-bold text-ink-900 mb-2">{t("sellers")}</div>
        <div className="max-h-64 overflow-y-auto pr-1">
          {sellersWith.map((s) => (
            <Check key={s.code} checked={list("seller").includes(s.code)} onChange={(v) => toggle("seller", s.code, v)} label={p(s.name)} count={facets?.sellers?.[s.code]} />
          ))}
        </div>
      </div>
    </div>
  );
}

function CatalogInner() {
  const { t, p, meta } = useApp();
  const router = useRouter();
  const pathname = usePathname();
  const sp = useSearchParams();
  const [data, setData] = useState<Paged<Product> | null>(null);
  const [loading, setLoading] = useState(true);
  const [drawer, setDrawer] = useState(false);
  const page = parseInt(sp.get("page") || "1", 10);

  const set = (k: string, v: string | null) => {
    const n = new URLSearchParams(sp.toString());
    v ? n.set(k, v) : n.delete(k);
    if (k !== "page") n.delete("page");
    router.replace(`${pathname}?${n.toString()}`, { scroll: k === "page" });
  };

  const query = sp.toString();
  useEffect(() => {
    setLoading(true);
    const params = Object.fromEntries(new URLSearchParams(query));
    api<Paged<Product>>(`/products/${qs({ ordering: "featured", ...params, facets: 1, page_size: PAGE })}`)
      .then(setData).catch(() => setData({ count: 0, next: null, previous: null, results: [] }))
      .finally(() => setLoading(false));
  }, [query]);

  const activeCats = (sp.get("category") || "").split(",").filter(Boolean);
  const title = activeCats.length === 1 ? p(meta?.categories.find((c) => c.slug === activeCats[0])?.name) : sp.get("q") ? `«${sp.get("q")}»` : t("catalog");
  const pages = data ? Math.ceil(data.count / PAGE) : 1;
  const chips = useMemo(() => {
    const out: { k: string; v: string; label: string }[] = [];
    (sp.get("category") || "").split(",").filter(Boolean).forEach((v) => out.push({ k: "category", v, label: p(meta?.categories.find((c) => c.slug === v)?.name) }));
    (sp.get("region") || "").split(",").filter(Boolean).forEach((v) => out.push({ k: "region", v, label: p(meta?.regions.find((r) => r.key === v)?.name) }));
    (sp.get("seller") || "").split(",").filter(Boolean).forEach((v) => out.push({ k: "seller", v, label: p(meta?.sellers.find((s) => s.code === v)?.name) }));
    if (sp.get("q")) out.push({ k: "q", v: sp.get("q")!, label: `«${sp.get("q")}»` });
    return out;
  }, [sp, meta, p]);
  const removeChip = (k: string, v: string) => {
    if (k === "q") return set("q", null);
    const rest = (sp.get(k) || "").split(",").filter((x) => x && x !== v);
    set(k, rest.join(",") || null);
  };

  return (
    <div className="container-x py-6">
      <div className="flex items-end justify-between gap-4 mb-4">
        <div>
          <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight">{title}</h1>
          <div className="text-ink-500 text-sm mt-1">{data ? t("found", { n: data.count }) : t("loading")}</div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" className="lg:hidden" onClick={() => setDrawer(true)}><SlidersHorizontal className="w-4 h-4" /> {t("filters")}</Button>
          <Select value={sp.get("ordering") || "featured"} onChange={(e) => set("ordering", e.target.value)} className="w-auto h-10 text-sm">
            <option value="featured">{t("sort_popular")}</option>
            <option value="price">{t("sort_price_asc")}</option>
            <option value="-price">{t("sort_price_desc")}</option>
            <option value="new">{t("sort_new")}</option>
          </Select>
        </div>
      </div>
      {chips.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-4">
          {chips.map((c) => (
            <button key={c.k + c.v} onClick={() => removeChip(c.k, c.v)} className="inline-flex items-center gap-1.5 rounded-full bg-brand-50 text-brand-700 px-3 py-1 text-sm font-medium hover:bg-brand-100">
              {c.label} <X className="w-3.5 h-3.5" />
            </button>
          ))}
          <button onClick={() => router.replace(pathname)} className="text-sm text-ink-500 hover:text-ink-900 px-2">{t("reset")}</button>
        </div>
      )}
      <div className="grid lg:grid-cols-[260px_1fr] gap-6">
        <aside className="hidden lg:block">
          <div className="card p-5 sticky top-28 max-h-[calc(100vh-8rem)] overflow-y-auto">
            <Filters params={sp as any} set={set} facets={data?.facets} />
          </div>
        </aside>
        <div>
          {loading && !data ? <ProductSkeleton n={12} /> : data && data.results.length ? (
            <div className={clsx(loading && "opacity-60 transition")}>
              <ProductGrid items={data.results} cols={3} />
            </div>
          ) : <Empty title={t("nothing_found")} action={<Button variant="soft" onClick={() => router.replace(pathname)}>{t("reset")}</Button>} />}
          {pages > 1 && (
            <div className="flex items-center justify-center gap-2 mt-8">
              <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => set("page", String(page - 1))}><ChevronLeft className="w-4 h-4" /> {t("prev")}</Button>
              <span className="text-sm text-ink-500 px-3 tabular-nums">{page} / {pages}</span>
              <Button variant="outline" size="sm" disabled={page >= pages} onClick={() => set("page", String(page + 1))}>{t("next")} <ChevronRight className="w-4 h-4" /></Button>
            </div>
          )}
        </div>
      </div>

      {drawer && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div className="absolute inset-0 bg-ink-900/50" onClick={() => setDrawer(false)} />
          <div className="absolute inset-y-0 left-0 w-[88%] max-w-sm bg-white flex flex-col">
            <div className="flex items-center justify-between px-5 h-14 border-b border-ink-100">
              <span className="font-bold">{t("filters")}</span>
              <button onClick={() => setDrawer(false)}><X className="w-5 h-5" /></button>
            </div>
            <div className="flex-1 overflow-y-auto p-5"><Filters params={sp as any} set={set} facets={data?.facets} /></div>
            <div className="p-4 border-t border-ink-100 grid grid-cols-2 gap-2">
              <Button variant="outline" onClick={() => router.replace(pathname)}>{t("reset")}</Button>
              <Button onClick={() => setDrawer(false)}>{t("show_results")} ({data?.count ?? 0})</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function CatalogPage() {
  return <Suspense><CatalogInner /></Suspense>;
}
