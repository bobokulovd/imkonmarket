"use client";
import clsx from "clsx";
import { Ban, CheckCheck, Copy, ExternalLink, Landmark, Link2, RefreshCw, Search, Truck } from "lucide-react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";
import { useMe } from "@/components/CabinetShell";
import { Badge, Button, Empty, Field, Input, Modal, Select, Spinner, STATUS_TONE } from "@/components/ui";
import { api, errText, qs } from "@/lib/api";
import { LANGS, useApp } from "@/lib/store";
import type { Contract, Paged } from "@/lib/types";
import { fmtDate } from "@/lib/util";

const TABS = ["", "active", "paid", "shipped", "done", "cancelled"];

function Detail({ id, onChanged }: { id: number; onChanged: () => void }) {
  const { t, p, money, unit, lang } = useApp();
  const { me } = useMe();
  const [c, setC] = useState<Contract | null>(null);
  const [amount, setAmount] = useState("");
  const [doc, setDoc] = useState("");
  const [pdfLang, setPdfLang] = useState(lang);
  const [link, setLink] = useState("");
  const [busy, setBusy] = useState("");
  const [err, setErr] = useState("");
  const [copied, setCopied] = useState(false);

  const load = useCallback(() => api<Contract>(`/seller/contracts/${id}/`, { authed: true }).then((x) => { setC(x); setAmount(String(Number(x.due_amount))); setPdfLang(x.lang); }), [id]);
  useEffect(() => { load(); }, [load]);
  if (!c) return <div className="py-16 grid place-items-center"><Spinner /></div>;
  const own = me.seller.role === "operator" || c.seller.code === me.seller.code;

  const act = async (kind: string, body: any = {}) => {
    if ((kind === "cancel" || kind === "ship") && !window.confirm(t("confirm_q"))) return;
    setBusy(kind); setErr("");
    try {
      if (kind === "pay-link") {
        const r = await api<{ url: string }>(`/seller/contracts/${id}/pay-link/`, { method: "POST", json: body, authed: true });
        setLink(r.url || "");
      } else {
        const r = await api<Contract>(`/seller/contracts/${id}/${kind}/`, { method: "POST", json: body, authed: true });
        setC(r); onChanged();
      }
    } catch (e) { setErr(errText(e)); } finally { setBusy(""); }
  };
  const orderUrl = typeof window !== "undefined" ? `${window.location.origin}/order/${c.application.token}` : "";

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone={STATUS_TONE[c.status]}>{t(`c_${c.status}` as any)}</Badge>
        <Badge tone="gray">{c.buyer_type.toUpperCase()}</Badge>
        <Badge tone="blue">{c.payment_method === "bank" ? t("pay_bank") : c.payment_method === "payme" ? "Payme" : "Click"}</Badge>
        {c.agent && <Badge tone="violet">{t("agent")}: {p(c.agent.name)}</Badge>}
        <span className="text-sm text-ink-500 ml-auto">{fmtDate(c.date)} · {t("app_number")}: {c.application.number}</span>
      </div>
      <div className="grid sm:grid-cols-4 gap-3">
        {[[t("grand_total"), money(c.grand_total)], [t("paid"), money(c.paid_amount)], [t("due"), money(c.due_amount)], [t("prepayment"), `${c.prepayment_percent}%`]].map(([k, v]) => (
          <div key={k} className="rounded-xl bg-ink-100/60 p-3"><div className="text-xs text-ink-500">{k}</div><div className="font-bold tabular-nums">{v}</div></div>
        ))}
      </div>
      <div className="rounded-xl border border-ink-100 text-sm">
        <div className="px-4 py-2.5 border-b border-ink-100 flex justify-between"><span className="font-semibold">{c.application.buyer_name}</span><span className="text-ink-500">{c.application.buyer_phone} · {c.application.buyer_inn || c.application.buyer_pinfl}</span></div>
        {c.application.items.map((i) => (
          <div key={i.id} className="px-4 py-2 flex justify-between gap-3 border-b border-ink-100 last:border-0">
            <span>{p(i.name)} <span className="text-ink-500">{p(i.spec)}</span></span>
            <span className="tabular-nums shrink-0">{i.qty} {unit(i.unit)} × {money(i.price)} = <b>{money(i.amount)}</b></span>
          </div>
        ))}
        {c.application.delivery_required && <div className="px-4 py-2 text-ink-500"><Truck className="w-4 h-4 inline" /> {c.application.delivery_address}</div>}
      </div>

      <div className="flex flex-wrap gap-2">
        <a href={c.pdf_url} target="_blank" rel="noreferrer"><Button variant="outline"><ExternalLink className="w-4 h-4" /> PDF</Button></a>
        <div className="inline-flex gap-1">
          <Select value={pdfLang} onChange={(e) => setPdfLang(e.target.value as any)} className="h-11 w-40">{LANGS.map((l) => <option key={l.code} value={l.code}>{l.label}</option>)}</Select>
          <Button variant="ghost" loading={busy === "regenerate"} onClick={() => act("regenerate", { lang: pdfLang })}><RefreshCw className="w-4 h-4" /> {t("regenerate")}</Button>
        </div>
        <Button variant="ghost" onClick={() => { navigator.clipboard?.writeText(orderUrl); setCopied(true); setTimeout(() => setCopied(false), 1500); }}>
          <Copy className="w-4 h-4" /> {copied ? t("copied") : t("view_order")}
        </Button>
      </div>

      {own && c.status !== "cancelled" && (
        <div className="grid md:grid-cols-2 gap-4">
          {(c.status === "active" || c.status === "paid") && Number(c.due_amount) > 0 && (
            <div className="rounded-xl border border-ink-100 p-4">
              <div className="font-semibold flex items-center gap-2 mb-3"><Landmark className="w-4 h-4" /> {t("register_payment")}</div>
              <div className="grid grid-cols-2 gap-2">
                <Field label={t("amount")}><Input inputMode="decimal" value={amount} onChange={(e) => setAmount(e.target.value.replace(/[^\d.]/g, ""))} /></Field>
                <Field label={t("document_no")}><Input value={doc} onChange={(e) => setDoc(e.target.value)} /></Field>
              </div>
              <Button className="mt-3 w-full" loading={busy === "payment"} disabled={!Number(amount)} onClick={() => act("payment", { amount, document_no: doc, method: "bank" })}>{t("register_payment")}</Button>
              {c.payment_method !== "bank" && (
                <div className="mt-3 pt-3 border-t border-ink-100">
                  <Button variant="soft" className="w-full" loading={busy === "pay-link"} onClick={() => act("pay-link", { method: c.payment_method })}><Link2 className="w-4 h-4" /> {t("pay_link")}</Button>
                  {link && <div className="mt-2 text-xs break-all bg-ink-100/60 rounded-lg p-2">{link}</div>}
                </div>
              )}
            </div>
          )}
          <div className="rounded-xl border border-ink-100 p-4 space-y-2">
            {(c.status === "paid" || (c.status === "active" && c.buyer_type === "b2b")) && (
              <Button className="w-full" variant="accent" loading={busy === "ship"} onClick={() => act("ship")}><Truck className="w-4 h-4" /> {t("ship")}</Button>
            )}
            {c.status === "shipped" && <Button className="w-full" loading={busy === "complete"} onClick={() => act("complete")}><CheckCheck className="w-4 h-4" /> {t("complete")}</Button>}
            {(c.status === "active" || c.status === "paid") && <Button className="w-full" variant="ghost" loading={busy === "cancel"} onClick={() => act("cancel")}><Ban className="w-4 h-4" /> {t("cancel_contract")}</Button>}
          </div>
        </div>
      )}
      {c.payments.length > 0 && (
        <div className="rounded-xl border border-ink-100 text-sm">
          <div className="px-4 py-2.5 border-b border-ink-100 font-semibold">{t("payments")}</div>
          {c.payments.map((pm) => (
            <div key={pm.id} className="px-4 py-2 flex justify-between gap-3 border-b border-ink-100 last:border-0">
              <span>{fmtDate(pm.paid_at || pm.created_at, true)} · {pm.method}{pm.document_no ? ` · №${pm.document_no}` : ""} {pm.is_demo && <Badge tone="amber">{t("demo")}</Badge>}</span>
              <span className={clsx("tabular-nums font-semibold", pm.status === "paid" ? "text-emerald-700" : "text-ink-500")}>{money(pm.amount)} · {pm.status}</span>
            </div>
          ))}
        </div>
      )}
      {err && <div className="text-sm text-red-700 bg-red-50 rounded-lg p-3">{err}</div>}
    </div>
  );
}

