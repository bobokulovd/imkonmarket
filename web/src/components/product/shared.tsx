"use client";
import { useEffect, useState } from "react";
import { api, ApiError, errText } from "@/lib/api";
import type { AttributeDef, SellerProduct } from "@/lib/types";

export type ProductChange = (p: SellerProduct) => void;

/** Kategoriya xususiyatlari lug'ati (variant o'qlari ham shu yerda: variant=true). */
export function useAttrDefs(category: string) {
  const [state, setState] = useState<{ cat: string; defs: AttributeDef[] } | null>(null);
  const [err, setErr] = useState("");
  useEffect(() => {
    let alive = true;
    setErr("");
    api<AttributeDef[] | { results: AttributeDef[] }>(`/attributes/?category=${encodeURIComponent(category)}`)
      .then((d) => alive && setState({ cat: category, defs: Array.isArray(d) ? d : d.results || [] }))
      .catch((e) => { if (alive) { setErr(errText(e)); setState({ cat: category, defs: [] }); } });
    return () => { alive = false; };
  }, [category]);
  // boshqa kategoriya lug'ati hali almashmagan bo'lsa — null (eski lug'at bilan forma qurilmasin)
  return { defs: state && state.cat === category ? state.defs : null, err };
}

/** EAN-13 nazorat raqami. Natija: "ok" | "len" (13 raqam emas) | kutilgan oxirgi raqam ("0".."9"). Bo'sh — "ok". */
export function eanCheck(v: string): "ok" | "len" | string {
  const s = v.replace(/\s+/g, "");
  if (!s) return "ok";
  if (!/^\d{13}$/.test(s)) return "len";
  const sum = s.slice(0, 12).split("").reduce((a, c, i) => a + Number(c) * (i % 2 ? 3 : 1), 0);
  const cd = String((10 - (sum % 10)) % 10);
  return cd === s[12] ? "ok" : cd;
}

/** 400 javobidan maydon xatolarini ajratish: {attributes:{code:msg}, barcode: msg, ...} → {"attributes.code": msg, barcode: msg} */
export function fieldErrors(e: unknown): Record<string, string> {
  const out: Record<string, string> = {};
  if (!(e instanceof ApiError) || typeof e.data !== "object" || !e.data) return out;
  const flat = (v: unknown): string => (Array.isArray(v) ? v.map(flat).join(", ") : typeof v === "object" && v ? Object.values(v).map(flat).join(", ") : String(v));
  for (const [k, v] of Object.entries(e.data as Record<string, unknown>)) {
    if (k === "attributes" && v && typeof v === "object" && !Array.isArray(v)) {
      for (const [ak, av] of Object.entries(v as Record<string, unknown>)) out[`attributes.${ak}`] = flat(av);
    } else out[k] = flat(v);
  }
  return out;
}

/** errText o'rniga: ichma-ich xatolarni ({barcode:{barcode:"..."}}) ham o'qiladigan matnga aylantiradi. */
export function errMsg(e: unknown): string {
  if (e instanceof ApiError && e.data && typeof e.data === "object" && !(e.data as { detail?: unknown }).detail) {
    const fe = fieldErrors(e);
    const vals = Array.from(new Set(Object.values(fe).filter(Boolean)));
    if (vals.length) return vals.join("\n");
  }
  return errText(e);
}

export const decimalOnly = (s: string) => s.replace(",", ".").replace(/[^\d.]/g, "");
export const digitsOnly = (s: string) => s.replace(/\D/g, "");
export const numStr = (v: string | number | null | undefined) => (v === null || v === undefined || v === "" ? "" : String(Number(v)));

export function ErrorBox({ text }: { text?: string }) {
  if (!text) return null;
  return <div className="text-sm text-red-700 bg-red-50 rounded-lg p-3 whitespace-pre-line">{text}</div>;
}
