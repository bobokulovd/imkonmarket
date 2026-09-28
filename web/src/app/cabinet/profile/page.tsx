"use client";
import { KeyRound, Landmark } from "lucide-react";
import { useEffect, useState } from "react";
import { useMe } from "@/components/CabinetShell";
import { Button, Field, Input, Textarea, Toast } from "@/components/ui";
import { api, errText } from "@/lib/api";
import { useApp } from "@/lib/store";

export default function ProfilePage() {
  const { t, p } = useApp();
  const { me, reload } = useMe();
  const s = me.seller;
  const [f, setF] = useState({ full_name: s.full_name, address: s.address, phone: s.phone, email: s.email, director: s.director, bank_name: s.bank_name, bank_account: s.bank_account, bank_mfo: s.bank_mfo, treasury_account: s.treasury_account, description: s.description?.uz || "" });
  const [pw, setPw] = useState({ old_password: "", new_password: "" });
  const [busy, setBusy] = useState("");
  const [err, setErr] = useState("");
  const [toast, setToast] = useState<string | null>(null);
  useEffect(() => { setErr(""); }, [f, pw]);

  const save = async () => {
    setBusy("p"); setErr("");
    try {
      const { description, ...rest } = f;
      await api("/auth/me/", { method: "PATCH", authed: true, json: { ...rest, description: { ...(s.description || {}), uz: description, uz_cyrl: "", uz_new: "" } } });
      reload(); setToast(t("saved"));
    } catch (e) { setErr(errText(e)); } finally { setBusy(""); }
  };
  const changePw = async () => {
    setBusy("pw"); setErr("");
    try { await api("/auth/change-password/", { method: "POST", authed: true, json: pw }); setPw({ old_password: "", new_password: "" }); setToast(t("saved")); }
    catch (e) { setErr(errText(e)); } finally { setBusy(""); }
  };
  const inp = (k: keyof typeof f, props: any = {}) => <Input value={f[k]} onChange={(e) => setF({ ...f, [k]: e.target.value })} {...props} />;

  return (
    <div className="max-w-3xl">
      <h1 className="text-2xl font-extrabold">{t("profile_title")}</h1>
      <div className="text-ink-500 text-sm mt-1">{p(s.name)} · {t("inn")}: {s.inn} · {p(s.region_i18n)}, {p(s.district_i18n)}</div>
      <div className="card p-5 mt-5">
        <div className="font-bold flex items-center gap-2 mb-4"><Landmark className="w-5 h-5 text-brand-600" /> {t("requisites")}</div>
        <div className="grid sm:grid-cols-2 gap-4">
          <Field label={t("legal_name")} className="sm:col-span-2">{inp("full_name", { placeholder: p(s.name) })}</Field>
          <Field label={t("address")} className="sm:col-span-2">{inp("address", { placeholder: `${p(s.region_i18n)}, ${p(s.district_i18n)}` })}</Field>
          <Field label={t("director")}>{inp("director")}</Field>
          <Field label={t("phone")}>{inp("phone")}</Field>
          <Field label={t("email")}>{inp("email")}</Field>
          <Field label={t("bank_name")}>{inp("bank_name")}</Field>
          <Field label={t("bank_account")}>{inp("bank_account", { maxLength: 20, inputMode: "numeric" })}</Field>
          <Field label={t("mfo")}>{inp("bank_mfo", { maxLength: 5, inputMode: "numeric" })}</Field>
          <Field label={t("treasury")} className="sm:col-span-2">{inp("treasury_account")}</Field>
          <Field label={t("description")} className="sm:col-span-2"><Textarea rows={3} value={f.description} onChange={(e) => setF({ ...f, description: e.target.value })} /></Field>
        </div>
        <Button className="mt-5" loading={busy === "p"} onClick={save}>{t("save")}</Button>
      </div>
      <div className="card p-5 mt-5">
        <div className="font-bold flex items-center gap-2 mb-4"><KeyRound className="w-5 h-5 text-brand-600" /> {t("change_password")}</div>
        <div className="grid sm:grid-cols-2 gap-4">
          <Field label={t("old_password")}><Input type="password" value={pw.old_password} onChange={(e) => setPw({ ...pw, old_password: e.target.value })} /></Field>
          <Field label={t("new_password")} hint="min 8"><Input type="password" value={pw.new_password} onChange={(e) => setPw({ ...pw, new_password: e.target.value })} /></Field>
        </div>
        <Button className="mt-5" variant="outline" loading={busy === "pw"} disabled={pw.new_password.length < 8} onClick={changePw}>{t("change_password")}</Button>
      </div>
      {err && <div className="text-sm text-red-700 bg-red-50 rounded-lg p-3 mt-4">{err}</div>}
      <Toast text={toast} onDone={() => setToast(null)} />
    </div>
  );
}
