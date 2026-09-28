"use client";
import { ArrowRight, BadgeCheck, Building2, ClipboardList, CreditCard, FileSignature, MapPin, ShieldCheck, Truck } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { ProductGrid, ProductSkeleton } from "@/components/ProductCard";
import { CAT_TONE, CatIcon } from "@/components/ui";
import { api } from "@/lib/api";
import { useApp } from "@/lib/store";
import type { Paged, Product } from "@/lib/types";

function useProducts(query: string) {
  const [items, setItems] = useState<Product[] | null>(null);
  useEffect(() => {
    api<Paged<Product>>(`/products/${query}`).then((r) => setItems(r.results)).catch(() => setItems([]));
  }, [query]);
  return items;
}

function Section({ title, href, children, sub }: { title: string; href?: string; children: React.ReactNode; sub?: string }) {
  const { t } = useApp();
  return (
    <section className="container-x mt-12">
      <div className="flex items-end justify-between mb-4 gap-4">
        <div>
          <h2 className="h-section">{title}</h2>
          {sub && <p className="text-ink-500 mt-1 text-sm md:text-base">{sub}</p>}
        </div>
        {href && <Link href={href} className="text-brand-700 font-semibold text-sm inline-flex items-center gap-1 shrink-0 hover:gap-2 transition-all">{t("see_all")} <ArrowRight className="w-4 h-4" /></Link>}
      </div>
      {children}
    </section>
  );
}

