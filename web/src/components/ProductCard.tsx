"use client";
import clsx from "clsx";
import { Check, MapPin, ShoppingCart, Truck } from "lucide-react";
import Link from "next/link";
import { useApp, useCart } from "@/lib/store";
import type { Product } from "@/lib/types";
import { ProductImage, SampleBadge } from "./ui";

export function StockLine({ p, className }: { p: Product; className?: string }) {
  const { t, unit } = useApp();
  if (p.available === null || p.available === undefined)
    return <span className={clsx("text-violet-700", className)}>{t("made_to_order")}</span>;
  if (p.available <= 0) return <span className={clsx("text-red-600", className)}>{t("out_of_stock")}</span>;
  return (
    <span className={clsx("text-emerald-700", className)}>
      {t("in_stock", { n: p.available.toLocaleString("ru-RU").replace(/ /g, " "), unit: unit(p.unit) })}
    </span>
  );
}

export function Price({ p, big }: { p: Product; big?: boolean }) {
  const { t, money, unit } = useApp();
  if (!p.price) return <div className={clsx("font-bold text-ink-700", big ? "text-2xl" : "text-[15px]")}>{t("price_on_request")}</div>;
  return (
    <div className="flex items-baseline gap-1 flex-wrap">
      <span className={clsx("font-extrabold text-ink-900 tabular-nums", big ? "text-3xl" : "text-lg")}>{money(p.price)}</span>
      <span className={clsx("text-ink-500", big ? "text-base" : "text-xs")}>{t("per_unit", { unit: unit(p.unit) })}</span>
    </div>
  );
}

export default function ProductCard({ p }: { p: Product }) {
  const { t, p: pick, meta } = useApp();
  const cart = useCart();
  const icon = meta?.categories.find((c) => c.slug === p.category)?.icon;
  const inCart = cart.has(p.id);
  const soldOut = p.available !== null && p.available !== undefined && p.available <= 0;
  const spec = pick(p.spec);
  return (
    <div className="group bg-white rounded-2xl border border-ink-100 shadow-card hover:shadow-pop hover:-translate-y-0.5 transition flex flex-col overflow-hidden">
      <Link href={`/product/${p.id}`} className="block aspect-[4/3] relative">
        <ProductImage src={p.image} category={p.category} icon={icon} alt={pick(p.name)} />
        {p.image && p.image_is_sample && <SampleBadge label={t("sample_image")} hint={t("sample_image_hint")} className="absolute right-2 bottom-2" />}
        {p.delivery && (
          <span className="absolute left-2 top-2 inline-flex items-center gap-1 rounded-lg bg-white/90 backdrop-blur px-2 py-1 text-[11px] font-semibold text-ink-700">
            <Truck className="w-3.5 h-3.5" /> {t("delivery")}
          </span>
        )}
      </Link>
      <div className="p-3.5 flex flex-col flex-1">
        <Price p={p} />
        <Link href={`/product/${p.id}`} className="mt-1 font-semibold text-ink-900 leading-snug line-clamp-2 hover:text-brand-700">
          {pick(p.name)}
        </Link>
        {spec && <div className="text-sm text-ink-500 line-clamp-1 mt-0.5">{spec}</div>}
        <div className="mt-2 flex items-center gap-1 text-xs text-ink-500">
          <MapPin className="w-3.5 h-3.5 shrink-0" />
          <span className="truncate">{pick(p.seller.name)} · {pick(p.seller.region_i18n)}</span>
        </div>
        <StockLine p={p} className="text-xs font-semibold mt-1" />
        <div className="mt-auto pt-3">
          <button
            disabled={soldOut}
            onClick={() => (inCart ? null : cart.add(p, p.min_order || 1))}
            className={clsx(
              "w-full h-10 rounded-xl text-sm font-semibold inline-flex items-center justify-center gap-2 transition",
              inCart ? "bg-emerald-50 text-emerald-700" : "bg-brand-600 text-white hover:bg-brand-700",
              soldOut && "opacity-40 pointer-events-none",
            )}
          >
            {inCart ? <><Check className="w-4 h-4" /> {t("in_cart")}</> : <><ShoppingCart className="w-4 h-4" /> {t("add_to_cart")}</>}
          </button>
        </div>
      </div>
    </div>
  );
}

export function ProductGrid({ items, cols = 4 }: { items: Product[]; cols?: 4 | 5 | 3 }) {
  return (
    <div className={clsx("grid grid-cols-2 gap-3 sm:gap-4", cols === 5 ? "md:grid-cols-4 xl:grid-cols-5" : cols === 3 ? "md:grid-cols-3" : "md:grid-cols-3 lg:grid-cols-4")}>
      {items.map((p) => <ProductCard key={p.id} p={p} />)}
    </div>
  );
}

export function ProductSkeleton({ n = 8 }: { n?: number }) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3 sm:gap-4">
      {Array.from({ length: n }).map((_, i) => (
        <div key={i} className="bg-white rounded-2xl border border-ink-100 overflow-hidden animate-pulse">
          <div className="aspect-[4/3] bg-ink-100" />
          <div className="p-3.5 space-y-2"><div className="h-5 bg-ink-100 rounded w-1/2" /><div className="h-4 bg-ink-100 rounded" /><div className="h-4 bg-ink-100 rounded w-2/3" /><div className="h-10 bg-ink-100 rounded-xl mt-3" /></div>
        </div>
      ))}
    </div>
  );
}
