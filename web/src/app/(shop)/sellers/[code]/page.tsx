"use client";
import { Factory, MapPin, Phone } from "lucide-react";
import { useEffect, useState } from "react";
import { ProductGrid, ProductSkeleton } from "@/components/ProductCard";
import { Empty } from "@/components/ui";
import { api } from "@/lib/api";
import { useApp } from "@/lib/store";
import type { Paged, Product, Seller } from "@/lib/types";

export default function SellerPage({ params }: { params: { code: string } }) {
  const { t, p } = useApp();
  const [s, setS] = useState<Seller | null>(null);
  const [items, setItems] = useState<Product[] | null>(null);
  useEffect(() => {
    api<Seller>(`/sellers/${params.code}/`).then(setS).catch(() => {});
    api<Paged<Product>>(`/products/?seller=${params.code}&page_size=200&ordering=name`).then((r) => setItems(r.results)).catch(() => setItems([]));
  }, [params.code]);
  return (
    <div>
      <div className="bg-gradient-to-r from-brand-900 to-brand-700 text-white">
        <div className="container-x py-8 flex items-center gap-5">
          <span className="w-16 h-16 rounded-2xl bg-white/15 grid place-items-center"><Factory className="w-8 h-8" /></span>
          <div>
            <h1 className="text-2xl md:text-3xl font-extrabold">{p(s?.name)}</h1>
            <div className="text-brand-100 mt-1 flex flex-wrap gap-x-4 gap-y-1 text-sm">
              <span className="inline-flex items-center gap-1"><MapPin className="w-4 h-4" /> {p(s?.region_i18n)}, {p(s?.district_i18n)}</span>
              {s?.inn && <span>{t("inn")}: {s.inn}</span>}
              {s?.phone && <span className="inline-flex items-center gap-1"><Phone className="w-4 h-4" /> {s.phone}</span>}
            </div>
          </div>
        </div>
      </div>
      <div className="container-x py-6">
        {p(s?.description) && <p className="text-ink-700 mb-6 max-w-3xl">{p(s?.description)}</p>}
        {items === null ? <ProductSkeleton /> : items.length ? <ProductGrid items={items} /> : <Empty title={t("no_data")} />}
      </div>
    </div>
  );
}
