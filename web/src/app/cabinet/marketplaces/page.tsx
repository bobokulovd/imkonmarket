"use client";
import clsx from "clsx";
import { useCallback, useEffect, useState } from "react";
import { Spinner, Toast } from "@/components/ui";
import Accounts from "@/components/mp/Accounts";
import { type Account, type MpMeta, type TKey } from "@/components/mp/common";
import Listings from "@/components/mp/Listings";
import Logs from "@/components/mp/Logs";
import MappingTab from "@/components/mp/Mapping";
import Orders from "@/components/mp/Orders";
import { api, errText } from "@/lib/api";
import { useApp } from "@/lib/store";

type Tab = "accounts" | "listings" | "orders" | "mapping" | "logs";

export default function MarketplacesPage() {
  const { t } = useApp();
  const [meta, setMeta] = useState<MpMeta | null>(null);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [tab, setTab] = useState<Tab>("accounts");
  const [accountId, setAccountId] = useState<number | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  const reload = useCallback(() => {
    api<Account[]>("/mp/accounts/", { authed: true }).then((a) => {
      setAccounts(a);
      setAccountId((cur) => cur ?? a[0]?.id ?? null);
    }).catch((e) => setToast(errText(e)));
  }, []);
  useEffect(() => {
    api<MpMeta>("/mp/meta/", { authed: true }).then(setMeta).catch((e) => setToast(errText(e)));
    reload();
    try { const s = sessionStorage.getItem("mp_tab"); if (s) setTab(s as Tab); } catch {}
  }, [reload]);
  const go = (x: Tab) => { setTab(x); try { sessionStorage.setItem("mp_tab", x); } catch {} };

  if (!meta) return <div className="py-20 grid place-items-center"><Spinner /></div>;
  const tabs: [Tab, TKey][] = [["accounts", "mp_accounts"], ["listings", "mp_listings"], ["orders", "mp_orders"], ["mapping", "mp_mapping"], ["logs", "mp_logs"]];
  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-ink-900">{t("marketplaces")}</h1>
        <p className="text-sm text-ink-500 mt-1 max-w-3xl">{t("mp_intro")}</p>
      </div>
      <div className="flex gap-1 overflow-x-auto no-scrollbar border-b border-ink-100">
        {tabs.map(([k, label]) => (
          <button key={k} onClick={() => go(k)} className={clsx("px-4 py-2.5 text-sm font-semibold border-b-2 -mb-px whitespace-nowrap", tab === k ? "border-brand-600 text-brand-700" : "border-transparent text-ink-500")}>{t(label)}</button>
        ))}
      </div>
      {tab === "accounts" && <Accounts meta={meta} accounts={accounts} reload={reload} notify={setToast} openListings={(id) => { setAccountId(id); go("listings"); }} />}
      {tab === "listings" && <Listings accounts={accounts} accountId={accountId} setAccountId={setAccountId} notify={setToast} />}
      {tab === "orders" && <Orders accounts={accounts} notify={setToast} isOperator={meta.is_operator} />}
      {tab === "mapping" && <MappingTab meta={meta} />}
      {tab === "logs" && <Logs accounts={accounts} notify={setToast} />}
      <Toast text={toast} onDone={() => setToast(null)} />
    </div>
  );
}
