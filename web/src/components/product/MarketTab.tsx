"use client";
import clsx from "clsx";
import { CheckCircle2, Info, RefreshCw, Rocket, XCircle } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { LISTING_TONE, MpBadge, type MpCode, type TKey, waitJob } from "@/components/mp/common";
import { Badge, Button, Field, Input, Select, Spinner } from "@/components/ui";
import { api } from "@/lib/api";
import { useApp } from "@/lib/store";
import type { Readiness, SellerProduct } from "@/lib/types";
import { ErrorBox, errMsg, StepBar } from "./shared";

const L_KEY: Record<string, TKey> = { draft: "mp_l_draft", pending: "mp_l_pending", active: "mp_l_active", rejected: "mp_l_rejected", error: "mp_l_error" };

type MpAttr = { marketplace: MpCode; key: string; name: string; required: boolean; values: { id: string | number; value: string }[] };
type MpInfo = { attributes: Record<string, string>; product_attributes: MpAttr[] };

function ScoreRing({ score }: { score: number }) {
  const r = 34, c = 2 * Math.PI * r;
  const color = score >= 80 ? "#059669" : score >= 50 ? "#d97706" : "#dc2626";
  return (
    <div className="relative w-24 h-24 shrink-0">
      <svg viewBox="0 0 80 80" className="w-full h-full -rotate-90">
        <circle cx="40" cy="40" r={r} fill="none" stroke="currentColor" strokeWidth="8" className="text-ink-100" />
        <circle cx="40" cy="40" r={r} fill="none" stroke={color} strokeWidth="8" strokeLinecap="round"
          strokeDasharray={c} strokeDashoffset={c * (1 - Math.max(0, Math.min(100, score)) / 100)} style={{ transition: "stroke-dashoffset .5s" }} />
      </svg>
      <div className="absolute inset-0 grid place-items-center text-xl font-extrabold tabular-nums" style={{ color }}>{score}%</div>
    </div>
  );
}

