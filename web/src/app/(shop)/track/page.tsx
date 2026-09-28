"use client";
import { PackageSearch } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Button, Field, Input } from "@/components/ui";
import { api } from "@/lib/api";
import { useApp } from "@/lib/store";

export default function TrackPage() {
  const { t } = useApp();
  const router = useRouter();
  const [number, setNumber] = useState("");
  const [phone, setPhone] = useState("+998 ");
  const [err, setErr] = useState(false);
  const [busy, setBusy] = useState(false);
  const [recent, setRecent] = useState<{ number: string; token: string }[]>([]);
  useEffect(() => { try { setRecent(JSON.parse(localStorage.getItem("ub_orders") || "[]")); } catch {} }, []);

  const find = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true); setErr(false);
    try {
      const r = await api<{ token: string }>(`/orders/track/?number=${encodeURIComponent(number.trim())}&phone=${encodeURIComponent(phone)}`);
      router.push(`/order/${r.token}`);
    } catch { setErr(true); } finally { setBusy(false); }
  };
  return (
    <div className="container-x py-10 max-w-md">
      <div className="card p-6">
        <div className="w-12 h-12 rounded-xl bg-brand-50 text-brand-700 grid place-items-center"><PackageSearch className="w-6 h-6" /></div>
        <h1 className="text-2xl font-extrabold mt-4">{t("track_title")}</h1>
        <p className="text-ink-500 mt-1">{t("track_sub")}</p>
        <form onSubmit={find} className="mt-5 space-y-4">
          <Field label={t("order_number")}><Input value={number} onChange={(e) => setNumber(e.target.value.toUpperCase())} placeholder="A-2026-000001" required /></Field>
          <Field label={t("phone")}><Input value={phone} onChange={(e) => setPhone(e.target.value)} inputMode="tel" required /></Field>
          {err && <div className="text-sm text-red-700">{t("not_found")}</div>}
          <Button size="lg" className="w-full" loading={busy}>{t("find")}</Button>
        </form>
      </div>
      {recent.length > 0 && (
        <div className="card p-5 mt-4">
          <div className="font-semibold mb-2 text-sm text-ink-500">{t("history")}</div>
          <div className="flex flex-wrap gap-2">
            {recent.map((r) => <Link key={r.token} href={`/order/${r.token}`} className="font-mono text-sm px-3 py-1.5 rounded-lg bg-ink-100 hover:bg-brand-50 hover:text-brand-700">{r.number}</Link>)}
          </div>
        </div>
      )}
    </div>
  );
}
