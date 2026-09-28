"use client";
import { CheckCircle2, CreditCard, FlaskConical } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { Badge, Button, Spinner } from "@/components/ui";
import { api, errText } from "@/lib/api";
import { useApp } from "@/lib/store";
import type { I18n } from "@/lib/types";

type Info = { payment_id: number; method: string; amount: string; status: string; contract: string; seller: I18n; order_token: string };

function DemoPay({ id }: { id: string }) {
  const { t, p, money } = useApp();
  const sp = useSearchParams();
  const router = useRouter();
  const c = sp.get("c") || "";
  const [info, setInfo] = useState<Info | null | undefined>(undefined);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [done, setDone] = useState(false);
  useEffect(() => { api<Info>(`/pay/demo/${id}/?c=${c}`).then(setInfo).catch(() => setInfo(null)); }, [id, c]);
  if (info === undefined) return <div className="py-32 grid place-items-center"><Spinner /></div>;
  if (!info) return <div className="py-20 text-center">{t("not_found")}</div>;
  const confirm = async () => {
    setBusy(true);
    try {
      await api(`/pay/demo/${id}/confirm/`, { method: "POST", json: { c } });
      setDone(true);
      setTimeout(() => router.push(`/order/${info.order_token}`), 1500);
    } catch (e) { setErr(errText(e)); } finally { setBusy(false); }
  };
  return (
    <div className="container-x py-10 max-w-md">
      <div className="card p-6">
        <div className="flex items-center justify-between">
          <div className="text-2xl font-extrabold">{info.method === "payme" ? "Payme" : "Click"}</div>
          <Badge tone="amber"><FlaskConical className="w-3.5 h-3.5" /> {t("demo")}</Badge>
        </div>
        <div className="text-sm text-ink-500 mt-1">{t("demo_title")}</div>
        <div className="mt-6 rounded-xl bg-ink-100/60 p-4 text-sm space-y-1.5">
          <div className="flex justify-between"><span className="text-ink-500">{t("contract")}</span><span className="font-mono">{info.contract}</span></div>
          <div className="flex justify-between"><span className="text-ink-500">{t("seller")}</span><span>{p(info.seller)}</span></div>
          <div className="flex justify-between text-base pt-2"><span className="font-semibold">{t("amount")}</span><span className="font-extrabold">{money(info.amount)}</span></div>
        </div>
        <p className="text-xs text-amber-800 bg-amber-50 rounded-lg p-3 mt-4">{t("demo_note")}</p>
        {done || info.status === "paid" ? (
          <div className="mt-5 flex items-center gap-2 text-emerald-700 font-semibold"><CheckCircle2 className="w-6 h-6" /> {t("demo_done")}</div>
        ) : (
          <Button size="lg" className="w-full mt-5" loading={busy} onClick={confirm}><CreditCard className="w-5 h-5" /> {t("demo_btn")}</Button>
        )}
        {err && <div className="text-sm text-red-700 mt-2">{err}</div>}
      </div>
    </div>
  );
}
export default function Page({ params }: { params: { id: string } }) {
  return <Suspense><DemoPay id={params.id} /></Suspense>;
}
