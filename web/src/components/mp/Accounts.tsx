"use client";
import clsx from "clsx";
import { KeyRound, Plus, RefreshCw, ShieldCheck, ShoppingBag, UploadCloud } from "lucide-react";
import { useState } from "react";
import { Badge, Button, Empty, Field, Input, Modal, Select } from "@/components/ui";
import { api, errText } from "@/lib/api";
import { useApp } from "@/lib/store";
import { fmtDate } from "@/lib/util";
import { ACC_TONE, type Account, type MpCode, type MpMeta, MpBadge, type TKey } from "./common";

const ST_KEY: Record<string, TKey> = { new: "mp_st_new", active: "mp_st_active", invalid: "mp_st_invalid", disabled: "mp_st_disabled" };

function AddAccount({ meta, onDone, onClose }: { meta: MpMeta; onDone: () => void; onClose: () => void }) {
  const { t, p, meta: site } = useApp();
  const [f, setF] = useState<Record<string, any>>({ marketplace: "yandex", title: "", cabinet_id: "", api_key: "", seller: "", domain: "net", language: "RU", currency: "UZS" });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const set = (k: string, v: any) => setF({ ...f, [k]: v });
  const save = async () => {
    setBusy(true); setErr("");
    const body: Record<string, any> = { marketplace: f.marketplace, title: f.title, cabinet_id: f.cabinet_id, api_key: f.api_key, currency: f.currency };
    if (f.marketplace === "yandex") body.options = { domain: f.domain, language: f.language };
    if (meta.is_operator && f.seller) body.seller = f.seller;
    try { await api("/mp/accounts/", { method: "POST", json: body, authed: true }); onDone(); } catch (e) { setErr(errText(e)); } finally { setBusy(false); }
  };
  const mp = f.marketplace as MpCode;
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-4 gap-2">
        {meta.marketplaces.map((m) => (
          <button key={m.code} type="button" onClick={() => set("marketplace", m.code)}
            className={clsx("rounded-xl border p-3 flex flex-col items-center gap-2 text-xs font-semibold", f.marketplace === m.code ? "border-brand-600 ring-4 ring-brand-100" : "border-ink-200")}>
            <MpBadge code={m.code} size={34} />{m.name}
          </button>
        ))}
      </div>
      {meta.is_operator && (
        <Field label={t("mp_seller")}>
          <Select value={f.seller} onChange={(e) => set("seller", e.target.value)}>
            <option value="">—</option>
            {site?.sellers.map((s) => <option key={s.code} value={s.code}>{p(s.name)}</option>)}
          </Select>
        </Field>
      )}
      {mp === "ozon" && <Field label={t("mp_client_id")}><Input value={f.cabinet_id} onChange={(e) => set("cabinet_id", e.target.value)} required /></Field>}
      {mp === "yandex" && (
        <>
          <Field label={t("mp_business_id")}><Input value={f.cabinet_id} onChange={(e) => set("cabinet_id", e.target.value)} /></Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label={t("mp_domain")}>
              <Select value={f.domain} onChange={(e) => set("domain", e.target.value)}>
                <option value="net">{t("mp_domain_net")}</option><option value="ru">.ru</option>
              </Select>
            </Field>
            <Field label={t("mp_card_lang")}>
              <Select value={f.language} onChange={(e) => set("language", e.target.value)}><option value="RU">RU</option><option value="UZ">UZ</option></Select>
            </Field>
          </div>
        </>
      )}
      <Field label={t("mp_api_key")} hint={t("mp_key_hint")}>
        <Input type="password" autoComplete="off" value={f.api_key} onChange={(e) => set("api_key", e.target.value)} />
      </Field>
      {mp === "wb" && <p className="text-xs text-amber-700 bg-amber-50 rounded-lg p-2.5">{t("mp_wb_token")}</p>}
      {(mp === "ozon" || mp === "wb") && (
        <Field label={t("mp_currency")} hint={t("mp_uzs_note")}>
          <Select value={f.currency} onChange={(e) => set("currency", e.target.value)}><option value="UZS">UZS</option><option value="RUB">RUB</option></Select>
        </Field>
      )}
      <Field label={t("mp_title")}><Input value={f.title} onChange={(e) => set("title", e.target.value)} /></Field>
      {err && <div className="text-sm text-red-600">{err}</div>}
      <div className="flex justify-end gap-2">
        <Button variant="ghost" onClick={onClose}>{t("close")}</Button>
        <Button onClick={save} loading={busy} disabled={!f.api_key}><ShieldCheck className="w-4 h-4" />{t("mp_add")}</Button>
      </div>
    </div>
  );
}

