"use client";
import { ShieldAlert, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";
import { Badge, Spinner, STATUS_TONE } from "@/components/ui";
import { api } from "@/lib/api";
import { useApp } from "@/lib/store";
import type { I18n } from "@/lib/types";
import { fmtDate } from "@/lib/util";

type V = { valid: boolean; number: string; date: string; status: string; seller: I18n; seller_inn: string; agent: I18n | null; buyer: string; buyer_type: string; total: string; paid: string };

export default function VerifyPage({ params }: { params: { token: string } }) {
  const { t, p, money } = useApp();
  const [v, setV] = useState<V | null | undefined>(undefined);
  useEffect(() => { api<V>(`/contracts/verify/${params.token}/`).then(setV).catch(() => setV(null)); }, [params.token]);
  if (v === undefined) return <div className="py-32 grid place-items-center"><Spinner /></div>;
  return (
    <div className="container-x py-10 max-w-lg">
      <div className="card p-6">
        {v ? (
          <>
            <div className="flex items-center gap-3 text-emerald-700"><ShieldCheck className="w-10 h-10" /><div className="text-xl font-extrabold">{t("verify_ok")}</div></div>
            <dl className="mt-6 divide-y divide-ink-100 text-sm">
              {[
                [t("contract_no"), <span className="font-mono">{v.number}</span>],
                [t("date"), fmtDate(v.date)],
                [t("status"), <Badge tone={STATUS_TONE[v.status]}>{t(`c_${v.status}` as any)}</Badge>],
                [t("seller"), `${p(v.seller)} (${t("inn")} ${v.seller_inn})`],
                ...(v.agent ? [[t("agent"), p(v.agent)]] : []),
                [t("buyer"), v.buyer],
                [t("amount"), money(v.total)],
                [t("paid"), money(v.paid)],
              ].map(([k, val]: any, i) => (
                <div key={i} className="py-2.5 grid grid-cols-[40%_1fr] gap-3"><dt className="text-ink-500">{k}</dt><dd className="font-medium">{val}</dd></div>
              ))}
            </dl>
          </>
        ) : (
          <div className="flex items-center gap-3 text-red-700"><ShieldAlert className="w-10 h-10" /><div className="text-xl font-extrabold">{t("verify_bad")}</div></div>
        )}
      </div>
    </div>
  );
}
