"use client";
import clsx from "clsx";
import { useApp } from "@/lib/store";
import type { PublicVariant, VariantAxis } from "@/lib/types";

export type Selection = Record<string, string>;

const inStock = (v: PublicVariant) => v.available === null || v.available > 0;
const eq = (a: unknown, b: unknown) => a !== undefined && a !== null && String(a) === String(b);

/** Tanlovga to'liq mos keladigan variant (barcha o'qlar bo'yicha) */
export function matchVariant(variants: PublicVariant[], axes: VariantAxis[], sel: Selection): PublicVariant | null {
  if (!axes.length) return variants.find((v) => String(v.id) === sel.__id) || null;
  return variants.find((v) => axes.every((a) => eq(v.attributes[a.code], sel[a.code]))) || null;
}

/** Boshlang'ich tanlov: so'ralgan (?variant=) yoki birinchi mavjud variant */
export function initialSelection(variants: PublicVariant[], axes: VariantAxis[], wantId?: number | null): Selection {
  const v = (wantId ? variants.find((x) => x.id === wantId) : null) || variants.find(inStock) || variants[0];
  return v ? selectionOf(v, axes) : {};
}

export function selectionOf(v: PublicVariant, axes: VariantAxis[]): Selection {
  if (!axes.length) return { __id: String(v.id) };
  return Object.fromEntries(axes.map((a) => [a.code, String(v.attributes[a.code] ?? "")]));
}

/**
 * Bitta o'q variantini bosganda: boshqa o'qlardagi tanlovni iloji boricha saqlab, mos variantga o'tamiz.
 * Mos kombinatsiya bo'lmasa — shu qiymatli eng yaqin (ko'proq mos keladigan, mavjud) variant tanlanadi.
 */
export function pickOption(variants: PublicVariant[], axes: VariantAxis[], sel: Selection, axis: string, v: string): Selection {
  const next = { ...sel, [axis]: v };
  const exact = matchVariant(variants, axes, next);
  if (exact) return next;
  const cands = variants.filter((x) => eq(x.attributes[axis], v));
  if (!cands.length) return next;
  const score = (x: PublicVariant) => axes.filter((a) => eq(x.attributes[a.code], sel[a.code])).length * 2 + (inStock(x) ? 1 : 0);
  const best = cands.reduce((a, b) => (score(b) > score(a) ? b : a));
  return selectionOf(best, axes);
}

type OptState = "ok" | "none" | "soldout";
function optionState(variants: PublicVariant[], axes: VariantAxis[], sel: Selection, axis: string, v: string): OptState {
  const cands = variants.filter((x) => eq(x.attributes[axis], v) && axes.every((a) => a.code === axis || !sel[a.code] || eq(x.attributes[a.code], sel[a.code])));
  if (!cands.length) return "none";
  return cands.some(inStock) ? "ok" : "soldout";
}

/** Har bir o'q uchun bitta qator — chip tugmalar (Uzum/Ozon uslubida) */
export default function VariantPicker({ variants, axes, sel, onChange }: {
  variants: PublicVariant[]; axes: VariantAxis[]; sel: Selection; onChange: (s: Selection) => void;
}) {
  const { t, p } = useApp();
  const chip = (active: boolean, state: OptState) => clsx(
    "min-w-[44px] h-10 px-3.5 rounded-xl border-2 text-sm font-semibold transition focus:outline-none focus-visible:ring-4 focus-visible:ring-brand-100",
    active ? "border-brand-600 bg-brand-50 text-brand-700" : "border-ink-100 bg-white text-ink-900 hover:border-ink-300",
    state !== "ok" && !active && "text-ink-500 line-through decoration-ink-500/60 bg-ink-100/50",
    state !== "ok" && active && "line-through decoration-brand-700/50",
  );

  if (!axes.length) {
    // o'qlarsiz variantlar (faqat nomi bor) — ro'yxat ko'rinishida
    return (
      <div>
        <div className="text-sm text-ink-500 mb-2">{t("sv_variant")}: <b className="text-ink-900">{p(variants.find((v) => String(v.id) === sel.__id)?.label)}</b></div>
        <div className="flex flex-wrap gap-2" role="radiogroup" aria-label={t("sv_variant")}>
          {variants.map((v) => {
            const active = String(v.id) === sel.__id;
            const st: OptState = inStock(v) ? "ok" : "soldout";
            return (
              <button key={v.id} type="button" role="radio" aria-checked={active} title={st === "soldout" ? t("out_of_stock") : undefined}
                onClick={() => onChange({ __id: String(v.id) })} className={chip(active, st)}>{p(v.label) || v.sku}</button>
            );
          })}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {axes.map((a) => {
        const curOpt = a.options.find((o) => o.v === sel[a.code]);
        return (
          <div key={a.code}>
            <div className="text-sm text-ink-500 mb-2">{p(a.name)}: <b className="text-ink-900">{curOpt ? p(curOpt.name) : "—"}</b></div>
            <div className="flex flex-wrap gap-2" role="radiogroup" aria-label={p(a.name)}>
              {a.options.map((o) => {
                const active = sel[a.code] === o.v;
                const st = optionState(variants, axes, sel, a.code, o.v);
                const title = st === "soldout" ? t("out_of_stock") : st === "none" ? t("sv_combo_none") : undefined;
                return (
                  <button key={o.v} type="button" role="radio" aria-checked={active} title={title}
                    aria-label={title ? `${p(o.name)} — ${title}` : p(o.name)}
                    onClick={() => onChange(pickOption(variants, axes, sel, a.code, o.v))} className={chip(active, st)}>
                    {p(o.name) || o.v}
                  </button>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}