function ContractsInner() {
  const { t, p, money } = useApp();
  const { me } = useMe();
  const sp = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const [data, setData] = useState<Paged<Contract> | null>(null);
  const [q, setQ] = useState("");
  const status = sp.get("status") || "";
  const open = sp.get("open");
  const set = (k: string, v: string | null) => {
    const n = new URLSearchParams(sp.toString());
    v ? n.set(k, v) : n.delete(k);
    router.replace(`${pathname}?${n}`);
  };
  const load = useCallback(() => {
    api<Paged<Contract>>(`/seller/contracts/${qs({ status, q: sp.get("q"), page: sp.get("page") })}`, { authed: true }).then(setData).catch(() => {});
  }, [status, sp]);
  useEffect(() => { load(); }, [load]);

  return (
    <div>
      <div className="flex flex-wrap gap-3 items-center justify-between">
        <h1 className="text-2xl font-extrabold">{t("contracts")}</h1>
        <form onSubmit={(e) => { e.preventDefault(); set("q", q || null); }} className="relative w-full sm:w-72">
          <Search className="w-4 h-4 absolute left-3 top-3.5 text-ink-500" />
          <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder={t("search_orders")} className="pl-9" />
        </form>
      </div>
      <div className="inline-flex flex-wrap bg-white rounded-xl border border-ink-100 p-1 mt-4">
        {TABS.map((s) => (
          <button key={s} onClick={() => set("status", s || null)} className={clsx("px-3 h-9 rounded-lg text-sm font-semibold", status === s ? "bg-brand-600 text-white" : "text-ink-700 hover:bg-ink-100")}>
            {s ? t(`c_${s}` as any) : t("all")}
          </button>
        ))}
      </div>
      <div className="card mt-4 overflow-hidden">
        {!data ? <div className="py-16 grid place-items-center"><Spinner /></div> : data.results.length === 0 ? <Empty title={t("no_data")} /> : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm min-w-[780px]">
              <thead className="bg-ink-100/60 text-ink-500 text-left">
                <tr><th className="px-4 py-3">{t("contract_no")}</th><th className="px-4 py-3">{t("buyer")}</th><th className="px-4 py-3 text-right">{t("amount")}</th><th className="px-4 py-3 text-right">{t("paid")}</th><th className="px-4 py-3">{t("status")}</th><th className="px-4 py-3">{t("date")}</th></tr>
              </thead>
              <tbody className="divide-y divide-ink-100">
                {data.results.map((c) => (
                  <tr key={c.id} className="hover:bg-brand-50/40 cursor-pointer" onClick={() => set("open", String(c.id))}>
                    <td className="px-4 py-3"><div className="font-mono font-semibold">{c.number}</div>
                      <div className="text-xs text-ink-500">{c.seller.code !== me.seller.code ? `${t("owner")}: ${p(c.seller.name)}` : ""}{c.agent ? ` ${t("agent")}: ${p(c.agent.name)}` : ""}</div></td>
                    <td className="px-4 py-3">{c.application.buyer_name}<div className="text-xs text-ink-500">{c.buyer_type.toUpperCase()} · {c.payment_method}</div></td>
                    <td className="px-4 py-3 text-right tabular-nums font-semibold">{money(c.grand_total)}</td>
                    <td className="px-4 py-3 text-right tabular-nums text-emerald-700">{money(c.paid_amount)}</td>
                    <td className="px-4 py-3"><Badge tone={STATUS_TONE[c.status]}>{t(`c_${c.status}` as any)}</Badge></td>
                    <td className="px-4 py-3 text-ink-500">{fmtDate(c.date)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      <Modal open={!!open} onClose={() => set("open", null)} wide title={<span className="font-mono">{data?.results.find((x) => String(x.id) === open)?.number || t("contract")}</span>}>
        {open && <Detail id={Number(open)} onChanged={load} />}
      </Modal>
    </div>
  );
}

export default function ContractsPage() {
  return <Suspense><ContractsInner /></Suspense>;
}
