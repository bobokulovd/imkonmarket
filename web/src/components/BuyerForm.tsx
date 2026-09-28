"use client";
import clsx from "clsx";
import { Building2, CreditCard, Landmark, Truck, User, Warehouse } from "lucide-react";
import { Badge, Field, Input, Select, Textarea } from "@/components/ui";
import { LANGS, useApp } from "@/lib/store";
import type { Lang } from "@/lib/types";

export type Buyer = {
  buyer_type: "b2c" | "b2b"; buyer_name: string; buyer_pinfl: string; buyer_passport: string; buyer_inn: string;
  buyer_director: string; buyer_phone: string; buyer_email: string; buyer_address: string; buyer_bank_name: string;
  buyer_bank_account: string; buyer_bank_mfo: string; payment_method: "click" | "payme" | "bank";
  delivery_required: boolean; delivery_address: string; comment: string; lang: Lang;
};

export const emptyBuyer = (lang: Lang): Buyer => ({
  buyer_type: "b2c", buyer_name: "", buyer_pinfl: "", buyer_passport: "", buyer_inn: "", buyer_director: "",
  buyer_phone: "+998 ", buyer_email: "", buyer_address: "", buyer_bank_name: "", buyer_bank_account: "",
  buyer_bank_mfo: "", payment_method: "payme", delivery_required: false, delivery_address: "", comment: "", lang,
});

export function validateBuyer(b: Buyer) {
  const e: Partial<Record<keyof Buyer, boolean>> = {};
  if (!b.buyer_name.trim()) e.buyer_name = true;
  if (b.buyer_phone.replace(/\D/g, "").length < 9) e.buyer_phone = true;
  if (b.buyer_type === "b2b" && !/^\d{9}$/.test(b.buyer_inn.trim())) e.buyer_inn = true;
  if (b.buyer_type === "b2c" && !/^\d{14}$/.test(b.buyer_pinfl.trim())) e.buyer_pinfl = true;
  if (b.delivery_required && !b.delivery_address.trim()) e.delivery_address = true;
  return e;
}

function Choice({ active, onClick, icon, title, sub, badge }: { active: boolean; onClick: () => void; icon: React.ReactNode; title: string; sub?: string; badge?: React.ReactNode }) {
  return (
    <button type="button" onClick={onClick}
      className={clsx("text-left rounded-xl border-2 p-3.5 transition flex gap-3 items-start", active ? "border-brand-600 bg-brand-50/60" : "border-ink-100 hover:border-ink-300 bg-white")}>
      <span className={clsx("w-10 h-10 rounded-lg grid place-items-center shrink-0", active ? "bg-brand-600 text-white" : "bg-ink-100 text-ink-700")}>{icon}</span>
      <span className="min-w-0">
        <span className="font-semibold text-ink-900 flex items-center gap-2 flex-wrap">{title} {badge}</span>
        {sub && <span className="block text-xs text-ink-500 mt-0.5 leading-snug">{sub}</span>}
      </span>
    </button>
  );
}

