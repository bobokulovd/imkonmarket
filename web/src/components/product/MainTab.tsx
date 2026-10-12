"use client";
import clsx from "clsx";
import { Info } from "lucide-react";
import { useState } from "react";
import { useMe } from "@/components/CabinetShell";
import { Button, Field, Input, Select, Textarea } from "@/components/ui";
import { api } from "@/lib/api";
import { LANGS, useApp } from "@/lib/store";
import { toCyrl, toNew } from "@/lib/translit";
import type { I18n, Lang, SellerProduct } from "@/lib/types";
import { decimalOnly, digitsOnly, ErrorBox, fieldErrors, numStr, errMsg } from "./shared";

export const UNITS = ["dona", "juft", "kg", "m²", "m³", "p/m", "to'plam", "tonna", "xizmat"];
export const DEFAULT_COUNTRY = "O'zbekiston";

type Form = {
  name: I18n; spec: I18n; description: I18n; category: string; unit: string; price: string; stock: string;
  daily_capacity: string; lead_days: string; min_order: string; delivery: boolean; is_active: boolean; note: string;
  seller: string; brand: string; country: string;
};

const fromProduct = (pr: SellerProduct | null, cat: string): Form => pr ? {
  name: pr.name || {}, spec: pr.spec || {}, description: pr.description || {}, category: pr.category, unit: pr.unit,
  price: numStr(pr.price), stock: pr.stock === null ? "" : String(pr.stock),
  daily_capacity: pr.daily_capacity ? String(pr.daily_capacity) : "", lead_days: String(pr.lead_days ?? 3),
  min_order: String(pr.min_order ?? 1), delivery: pr.delivery, is_active: pr.is_active, note: pr.note || "", seller: "",
  brand: pr.brand || "", country: pr.country || "",
} : {
  name: {}, spec: {}, description: {}, category: cat, unit: "dona", price: "", stock: "", daily_capacity: "", lead_days: "3",
  min_order: "1", delivery: true, is_active: true, note: "", seller: "", brand: "", country: DEFAULT_COUNTRY,
};

