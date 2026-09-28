"use client";
import clsx from "clsx";
import { Building2, FileSignature, Search, User } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";
import { useMe } from "@/components/CabinetShell";
import { Badge, Button, Empty, Field, Input, Modal, Select, Spinner, STATUS_TONE, Textarea } from "@/components/ui";
import { api, errText, qs } from "@/lib/api";
import { LANGS, useApp } from "@/lib/store";
import type { Paged, SellerApplication } from "@/lib/types";
import { fmtDate, LOG_KEYS } from "@/lib/util";

const STATUS_TABS = ["", "new,review", "contract", "rejected,cancelled"];

function Detail({ id, onClose, onChanged }: { id: number; onClose: () => void; onChanged: () => void }) {
  const { t, p, money, unit } = useApp();
  const { me } = useMe();
  const [a, setA] = useState<SellerApplication | null>(null);
  const [edits, setEdits] = useState<Record<number, { qty: number; price: string }>>({});
  const [terms, setTerms] = useState({ delivery_cost: "0", prepayment_percent: "100", payment_days: "10", delivery_days: "15", lang: "uz", seller_comment: "" });
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState("");
  const [err, setErr] = useState("");

  const load = useCallback(() => api<SellerApplication>(`/seller/applications/${id}/`, { authed: true }).then((x) => {
    setA(x);
    setEdits(Object.fromEntries(x.items.map((i) => [i.id, { qty: i.qty, price: i.price ? String(Number(i.price)) : "" }])));
    setTerms((tm) => ({ ...tm, lang: x.lang }));
  }), [id]);
  useEffect(() => { load(); }, [load]);

  if (!a) return <div className="py-16 grid place-items-center"><Spinner /></div>;
  const own = me.seller.role === "operator" || a.seller.code === me.seller.code;
  const editable = own && (a.status === "new" || a.status === "review");
  const total = a.items.reduce((s, i) => s + (Number(edits[i.id]?.price || 0) * (edits[i.id]?.qty || 0)), 0);

  const act = async (kind: string, body: any = {}) => {
    setBusy(kind); setErr("");
    try {
      await api(`/seller/applications/${id}/${kind}/`, { method: "POST", json: body, authed: true });
      await load(); onChanged();
    } catch (e) { setErr(errText(e)); } finally { setBusy(""); }
  };
  const confirm = () => act("confirm", {
    items: a.items.map((i) => ({ id: i.id, qty: edits[i.id].qty, price: edits[i.id].price })),
    ...terms,
  });

  const rows: [string, string][] = a.buyer_type === "b2b"
    ? [[t("company_name"), a.buyer_name], [t("inn"), a.buyer_inn], [t("director"), a.buyer_director], [t("phone"), a.buyer_phone], [t("email"), a.buyer_email], [t("address"), a.buyer_address], [t("bank_name"), a.buyer_bank_name], [t("bank_account"), `${a.buyer_bank_account} ${a.buyer_bank_mfo ? `(${t("mfo")} ${a.buyer_bank_mfo})` : ""}`]]
    : [[t("full_name"), a.buyer_name], [t("pinfl"), a.buyer_pinfl], [t("passport"), a.buyer_passport], [t("phone"), a.buyer_phone], [t("email"), a.buyer_email], [t("address"), a.buyer_address]];

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap gap-2 items-center">
        <Badge tone={STATUS_TONE[a.status]}>{t(`st_${a.status}` as any)}</Badge>
        <Badge tone="gray">{a.buyer_type === "b2b" ? t("company") : t("individual")}</Badge>
        <Badge tone="blue">{a.payment_method === "bank" ? t("pay_bank") : a.payment_method === "payme" ? "Payme" : "Click"}</Badge>
        <Badge tone="gray">{a.delivery_required ? t("delivery_to") : t("pickup")}</Badge>
        {a.agent && <Badge tone="violet">{t("agent")}: {p(a.agent.name)}</Badge>}
        {me.seller.role === "operator" && <Badge tone="orange">{p(a.seller.name)}</Badge>}
      </div>
      <div className="grid md:grid-cols-2 gap-5">
        <div className="rounded-xl border border-ink-100 p-4">
          <div className="font-semibold mb-2">{t("buyer_info")}</div>
          <dl className="text-sm space-y-1">
            {rows.filter(([, v]) => v && v.trim()).map(([k, v]) => <div key={k} className="grid grid-cols-[40%_1fr] gap-2"><dt className="text-ink-500">{k}</dt><dd className="break-words">{v}</dd></div>)}
            {a.delivery_required && <div className="grid grid-cols-[40%_1fr] gap-2"><dt className="text-ink-500">{t("delivery_address")}</dt><dd>{a.delivery_address}</dd></div>}
          </dl>
          {a.comment && <div className="text-sm mt-3 bg-ink-100/60 rounded-lg p-2.5">{a.comment}</div>}
        </div>
        <div className="rounded-xl border border-ink-100 p-4 text-sm">
          <div className="font-semibold mb-2">{t("history")}</div>
          <ol className="space-y-1.5">{a.logs.map((l, i) => <li key={i} className="flex gap-2"><span className="text-ink-500 tabular-nums w-28 shrink-0">{fmtDate(l.created_at, true)}</span><span>{LOG_KEYS[l.status] ? t(LOG_KEYS[l.status] as any) : l.status}{l.text ? ` · ${l.text}` : ""}</span></li>)}</ol>
          {a.contract && (
            <Link href={`/cabinet/contracts?open=${a.contract.id}`} className="mt-4 flex items-center gap-2 rounded-lg bg-emerald-50 text-emerald-800 p-3 font-semibold">
              <FileSignature className="w-4 h-4" /> {a.contract.number} · {t(`c_${a.contract.status}` as any)}
            </Link>
          )}
        </div>
      </div>

      <div className="rounded-xl border border-ink-100 overflow-x-auto">
        <table className="w-full text-sm min-w-[560px]">
          <thead className="bg-ink-100/60 text-ink-500 text-left">
            <tr><th className="px-3 py-2">{t("name")}</th><th className="px-3 py-2 w-28">{t("qty")}</th><th className="px-3 py-2 w-36">{t("price_per")}</th><th className="px-3 py-2 text-right">{t("amount")}</th></tr>
          </thead>
          <tbody className="divide-y divide-ink-100">
            {a.items.map((i) => (
              <tr key={i.id}>
                <td className="px-3 py-2"><div className="font-medium">{p(i.name)}</div><div className="text-xs text-ink-500">{p(i.spec)} · {i.sku} · {t("available")}: {i.available ?? "∞"}</div></td>
                <td className="px-3 py-2">
                  {editable ? <Input className="h-9" inputMode="numeric" value={edits[i.id]?.qty ?? i.qty} onChange={(e) => setEdits({ ...edits, [i.id]: { ...edits[i.id], qty: parseInt(e.target.value.replace(/\D/g, "") || "0", 10) } })} /> : `${i.qty}`}
                  <span className="text-xs text-ink-500"> {unit(i.unit)}</span>
                </td>
                <td className="px-3 py-2">
                  {editable ? <Input className={clsx("h-9", !edits[i.id]?.price && "border-amber-400")} inputMode="decimal" placeholder={t("set_price")} value={edits[i.id]?.price ?? ""} onChange={(e) => setEdits({ ...edits, [i.id]: { ...edits[i.id], price: e.target.value.replace(/[^\d.]/g, "") } })} /> : (i.price ? money(i.price) : "—")}
                </td>
                <td className="px-3 py-2 text-right tabular-nums font-semibold">{money(Number(edits[i.id]?.price || i.price || 0) * (edits[i.id]?.qty || i.qty))}</td>
              </tr>
            ))}
          </tbody>
          <tfoot><tr className="border-t border-ink-100"><td colSpan={3} className="px-3 py-2 font-bold">{t("total")}</td><td className="px-3 py-2 text-right font-extrabold tabular-nums">{money(editable ? total : a.total)}</td></tr></tfoot>
        </table>
      </div>

      {editable && (
        <div className="rounded-xl bg-brand-50/50 border border-brand-100 p-4">
          <div className="grid sm:grid-cols-3 gap-3">
            <Field label={t("delivery_cost") + `, ${t("sum")}`}><Input inputMode="numeric" value={terms.delivery_cost} onChange={(e) => setTerms({ ...terms, delivery_cost: e.target.value.replace(/\D/g, "") })} /></Field>
            {a.buyer_type === "b2b" && <Field label={t("prepayment")}><Input inputMode="numeric" value={terms.prepayment_percent} onChange={(e) => setTerms({ ...terms, prepayment_percent: e.target.value.replace(/\D/g, "") })} /></Field>}
            <Field label={t("payment_days")}><Input inputMode="numeric" value={terms.payment_days} onChange={(e) => setTerms({ ...terms, payment_days: e.target.value.replace(/\D/g, "") })} /></Field>
            <Field label={t("delivery_days")}><Input inputMode="numeric" value={terms.delivery_days} onChange={(e) => setTerms({ ...terms, delivery_days: e.target.value.replace(/\D/g, "") })} /></Field>
            <Field label={t("contract_lang")}><Select value={terms.lang} onChange={(e) => setTerms({ ...terms, lang: e.target.value })}>{LANGS.map((l) => <option key={l.code} value={l.code}>{l.label}</option>)}</Select></Field>
            <Field label={t("seller_comment")} className="sm:col-span-3"><Textarea rows={2} value={terms.seller_comment} onChange={(e) => setTerms({ ...terms, seller_comment: e.target.value })} /></Field>
          </div>
          <div className="flex flex-wrap gap-2 mt-4">
            <Button loading={busy === "confirm"} onClick={confirm}><FileSignature className="w-4 h-4" /> {t("confirm")}</Button>
            {a.status === "new" && <Button variant="outline" loading={busy === "review"} onClick={() => act("review")}>{t("review")}</Button>}
          </div>
          <div className="flex gap-2 mt-4 items-end">
            <Field label={t("reject_reason")} className="flex-1"><Input value={reason} onChange={(e) => setReason(e.target.value)} /></Field>
            <Button variant="danger" loading={busy === "reject"} disabled={!reason.trim()} onClick={() => act("reject", { reason })}>{t("reject")}</Button>
          </div>
        </div>
      )}
      {err && <div className="text-sm text-red-700 bg-red-50 rounded-lg p-3">{err}</div>}
    </div>
  );
}

