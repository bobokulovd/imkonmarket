"use client";
import { Check, ChevronRight, Clock, Factory, FileSignature, MapPin, ShoppingCart, Truck, Zap } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { Price, ProductGrid, StockLine } from "@/components/ProductCard";
import Gallery, { type GalleryItem } from "@/components/shop/Gallery";
import VariantPicker, { initialSelection, matchVariant, type Selection } from "@/components/shop/VariantPicker";
import { Button, Empty, Qty, Spinner } from "@/components/ui";
import { api } from "@/lib/api";
import { useApp, useCart, withVariant } from "@/lib/store";
import type { ProductDetail } from "@/lib/types";

const num = (v: string | null | undefined) => (v === null || v === undefined || v === "" ? null : Number(v));
const fmtNum = (n: number) => n.toLocaleString("ru-RU", { maximumFractionDigits: 2 }).replace(/ /g, " ");

export default function ProductPage({ params }: { params: { id: string } }) {
  const { t, p, money, unit, meta } = useApp();
  const cart = useCart();
  const router = useRouter();
  const [d, setD] = useState<ProductDetail | null | undefined>(undefined);
  const [qty, setQty] = useState(1);
  const [sel, setSel] = useState<Selection>({});
  const [img, setImg] = useState(0);

  useEffect(() => {
    let want: number | null = null;
    try { want = Number(new URLSearchParams(window.location.search).get("variant")) || null; } catch {}
    api<ProductDetail>(`/products/${params.id}/`).then((x) => {
      setD(x);
      setQty(x.min_order || 1);
      setImg(0);
      setSel(x.variants?.length ? initialSelection(x.variants, x.variant_axes || [], want) : {});
    }).catch(() => setD(null));
  }, [params.id]);

  const variants = d?.variants || [];
  const axes = d?.variant_axes || [];
  const hasVariants = variants.length > 0;
  const variant = hasVariants ? matchVariant(variants, axes, sel) : null;

  // galereya: mahsulot rasmlari; variant rasmi galereyada bo'lmasa — boshiga qo'shiladi
  const gallery = useMemo<GalleryItem[]>(() => {
    if (!d) return [];
    const list: GalleryItem[] = (d.images || []).slice().sort((a, b) => a.order - b.order).map((im) => ({ key: im.id, url: im.url, is_sample: im.is_sample }));
    if (!list.length && d.image) list.push({ key: "main", url: d.image, is_sample: d.image_is_sample });
    const extra = variants.filter((v) => v.image_url && !list.some((x) => x.url === v.image_url) && !(v.image && list.some((x) => x.key === v.image)));
    extra.forEach((v) => list.push({ key: `v${v.id}`, url: v.image_url! }));
    return list;
  }, [d]); // eslint-disable-line react-hooks/exhaustive-deps

  // variant almashganda — uning rasmiga o'tamiz, miqdorni qoldiqqa moslaymiz
  useEffect(() => {
    if (!variant || !d) return;
    const i = gallery.findIndex((g) => (variant.image != null && g.key === variant.image) || (variant.image_url && g.url === variant.image_url));
    if (i >= 0) setImg(i);
    setQty((q) => {
      const min = d.min_order || 1;
      let v = Math.max(q, min);
      if (variant.available !== null) v = Math.min(v, Math.max(variant.available, min));
      return v;
    });
  }, [variant?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  if (d === undefined) return <div className="py-32 grid place-items-center"><Spinner /></div>;
  if (d === null) return <Empty title={t("not_found")} />;

  const cat = meta?.categories.find((c) => c.slug === d.category);
  const view = withVariant(d, variant); // narx/qoldiq/SKU — tanlangan variantdan
  const needPick = hasVariants && !variant;
  const soldOut = view.available !== null && view.available <= 0;
  const inCart = cart.has(d.id, variant?.id ?? null);
  const total = view.price && !needPick ? Number(view.price) * qty : null;
  const min = d.min_order || 1;
  const clamp = (v: number) => Math.max(min, view.available != null ? Math.min(v, view.available) : v);
  const addToCart = () => cart.add(d, qty, variant);

  const dims = [num(d.length_cm), num(d.width_cm), num(d.height_cm)];
  const specs: [string, React.ReactNode][] = [];
  if (d.brand) specs.push([t("mp_brand"), d.brand]);
  if (d.country) specs.push([t("sv_country"), d.country]);
  (d.characteristics || []).forEach((c) => { const v = p(c.value); if (v) specs.push([p(c.name), v]); });
  specs.push(
    [t("sku"), <span key="sku" className="font-mono text-sm">{view.sku}</span>],
    [t("unit"), unit(d.unit)],
  );
  if (p(d.spec)) specs.push([t("specs"), p(d.spec)]);
  specs.push(
    [t("produced_at"), p(d.address)],
    [t("daily_capacity"), d.daily_capacity ? `${d.daily_capacity.toLocaleString("ru-RU")} ${unit(d.unit)}` : "—"],
    [t("delivery"), d.delivery ? t("delivery_yes") : t("delivery_no")],
  );
  if (num(d.weight_kg)) specs.push([t("sv_pkg_weight"), `${fmtNum(num(d.weight_kg)!)} ${t("sv_kg")}`]);
  if (dims.every((x) => x)) specs.push([t("sv_pkg_dims"), `${dims.map((x) => fmtNum(x!)).join(" × ")} ${t("sv_cm")}`]);
  if (d.ikpu) specs.push([t("sv_ikpu"), <span key="ikpu" className="font-mono text-sm">{d.ikpu}</span>]);

  return (
    <div className="container-x py-6">
      <nav className="text-sm text-ink-500 flex items-center gap-1 flex-wrap mb-4" aria-label="breadcrumb">
        <Link href="/" className="hover:text-ink-900">{t("home")}</Link><ChevronRight className="w-3.5 h-3.5" />
        <Link href="/catalog" className="hover:text-ink-900">{t("catalog")}</Link><ChevronRight className="w-3.5 h-3.5" />
        <Link href={`/catalog?category=${d.category}`} className="hover:text-ink-900">{p(cat?.name)}</Link>
      </nav>
      <div className="grid lg:grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)] gap-6 lg:gap-10">
        <div className="lg:sticky lg:top-24 self-start w-full">
          <Gallery items={gallery} active={img} onChange={setImg} alt={p(d.name)} category={d.category} icon={cat?.icon} />
        </div>
        <div className="min-w-0">
          {d.brand && <div className="text-sm font-semibold text-brand-700">{d.brand}</div>}
          <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight leading-tight">{p(d.name)}</h1>
          {p(d.spec) && <div className="text-ink-500 mt-1.5 text-lg">{p(d.spec)}</div>}
          <Link href={`/sellers/${d.seller.code}`} className="mt-3 inline-flex items-center gap-2 text-sm font-semibold text-brand-700 hover:underline">
            <Factory className="w-4 h-4" /> {p(d.seller.name)} · {p(d.seller.region_i18n)}
          </Link>

          <div className="card p-5 mt-5">
            <Price p={view} big from={needPick} />
            {!needPick && <StockLine p={view} className="text-sm font-semibold mt-1 block" />}
            {variant && <div className="text-xs text-ink-500 mt-1">{t("sku")}: <span className="font-mono">{variant.sku}</span></div>}

            {hasVariants && (
              <div className="mt-5 pt-5 border-t border-ink-100">
                <VariantPicker variants={variants} axes={axes} sel={sel} onChange={setSel} />
                {needPick && <div className="text-sm text-amber-700 mt-3">{t("sv_pick_variant_hint")}</div>}
              </div>
            )}

            {!soldOut && !needPick && (
              <>
                <div className="flex items-center gap-3 mt-5 flex-wrap">
                  <Qty value={qty} onChange={(v) => setQty(clamp(v))} min={min} max={view.available} />
                  <span className="text-sm text-ink-500">{unit(d.unit)}</span>
                  {total !== null && <span className="ml-auto text-right"><span className="text-xs text-ink-500 block">{t("total")}</span><span className="font-extrabold text-lg tabular-nums">{money(total)}</span></span>}
                </div>
                {min > 1 && <div className="text-xs text-ink-500 mt-2">{t("min_order", { n: min })}</div>}
                <div className="grid grid-cols-2 gap-2 mt-5">
                  {inCart ? (
                    <Button variant="soft" size="lg" onClick={() => router.push("/cart")}><Check className="w-5 h-5" /> {t("go_to_cart")}</Button>
                  ) : (
                    <Button size="lg" onClick={addToCart}><ShoppingCart className="w-5 h-5" /> {t("add_to_cart")}</Button>
                  )}
                  <Button variant="accent" size="lg" onClick={() => { if (!inCart) addToCart(); router.push("/checkout"); }}>
                    <Zap className="w-5 h-5" /> {t("buy_now")}
                  </Button>
                </div>
              </>
            )}
            {soldOut && !needPick && hasVariants && <div className="mt-4 text-sm text-ink-500">{t("sv_variant_soldout")}</div>}
            <div className="mt-5 grid gap-2.5 text-sm text-ink-700">
              <div className="flex gap-2.5"><Truck className="w-5 h-5 text-ink-500 shrink-0" /> {d.delivery ? t("delivery_yes") : t("delivery_no")}</div>
              <div className="flex gap-2.5"><Clock className="w-5 h-5 text-ink-500 shrink-0" /> {t("lead_days", { n: d.lead_days })}</div>
              <div className="flex gap-2.5"><FileSignature className="w-5 h-5 text-ink-500 shrink-0" /> {t("price_note")}</div>
              <div className="flex gap-2.5"><MapPin className="w-5 h-5 text-ink-500 shrink-0" /> {p(d.address)}</div>
            </div>
          </div>
        </div>
      </div>

      <div className="grid lg:grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)] gap-6 lg:gap-10 mt-8">
        <section className="card overflow-hidden self-start" aria-labelledby="specs-h">
          <h2 id="specs-h" className="px-5 py-4 font-bold text-lg border-b border-ink-100">{t("sv_characteristics")}</h2>
          <dl className="divide-y divide-ink-100">
            {specs.map(([k, v], i) => (
              <div key={i} className="px-5 py-2.5 grid grid-cols-[minmax(0,42%)_1fr] gap-3 text-sm">
                <dt className="text-ink-500">{k}</dt><dd className="text-ink-900 break-words">{v}</dd>
              </div>
            ))}
          </dl>
        </section>
        {p(d.description) && (
          <section className="card p-5 self-start" aria-labelledby="desc-h">
            <h2 id="desc-h" className="font-bold text-lg mb-3">{t("sv_description")}</h2>
            <p className="text-ink-700 leading-relaxed whitespace-pre-line">{p(d.description)}</p>
          </section>
        )}
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
