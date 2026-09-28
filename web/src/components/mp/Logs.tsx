"use client";
import clsx from "clsx";
import { RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Button, Select, Spinner } from "@/components/ui";
import { api, errText, qs } from "@/lib/api";
import { useApp } from "@/lib/store";
import type { Paged } from "@/lib/types";
import { fmtDate } from "@/lib/util";
import type { Account } from "./common";

type Row = { id: number; account: number; operation: string; method: string; endpoint: string; http_status: number | null; ok: boolean; duration_ms: number; error: string; created_at: string };

export default function Logs({ accounts, notify }: { accounts: Account[]; notify: (s: string) => void }) {
  const { t } = useApp();
  const [data, setData] = useState<Paged<Row> | null>(null);
  const [account, setAccount] = useState("");
  const [errors, setErrors] = useState(false);
  const [page, setPage] = useState(1);
  const load = useCallback(() => {
    api<Paged<Row>>(`/mp/logs/${qs({ account, errors: errors ? 1 : "", page, page_size: 50 })}`, { authed: true }).then(setData).catch((e) => notify(errText(e)));
  }, [account, errors, page, notify]);
  useEffect(() => { load(); }, [load]);
  const name = (id: number) => { const a = accounts.find((x) => x.id === id); return a ? `${a.marketplace_name} ${a.title}` : id; };
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2 items-center">
        <Select className="!w-auto" value={account} onChange={(e) => { setAccount(e.target.value); setPage(1); }}>
          <option value="">{t("all")}</option>{accounts.map((a) => <option key={a.id} value={a.id}>{a.marketplace_name} {a.title}</option>)}
        </Select>
        <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={errors} onChange={(e) => setErrors(e.target.checked)} />{t("mp_only_errors")}</label>
        <Button variant="outline" onClick={load}><RefreshCw className="w-4 h-4" /></Button>
      </div>
      {!data ? <Spinner /> : (
        <div className="card overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-left text-xs text-ink-500"><tr>
              <th className="p-2.5">{t("date")}</th><th className="p-2.5">{t("marketplaces")}</th><th className="p-2.5">{t("mp_op")}</th>
              <th className="p-2.5">Endpoint</th><th className="p-2.5">HTTP</th><th className="p-2.5">{t("mp_duration")}</th><th className="p-2.5">{t("error")}</th></tr></thead>
            <tbody className="divide-y divide-ink-100">
              {data.results.map((r) => (
                <tr key={r.id} className={clsx(!r.ok && "bg-red-50/50")}>
                  <td className="p-2.5 whitespace-nowrap text-ink-500">{fmtDate(r.created_at, true)}</td>
                  <td className="p-2.5 whitespace-nowrap">{name(r.account)}</td>
                  <td className="p-2.5">{r.operation}</td>
                  <td className="p-2.5 font-mono text-xs">{r.method} {r.endpoint}</td>
                  <td className={clsx("p-2.5 font-semibold", r.ok ? "text-emerald-700" : "text-red-700")}>{r.http_status ?? "—"}</td>
                  <td className="p-2.5 tabular-nums">{r.duration_ms}</td>
                  <td className="p-2.5 text-xs text-red-700 max-w-[380px]">{r.error}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {data && (
        <div className="flex justify-center gap-2">
          <Button variant="outline" size="sm" disabled={!data.previous} onClick={() => setPage(page - 1)}>{t("prev")}</Button>
          <Button variant="outline" size="sm" disabled={!data.next} onClick={() => setPage(page + 1)}>{t("next")}</Button>
        </div>
      )}
    </div>
  );
}
