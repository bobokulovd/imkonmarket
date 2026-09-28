"use client";
import { CheckCircle2, Factory, ShoppingCart } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import BuyerForm, { emptyBuyer, validateBuyer, type Buyer } from "@/components/BuyerForm";
import { Button, Empty } from "@/components/ui";
import { api, errText } from "@/lib/api";
import { useApp, useCart } from "@/lib/store";
import type { I18n } from "@/lib/types";
import { groupBySeller } from "@/lib/util";

type Created = { number: string; token: string; seller: I18n; total: string; has_unpriced: boolean };

export default function CheckoutPage() {
  const { t, p, money, lang, unit } = useApp();
  const cart = useCart();
  const [b, setB] = useState<Buyer>(() => emptyBuyer("uz"));
  const [errors, setErrors] = useState<Partial<Record<keyof Buyer, boolean>>>({});
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [done, setDone] = useState<Created[] | null>(null);

  useEffect(() => {
    try {
      const saved = localStorage.getItem("ub_buyer");
      setB(saved ? { ...emptyBuyer(lang), ...JSON.parse(saved), lang } : emptyBuyer(lang));
    } catch { setB(emptyBuyer(lang)); }
  }, [lang]);

  const set = (patch: Partial<Buyer>) => setB((x) => ({ ...x, ...patch }));

  if (done)
    return (
      <div className="container-x py-10 max-w-2xl">
        <div className="card p-6 md:p-8 text-center">
          <CheckCircle2 className="w-16 h-16 text-emerald-500 mx-auto" />
          <h1 className="text-2xl font-extrabold mt-4">{t("success_title")}</h1>
          <p className="text-ink-500 mt-2">{t("success_sub")}</p>
          <div className="mt-6 space-y-3 text-left">
            {done.map((a) => (
              <div key={a.token} className="rounded-xl border border-ink-100 p-4 flex items-center gap-4">
                <div className="flex-1">
                  <div className="text-xs text-ink-500">{t("app_number")}</div>
                  <div className="font-mono font-bold text-lg">{a.number}</div>
                  <div className="text-sm text-ink-700">{p(a.seller)} · {money(a.total)}</div>
                </div>
                <Link href={`/order/${a.token}`}><Button variant="soft">{t("view_order")}</Button></Link>
              </div>
            ))}
          </div>
        </div>
      </div>
    );

  if (!cart.lines.length)
    return <Empty icon={<ShoppingCart className="w-7 h-7" />} title={t("cart_empty")} action={<Link href="/catalog"><Button>{t("go_shopping")}</Button></Link>} />;

  const groups = groupBySeller(cart.lines);
  const total = cart.lines.reduce((s, l) => s + (l.product.price ? Number(l.product.price) * l.qty : 0), 0);

  const submit = async () => {
    const e = validateBuyer(b);
    setErrors(e);
    if (Object.keys(e).length) { window.scrollTo({ top: 0, behavior: "smooth" }); return; }
    setBusy(true); setErr("");
    try {
      const res = await api<Created[]>("/applications/", {
        method: "POST",
        json: { ...b, buyer_phone: b.buyer_phone.replace(/[^\d+]/g, ""), items: cart.lines.map((l) => ({ product: l.product.id, qty: l.qty })) },
      });
      try {
        const { comment, ...keep } = b;
        localStorage.setItem("ub_buyer", JSON.stringify(keep));
        const hist = JSON.parse(localStorage.getItem("ub_orders") || "[]");
        localStorage.setItem("ub_orders", JSON.stringify([...res.map((r) => ({ number: r.number, token: r.token })), ...hist].slice(0, 30)));
      } catch {}
      cart.clear();
      setDone(res);
      window.scrollTo({ top: 0 });
    } catch (e) {
      setErr(errText(e));
    } finally { setBusy(false); }
  };

  return (
    <div className="container-x py-6">
      <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight">{t("checkout_title")}</h1>
      <div className="grid lg:grid-cols-[1fr_380px] gap-6 mt-5">
        <div className="card p-5 md:p-6">
          <div className="font-bold text-lg mb-4">{t("your_data")}</div>
          <BuyerForm b={b} set={set} errors={errors} />
        </div>
        <aside>
          <div className="card p-5 sticky top-28">
            <div className="font-bold text-lg">{t("order_summary")}</div>
            <div className="mt-3 space-y-4 max-h-[46vh] overflow-y-auto pr-1">
              {groups.map((g) => (
                <div key={g[0].product.seller.code}>
                  <div className="text-sm font-semibold flex items-center gap-1.5 text-ink-700"><Factory className="w-4 h-4" /> {p(g[0].product.seller.name)}</div>
                  {g.map((l) => (
                    <div key={l.product.id} className="flex justify-between gap-3 text-sm mt-1.5">
                      <span className="text-ink-700 line-clamp-2">{p(l.product.name)} <span className="text-ink-500">× {l.qty} {unit(l.product.unit)}</span></span>
                      <span className="tabular-nums shrink-0">{l.product.price ? money(Number(l.product.price) * l.qty) : "—"}</span>
                    </div>
                  ))}
                </div>
              ))}
            </div>
            <div className="border-t border-ink-100 mt-4 pt-4 flex justify-between items-baseline">
              <span className="font-semibold">{t("total")}</span>
              <span className="text-2xl font-extrabold tabular-nums">{money(total)}</span>
            </div>
            {err && <div className="mt-3 text-sm text-red-700 bg-red-50 rounded-lg p-3">{err}</div>}
            <Button size="lg" variant="accent" className="w-full mt-4" loading={busy} onClick={submit}>{t("submit")}</Button>
            <p className="text-xs text-ink-500 mt-3 leading-relaxed">{t("agree")}</p>
          </div>
        </aside>
      </div>
    </div>
  );
}
