"use client";
import clsx from "clsx";
import { Check } from "lucide-react";
import { useState } from "react";
import { Button, Field, Input, Select, Spinner } from "@/components/ui";
import { api } from "@/lib/api";
import { useApp } from "@/lib/store";
import type { AttributeDef, AttrValue, SellerProduct } from "@/lib/types";
import IkpuPicker from "./IkpuPicker";
import { decimalOnly, digitsOnly, eanCheck, ErrorBox, fieldErrors, numStr, type ProductChange, errMsg, StepBar } from "./shared";

type Val = string | string[];
type Card = { barcode: string; weight_kg: string; length_cm: string; width_cm: string; height_cm: string };

const toVal = (d: AttributeDef, v: AttrValue | undefined): Val => {
  if (v === undefined || v === null) return d.multi && d.type === "enum" ? [] : "";
  if (d.type === "enum" && d.multi) return (Array.isArray(v) ? v : [v]).map(String);
  if (Array.isArray(v)) return v.length ? String(v[0]) : "";
  return String(v);
};
const fromVal = (d: AttributeDef, v: Val): AttrValue | undefined => {
  if (Array.isArray(v)) return v.length ? v : undefined;
  if (v === "") return undefined;
  if (d.type === "bool") return v === "true";
  if (d.type === "number") { const n = Number(v); return Number.isFinite(n) ? n : v; }
  return v;
};
const cardOf = (pr: SellerProduct): Card => ({
  barcode: pr.barcode || "", weight_kg: numStr(pr.weight_kg), length_cm: numStr(pr.length_cm), width_cm: numStr(pr.width_cm), height_cm: numStr(pr.height_cm),
});

export default function AttributesTab({ product, defs, onChange, onNext }: { product: SellerProduct; defs: AttributeDef[] | null; onChange: ProductChange; onNext?: () => void }) {
  const { t, p } = useApp();
  const list = (defs || []).filter((d) => !d.variant);
  const [vals, setVals] = useState<Record<string, Val>>({});
  const [inited, setInited] = useState(false);
  const [card, setCard] = useState<Card>(() => cardOf(product));
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [fe, setFe] = useState<Record<string, string>>({});
  const [ok, setOk] = useState(false);

  // lug'at kelgach qiymatlarni bir marta boshlang'ich holatga keltiramiz
  if (defs && !inited) {
    setInited(true);
    setVals(Object.fromEntries(list.map((d) => [d.code, toVal(d, product.attributes?.[d.code])])));
  }

  const setV = (code: string, v: Val) => { setVals((s) => ({ ...s, [code]: v })); setOk(false); };
  const setC = (k: keyof Card, v: string) => { setCard((s) => ({ ...s, [k]: v })); setOk(false); };
  const ean = eanCheck(card.barcode);
  const missing = list.filter((d) => d.required && (Array.isArray(vals[d.code]) ? !vals[d.code].length : !vals[d.code]));

  const save = async (): Promise<boolean> => {
    setBusy(true); setErr(""); setFe({}); setOk(false);
    const attributes: Record<string, AttrValue> = {};
    for (const d of list) {
      const v = fromVal(d, vals[d.code] ?? "");
      if (v !== undefined) attributes[d.code] = v;
    }
    const json = {
      attributes, barcode: card.barcode.replace(/\s+/g, ""), weight_kg: card.weight_kg || null,
      length_cm: card.length_cm || null, width_cm: card.width_cm || null, height_cm: card.height_cm || null,
    };
    try {
      const saved = await api<SellerProduct>(`/seller/products/${product.id}/`, { method: "PATCH", json, authed: true });
      onChange(saved);
      setVals(Object.fromEntries(list.map((d) => [d.code, toVal(d, saved.attributes?.[d.code])])));
      setCard(cardOf(saved));
      setOk(true);
      return true;
    } catch (e) { setErr(errMsg(e)); setFe(fieldErrors(e)); return false; } finally { setBusy(false); }
  };

  return (
    <div className="space-y-6">
      <section>
        <h3 className="font-bold text-ink-900">{t("pe_attrs_title")}</h3>
        <p className="text-xs text-ink-500 mt-0.5">{t("pe_attrs_hint")}</p>
        {!defs ? <div className="py-8 grid place-items-center"><Spinner /></div> : list.length === 0 ? (
          <div className="text-sm text-ink-500 py-4">{t("pe_attrs_none")}</div>
        ) : (
          <div className="grid sm:grid-cols-2 gap-3 mt-3">
            {list.map((d) => (
              <AttrInput key={d.code} d={d} value={vals[d.code] ?? ""} onChange={(v) => setV(d.code, v)}
                label={`${p(d.name)}${d.unit && d.type !== "number" ? `, ${d.unit}` : ""}${d.required ? " *" : ""}`} hint={p(d.hint)} error={fe[`attributes.${d.code}`]} />
            ))}
          </div>
        )}
        {missing.length > 0 && <p className="text-xs text-amber-700 mt-2">{t("pe_attrs_missing")}: {missing.map((d) => p(d.name)).join(", ")}</p>}
      </section>

      <section className="rounded-2xl border border-ink-100 p-4 space-y-4 bg-ink-50/40">
        <div>
          <h3 className="font-bold text-ink-900">{t("pe_mpdata")}</h3>
          <p className="text-xs text-ink-500 mt-0.5">{t("pe_mpdata_hint")}</p>
        </div>
        <div>
          <div className="text-sm font-medium text-ink-700 mb-1.5">{t("pe_ikpu")}</div>
          <IkpuPicker product={product} onChange={onChange} />
        </div>
        <div className="grid sm:grid-cols-2 gap-3">
          <Field label={`${t("mp_barcode")} (EAN-13)`} error={fe.barcode || (ean === "len" ? t("pe_ean_len") : ean !== "ok" ? t("pe_ean_bad", { d: ean }) : undefined)} hint={t("pe_ean_hint")}>
            <Input value={card.barcode} inputMode="numeric" className="font-mono" onChange={(e) => setC("barcode", digitsOnly(e.target.value).slice(0, 13))} placeholder="4780000000000" />
          </Field>
          <Field label={t("mp_weight")} error={fe.weight_kg}>
            <Input inputMode="decimal" value={card.weight_kg} onChange={(e) => setC("weight_kg", decimalOnly(e.target.value))} />
          </Field>
        </div>
        <Field label={t("mp_dims")} error={fe.length_cm || fe.width_cm || fe.height_cm}>
          <div className="grid grid-cols-3 gap-2">
            {(["length_cm", "width_cm", "height_cm"] as const).map((k, i) => (
              <Input key={k} inputMode="decimal" value={card[k]} placeholder={[t("pe_len"), t("pe_wid"), t("pe_hei")][i]}
                onChange={(e) => setC(k, decimalOnly(e.target.value))} />
            ))}
          </div>
        </Field>
      </section>

      <ErrorBox text={err} />
      <StepBar onSave={save} onNext={onNext} busy={busy} saveDisabled={!defs || (ean !== "ok")}>
        {ok && <span className="text-sm text-emerald-700 flex items-center gap-1 mr-auto"><Check className="w-4 h-4" />{t("saved")}</span>}
      </StepBar>
    </div>
  );
}