export default function MarketTab({ product, active, version, onFinish }: { product: SellerProduct; active: boolean; version: number; onFinish?: () => void }) {
  const { t } = useApp();
  const [r, setR] = useState<Readiness | null>(null);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const [info, setInfo] = useState<MpInfo | null>(null);
  const [infoBusy, setInfoBusy] = useState(false);
  const [infoMsg, setInfoMsg] = useState("");

  const load = useCallback(() => {
    setLoading(true); setErr("");
    api<Readiness>(`/mp/product-info/${product.id}/readiness/`, { authed: true })
      .then(setR).catch((e) => setErr(errMsg(e))).finally(() => setLoading(false));
    api<MpInfo>(`/mp/product-info/${product.id}/`, { authed: true }).then(setInfo).catch(() => setInfo(null));
  }, [product.id]);
  // faqat ko'rinib turganda va mahsulot o'zgargach qayta yuklaymiz
  useEffect(() => { if (active) load(); }, [active, version, load]);

  const activeAccounts = (r?.marketplaces || []).filter((m) => m.status === "active");
  const publish = async () => {
    setBusy(true); setErr(""); setMsg("");
    try {
      const res = await api<{ listings: unknown[]; jobs: { id: number }[] }>(`/mp/product-info/${product.id}/publish-all/`, { method: "POST", json: {}, authed: true });
      setMsg(t("pe_mp_sent"));
      if (res.jobs?.length) await Promise.all(res.jobs.map((j) => waitJob(j.id, 30000).catch(() => null)));
      else await new Promise((ok) => setTimeout(ok, 1500));
      load();
    } catch (e) { setErr(errMsg(e)); } finally { setBusy(false); }
  };

  const saveInfo = async () => {
    if (!info) return;
    setInfoBusy(true); setInfoMsg("");
    try {
      const d = await api<MpInfo>(`/mp/product-info/${product.id}/`, { method: "PUT", json: { attributes: info.attributes || {} }, authed: true });
      setInfo(d); setInfoMsg(t("saved")); load();
    } catch (e) { setInfoMsg(errMsg(e)); } finally { setInfoBusy(false); }
  };

  if (!r) return err ? <ErrorBox text={err} /> : <div className="py-12 grid place-items-center"><Spinner /></div>;

  return (
    <div className="space-y-5">
      <section className="flex flex-col sm:flex-row gap-5 items-start">
        <div className="flex items-center gap-4">
          <ScoreRing score={r.score} />
          <div>
            <div className="font-bold text-ink-900">{t("pe_mp_score")}</div>
            <div className="text-xs text-ink-500 max-w-[220px]">{t("pe_mp_score_hint")}</div>
            <button type="button" onClick={load} className="mt-1 text-xs text-brand-700 inline-flex items-center gap-1 hover:underline">
              <RefreshCw className={clsx("w-3.5 h-3.5", loading && "animate-spin")} />{t("pe_mp_refresh")}
            </button>
          </div>
        </div>
        <ul className="flex-1 grid sm:grid-cols-2 gap-x-4 gap-y-1.5 text-sm w-full">
          {r.checks.map((c) => (
            <li key={c.key} className="flex gap-2 items-start">
              {c.ok ? <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" /> : <XCircle className="w-4 h-4 text-red-500 shrink-0 mt-0.5" />}
              <span className={c.ok ? "text-ink-700" : "text-ink-900 font-medium"}>{c.label}</span>
            </li>
          ))}
        </ul>
      </section>

      <div className="rounded-xl bg-ink-100/60 p-3 text-xs text-ink-700 flex gap-2"><Info className="w-4 h-4 shrink-0 text-brand-600" />{t("pe_mp_sample_note")}</div>

      <section className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h3 className="font-bold text-ink-900">{t("pe_mp_accounts")}</h3>
          <span title={activeAccounts.length ? "" : t("pe_mp_no_accounts")}>
            <Button onClick={publish} loading={busy} disabled={!activeAccounts.length}><Rocket className="w-4 h-4" />{t("pe_mp_publish_all")}</Button>
          </span>
        </div>
        {msg && <div className="text-sm text-emerald-700">{msg}</div>}
        <ErrorBox text={err} />
        {r.marketplaces.length === 0 ? (
          <div className="text-sm text-ink-500 rounded-xl border border-dashed border-ink-300 p-4 text-center">{t("pe_mp_no_accounts")}</div>
        ) : (
          <div className="grid sm:grid-cols-2 gap-3">
            {r.marketplaces.map((m) => (
              <div key={m.account} className={clsx("rounded-xl border p-3", m.ok ? "border-emerald-200 bg-emerald-50/40" : "border-ink-100")}>
                <div className="flex items-center gap-2">
                  <MpBadge code={m.marketplace} />
                  <div className="min-w-0 flex-1">
                    <div className="font-semibold truncate">{m.name}</div>
                    {m.status !== "active" && <div className="text-xs text-amber-700">{t("pe_mp_acc_inactive")}</div>}
                  </div>
                  {m.ok ? <Badge tone="green"><CheckCircle2 className="w-3.5 h-3.5" />{t("pe_mp_ready")}</Badge> : <Badge tone="amber">{t("pe_mp_not_ready")}</Badge>}
                </div>
                {m.errors.length > 0 && (
                  <ul className="mt-2 space-y-1 text-xs text-red-700 list-disc pl-4">
                    {m.errors.map((e, i) => <li key={i}>{e}</li>)}
                  </ul>
                )}
                {m.listings.length > 0 && (
                  <div className="mt-2 pt-2 border-t border-ink-100 space-y-1">
                    {m.listings.map((l) => (
                      <div key={l.id} className="text-xs">
                        <div className="flex items-center gap-2 justify-between">
                          <span className="font-mono text-ink-500 truncate">{l.offer_id}</span>
                          <Badge tone={LISTING_TONE[l.status] || "gray"}>{L_KEY[l.status] ? t(L_KEY[l.status]) : l.status}</Badge>
                        </div>
                        {l.error && <div className="text-red-600 mt-0.5 line-clamp-2">{l.error}</div>}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </section>

      {info && info.product_attributes?.length > 0 && (
        <section className="rounded-2xl border border-ink-100 p-4 space-y-3">
          <div>
            <h3 className="font-bold text-ink-900">{t("pe_mp_extra")}</h3>
            <p className="text-xs text-ink-500 mt-0.5">{t("pe_mp_extra_hint")}</p>
          </div>
          <div className="grid sm:grid-cols-2 gap-3">
            {info.product_attributes.map((a) => {
              const v = info.attributes?.[a.key] || "";
              const set = (x: string) => setInfo({ ...info, attributes: { ...(info.attributes || {}), [a.key]: x } });
              return (
                <Field key={a.key} label={`${a.marketplace.toUpperCase()} · ${a.name}${a.required ? " *" : ""}`}>
                  {a.values?.length ? (
                    <Select value={v} onChange={(e) => set(e.target.value)}>
                      <option value="">—</option>{a.values.map((o) => <option key={o.id} value={o.value}>{o.value}</option>)}
                    </Select>
                  ) : <Input value={v} onChange={(e) => set(e.target.value)} />}
                </Field>
              );
            })}
          </div>
          <div className="flex items-center gap-3 justify-end">
            {infoMsg && <span className="text-sm text-ink-700">{infoMsg}</span>}
            <Button onClick={saveInfo} loading={infoBusy}>{t("save")}</Button>
          </div>
        </section>
      )}
      {onFinish && <StepBar onNext={onFinish} nextLabel={t("pe_finish")} />}
    </div>
  );
}
