"use client";
import { BadgeCheck, FileSignature, Warehouse } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { LangSwitch, Logo, LogoMark } from "@/components/Shell";
import { Button, Field, Input } from "@/components/ui";
import { api, auth } from "@/lib/api";
import { useApp } from "@/lib/store";

export default function LoginPage() {
  const { t } = useApp();
  const router = useRouter();
  const [username, setU] = useState("");
  const [password, setP] = useState("");
  const [err, setErr] = useState(false);
  const [busy, setBusy] = useState(false);
  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true); setErr(false);
    try {
      const r = await api<{ access: string; refresh: string }>("/auth/login/", { method: "POST", json: { username: username.trim(), password } });
      auth.set(r.access, r.refresh);
      router.replace("/cabinet");
    } catch { setErr(true); } finally { setBusy(false); }
  };
  return (
    <div className="min-h-screen grid lg:grid-cols-2">
      <div className="hidden lg:flex flex-col justify-between bg-gradient-to-br from-brand-950 via-brand-900 to-brand-700 text-white p-12 relative overflow-hidden">
        <div className="absolute -right-24 -bottom-24 w-96 h-96 rounded-full bg-brand-500/20 blur-3xl" />
        <div className="absolute right-12 top-24 opacity-10"><LogoMark className="w-72 h-72" /></div>
        <Logo light />
        <div className="relative">
          <div className="text-accent-400 font-bold tracking-wide uppercase text-sm">ImkonMarket</div>
          <h1 className="text-4xl font-extrabold mt-2 leading-tight max-w-md">{t("cabinet")}</h1>
          <p className="text-brand-100 mt-3 max-w-md">{t("agent_sub")}</p>
          <ul className="mt-8 space-y-3 text-brand-100">
            {[[Warehouse, t("general_catalog")], [FileSignature, t("contracts")], [BadgeCheck, t("applications")]].map(([I, l]: any) => (
              <li key={l} className="flex items-center gap-3"><span className="w-9 h-9 rounded-lg bg-white/10 grid place-items-center"><I className="w-5 h-5" /></span>{l}</li>
            ))}
          </ul>
        </div>
        <div className="text-brand-200 text-sm relative">© {new Date().getFullYear()} ImkonMarket</div>
      </div>
      <div className="flex flex-col">
        <div className="flex justify-between items-center p-4"><div className="lg:hidden"><Logo /></div><div className="ml-auto"><LangSwitch /></div></div>
        <div className="flex-1 grid place-items-center p-6">
          <form onSubmit={submit} className="w-full max-w-sm">
            <LogoMark className="w-14 h-14" />
            <h2 className="text-2xl font-extrabold mt-4">Imkon<span className="text-brand-600">Market</span> · {t("sign_in")}</h2>
            <p className="text-ink-500 mt-1 text-sm">{t("cabinet_login_sub")}</p>
            <div className="space-y-4 mt-6">
              <Field label={t("username")}><Input value={username} onChange={(e) => setU(e.target.value)} autoComplete="username" placeholder="jiek14" autoCapitalize="none" required /></Field>
              <Field label={t("password")}><Input type="password" value={password} onChange={(e) => setP(e.target.value)} autoComplete="current-password" required /></Field>
              {err && <div className="text-sm text-red-700 bg-red-50 rounded-lg px-3 py-2">{t("wrong_login")}</div>}
              <Button size="lg" className="w-full" loading={busy}>{t("sign_in")}</Button>
              <Link href="/" className="block text-center text-sm text-ink-500 hover:text-ink-900">← {t("home")}</Link>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