function AppsInner() {
  const { t, p, money } = useApp();
  const { me } = useMe();
  const sp = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const [data, setData] = useState<Paged<SellerApplication> | null>(null);
  const [q, setQ] = useState("");
  const status = sp.get("status") || "";
  const scope = sp.get("scope") || "";
  const open = sp.get("open");
  const page = sp.get("page") || "1";

  const set = (k: string, v: string | null) => {
    const n = new URLSearchParams(sp.toString());
    v ? n.set(k, v) : n.delete(k);
    if (k !== "open" && k !== "page") n.delete("page");
    router.replace(`${pathname}?${n}`);
  };
  const load = useCallback(() => {
    api<Paged<SellerApplication>>(`/seller/applications/${qs({ status, scope, q: sp.get("q"), page })}`, { authed: true }).then(setData).catch(() => {});
  }, [status, scope, sp, page]);
  useEffect(() => { load(); }, [load]);

  const tabLabel = (s: string) => (s === "" ? t("all") : s === "new,review" ? t("st_new") : s === "contract" ? t("st_contract") : t("st_rejected"));

  return (
    <div>
      <div className="flex flex-wrap gap-3 items-center justify-between">
        <h1 className="text-2xl font-extrabold">{t("applications")}</h1>
        <form onSubmit={(e) => { e.preventDefault(); set("q", q || null); }} className="relative w-full sm:w-72">
          <Search className="w-4 h-4 absolute left-3 top-3.5 text-ink-500" />
          <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder={t("search_orders")} className="pl-9 h-11" />
        </form>
      </div>
      <div className="flex flex-wrap gap-2 mt-4">
        <div className="inline-flex bg-white rounded-xl border border-ink-100 p-1">
          {STATUS_TABS.map((s) => (
            <button key={s} onClick={() => set("status", s || null)} className={clsx("px-3 h-9 rounded-lg text-sm font-semibold", status === s ? "bg-brand-600 text-white" : "text-ink-700 hover:bg-ink-100")}>{tabLabel(s)}</button>
          ))}
        </div>
        {me.seller.role !== "operator" && (
          <div className="inline-flex bg-white rounded-xl border border-ink-100 p-1">
            {[["", t("scope_all")], ["own", t("scope_own")], ["agent", t("scope_agent")]].map(([s, l]) => (
              <button key={s} onClick={() => set("scope", s || null)} className={clsx("px-3 h-9 rounded-lg text-sm font-semibold", scope === s ? "bg-ink-900 text-white" : "text-ink-700 hover:bg-ink-100")}>{l}</button>
            ))}
          </div>
        )}
      </div>

      <div className="card mt-4 overflow-hidden">
        {!data ? <div className="py-16 grid place-items-center"><Spinner /></div> : data.results.length === 0 ? <Empty title={t("no_data")} /> : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm min-w-[760px]">
              <thead className="bg-ink-100/60 text-ink-500 text-left">
                <tr><th className="px-4 py-3">№</th><th className="px-4 py-3">{t("buyer")}</th><th className="px-4 py-3">{t("items")}</th><th className="px-4 py-3">{t("payment_method")}</th><th className="px-4 py-3 text-right">{t("amount")}</th><th className="px-4 py-3">{t("status")}</th><th className="px-4 py-3">{t("created")}</th></tr>
              </thead>
              <tbody className="divide-y divide-ink-100">
                {data.results.map((a) => (
                  <tr key={a.id} className="hover:bg-brand-50/40 cursor-pointer" onClick={() => set("open", String(a.id))}>
                    <td className="px-4 py-3 font-mono font-semibold">{a.number}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1.5 font-medium">{a.buyer_type === "b2b" ? <Building2 className="w-4 h-4 text-ink-500" /> : <User className="w-4 h-4 text-ink-500" />}{a.buyer_name}</div>
                      <div className="text-xs text-ink-500">{a.buyer_phone}{a.agent ? ` · ${t("agent")}: ${p(a.agent.name)}` : ""}{a.seller.code !== me.seller.code ? ` · ${t("owner")}: ${p(a.seller.name)}` : ""}</div>
                    </td>
                    <td className="px-4 py-3">{a.items_count}{a.has_unpriced && <Badge tone="amber" className="ml-2">{t("set_price")}</Badge>}</td>
                    <td className="px-4 py-3">{a.payment_method === "bank" ? t("pay_bank") : a.payment_method === "payme" ? "Payme" : "Click"}</td>
                    <td className="px-4 py-3 text-right tabular-nums font-semibold">{money(a.total)}</td>
                    <td className="px-4 py-3"><Badge tone={STATUS_TONE[a.status]}>{t(`st_${a.status}` as any)}</Badge></td>
                    <td className="px-4 py-3 text-ink-500 tabular-nums">{fmtDate(a.created_at, true)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      {data && data.count > 24 && (
        <div className="flex justify-center gap-2 mt-4">
          <Button size="sm" variant="outline" disabled={!data.previous} onClick={() => set("page", String(Number(page) - 1))}>{t("prev")}</Button>
          <Button size="sm" variant="outline" disabled={!data.next} onClick={() => set("page", String(Number(page) + 1))}>{t("next")}</Button>
        </div>
      )}
      <Modal open={!!open} onClose={() => set("open", null)} wide title={<span className="font-mono">{data?.results.find((x) => String(x.id) === open)?.number || t("applications")}</span>}>
        {open && <Detail id={Number(open)} onClose={() => set("open", null)} onChanged={load} />}
      </Modal>
    </div>
  );
}

export default function ApplicationsPage() {
  return <Suspense><AppsInner /></Suspense>;
}