function AttrInput({ d, value, onChange, label, hint, error }: { d: AttributeDef; value: Val; onChange: (v: Val) => void; label: string; hint?: string; error?: string }) {
  const { t, p } = useApp();
  if (d.type === "enum" && d.multi) {
    const arr = Array.isArray(value) ? value : [];
    return (
      <div className="sm:col-span-2">
        <div className="text-sm font-medium text-ink-700 mb-1.5">{label}</div>
        <div className="flex flex-wrap gap-1.5">
          {d.options.map((o) => {
            const on = arr.includes(o.v);
            return (
              <button key={o.v} type="button" onClick={() => onChange(on ? arr.filter((x) => x !== o.v) : [...arr, o.v])}
                className={clsx("px-3 h-8 rounded-full text-sm border transition", on ? "bg-brand-600 border-brand-600 text-white" : "bg-white border-ink-300 text-ink-700 hover:bg-ink-100")}>
                {p(o.name) || o.v}
              </button>
            );
          })}
        </div>
        {hint && !error && <div className="text-xs text-ink-500 mt-1">{hint}</div>}
        {error && <div className="text-xs text-red-600 mt-1">{error}</div>}
      </div>
    );
  }
  const v = Array.isArray(value) ? value[0] || "" : value;
  return (
    <Field label={label} hint={hint || undefined} error={error}>
      {d.type === "enum" ? (
        <Select value={v} onChange={(e) => onChange(e.target.value)}>
          <option value="">—</option>
          {d.options.map((o) => <option key={o.v} value={o.v}>{p(o.name) || o.v}</option>)}
        </Select>
      ) : d.type === "bool" ? (
        <Select value={v} onChange={(e) => onChange(e.target.value)}>
          <option value="">—</option><option value="true">{t("pe_yes")}</option><option value="false">{t("pe_no")}</option>
        </Select>
      ) : d.type === "number" ? (
        <div className="relative">
          <Input inputMode="decimal" value={v} onChange={(e) => onChange(e.target.value.replace(",", ".").replace(/[^\d.-]/g, ""))} className={d.unit ? "pr-14" : undefined} />
          {d.unit && <span className="absolute right-3 top-1/2 -translate-y-1/2 text-sm text-ink-500 pointer-events-none">{d.unit}</span>}
        </div>
      ) : (
        <Input value={v} onChange={(e) => onChange(e.target.value)} />
      )}
    </Field>
  );
}