function Settings({ acc, onSaved }: { acc: Account; onSaved: (msg: string) => void }) {
  const { t } = useApp();
  const [f, setF] = useState({ ...acc, api_key: "" } as Account & { api_key: string });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const set = (k: string, v: any) => setF({ ...f, [k]: v } as any);
  const save = async () => {
    setBusy(true); setErr("");
    const body: Record<string, any> = {
      title: f.title, cabinet_id: f.cabinet_id, campaign_id: f.campaign_id, warehouse_id: f.warehouse_id, currency: f.currency,
      rate_source: f.rate_source, manual_rate: f.manual_rate || null, markup_percent: f.markup_percent || 0,
      stock_buffer: f.stock_buffer || 0, mto_stock: f.mto_stock || 0, auto_sync: f.auto_sync, is_enabled: f.is_enabled, options: f.options,
    };
    if (f.api_key) body.api_key = f.api_key;
    try { await api(`/mp/accounts/${acc.id}/`, { method: "PATCH", json: body, authed: true }); onSaved(t("saved")); } catch (e) { setErr(errText(e)); } finally { setBusy(false); }
  };
  const info = acc.info || ({} as Account["info"]);
  return (
    <div className="space-y-4">
      <div className="grid sm:grid-cols-2 gap-3">
        {acc.marketplace === "uzum" && (
          <Field label={t("mp_shop")}>
            <Select value={f.cabinet_id} onChange={(e) => set("cabinet_id", e.target.value)}>
              <option value="">—</option>{info.shops?.map((s) => <option key={s.id} value={s.id}>{s.name} ({s.id})</option>)}
            </Select>
          </Field>
        )}
        {acc.marketplace === "ozon" && <Field label={t("mp_client_id")}><Input value={f.cabinet_id} onChange={(e) => set("cabinet_id", e.target.value)} /></Field>}
        {acc.marketplace === "yandex" && (
          <>
            <Field label="Business ID"><Input value={f.cabinet_id} onChange={(e) => set("cabinet_id", e.target.value)} /></Field>
            <Field label={t("mp_campaign")}>
              <Select value={f.campaign_id} onChange={(e) => set("campaign_id", e.target.value)}>
                <option value="">—</option>
                {info.campaigns?.map((c) => <option key={c.id} value={c.id}>{c.domain || c.id} · {c.placement} {c.api !== "AVAILABLE" ? `(${c.api})` : ""}</option>)}
              </Select>
            </Field>
          </>
        )}
        {acc.marketplace !== "uzum" && (
          <Field label={t("mp_warehouse")}>
            <Select value={f.warehouse_id} onChange={(e) => set("warehouse_id", e.target.value)}>
              <option value="">—</option>{info.warehouses?.map((w) => <option key={w.id} value={w.id}>{w.name} ({w.id})</option>)}
            </Select>
          </Field>
        )}
        <Field label={t("mp_title")}><Input value={f.title} onChange={(e) => set("title", e.target.value)} /></Field>
      </div>
      <div className="rounded-xl border border-ink-100 p-4 space-y-3">
        <div className="grid sm:grid-cols-4 gap-3">
          <Field label={t("mp_currency")}>
            <Select value={f.currency} onChange={(e) => set("currency", e.target.value)}><option value="UZS">UZS</option><option value="RUB">RUB</option></Select>
          </Field>
          {f.currency !== "UZS" && (
            <Field label={t("mp_rate_source")}>
              <Select value={f.rate_source} onChange={(e) => set("rate_source", e.target.value)}>
                <option value="cbu">{t("mp_rate_cbu")}</option><option value="manual">{t("mp_rate_manual")}</option>
              </Select>
            </Field>
          )}
          {f.currency !== "UZS" && f.rate_source === "manual" && (
            <Field label={t("mp_manual_rate")}><Input inputMode="decimal" value={f.manual_rate || ""} onChange={(e) => set("manual_rate", e.target.value)} /></Field>
          )}
          <Field label={t("mp_markup")}><Input inputMode="decimal" value={f.markup_percent} onChange={(e) => set("markup_percent", e.target.value)} /></Field>
        </div>
        <p className="text-xs text-ink-500">{t("mp_uzs_note")}</p>
      </div>
      <div className="grid sm:grid-cols-2 gap-3">
        <Field label={t("mp_buffer")}><Input inputMode="numeric" value={f.stock_buffer} onChange={(e) => set("stock_buffer", e.target.value)} /></Field>
        <Field label={t("mp_mto_stock")} hint={t("mp_mto_hint")}><Input inputMode="numeric" value={f.mto_stock} onChange={(e) => set("mto_stock", e.target.value)} /></Field>
      </div>
      <div className="flex flex-wrap gap-5 text-sm">
        <label className="flex items-center gap-2"><input type="checkbox" checked={f.auto_sync} onChange={(e) => set("auto_sync", e.target.checked)} /> {t("mp_auto_sync")}</label>
        <label className="flex items-center gap-2"><input type="checkbox" checked={f.is_enabled} onChange={(e) => set("is_enabled", e.target.checked)} /> {t("mp_enabled")}</label>
      </div>
      <Field label={`${t("mp_new_key")} (${acc.masked_key})`} hint={t("mp_key_hint")}>
        <Input type="password" autoComplete="off" value={f.api_key} onChange={(e) => set("api_key", e.target.value)} />
      </Field>
      {err && <div className="text-sm text-red-600">{err}</div>}
      <div className="flex justify-end"><Button onClick={save} loading={busy}>{t("save")}</Button></div>
    </div>
  );
}