export default function MainTab({ product, defaultCategory, onSaved, onClose }: {
  product: SellerProduct | null; defaultCategory: string; onSaved: (p: SellerProduct, created: boolean) => void; onClose: () => void;
}) {
  const { t, p, meta, unit, money } = useApp();
  const { me } = useMe();
  const [f, setF] = useState<Form>(() => fromProduct(product, defaultCategory));
  const [tab, setTab] = useState<Lang>("uz");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [fe, setFe] = useState<Record<string, string>>({});
  const hasVariants = !!product?.has_variants;

  const setI = (k: "name" | "spec" | "description", v: string) => {
    const cur: I18n = { ...f[k] };
    if (tab === "uz") {
      // avtomatik to'ldirilgan (uz dan olingan) qiymatlarni tozalaymiz — backend qayta hosil qiladi
      const old = cur.uz || "";
      (Object.keys(cur) as Lang[]).forEach((l) => {
        if (l === "uz") return;
        if (cur[l] === old || (l === "uz_cyrl" && cur[l] === toCyrl(old)) || (l === "uz_new" && cur[l] === toNew(old))) cur[l] = "";
      });
    }
    cur[tab] = v;
    setF({ ...f, [k]: cur });
  };

  const save = async () => {
    setBusy(true); setErr(""); setFe({});
    const json: Record<string, unknown> = {
      name: f.name, spec: f.spec, description: f.description, category: f.category, unit: f.unit,
      daily_capacity: f.daily_capacity || null, lead_days: f.lead_days || 3, min_order: f.min_order || 1,
      delivery: f.delivery, is_active: f.is_active, note: f.note, brand: f.brand.trim(), country: f.country.trim(),
    };
    if (!hasVariants) { json.price = f.price || null; json.stock = f.stock === "" ? null : f.stock; }
    if (!product && f.seller) json.seller = f.seller;
    try {
      const saved = product
        ? await api<SellerProduct>(`/seller/products/${product.id}/`, { method: "PATCH", json, authed: true })
        : await api<SellerProduct>("/seller/products/", { method: "POST", json, authed: true });
      setF(fromProduct(saved, saved.category));
      onSaved(saved, !product);
    } catch (e) { setErr(errMsg(e)); setFe(fieldErrors(e)); } finally { setBusy(false); }
  };

  const catChanged = !!product && f.category !== product.category;

  return (
    <div className="space-y-5">
      <div>
        <div className="flex gap-1 overflow-x-auto no-scrollbar border-b border-ink-100">
          {LANGS.map((l) => (
            <button key={l.code} type="button" onClick={() => setTab(l.code)} className={clsx("px-3 py-2 text-sm font-semibold border-b-2 -mb-px whitespace-nowrap", tab === l.code ? "border-brand-600 text-brand-700" : "border-transparent text-ink-500")}>
              {l.short}{f.name[l.code] ? " ✓" : ""}
            </button>
          ))}
        </div>
        <div className="grid gap-3 mt-3">
          <Field label={`${t("name")} (${LANGS.find((l) => l.code === tab)?.label})${tab === "uz" ? " *" : ""}`} error={fe.name}><Input value={f.name[tab] || ""} onChange={(e) => setI("name", e.target.value)} placeholder={tab !== "uz" ? f.name.uz : ""} /></Field>
          <Field label={t("spec")}><Input value={f.spec[tab] || ""} onChange={(e) => setI("spec", e.target.value)} placeholder={tab !== "uz" ? f.spec.uz : ""} /></Field>
          <Field label={t("description")}><Textarea rows={3} value={f.description[tab] || ""} onChange={(e) => setI("description", e.target.value)} /></Field>
          <p className="text-xs text-ink-500">{t("tr_hint")}</p>
        </div>
      </div>
      <div className="grid sm:grid-cols-3 gap-3">
        {me.seller.role === "operator" && !product && (
          <Field label={t("seller")} className="sm:col-span-3"><Select value={f.seller} onChange={(e) => setF({ ...f, seller: e.target.value })}>
            <option value="">—</option>{meta?.sellers.map((s) => <option key={s.code} value={s.code}>{p(s.name)}</option>)}</Select></Field>
        )}
        <Field label={t("category")} className="sm:col-span-2" error={fe.category} hint={catChanged ? t("pe_cat_change_hint") : undefined}>
          <Select value={f.category} onChange={(e) => setF({ ...f, category: e.target.value })}>{meta?.categories.map((c) => <option key={c.slug} value={c.slug}>{p(c.name)}</option>)}</Select>
        </Field>
        <Field label={t("unit")} error={fe.unit}><Select value={f.unit} onChange={(e) => setF({ ...f, unit: e.target.value })}>{UNITS.map((u) => <option key={u} value={u}>{unit(u)}</option>)}</Select></Field>
        <Field label={t("mp_brand")} hint={t("pe_brand_hint")} error={fe.brand}><Input value={f.brand} onChange={(e) => setF({ ...f, brand: e.target.value })} /></Field>
        <Field label={t("mp_country")} error={fe.country}><Input value={f.country} onChange={(e) => setF({ ...f, country: e.target.value })} placeholder={DEFAULT_COUNTRY} /></Field>
        <Field label={t("notes")}><Input value={f.note} onChange={(e) => setF({ ...f, note: e.target.value })} /></Field>
        {hasVariants && product ? (
          <div className="sm:col-span-3 rounded-xl bg-brand-50 text-brand-700 text-sm p-3 flex gap-2">
            <Info className="w-4 h-4 shrink-0 mt-0.5" />
            <div>
              <div className="font-semibold">{t("pe_from_variants")}</div>
              <div className="mt-0.5">{t("price")}: {product.price ? t("pe_from", { v: money(product.price) }) : t("price_on_request")} · {t("stock")}: {product.stock ?? "∞"}</div>
            </div>
          </div>
        ) : (
          <>
            <Field label={`${t("price")}, ${t("sum")}`} hint={`∅ = ${t("price_on_request")}`} error={fe.price}><Input inputMode="decimal" value={f.price} onChange={(e) => setF({ ...f, price: decimalOnly(e.target.value) })} /></Field>
            <Field label={t("stock")} hint={t("stock_hint")} error={fe.stock}><Input inputMode="numeric" value={f.stock} onChange={(e) => setF({ ...f, stock: digitsOnly(e.target.value) })} /></Field>
          </>
        )}
        <Field label={t("daily_capacity")}><Input inputMode="numeric" value={f.daily_capacity} onChange={(e) => setF({ ...f, daily_capacity: digitsOnly(e.target.value) })} /></Field>
        <Field label={t("lead_days", { n: "" }).replace(/[:\s]+$/, "")}><Input inputMode="numeric" value={f.lead_days} onChange={(e) => setF({ ...f, lead_days: digitsOnly(e.target.value) })} /></Field>
        <Field label={t("min_order", { n: "" }).replace(/[:\s]+$/, "")}><Input inputMode="numeric" value={f.min_order} onChange={(e) => setF({ ...f, min_order: digitsOnly(e.target.value) })} /></Field>
      </div>
      <div className="flex flex-wrap gap-5 text-sm">
        <label className="flex items-center gap-2"><input type="checkbox" className="w-4 h-4 accent-brand-600" checked={f.delivery} onChange={(e) => setF({ ...f, delivery: e.target.checked })} /> {t("delivery_yes")}</label>
        <label className="flex items-center gap-2"><input type="checkbox" className="w-4 h-4 accent-brand-600" checked={f.is_active} onChange={(e) => setF({ ...f, is_active: e.target.checked })} /> {t("published")}</label>
      </div>
      {!product && <p className="text-xs text-ink-500 flex gap-1.5"><Info className="w-4 h-4 shrink-0" />{t("pe_new_hint")}</p>}
      <ErrorBox text={err} />
      <div className="flex gap-2 justify-end">
        <Button variant="ghost" onClick={onClose}>{t("close")}</Button>
        <Button loading={busy} disabled={!f.name.uz?.trim()} onClick={save}>{product ? t("save") : t("pe_create_continue")}</Button>
      </div>
    </div>
  );
}
