"use client";
import clsx from "clsx";
import { Check, CreditCard, Download, ExternalLink, Factory, FileText, Landmark, MessageSquare, Truck } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Badge, Button, Empty, STATUS_TONE, Spinner } from "@/components/ui";
import { api, errText } from "@/lib/api";
import { useApp } from "@/lib/store";
import type { Order } from "@/lib/types";
import { fmtDate } from "@/lib/util";

const STEPS = ["new", "review", "contract", "paid", "shipped", "done"] as const;

export default function OrderPage({ params }: { params: { token: string } }) {
  const { t, p, money, unit, meta } = useApp();
  const [o, setO] = useState<Order | null | undefined>(undefined);
  const [paying, setPaying] = useState<string | null>(null);
  const [err, setErr] = useState("");

  const load = useCallback(() => api<Order>(`/orders/${params.token}/`).then(setO).catch(() => setO(null)), [params.token]);
  useEffect(() => { load(); const id = setInterval(load, 15000); return () => clearInterval(id); }, [load]);

  if (o === undefined) return <div className="py-32 grid place-items-center"><Spinner /></div>;
  if (o === null) return <Empty title={t("not_found")} />;

  const c = o.contract;
  const stage = c ? (c.status === "active" ? "contract" : c.status) : o.status;
  const idx = STEPS.indexOf(stage as any);
  const cancelled = o.status === "rejected" || o.status === "cancelled" || c?.status === "cancelled";
  const statusLabel = c ? t(`c_${c.status}` as any) : t(`st_${o.status}` as any);
  const stepLabel: Record<string, string> = {
    new: t("st_new"), review: t("st_review"), contract: t("contract"), paid: t("c_paid"), shipped: t("c_shipped"), done: t("c_done"),
  };

  const pay = async (method: string) => {
    setPaying(method); setErr("");
    try {
      const r = await api<{ url?: string; paid?: boolean }>(`/orders/${o.token}/pay/`, { method: "POST", json: { method } });
      if (r.url) window.location.href = r.url;
      else load();
    } catch (e) { setErr(errText(e)); } finally { setPaying(null); }
  };

  return (
    <div className="container-x py-6 max-w-5xl">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight font-mono">{o.number}</h1>
        <Badge tone={cancelled ? "red" : STATUS_TONE[c?.status || o.status]}>{statusLabel}</Badge>
      </div>
      <div className="text-ink-500 mt-1 text-sm">{fmtDate(o.created_at, true)} · {o.buyer_name}</div>

      {!cancelled && (
        <div className="card p-4 md:p-5 mt-5 overflow-x-auto">
          <div className="flex items-center min-w-[560px]">
            {STEPS.map((s, i) => (
              <div key={s} className="flex-1 flex items-center">
                <div className="flex flex-col items-center gap-1.5 w-20">
                  <span className={clsx("w-8 h-8 rounded-full grid place-items-center text-sm font-bold", i <= idx ? "bg-brand-600 text-white" : "bg-ink-100 text-ink-500")}>
                    {i < idx ? <Check className="w-4 h-4" /> : i + 1}
                  </span>
                  <span className={clsx("text-xs text-center leading-tight", i <= idx ? "text-ink-900 font-semibold" : "text-ink-500")}>{stepLabel[s]}</span>
                </div>
                {i < STEPS.length - 1 && <div className={clsx("flex-1 h-0.5 -mt-5", i < idx ? "bg-brand-600" : "bg-ink-100")} />}
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="grid lg:grid-cols-[1fr_360px] gap-5 mt-5">
        <div className="space-y-5">
          <div className="card">
            <div className="px-5 py-3 border-b border-ink-100 flex items-center gap-2 font-bold"><Factory className="w-4 h-4" /> {p(o.seller.name)} <span className="font-normal text-ink-500 text-sm">· {p(o.seller.region_i18n)}</span></div>
            {o.agent && <div className="px-5 pt-3 text-sm text-ink-500">{t("via_agent", { a: p(o.agent.name) })}</div>}
            <div className="divide-y divide-ink-100">
              {o.items.map((it) => (
                <div key={it.id} className="px-5 py-3 flex gap-4 text-sm">
                  <div className="flex-1">
                    <div className="font-semibold text-ink-900">{p(it.name)}</div>
                    <div className="text-ink-500">{p(it.spec)} · {it.sku}</div>
                  </div>
                  <div className="text-right tabular-nums">
                    <div>{it.qty} {unit(it.unit)} × {it.price ? money(it.price) : t("price_on_request")}</div>
                    <div className="font-bold">{it.price ? money(it.amount) : "—"}</div>
                  </div>
                </div>
              ))}
            </div>
            {c && Number(c.delivery_cost) > 0 && (
              <div className="px-5 py-2 border-t border-ink-100 flex justify-between text-sm"><span className="text-ink-500">{t("delivery_cost")}</span><span className="tabular-nums">{money(c.delivery_cost)}</span></div>
            )}
            <div className="px-5 py-3 border-t border-ink-100 flex justify-between font-bold">
              <span>{t("total")}</span><span className="tabular-nums">{money(c ? c.grand_total : o.total)}</span>
            </div>
          </div>
          {o.seller_comment && (
            <div className="card p-5 text-sm"><div className="font-semibold flex items-center gap-2 mb-1"><MessageSquare className="w-4 h-4" /> {t("seller_comment")}</div>{o.seller_comment}</div>
          )}
          <div className="card p-5">
            <div className="font-bold mb-3">{t("history")}</div>
            <ol className="space-y-2.5 text-sm">
              {o.logs.map((l, i) => (
                <li key={i} className="flex gap-3">
                  <span className="w-2 h-2 rounded-full bg-brand-500 mt-1.5 shrink-0" />
                  <span className="text-ink-500 w-32 shrink-0 tabular-nums">{fmtDate(l.created_at, true)}</span>
                  <span className="text-ink-900">{({ new: t("st_new"), review: t("st_review"), contract: t("st_contract"), payment: t("paid"), shipped: t("c_shipped"), done: t("c_done"), rejected: t("st_rejected"), cancelled: t("st_cancelled") } as any)[l.status] || l.status}
                    {l.status === "contract" && l.text ? ` · ${l.text}` : ""}</span>
                </li>
              ))}
            </ol>
          </div>
        </div>

        <aside className="space-y-5">
          {!c && !cancelled && <div className="card p-5 text-sm text-ink-700 leading-relaxed">{t("waiting_seller")}</div>}
          {c && (
            <div className="card p-5">
              <div className="flex items-center gap-2 font-bold"><FileText className="w-5 h-5 text-brand-600" /> {t("contract")}</div>
              <div className="font-mono text-sm mt-1">{c.number} · {fmtDate(c.date)}</div>
              <div className="mt-4 space-y-1.5 text-sm">
                <div className="flex justify-between"><span className="text-ink-500">{t("grand_total")}</span><span className="font-semibold tabular-nums">{money(c.grand_total)}</span></div>
                {Number(c.delivery_cost) > 0 && <div className="flex justify-between"><span className="text-ink-500">{t("delivery_cost")}</span><span className="tabular-nums">{money(c.delivery_cost)}</span></div>}
                <div className="flex justify-between"><span className="text-ink-500">{t("paid")}</span><span className="tabular-nums text-emerald-700">{money(c.paid_amount)}</span></div>
                <div className="flex justify-between"><span className="text-ink-500">{t("due")}</span><span className="font-bold tabular-nums">{money(c.due_amount)}</span></div>
              </div>
              <div className="grid gap-2 mt-4">
                <a href={c.pdf_url} target="_blank" rel="noreferrer"><Button variant="outline" className="w-full"><ExternalLink className="w-4 h-4" /> {t("open_pdf")}</Button></a>
                <a href={`${c.pdf_url}?dl=1`}><Button variant="ghost" className="w-full"><Download className="w-4 h-4" /> {t("download_pdf")}</Button></a>
              </div>
              {Number(c.due_amount) > 0 && !cancelled && c.status === "active" && (
                <div className="mt-5 pt-5 border-t border-ink-100">
                  {c.payment_method !== "bank" ? (
                    <div className="grid gap-2">
                      {(["payme", "click"] as const).map((m) => (
                        <Button key={m} size="lg" variant={m === c.payment_method ? "accent" : "outline"} loading={paying === m} onClick={() => pay(m)}>
                          <CreditCard className="w-5 h-5" /> {t("pay_with", { m: m === "payme" ? "Payme" : "Click" })}
                          {meta?.payments?.[m]?.demo && <Badge tone="amber">{t("demo")}</Badge>}
                        </Button>
                      ))}
                    </div>
                  ) : (
                    <div className="text-sm">
                      <div className="font-semibold flex items-center gap-2"><Landmark className="w-4 h-4" /> {t("bank_title")}</div>
                      <p className="text-ink-500 mt-1">{t("bank_hint")}</p>
                      <div className="mt-3 rounded-xl bg-ink-100/60 p-3 space-y-1 font-mono text-[13px]">
                        <div>{p(o.seller.name)}</div>
                        <div>{t("inn")}: {o.seller.inn}</div>
                        <div>{t("contract_no")}: {c.number}</div>
                        <div>{t("amount")}: {money(c.due_amount)}</div>
                      </div>
                      <p className="text-xs text-ink-500 mt-2">{t("pay_bank_note")}</p>
                    </div>
                  )}
                  {err && <div className="text-sm text-red-700 mt-2">{err}</div>}
                </div>
              )}
              {(c.status === "shipped" || c.status === "done") && (
                <div className="mt-4 text-sm text-violet-700 bg-violet-50 rounded-lg p-3 flex gap-2"><Truck className="w-4 h-4 mt-0.5" /> {t("c_shipped")} {fmtDate(c.shipped_at)}</div>
              )}
            </div>
          )}
          <div className="card p-5 text-sm">
            <div className="text-ink-500">{t("seller")}</div>
            <Link href={`/sellers/${o.seller.code}`} className="font-semibold hover:text-brand-700">{p(o.seller.name)}</Link>
            {o.seller.phone && <div className="mt-1">{o.seller.phone}</div>}
          </div>
        </aside>
      </div>
    </div>
  );
}
