import type { CartLine } from "./store";

export function groupBySeller(lines: CartLine[]) {
  const map = new Map<string, CartLine[]>();
  lines.forEach((l) => {
    const k = l.product.seller.code;
    map.set(k, [...(map.get(k) || []), l]);
  });
  return Array.from(map.values());
}

export function fmtDate(s?: string | null, withTime = false) {
  if (!s) return "";
  const d = new Date(s);
  const pad = (n: number) => String(n).padStart(2, "0");
  const base = `${pad(d.getDate())}.${pad(d.getMonth() + 1)}.${d.getFullYear()}`;
  return withTime ? `${base} ${pad(d.getHours())}:${pad(d.getMinutes())}` : base;
}

export const LOG_KEYS: Record<string, string> = {
  new: "st_new", review: "st_review", contract: "st_contract", payment: "paid", shipped: "c_shipped",
  done: "c_done", rejected: "st_rejected", cancelled: "st_cancelled", refund: "c_cancelled",
};
