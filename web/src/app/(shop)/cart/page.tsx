"use client";
import { Factory, Info, ShoppingCart, Trash2 } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { StockLine } from "@/components/ProductCard";
import { Button, Empty, ProductImage, Qty } from "@/components/ui";
import { useApp, useCart } from "@/lib/store";
import { groupBySeller } from "@/lib/util";

export default function CartPage() {
  const { t, p, money, unit, meta } = useApp();
  const cart = useCart();
  const router = useRouter();
  if (!cart.lines.length)
    return <Empty icon={<ShoppingCart className="w-7 h-7" />} title={t("cart_empty")} sub={t("cart_empty_sub")}
      action={<Link href="/catalog"><Button>{t("go_shopping")}</Button></Link>} />;

  const groups = groupBySeller(cart.lines);
  const total = cart.lines.reduce((s, l) => s + (l.product.price ? Number(l.product.price) * l.qty : 0), 0);
  const unpriced = cart.lines.some((l) => !l.product.price);

  return (
    <div className="container-x py-6">
      <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight">{t("cart")} <span className="text-ink-500 text-lg font-semibold">· {t("items_n", { n: cart.count })}</span></h1>
      <div className="mt-3 flex items-start gap-2 text-sm text-brand-800 bg-brand-50 rounded-xl px-4 py-3"><Info className="w-4 h-4 mt-0.5 shrink-0" />{t("separate_note")}</div>
      <div className="grid lg:grid-cols-[1fr_340px] gap-6 mt-5">
        <div className="space-y-4">
          {groups.map((g) => {
            const s = g[0].product.seller;
            const sub = g.reduce((acc, l) => acc + (l.product.price ? Number(l.product.price) * l.qty : 0), 0);
            return (
              <div key={s.code} className="card overflow-hidden">
                <div className="px-5 py-3 border-b border-ink-100 flex items-center justify-between gap-3 bg-ink-100/40">
                  <Link href={`/sellers/${s.code}`} className="font-bold inline-flex items-center gap-2 hover:text-brand-700"><Factory className="w-4 h-4" /> {p(s.name)} <span className="font-normal text-ink-500 text-sm">· {p(s.region_i18n)}</span></Link>
                  <span className="text-sm font-semibold tabular-nums">{money(sub)}</span>
                </div>
                <div className="divide-y divide-ink-100">
                  {g.map(({ product: pr, qty }) => {
                    const icon = meta?.categories.find((c) => c.slug === pr.category)?.icon;
                    return (
                      <div key={pr.id} className="p-4 flex gap-4">
                        <Link href={`/product/${pr.id}`} className="w-20 h-20 sm:w-24 sm:h-24 rounded-xl overflow-hidden shrink-0">
                          <ProductImage src={pr.image} category={pr.category} icon={icon} />
                        </Link>
                        <div className="flex-1 min-w-0">
                          <Link href={`/product/${pr.id}`} className="font-semibold leading-snug hover:text-brand-700 line-clamp-2">{p(pr.name)}</Link>
                          <div className="text-sm text-ink-500">{p(pr.spec)}</div>
                          <StockLine p={pr} className="text-xs font-semibold" />
                          <div className="mt-2 flex items-center gap-3 flex-wrap">
                            <Qty size="sm" value={qty} onChange={(v) => cart.setQty(pr.id, v)} min={pr.min_order || 1} max={pr.available} />
                            <span className="text-sm text-ink-500">× {pr.price ? money(pr.price) : t("price_on_request")} / {unit(pr.unit)}</span>
                          </div>
                        </div>
                        <div className="flex flex-col items-end justify-between">
                          <button onClick={() => cart.remove(pr.id)} className="p-2 rounded-lg text-ink-500 hover:text-red-600 hover:bg-red-50" aria-label={t("remove")}><Trash2 className="w-4 h-4" /></button>
                          <div className="font-bold tabular-nums">{pr.price ? money(Number(pr.price) * qty) : "—"}</div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
        <aside>
          <div className="card p-5 sticky top-28">
            <div className="flex justify-between text-sm text-ink-500"><span>{t("items_n", { n: cart.count })}</span><span>{groups.length} × {t("contract")}</span></div>
            <div className="flex justify-between items-baseline mt-3"><span className="font-semibold">{t("total")}</span><span className="text-2xl font-extrabold tabular-nums">{money(total)}</span></div>
            {unpriced && <div className="text-xs text-amber-700 bg-amber-50 rounded-lg p-2.5 mt-3">{t("priced_later")}</div>}
            <Button size="lg" variant="accent" className="w-full mt-5" onClick={() => router.push("/checkout")}>{t("checkout")}</Button>
          </div>
        </aside>
      </div>
    </div>
  );
}
