"use client";
import { api } from "@/lib/api";
import type { I18n } from "@/lib/types";
import type { Dict } from "@/lib/dict";

export type MpCode = "uzum" | "ozon" | "yandex" | "wb";

export interface MpMeta {
  marketplaces: { code: MpCode; name: string; capabilities: string[]; credential_fields: string[] }[];
  encryption_ready: boolean;
  rates: Record<string, { rate: string; nominal: number; date: string }>;
  is_operator: boolean;
  attribute_fields: string[];
}

export interface Account {
  id: number; seller: { code: string; name: I18n }; marketplace: MpCode; marketplace_name: string; title: string;
  cabinet_id: string; campaign_id: string; warehouse_id: string; masked_key: string;
  status: "new" | "active" | "invalid" | "disabled"; status_message: string; last_checked_at: string | null;
  key_expires_at: string | null; options: Record<string, any>; currency: "UZS" | "RUB"; rate_source: "cbu" | "manual";
  manual_rate: string | null; markup_percent: string; stock_buffer: number; mto_stock: number; auto_sync: boolean;
  is_enabled: boolean; orders_synced_at: string | null; stock_synced_at: string | null; capabilities: string[];
  counts: Record<string, number>;
  info: { shops?: { id: string; name: string }[]; campaigns?: { id: string; domain: string; placement: string; api: string; business_id: string }[];
    warehouses?: { id: string; name: string }[]; roles?: string[]; scopes?: string[]; token_type?: string; remote_count: number };
}

export interface Listing {
  id: number; account: number; account_name: string; marketplace: MpCode; offer_id: string; external_id: string;
  external_sku: string; status: "draft" | "pending" | "active" | "rejected" | "error"; last_error: string;
  pushed_price: string | null; pushed_currency: string; pushed_stock: number | null; last_synced_at: string | null;
  product: { id: number; sku: string; name: I18n; price: string | null; stock: number | null; reserved: number;
    available: number | null; unit: string; category: string; image: string | null };
}

export interface MpOrder {
  id: number; account: number; account_name: string; marketplace: MpCode; seller: string; external_id: string;
  scheme: string; status: string; state: string; items: { offer_id: string; name: string; qty: number; price: string; product_id: number | null }[];
  total: string; currency: string; ordered_at: string | null; stock_state: string; actions: string[];
}

export interface Job { id: number; kind: string; status: string; last_error: string; result: any }

export const MP_STYLE: Record<MpCode, { bg: string; fg: string; short: string }> = {
  uzum: { bg: "#7000ff", fg: "#fff", short: "U" },
  ozon: { bg: "#005bff", fg: "#fff", short: "O" },
  yandex: { bg: "#ffcc00", fg: "#111", short: "Я" },
  wb: { bg: "#cb11ab", fg: "#fff", short: "WB" },
};

export function MpBadge({ code, size = 28 }: { code: MpCode; size?: number }) {
  const s = MP_STYLE[code];
  return (
    <span className="inline-grid place-items-center rounded-lg font-black shrink-0"
      style={{ background: s.bg, color: s.fg, width: size, height: size, fontSize: size * 0.4 }}>{s.short}</span>
  );
}

export const LISTING_TONE: Record<string, string> = { draft: "gray", pending: "amber", active: "green", rejected: "red", error: "red" };
export const ACC_TONE: Record<string, string> = { new: "amber", active: "green", invalid: "red", disabled: "gray" };
export const ORDER_TONE: Record<string, string> = { new: "blue", processing: "amber", shipped: "violet", delivered: "green", cancelled: "gray", returned: "red" };

export type TKey = keyof Dict;

/** Vazifa tugaguncha kutish (worker bajaradi). Timeout bo'lsa — oxirgi holat. */
export async function waitJob(id: number, timeoutMs = 60000): Promise<Job> {
  const t0 = Date.now();
  let job: Job = await api<Job>(`/mp/jobs/${id}/`, { authed: true });
  while (["queued", "running"].includes(job.status) && Date.now() - t0 < timeoutMs) {
    await new Promise((r) => setTimeout(r, 1500));
    job = await api<Job>(`/mp/jobs/${id}/`, { authed: true });
  }
  return job;
}

export function money2(v: string | number | null | undefined, cur?: string) {
  if (v === null || v === undefined || v === "") return "—";
  const s = new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 2 }).format(Number(v)).replace(/ /g, " ");
  return cur ? `${s} ${cur === "UZS" ? "so'm" : cur}` : s;
}
