"use client";
import { Factory, MapPin } from "lucide-react";
import Link from "next/link";
import { useApp } from "@/lib/store";

export default function SellersPage() {
  const { t, p, meta } = useApp();
  const list = [...(meta?.sellers || [])].sort((a, b) => b.product_count - a.product_count || a.id - b.id);
  const regions = Array.from(new Set(list.map((s) => s.region)));
  return (
    <div className="container-x py-6">
      <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight">{t("sellers_title")}</h1>
      {regions.map((r) => (
        <section key={r} className="mt-8">
          <h2 className="font-bold text-ink-700 flex items-center gap-2 mb-3"><MapPin className="w-4 h-4" /> {p(list.find((s) => s.region === r)?.region_i18n)}</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-3">
            {list.filter((s) => s.region === r).map((s) => (
              <Link key={s.code} href={`/sellers/${s.code}`} className="card p-4 hover:shadow-pop transition">
                <div className="flex items-center gap-3">
                  <span className="w-10 h-10 rounded-xl bg-brand-50 text-brand-700 grid place-items-center"><Factory className="w-5 h-5" /></span>
                  <div className="min-w-0">
                    <div className="font-bold truncate">{p(s.name)}</div>
                    <div className="text-xs text-ink-500 truncate">{p(s.district_i18n)}</div>
                  </div>
                </div>
                <div className={`text-xs font-semibold mt-3 ${s.product_count ? "text-brand-700" : "text-ink-500"}`}>{t("products_n", { n: s.product_count })}</div>
              </Link>
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
