"use client";
import clsx from "clsx";
import { RefreshCw, ShoppingCart } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Badge, Button, Empty, Select, Spinner } from "@/components/ui";
import { api, errText, qs } from "@/lib/api";
import { useApp } from "@/lib/store";
import type { Paged } from "@/lib/types";
import { fmtDate } from "@/lib/util";
import { type Account, money2, MpBadge, type MpOrder, ORDER_TONE, type TKey } from "./common";

const O_KEY: Record<string, TKey> = { new: "mp_o_new", processing: "mp_o_processing", shipped: "mp_o_shipped", delivered: "mp_o_delivered", cancelled: "mp_o_cancelled", returned: "mp_o_returned" };
const A_KEY: Record<string, TKey> = { confirm: "mp_a_confirm", ship: "mp_a_ship", deliver: "mp_a_deliver", cancel: "mp_a_cancel" };

export default function Orders({ accounts, notify, isOperator }: { accounts: Account[]; notify: (s: string) => void; isOperator: boolean }) {
  const { t } = useApp();
  const [data, setData] = useState<Paged<MpOrder> | null>(null);
  const [account, setAccount] = useState("");
  const [state, setState] = useState("new,processing");
  const [page, setPage] = useState(1);
  const load = useCallback(() => {
    api<Paged<MpOrder>>(`/mp/orders/${qs({ account, state, page })}`, { authed: true }).then(setData).catch((e) => notify(errText(e)));
  }, [account, state, page, notify]);
  useEffect(() => { load(); }, [load]);
  const act = async (o: MpOrder, action: string) => {
    if (action === "cancel" && !confirm(t("confirm_q"))) return;
    try { await api(`/mp/orders/${o.id}/action/`, { method: "POST", json: { action }, authed: true }); notify(t("mp_queued")); setTimeout(load, 5000); }
    catch (e) { notify(errText(e)); }
  };
  return (
    <div className="space-y-4">
      <p className="text-sm text-ink-500">{t("mp_order_note")}</p>
      <div className="flex flex-wrap gap-2">
        <Select className="!w-auto" value={account} onChange={(e) => { setAccount(e.target.value); setPage(1); }}>
          <option value="">{t("all")}</option>
          {accounts.map((a) => <option key={a.id} value={a.id}>{a.marketplace_name} {a.title}</option>)}
        </Select>
        <Select className="!w-auto" value={state} onChange={(e) => { setState(e.target.value); setPage(1); }}>
          <option value="new,processing">{t("mp_o_new")} + {t("mp_o_processing")}</option>
          <option value="">{t("all")}</option>
          {Object.entries(O_KEY).map(([k, v]) => <option key={k} value={k}>{t(v)}</option>)}
        </Select>
        <Button variant="outline" onClick={load}><RefreshCw className="w-4 h-4" /></Button>
      </div>
      {!data ? <Spinner /> : data.results.length === 0 ? <Empty icon={<ShoppingCart className="w-7 h-7" />} title={t("nothing_found")} /> : (
        <div className="space-y-3">
          {data.results.map((o) => (
            <div key={o.id} className="card p-4">
              <div className="flex flex-wrap items-center gap-2">
                <MpBadge code={o.marketplace} size={26} />
                <span className="font-bold">№ {o.external_id}</span>
                <Badge tone={ORDER_TONE[o.state]}>{t(O_KEY[o.state])}</Badge>
                <Badge>{o.scheme}</Badge>
                <span className="text-xs text-ink-500">{o.status}</span>
                {isOperator && <span className="text-xs text-ink-500">· {o.seller}</span>}
                <span className="ml-auto text-sm text-ink-500">{fmtDate(o.ordered_at, true)}</span>
              </div>
              <div className="mt-2 divide-y divide-ink-100 text-sm">
                {o.items.map((it, i) => (
                  <div key={i} className="py-1.5 flex gap-3">
                    <span className={clsx("flex-1 min-w-0 truncate", !it.product_id && "text-amber-700")}>{it.name || it.offer_id} <span className="text-ink-400">({it.offer_id})</span></span>
                    <span className="tabular-nums">{it.qty} × {money2(it.price)}</span>
                  </div>
                ))}
              </div>
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <span className="font-bold">{money2(o.total, o.currency)}</span>
                {o.stock_state === "reserved" && <Badge tone="amber">{t("mp_stock_reserved")}</Badge>}
                {o.stock_state === "deducted" && <Badge tone="green">{t("mp_stock_deducted")}</Badge>}
                <div className="ml-auto flex gap-2">
                  {o.actions.map((a) => <Button key={a} size="sm" variant={a === "cancel" ? "outline" : "primary"} onClick={() => act(o, a)}>{t(A_KEY[a])}</Button>)}
                </div>
              </div>
            </div>
          ))}
          <div className="flex justify-center gap-2">
            <Button variant="outline" size="sm" disabled={!data.previous} onClick={() => setPage(page - 1)}>{t("prev")}</Button>
            <Button variant="outline" size="sm" disabled={!data.next} onClick={() => setPage(page + 1)}>{t("next")}</Button>
          </div>
        </div>
      )}
    </div>
  );
}
