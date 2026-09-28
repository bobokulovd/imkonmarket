"use client";
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api } from "./api";
import { en, kaa, ru, uz, type Dict } from "./dict";
import { toCyrl, toNew } from "./translit";
import type { I18n, Lang, Meta, Product } from "./types";

// ---------------- i18n
const cache: Partial<Record<Lang, Dict>> = { uz, ru, en, kaa };
function dictFor(lang: Lang): Dict {
  if (!cache[lang]) {
    const fn = lang === "uz_cyrl" ? toCyrl : toNew;
    cache[lang] = Object.fromEntries(Object.entries(uz).map(([k, v]) => [k, fn(v)])) as Dict;
  }
  return cache[lang]!;
}
export const LANGS: { code: Lang; label: string; short: string }[] = [
  { code: "uz", label: "O'zbekcha", short: "UZ" },
  { code: "uz_cyrl", label: "Ўзбекча", short: "ЎЗ" },
  { code: "uz_new", label: "Ózbekçe (yangi)", short: "ÓZ" },
  { code: "ru", label: "Русский", short: "RU" },
  { code: "kaa", label: "Qaraqalpaqsha", short: "QQ" },
  { code: "en", label: "English", short: "EN" },
];
const HTML_LANG: Record<Lang, string> = { uz: "uz", uz_cyrl: "uz-Cyrl", uz_new: "uz", ru: "ru", kaa: "kaa", en: "en" };

type Ctx = {
  lang: Lang;
  setLang: (l: Lang) => void;
  t: (k: keyof Dict, vars?: Record<string, string | number>) => string;
  p: (d?: I18n | null) => string;
  money: (v: string | number | null | undefined) => string;
  unit: (u: string) => string;
  meta: Meta | null;
};
const I18nCtx = createContext<Ctx>(null as any);

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLangState] = useState<Lang>("uz");
  const [meta, setMeta] = useState<Meta | null>(null);

  useEffect(() => {
    try {
      const saved = localStorage.getItem("ub_lang") as Lang | null;
      if (saved && LANGS.some((l) => l.code === saved)) setLangState(saved);
    } catch {}
    api<Meta>("/meta/").then(setMeta).catch(() => {});
  }, []);
  useEffect(() => {
    document.documentElement.lang = HTML_LANG[lang];
  }, [lang]);

  const setLang = useCallback((l: Lang) => {
    setLangState(l);
    try { localStorage.setItem("ub_lang", l); } catch {}
  }, []);

  const value = useMemo<Ctx>(() => {
    const d = dictFor(lang);
    const t: Ctx["t"] = (k, vars) => {
      let s = d[k] ?? uz[k] ?? String(k);
      if (vars) for (const [a, b] of Object.entries(vars)) s = s.replace(`{${a}}`, String(b));
      return s;
    };
    const p: Ctx["p"] = (o) => (o ? o[lang] || o.uz || Object.values(o).find(Boolean) || "" : "");
    const money: Ctx["money"] = (v) => {
      if (v === null || v === undefined || v === "") return "";
      const n = Number(v);
      const s = new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 2 }).format(n).replace(/ /g, " ");
      return `${s} ${t("sum")}`;
    };
    const unit: Ctx["unit"] = (u) => p(meta?.units?.[u]) || u;
    return { lang, setLang, t, p, money, unit, meta };
  }, [lang, meta, setLang]);

  return (
    <I18nCtx.Provider value={value}>
      <CartProvider>{children}</CartProvider>
    </I18nCtx.Provider>
  );
}
export const useApp = () => useContext(I18nCtx);

// ---------------- cart
export type CartLine = { product: Product; qty: number };
type CartCtx = {
  lines: CartLine[];
  add: (p: Product, qty?: number) => void;
  setQty: (id: number, qty: number) => void;
  remove: (id: number) => void;
  clear: (ids?: number[]) => void;
  count: number;
  has: (id: number) => boolean;
};
const CartC = createContext<CartCtx>(null as any);

function CartProvider({ children }: { children: React.ReactNode }) {
  const [lines, setLines] = useState<CartLine[]>([]);
  const [ready, setReady] = useState(false);
  useEffect(() => {
    try {
      const raw = localStorage.getItem("ub_cart");
      if (raw) setLines(JSON.parse(raw));
    } catch {}
    setReady(true);
  }, []);
  useEffect(() => {
    if (!ready) return;
    try { localStorage.setItem("ub_cart", JSON.stringify(lines)); } catch {}
  }, [lines, ready]);

  const clampQty = (p: Product, q: number) => {
    let v = Math.max(q, p.min_order || 1);
    if (p.available !== null && p.available !== undefined) v = Math.min(v, Math.max(p.available, 0));
    return v;
  };
  const value: CartCtx = {
    lines,
    count: lines.length,
    has: (id) => lines.some((l) => l.product.id === id),
    add: (p, qty = 1) =>
      setLines((ls) => {
        const ex = ls.find((l) => l.product.id === p.id);
        if (ex) return ls.map((l) => (l.product.id === p.id ? { product: p, qty: clampQty(p, l.qty + qty) } : l));
        return [...ls, { product: p, qty: clampQty(p, qty) }];
      }),
    setQty: (id, qty) => setLines((ls) => ls.map((l) => (l.product.id === id ? { ...l, qty: clampQty(l.product, qty) } : l))),
    remove: (id) => setLines((ls) => ls.filter((l) => l.product.id !== id)),
    clear: (ids) => setLines((ls) => (ids ? ls.filter((l) => !ids.includes(l.product.id)) : [])),
  };
  return <CartC.Provider value={value}>{children}</CartC.Provider>;
}
export const useCart = () => useContext(CartC);