export default function BuyerForm({ b, set, errors, allowOnline = true }: { b: Buyer; set: (patch: Partial<Buyer>) => void; errors: Partial<Record<keyof Buyer, boolean>>; allowOnline?: boolean }) {
  const { t, meta } = useApp();
  const req = t("required");
  const inp = (k: keyof Buyer, props: React.InputHTMLAttributes<HTMLInputElement> = {}) => (
    <Input value={String(b[k] ?? "")} onChange={(e) => set({ [k]: e.target.value } as any)} {...props}
      className={errors[k] ? "border-red-400 focus:border-red-500 focus:ring-red-100" : ""} />
  );
  return (
    <div className="space-y-6">
      <div>
        <div className="text-sm font-semibold text-ink-700 mb-2">{t("buyer_type")}</div>
        <div className="grid sm:grid-cols-2 gap-3">
          <Choice active={b.buyer_type === "b2c"} onClick={() => set({ buyer_type: "b2c" })} icon={<User className="w-5 h-5" />} title={t("individual")} sub="B2C" />
          <Choice active={b.buyer_type === "b2b"} onClick={() => set({ buyer_type: "b2b", payment_method: "bank" })} icon={<Building2 className="w-5 h-5" />} title={t("company")} sub="B2B" />
        </div>
      </div>

      {b.buyer_type === "b2c" ? (
        <div className="grid sm:grid-cols-2 gap-4">
          <Field label={t("full_name") + " *"} error={errors.buyer_name ? req : undefined} className="sm:col-span-2">{inp("buyer_name", { autoComplete: "name" })}</Field>
          <Field label={t("pinfl") + " *"} error={errors.buyer_pinfl ? req : undefined}>{inp("buyer_pinfl", { inputMode: "numeric", maxLength: 14 })}</Field>
          <Field label={t("passport")}>{inp("buyer_passport", { placeholder: "AA1234567", maxLength: 12 })}</Field>
          <Field label={t("phone") + " *"} error={errors.buyer_phone ? req : undefined}>{inp("buyer_phone", { inputMode: "tel", autoComplete: "tel" })}</Field>
          <Field label={t("email")}>{inp("buyer_email", { type: "email" })}</Field>
          <Field label={t("address")} className="sm:col-span-2">{inp("buyer_address")}</Field>
        </div>
      ) : (
        <div className="grid sm:grid-cols-2 gap-4">
          <Field label={t("company_name") + " *"} error={errors.buyer_name ? req : undefined} className="sm:col-span-2">{inp("buyer_name", { placeholder: "\"...\" MChJ" })}</Field>
          <Field label={t("inn") + " *"} error={errors.buyer_inn ? req : undefined}>{inp("buyer_inn", { inputMode: "numeric", maxLength: 9 })}</Field>
          <Field label={t("director")}>{inp("buyer_director")}</Field>
          <Field label={t("phone") + " *"} error={errors.buyer_phone ? req : undefined}>{inp("buyer_phone", { inputMode: "tel" })}</Field>
          <Field label={t("email")}>{inp("buyer_email", { type: "email" })}</Field>
          <Field label={t("address")} className="sm:col-span-2">{inp("buyer_address")}</Field>
          <Field label={t("bank_name")}>{inp("buyer_bank_name")}</Field>
          <div className="grid grid-cols-[1fr_110px] gap-3">
            <Field label={t("bank_account")}>{inp("buyer_bank_account", { inputMode: "numeric", maxLength: 20 })}</Field>
            <Field label={t("mfo")}>{inp("buyer_bank_mfo", { inputMode: "numeric", maxLength: 5 })}</Field>
          </div>
        </div>
      )}

      <div>
        <div className="text-sm font-semibold text-ink-700 mb-2">{t("payment_method")}</div>
        <div className="grid sm:grid-cols-3 gap-3">
          {allowOnline && (["payme", "click"] as const).map((m) => (
            <Choice key={m} active={b.payment_method === m} onClick={() => set({ payment_method: m })} icon={<CreditCard className="w-5 h-5" />}
              title={m === "payme" ? "Payme" : "Click"} badge={meta?.payments?.[m]?.demo ? <Badge tone="amber">{t("demo")}</Badge> : null} />
          ))}
          <Choice active={b.payment_method === "bank"} onClick={() => set({ payment_method: "bank" })} icon={<Landmark className="w-5 h-5" />} title={t("pay_bank")} />
        </div>
        <div className="text-xs text-ink-500 mt-2">{b.payment_method === "bank" ? t("pay_bank_note") : t("pay_online_note")}</div>
      </div>

      <div>
        <div className="text-sm font-semibold text-ink-700 mb-2">{t("delivery")}</div>
        <div className="grid sm:grid-cols-2 gap-3">
          <Choice active={!b.delivery_required} onClick={() => set({ delivery_required: false })} icon={<Warehouse className="w-5 h-5" />} title={t("pickup")} />
          <Choice active={b.delivery_required} onClick={() => set({ delivery_required: true })} icon={<Truck className="w-5 h-5" />} title={t("delivery_to")} />
        </div>
        {b.delivery_required && (
          <Field label={t("delivery_address") + " *"} error={errors.delivery_address ? req : undefined} className="mt-3">{inp("delivery_address")}</Field>
        )}
      </div>

      <div className="grid sm:grid-cols-2 gap-4">
        <Field label={t("contract_lang")}>
          <Select value={b.lang} onChange={(e) => set({ lang: e.target.value as Lang })}>
            {LANGS.map((l) => <option key={l.code} value={l.code}>{l.label}</option>)}
          </Select>
        </Field>
        <Field label={t("comment")} className="sm:col-span-2">
          <Textarea value={b.comment} onChange={(e) => set({ comment: e.target.value })} rows={3} />
        </Field>
      </div>
    </div>
  );
}
