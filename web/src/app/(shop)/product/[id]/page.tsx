"use client";
import { Check, ChevronRight, Clock, Factory, FileSignature, MapPin, ShoppingCart, Truck, Zap } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Price, ProductGrid, StockLine } from "@/components/ProductCard";
import { Button, Empty, ProductImage, Qty, SampleBadge, Spinner } from "@/components/ui";
import { api } from "@/lib/api";
import { useApp, useCart } from "@/lib/store";
import type { ProductDetail } from "@/lib/types";

export default function ProductPage({ params }: { params: { id: string } }) {
  const { t, p, money, unit, meta } = useApp();
  const cart = useCart();
  const router = useRouter();
  const [d, setD] = useState<ProductDetail | null | undefined>(undefined);
  const [qty, setQty] = useState(1);

  useEffect(() => {
    api<ProductDetail>(`/products/${params.id}/`).then((x) => { setD(x); setQty(x.min_order || 1); }).catch(() => setD(null));
  }, [params.id]);

  if (d === undefined) return <div className="py-32 grid place-items-center"><Spinner /></div>;
  if (d === null) return <Empty title={t("not_found")} />;

  const cat = meta?.categories.find((c) => c.slug === d.category);
  const soldOut = d.available !== null && d.available <= 0;
  const inCart = cart.has(d.id);
  const total = d.price ? Number(d.price) * qty : null;
  const specs: [string, React.ReactNode][] = [
    [t("sku"), <span className="font-mono text-sm">{d.sku}</span>],
    [t("unit"), unit(d.unit)],
    [t("specs"), p(d.spec) || "—"],
    [t("produced_at"), p(d.address)],
    [t("daily_capacity"), d.daily_capacity ? `${d.daily_capacity.toLocaleString("ru-RU")} ${unit(d.unit)}` : "—"],
    [t("delivery"), d.delivery ? t("delivery_yes") : t("delivery_no")],
  ];

  return (
    <div className="container-x py-6">
      <nav className="text-sm text-ink-500 flex items-center gap-1 flex-wrap mb-4">
        <Link href="/" className="hover:text-ink-900">{t("home")}</Link><ChevronRight className="w-3.5 h-3.5" />
        <Link href="/catalog" className="hover:text-ink-900">{t("catalog")}</Link><ChevronRight className="w-3.5 h-3.5" />
        <Link href={`/catalog?category=${d.category}`} className="hover:text-ink-900">{p(cat?.name)}</Link>
      </nav>
      <div className="grid lg:grid-cols-[1.1fr_1fr] gap-6 lg:gap-10">
        <div className="card overflow-hidden aspect-[4/3] lg:aspect-square relative">
          <ProductImage src={d.image} category={d.category} icon={cat?.icon} alt={p(d.name)} />
          {d.image && d.image_is_sample && <SampleBadge label={t("sample_image")} hint={t("sample_image_hint")} className="absolute right-3 bottom-3 text-xs" />}
        </div>
        <div>
          <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight leading-tight">{p(d.name)}</h1>
          {p(d.spec) && <div className="text-ink-500 mt-1.5 text-lg">{p(d.spec)}</div>}
          <Link href={`/sellers/${d.seller.code}`} className="mt-3 inline-flex items-center gap-2 text-sm font-semibold text-brand-700 hover:underline">
            <Factory className="w-4 h-4" /> {p(d.seller.name)} · {p(d.seller.region_i18n)}
          </Link>

          <div className="card p-5 mt-5">
            <Price p={d} big />
            <StockLine p={d} className="text-sm font-semibold mt-1 block" />
            {!soldOut && (
              <>
                <div className="flex items-center gap-3 mt-5 flex-wrap">
                  <Qty value={qty} onChange={(v) => setQty(Math.max(d.min_order || 1, d.available != null ? Math.min(v, d.available) : v))} min={d.min_order || 1} max={d.available} />
                  <span className="text-sm text-ink-500">{unit(d.unit)}</span>
                  {total !== null && <span className="ml-auto text-right"><span className="text-xs text-ink-500 block">{t("total")}</span><span className="font-extrabold text-lg tabular-nums">{money(total)}</span></span>}
                </div>
                {d.min_order > 1 && <div className="text-xs text-ink-500 mt-2">{t("min_order", { n: d.min_order })}</div>}
                <div className="grid grid-cols-2 gap-2 mt-5">
                  {inCart ? (
                    <Button variant="soft" size="lg" onClick={() => router.push("/cart")}><Check className="w-5 h-5" /> {t("go_to_cart")}</Button>
                  ) : (
                    <Button size="lg" onClick={() => cart.add(d, qty)}><ShoppingCart className="w-5 h-5" /> {t("add_to_cart")}</Button>
                  )}
                  <Button variant="accent" size="lg" onClick={() => { if (!inCart) cart.add(d, qty); router.push("/checkout"); }}>
                    <Zap className="w-5 h-5" /> {t("buy_now")}
                  </Button>
                </div>
              </>
            )}
            <div className="mt-5 grid gap-2.5 text-sm text-ink-700">
              <div className="flex gap-2.5"><Truck className="w-5 h-5 text-ink-500 shrink-0" /> {d.delivery ? t("delivery_yes") : t("delivery_no")}</div>
              <div className="flex gap-2.5"><Clock className="w-5 h-5 text-ink-500 shrink-0" /> {t("lead_days", { n: d.lead_days })}</div>
              <div className="flex gap-2.5"><FileSignature className="w-5 h-5 text-ink-500 shrink-0" /> {t("price_note")}</div>
              <div className="flex gap-2.5"><MapPin className="w-5 h-5 text-ink-500 shrink-0" /> {p(d.address)}</div>
            </div>
          </div>

          <div className="card mt-5 divide-y divide-ink-100">
            <div className="px-5 py-3 font-bold">{t("specs")}</div>
            {specs.map(([k, v], i) => (
              <div key={i} className="px-5 py-2.5 grid grid-cols-[40%_1fr] gap-3 text-sm">
                <span className="text-ink-500">{k}</span><span className="text-ink-900">{v}</span>
              </div>
            ))}
          </div>
          {p(d.description) && <p className="mt-5 text-ink-700 leading-relaxed whitespace-pre-line">{p(d.description)}</p>}
        </div>
      </div>

      {d.same_seller.length > 0 && (
        <section className="mt-12">
          <h2 className="h-section mb-4">{t("same_seller")}</h2>
          <ProductGrid items={d.same_seller.slice(0, 4)} />
        </section>
      )}
      {d.similar.length > 0 && (
        <section className="mt-12">
          <h2 className="h-section mb-4">{t("similar")}</h2>
          <ProductGrid items={d.similar.slice(0, 8)} />
        </section>
      )}
    </div>
  );
}