export default function Accounts({ meta, accounts, reload, notify, openListings }:
  { meta: MpMeta; accounts: Account[]; reload: () => void; notify: (s: string) => void; openListings: (id: number) => void }) {
  const { t, p } = useApp();
  const [adding, setAdding] = useState(false);
  const [edit, setEdit] = useState<Account | null>(null);
  const act = async (a: Account, path: string) => {
    try { await api(`/mp/accounts/${a.id}/${path}/`, { method: "POST", authed: true }); notify(t("mp_queued")); setTimeout(reload, 2500); }
    catch (e) { notify(errText(e)); }
  };
  return (
    <div className="space-y-4">
      {!meta.encryption_ready && <div className="rounded-xl bg-red-50 text-red-700 text-sm p-3">{t("mp_enc_missing")}</div>}
      <div className="flex justify-end"><Button onClick={() => setAdding(true)} disabled={!meta.encryption_ready}><Plus className="w-4 h-4" />{t("mp_add")}</Button></div>
      {accounts.length === 0 && <Empty icon={<ShoppingBag className="w-7 h-7" />} title={t("mp_no_accounts")} sub={t("mp_intro")} />}
      <div className="grid md:grid-cols-2 gap-4">
        {accounts.map((a) => (
          <div key={a.id} className="card p-5 space-y-3">
            <div className="flex items-start gap-3">
              <MpBadge code={a.marketplace} size={40} />
              <div className="min-w-0 flex-1">
                <div className="font-bold text-ink-900 flex items-center gap-2 flex-wrap">{a.marketplace_name}{a.title && <span className="text-ink-500 font-medium">· {a.title}</span>}
                  <Badge tone={ACC_TONE[a.status]}>{t(ST_KEY[a.status])}</Badge>{!a.is_enabled && <Badge>{t("mp_st_disabled")}</Badge>}</div>
                {meta.is_operator && <div className="text-xs text-ink-500">{p(a.seller.name)}</div>}
                <div className="text-xs text-ink-500 mt-0.5 flex items-center gap-1.5 flex-wrap"><KeyRound className="w-3.5 h-3.5" /><span className="font-mono">{a.masked_key}</span>
                  {a.cabinet_id && <span>· ID {a.cabinet_id}</span>}{a.campaign_id && <span>· {a.campaign_id}</span>}{a.warehouse_id && <span>· {t("mp_warehouse")} {a.warehouse_id}</span>}</div>
              </div>
            </div>
            {a.status_message && <div className={clsx("text-xs rounded-lg p-2", a.status === "invalid" ? "bg-red-50 text-red-700" : "bg-amber-50 text-amber-800")}>{a.status_message}</div>}
            <div className="grid grid-cols-4 gap-2 text-center">
              {(["active", "pending", "error", "orders_new"] as const).map((k) => (
                <button key={k} onClick={() => openListings(a.id)} className="rounded-xl bg-ink-50 py-2">
                  <div className="text-lg font-bold">{(a.counts[k] || 0) + (k === "error" ? a.counts.rejected || 0 : 0)}</div>
                  <div className="text-[11px] text-ink-500">{t(({ active: "mp_l_active", pending: "mp_l_pending", error: "mp_l_error", orders_new: "mp_orders" } as Record<string, TKey>)[k])}</div>
                </button>
              ))}
            </div>
            <div className="text-xs text-ink-500 flex flex-wrap gap-x-4">
              <span>{t("mp_currency")}: <b>{a.currency}</b>{a.currency !== "UZS" && ` (${a.rate_source === "cbu" ? "CBU" : a.manual_rate})`}{Number(a.markup_percent) ? ` +${a.markup_percent}%` : ""}</span>
              {a.last_checked_at && <span>{t("mp_last_check")}: {fmtDate(a.last_checked_at, true)}</span>}
              {a.key_expires_at && <span className={new Date(a.key_expires_at).getTime() - Date.now() < 14 * 864e5 ? "text-red-600 font-semibold" : ""}>{t("mp_expires")}: {fmtDate(a.key_expires_at)}</span>}
            </div>
            <div className="flex flex-wrap gap-2">
              <Button size="sm" variant="outline" onClick={() => act(a, "check")}><ShieldCheck className="w-4 h-4" />{t("mp_check")}</Button>
              {a.status === "active" && <Button size="sm" variant="outline" onClick={() => act(a, "sync")}><UploadCloud className="w-4 h-4" />{t("mp_sync")}</Button>}
              {a.status === "active" && a.capabilities.includes("orders") && <Button size="sm" variant="outline" onClick={() => act(a, "fetch-orders")}><RefreshCw className="w-4 h-4" />{t("mp_fetch_orders")}</Button>}
              {a.status === "active" && a.capabilities.includes("link_existing") && <Button size="sm" variant="outline" onClick={() => act(a, "fetch-remote")}><RefreshCw className="w-4 h-4" />{t("mp_fetch_remote")}</Button>}
              <Button size="sm" variant="soft" onClick={() => setEdit(a)}>{t("mp_settings")}</Button>
            </div>
          </div>
        ))}
      </div>
      <Modal open={adding} onClose={() => setAdding(false)} title={t("mp_add")}>
        <AddAccount meta={meta} onClose={() => setAdding(false)} onDone={() => { setAdding(false); notify(t("mp_queued")); reload(); setTimeout(reload, 4000); }} />
      </Modal>
      <Modal open={!!edit} onClose={() => setEdit(null)} title={edit ? `${edit.marketplace_name} ${edit.title || ""}` : ""} wide>
        {edit && <Settings acc={edit} onSaved={(m) => { setEdit(null); notify(m); reload(); }} />}
      </Modal>
    </div>
  );
}