export default function HomePage() {
  const { t, p, meta } = useApp();
  const popular = useProducts("?ordering=featured&priced=1&page_size=10");
  const schools = useProducts("?category=talim-mebeli&priced=1&page_size=8");
  const build = useProducts("?category=qurilish,temir-beton&priced=1&in_stock=1&page_size=8&ordering=featured");
  const cats = meta?.categories || [];
  const promo = ["talim-mebeli", "qurilish", "mebel", "suvenir"].map((s) => cats.find((c) => c.slug === s)).filter(Boolean) as typeof cats;

  return (
    <div>
      {/* HERO */}
      <section className="bg-gradient-to-b from-brand-900 via-brand-800 to-brand-700 text-white">
        <div className="container-x py-10 md:py-16 grid lg:grid-cols-[1.1fr_1fr] gap-10 items-center">
          <div>
            <span className="inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1 text-xs font-semibold text-brand-100">
              <ShieldCheck className="w-4 h-4" /> Click · Payme · {t("pay_bank")}
            </span>
            <h1 className="mt-4 text-3xl md:text-5xl font-extrabold tracking-tight leading-[1.1]">{t("hero_title")}</h1>
            <p className="mt-4 text-brand-100 text-base md:text-lg max-w-xl">{t("hero_sub")}</p>
            <div className="mt-7 flex flex-wrap gap-3">
              <Link href="/catalog" className="h-12 px-6 rounded-xl bg-accent-500 hover:bg-accent-600 font-bold inline-flex items-center gap-2 shadow-lg shadow-black/10">
                {t("hero_cta")} <ArrowRight className="w-5 h-5" />
              </Link>
              <Link href="/catalog?category=talim-mebeli" className="h-12 px-6 rounded-xl bg-white/10 hover:bg-white/20 font-semibold inline-flex items-center gap-2">
                <Building2 className="w-5 h-5" /> {t("hero_cta2")}
              </Link>
            </div>
            <div className="mt-9 grid grid-cols-3 gap-4 max-w-lg">
              {[
                [meta?.stats.products ?? "—", t("stat_products")],
                [meta?.stats.sellers ?? "—", t("stat_sellers")],
                [meta?.stats.regions ?? "—", t("stat_regions")],
              ].map(([n, l], i) => (
                <div key={i}>
                  <div className="text-2xl md:text-3xl font-extrabold tabular-nums">{n}</div>
                  <div className="text-xs md:text-sm text-brand-200 leading-tight">{l}</div>
                </div>
              ))}
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3 md:gap-4">
            {promo.map((c, i) => {
              const tone = CAT_TONE[c.slug];
              return (
                <Link key={c.slug} href={`/catalog?category=${c.slug}`}
                  className={`rounded-2xl p-4 md:p-5 flex flex-col justify-between min-h-[140px] md:min-h-[170px] hover:scale-[1.02] transition shadow-lg shadow-black/10 ${i === 0 ? "row-span-1" : ""}`}
                  style={{ background: `linear-gradient(135deg, ${tone[0]}, ${tone[1]})` }}>
                  <CatIcon icon={c.icon} className="w-9 h-9 md:w-11 md:h-11" color={tone[2]} />
                  <div>
                    <div className="font-bold text-ink-900 leading-tight">{p(c.name)}</div>
                    <div className="text-sm mt-0.5" style={{ color: tone[2] }}>{t("products_n", { n: c.count })}</div>
                  </div>
                </Link>
              );
            })}
          </div>
        </div>
      </section>

      {/* KATEGORIYALAR */}
      <section className="container-x -mt-6 relative">
        <div className="card p-3 md:p-4 flex gap-2 overflow-x-auto no-scrollbar">
          {cats.map((c) => {
            const tone = CAT_TONE[c.slug];
            return (
              <Link key={c.slug} href={`/catalog?category=${c.slug}`}
                className="shrink-0 w-[112px] md:w-[124px] rounded-xl p-2.5 hover:bg-ink-100 text-center transition">
                <span className="mx-auto w-12 h-12 rounded-2xl grid place-items-center" style={{ background: tone?.[0] }}>
                  <CatIcon icon={c.icon} className="w-6 h-6" color={tone?.[2]} />
                </span>
                <div className="mt-2 text-[12.5px] font-medium leading-tight text-ink-900 line-clamp-2">{p(c.name)}</div>
              </Link>
            );
          })}
        </div>
      </section>

      <Section title={t("popular")} href="/catalog">
        {popular ? <ProductGrid items={popular} cols={5} /> : <ProductSkeleton n={10} />}
      </Section>

      {/* MAKTABLAR */}
      <section className="container-x mt-14">
        <div className="rounded-3xl bg-gradient-to-r from-sky-50 to-brand-50 border border-brand-100 p-5 md:p-8">
          <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4 mb-5">
            <div className="max-w-2xl">
              <h2 className="h-section">{t("schools_title")}</h2>
              <p className="text-ink-700 mt-1.5">{t("schools_sub")}</p>
            </div>
            <Link href="/catalog?category=talim-mebeli" className="h-11 px-5 rounded-xl bg-brand-600 text-white font-semibold inline-flex items-center gap-2 self-start hover:bg-brand-700">
              {t("see_all")} <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
          {schools ? <ProductGrid items={schools} /> : <ProductSkeleton />}
        </div>
      </section>

      <Section title={t("build_title")} sub={t("build_sub")} href="/catalog?category=qurilish,temir-beton">
        {build ? <ProductGrid items={build} /> : <ProductSkeleton />}
      </Section>

      {/* QANDAY ISHLAYDI */}
      <section className="container-x mt-14">
        <h2 className="h-section mb-5">{t("how_title")}</h2>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[
            [ClipboardList, t("how1_t"), t("how1_d")],
            [BadgeCheck, t("how2_t"), t("how2_d")],
            [FileSignature, t("how3_t"), t("how3_d")],
            [CreditCard, t("how4_t"), t("how4_d")],
          ].map(([I, title, d]: any, i) => (
            <div key={i} className="card p-5 relative">
              <span className="absolute right-4 top-3 text-5xl font-black text-ink-100">{i + 1}</span>
              <span className="w-11 h-11 rounded-xl bg-brand-50 text-brand-700 grid place-items-center"><I className="w-5 h-5" /></span>
              <div className="font-bold mt-4 text-ink-900">{title}</div>
              <div className="text-sm text-ink-500 mt-1 leading-relaxed">{d}</div>
            </div>
          ))}
        </div>
      </section>

      {/* B2B */}
      <section className="container-x mt-14">
        <div className="rounded-3xl bg-ink-900 text-white p-6 md:p-10 grid md:grid-cols-[1.4fr_1fr] gap-6 items-center overflow-hidden relative">
          <div className="absolute -right-16 -top-16 w-64 h-64 rounded-full bg-brand-600/30 blur-2xl" />
          <div className="relative">
            <h2 className="text-2xl md:text-3xl font-extrabold">{t("b2b_title")}</h2>
            <p className="mt-2 text-ink-300 max-w-xl">{t("b2b_sub")}</p>
            <div className="mt-5 flex flex-wrap gap-2 text-sm">
              {[t("contract"), "QR", t("pay_bank"), t("delivery")].map((x) => (
                <span key={x} className="px-3 py-1.5 rounded-lg bg-white/10 inline-flex items-center gap-1.5"><BadgeCheck className="w-4 h-4 text-emerald-400" /> {x}</span>
              ))}
            </div>
          </div>
          <div className="relative md:text-right">
            <Link href="/catalog" className="h-12 px-6 rounded-xl bg-accent-500 hover:bg-accent-600 font-bold inline-flex items-center gap-2">
              <Truck className="w-5 h-5" /> {t("b2b_cta")}
            </Link>
          </div>
        </div>
      </section>

      {/* SOTUVCHILAR */}
      <Section title={t("sellers_title")} href="/sellers">
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
          {(meta?.sellers || []).filter((s) => s.product_count > 0).sort((a, b) => b.product_count - a.product_count).map((s) => (
            <Link key={s.code} href={`/sellers/${s.code}`} className="card p-4 hover:shadow-pop transition">
              <div className="w-10 h-10 rounded-xl bg-brand-50 text-brand-700 grid place-items-center font-extrabold text-sm">
                {s.code.replace(/\D/g, "")}
              </div>
              <div className="font-bold mt-3 text-ink-900">{p(s.name)}</div>
              <div className="text-xs text-ink-500 mt-0.5 flex items-center gap-1"><MapPin className="w-3 h-3" />{p(s.region_i18n)}</div>
              <div className="text-xs font-semibold text-brand-700 mt-2">{t("products_n", { n: s.product_count })}</div>
            </Link>
          ))}
        </div>
      </Section>
    </div>
  );
}
