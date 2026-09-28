// Bo'sh bo'lsa — shu domen (Next.js /api ni backendga proksi qiladi)
export const API_URL = (process.env.NEXT_PUBLIC_API_URL || "").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(public status: number, public data: any) {
    super(typeof data === "object" ? JSON.stringify(data) : String(data));
  }
}

const TOKEN_KEY = "ub_token";
const REFRESH_KEY = "ub_refresh";

export const auth = {
  get token() {
    if (typeof window === "undefined") return null;
    try { return localStorage.getItem(TOKEN_KEY); } catch { return null; }
  },
  set(access: string, refresh?: string) {
    try {
      localStorage.setItem(TOKEN_KEY, access);
      if (refresh) localStorage.setItem(REFRESH_KEY, refresh);
    } catch {}
  },
  clear() {
    try { localStorage.removeItem(TOKEN_KEY); localStorage.removeItem(REFRESH_KEY); } catch {}
  },
  get refresh() {
    try { return localStorage.getItem(REFRESH_KEY); } catch { return null; }
  },
};

async function refreshToken(): Promise<boolean> {
  const r = auth.refresh;
  if (!r) return false;
  const res = await fetch(`${API_URL}/api/auth/refresh/`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ refresh: r }),
  });
  if (!res.ok) return false;
  const d = await res.json();
  auth.set(d.access);
  return true;
}

export async function api<T = any>(path: string, opts: RequestInit & { json?: any; authed?: boolean } = {}, retry = true): Promise<T> {
  const headers: Record<string, string> = { ...(opts.headers as any) };
  let body = opts.body;
  if (opts.json !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(opts.json);
  }
  if (opts.authed && auth.token) headers["Authorization"] = `Bearer ${auth.token}`;
  const res = await fetch(`${API_URL}/api${path}`, { ...opts, headers, body, cache: "no-store" });
  if (res.status === 401 && opts.authed && retry && (await refreshToken())) return api<T>(path, opts, false);
  const ct = res.headers.get("content-type") || "";
  const data = ct.includes("json") ? await res.json() : await res.text();
  if (!res.ok) throw new ApiError(res.status, data);
  return data as T;
}

export function errText(e: unknown): string {
  if (e instanceof ApiError) {
    const d = e.data;
    if (typeof d === "string") return d.slice(0, 200);
    if (d?.detail) return String(d.detail);
    return Object.entries(d || {}).map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(", ") : v}`).join("; ");
  }
  return (e as Error)?.message || "Error";
}

export function qs(params: Record<string, any>) {
  const u = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "" && v !== false) u.set(k, String(v));
  });
  const s = u.toString();
  return s ? `?${s}` : "";
}
