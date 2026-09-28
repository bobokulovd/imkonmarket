"use client";
import clsx from "clsx";
import { CheckCircle2, Info, Link2, RefreshCw, Search, UploadCloud, XCircle } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Badge, Button, Empty, Field, Input, Modal, ProductImage, Select, Spinner } from "@/components/ui";
import { api, errText, qs } from "@/lib/api";
import { useApp } from "@/lib/store";
import type { Paged, SellerProduct } from "@/lib/types";
import { fmtDate } from "@/lib/util";
import { type Account, LISTING_TONE, type Listing, money2, MpBadge, type TKey } from "./common";

const L_KEY: Record<string, TKey> = { draft: "mp_l_draft", pending: "mp_l_pending", active: "mp_l_active", rejected: "mp_l_rejected", error: "mp_l_error" };

function InfoEditor({ productId, onClose, notify }: { productId: number; onClose: () => void; notify: (s: string) => void }) {
  const { t } = useApp();
  const [d, setD] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  useEffect(() => { api(`/mp/product-info/${productId}/`, { authed: true }).then(setD).catch((e) => setErr(errText(e))); }, [productId]);
  if (!d) return err ? <div className="text-red-600 text-sm">{err}</div> : <Spinner />;
  const set = (k: string, v: any) => setD({ ...d, [k]: v });
  const setAttr = (k: string, v: string) => setD({ ...d, attributes: { ...(d.attributes || {}), [k]: v } });
  const save = async () => {
    setBusy(true); setErr("");
    const body = { brand: d.brand, barcode: d.barcode, country: d.country, attributes: d.attributes || {},
      weight_kg: d.weight_kg || null, length_cm: d.length_cm || null, width_cm: d.width_cm || null, height_cm: d.height_cm || null };
    try { await api(`/mp/product-info/${productId}/`, { method: "PUT", json: body, authed: true }); notify(t("saved")); onClose(); }
    catch (e) { setErr(errText(e)); } finally { setBusy(false); }
  };
  return (
    <div className="space-y-4">
      <div className="grid sm:grid-cols-3 gap-3">
        <Field label={t("mp_brand")}><Input value={d.brand || ""} onChange={(e) => set("brand", e.target.value)} /></Field>
        <Field label={t("mp_barcode")}><Input value={d.barcode || ""} onChange={(e) => set("barcode", e.target.value)} /></Field>
        <Field label={t("mp_country")}><Input value={d.country || ""} onChange={(e) => set("country", e.target.value)} /></Field>
      </div>
      <div className="grid grid-cols-4 gap-3 items-end">
        <Field label={t("mp_weight")}><Input inputMode="decimal" value={d.weight_kg || ""} onChange={(e) => set("weight_kg", e.target.value)} /></Field>
        <Field label={t("mp_dims")} className="col-span-3">
          <div className="grid grid-cols-3 gap-2">
            {["length_cm", "width_cm", "height_cm"].map((k) => <Input key={k} inputMode="decimal" value={d[k] || ""} onChange={(e) => set(k, e.target.value)} />)}
          </div>
        </Field>
      </div>
      {d.product_attributes?.length > 0 && (
        <div className="space-y-3">
          <div className="font-semibold text-ink-900">{t("mp_attrs")}</div>
          <div className="grid sm:grid-cols-2 gap-3">
            {d.product_attributes.map((a: any) => (
              <Field key={a.key} label={`${a.marketplace.toUpperCase()} · ${a.name}${a.required ? " *" : ""}`}>
                {a.values?.length ? (
                  <Select value={d.attributes?.[a.key] || ""} onChange={(e) => setAttr(a.key, e.target.value)}>
                    <option value="">—</option>{a.values.map((v: any) => <option key={v.id} value={v.value}>{v.value}</option>)}
                  </Select>
                ) : <Input value={d.attributes?.[a.key] || ""} onChange={(e) => setAttr(a.key, e.target.value)} />}
              </Field>
            ))}
          </div>
        </div>
      )}
      {err && <div className="text-sm text-red-600">{err}</div>}
      <div className="flex justify-end"><Button onClick={save} loading={busy}>{t("save")}</Button></div>
    </div>
  );
}

function LinkModal({ acc, product, listing, onDone }: { acc: Account; product: SellerProduct; listing?: Listing; onDone: () => void }) {
  const { t } = useApp();
  const [q, setQ] = useState(product.sku);
  const [data, setData] = useState<{ fetched_at: string | null; items: any[] } | null>(null);
  const [err, setErr] = useState("");
  const load = useCallback(() => {
    api(`/mp/accounts/${acc.id}/remote/${qs({ q })}`, { authed: true }).then(setData).catch((e) => setErr(errText(e)));
  }, [acc.id, q]);
  useEffect(() => { load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  const link = async (sku: string) => {
    setErr("");
    try {
      let lid = listing?.id;
      if (!lid) {
        const r = await api<any>("/mp/listings/", { method: "POST", json: { account: acc.id, product_ids: [product.id], publish: false }, authed: true });
        lid = r.listings[0].id;
      }
      await api(`/mp/listings/${lid}/link/`, { method: "POST", json: { external_sku: sku }, authed: true });
      onDone();
    } catch (e) { setErr(errText(e)); }
  };
  return (
    <div className="space-y-3">
      <p className="text-sm text-ink-500">{t("mp_link_hint")}</p>
      <div className="flex gap-2">
        <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder={t("search")} onKeyDown={(e) => e.key === "Enter" && load()} />
        <Button variant="outline" onClick={load}><Search className="w-4 h-4" /></Button>
      </div>
      {!data ? <Spinner /> : data.items.length === 0 ? <div className="text-sm text-ink-500">— {data.fetched_at ? "" : t("mp_fetch_remote")}</div> : (
        <div className="divide-y divide-ink-100 max-h-[50vh] overflow-y-auto">
          {data.items.map((it) => (
            <div key={it.external_sku} className="py-2 flex items-center gap-3 text-sm">
              <div className="flex-1 min-w-0"><div className="font-medium truncate">{it.title}</div>
                <div className="text-xs text-ink-500">SKU {it.external_sku} · {it.offer_id || "—"} · {it.barcode || "—"}</div></div>
              {it.product_id ? <Badge tone={it.product_id === product.id ? "green" : "gray"}>{it.product_id === product.id ? "✓" : "#" + it.product_id}</Badge>
                : <Button size="sm" onClick={() => link(it.external_sku)}><Link2 className="w-4 h-4" /></Button>}
            </div>
          ))}
        </div>
      )}
      {err && <div className="text-sm text-red-600">{err}</div>}
    </div>
  );
}

export default function Listings({ accounts, accountId, setAccountId, notify }:
  { accounts: Account[]; accountId: number | null; setAccountId: (id: number) => void; notify: (s: string) => void }) {
  const { t, p, money, unit } = useApp();
  const acc = accounts.find((a) => a.id === accountId) || null;
  const [products, setProducts] = useState<SellerProduct[] | null>(null);
  const [listings, setListings] = useState<Record<number, Listing>>({});
  const [q, setQ] = useState("");
  const [filter, setFilter] = useState("");
  const [sel, setSel] = useState<Set<number>>(new Set());
  const [info, setInfo] = useState<number | null>(null);
  const [linkFor, setLinkFor] = useState<SellerProduct | null>(null);
  const [check, setCheck] = useState<{ p: SellerProduct; res: any } | null>(null);
  const [busy, setBusy] = useState(false);
  const canCreate = acc?.capabilities.includes("create_cards");

  const load = useCallback(async () => {
    if (!acc) return;
    const [pr, ls] = await Promise.all([
      api<Paged<SellerProduct>>(`/seller/products/${qs({ q, page_size: 500, seller: acc.seller.code })}`, { authed: true }),
      api<Paged<Listing>>(`/mp/listings/${qs({ account: acc.id, page_size: 500 })}`, { authed: true }),
    ]);
    setProducts(pr.results.filter((x) => x.seller?.code === acc.seller.code));
    setListings(Object.fromEntries(ls.results.map((l) => [l.product.id, l])));
  }, [acc, q]);
  useEffect(() => { setProducts(null); setSel(new Set()); load().catch((e) => notify(errText(e))); }, [accountId]); // eslint-disable-line react-hooks/exhaustive-deps

  const rows = useMemo(() => (products || []).filter((x) => {
    const l = listings[x.id];
    if (!filter) return true;
    if (filter === "none") return !l;
    return l?.status === filter || (filter === "error" && l?.status === "rejected");
  }), [products, listings, filter]);

  const publish = async (ids: number[]) => {
    if (!acc || !ids.length) return;
    setBusy(true);
    try {
      await api("/mp/listings/", { method: "POST", json: { account: acc.id, product_ids: ids }, authed: true });
      notify(t("mp_queued")); setSel(new Set()); await load(); setTimeout(() => load(), 5000);
    } catch (e) { notify(errText(e)); } finally { setBusy(false); }
  };
  const doCheck = async (pr: SellerProduct) => {
    try {
      let l = listings[pr.id];
      if (!l) {
        const r = await api<any>("/mp/listings/", { method: "POST", json: { account: acc!.id, product_ids: [pr.id], publish: false }, authed: true });
        l = r.listings[0];
        await load();
      }
      setCheck({ p: pr, res: await api(`/mp/listings/${l.id}/check/`, { authed: true }) });
    } catch (e) { notify(errText(e)); }
  };
  const refresh = async (l: Listing) => { await api(`/mp/listings/${l.id}/refresh/`, { method: "POST", authed: true }); notify(t("mp_queued")); setTimeout(load, 4000); };

  if (!accounts.length) return <Empty title={t("mp_no_accounts")} />;
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2 items-center">
        <div className="flex gap-2 overflow-x-auto no-scrollbar">
          {accounts.map((a) => (
            <button key={a.id} onClick={() => setAccountId(a.id)} className={clsx("flex items-center gap-2 rounded-xl border px-3 h-10 text-sm font-semibold whitespace-nowrap", a.id === accountId ? "border-brand-600 bg-brand-50" : "border-ink-200 bg-white")}>
              <MpBadge code={a.marketplace} size={22} />{a.title || a.marketplace_name}
            </button>
          ))}
        </div>
      </div>
      {!acc ? <div className="text-ink-500">{t("mp_select_account")}</div> : (
        <>
          {!canCreate && <div className="rounded-xl bg-violet-50 text-violet-800 text-sm p-3">{t("mp_link_hint")}</div>}
          <div className="flex flex-wrap gap-2 items-center">
            <div className="relative flex-1 min-w-[200px] max-w-md">
              <Search className="w-4 h-4 absolute left-3 top-3.5 text-ink-500" />
              <Input className="pl-9" value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === "Enter" && load()} placeholder={t("search")} />
            </div>
            <Select className="!w-auto" value={filter} onChange={(e) => setFilter(e.target.value)}>
              <option value="">{t("all")}</option><option value="none">{t("mp_not_listed")}</option>
              {Object.entries(L_KEY).filter(([k]) => k !== "rejected").map(([k, v]) => <option key={k} value={k}>{t(v)}</option>)}
            </Select>
            <Button variant="outline" onClick={() => load()}><RefreshCw className="w-4 h-4" /></Button>
            {canCreate && <Button onClick={() => publish(Array.from(sel))} loading={busy} disabled={!sel.size}><UploadCloud className="w-4 h-4" />{t("mp_publish_sel")} ({sel.size})</Button>}
          </div>
          {!products ? <Spinner /> : rows.length === 0 ? <Empty title={t("nothing_found")} /> : (
            <div className="card divide-y divide-ink-100">
              {rows.map((pr) => {
                const l = listings[pr.id];
                return (
                  <div key={pr.id} className="p-3 flex gap-3 items-start">
                    {canCreate && <input type="checkbox" className="mt-4" checked={sel.has(pr.id)} onChange={(e) => { const s = new Set(sel); if (e.target.checked) s.add(pr.id); else s.delete(pr.id); setSel(s); }} />}
                    <div className="w-14 h-14 rounded-lg overflow-hidden shrink-0"><ProductImage src={pr.image_url} category={pr.category} /></div>
                    <div className="flex-1 min-w-0">
                      <div className="font-semibold text-ink-900 truncate">{p(pr.name)}</div>
                      <div className="text-xs text-ink-500">{pr.sku} · {pr.price ? money(pr.price) : "—"} · {t("available")}: {pr.available ?? "∞"} {unit(pr.unit)}</div>
                      {l && (
                        <div className="text-xs mt-1 flex flex-wrap gap-x-3 gap-y-1 items-center">
                          <Badge tone={LISTING_TONE[l.status]}>{t(L_KEY[l.status])}</Badge>
                          {l.external_id && <span className="text-ink-500">ID {l.external_id}{l.external_sku ? ` / ${l.external_sku}` : ""}</span>}
                          {l.pushed_price && <span className="text-ink-500">{t("mp_pushed")}: {money2(l.pushed_price, l.pushed_currency)} · {l.pushed_stock ?? "—"}</span>}
                          {l.last_synced_at && <span className="text-ink-400">{fmtDate(l.last_synced_at, true)}</span>}
                        </div>
                      )}
                      {l?.last_error && <div className="text-xs text-red-600 mt-1 line-clamp-3">{l.last_error}</div>}
                    </div>
                    <div className="flex flex-wrap gap-1 justify-end shrink-0">
                      <Button size="sm" variant="ghost" title={t("mp_market_info")} onClick={() => setInfo(pr.id)}><Info className="w-4 h-4" /></Button>
                      {canCreate && <Button size="sm" variant="ghost" title={t("mp_check_ready")} onClick={() => doCheck(pr)}><CheckCircle2 className="w-4 h-4" /></Button>}
                      {l && ["pending", "active"].includes(l.status) && <Button size="sm" variant="ghost" onClick={() => refresh(l)}><RefreshCw className="w-4 h-4" /></Button>}
                      {canCreate ? <Button size="sm" variant="soft" onClick={() => publish([pr.id])}><UploadCloud className="w-4 h-4" /></Button>
                        : <Button size="sm" variant="soft" title={t("mp_link")} onClick={() => setLinkFor(pr)}><Link2 className="w-4 h-4" /></Button>}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </>
      )}
      <Modal open={info !== null} onClose={() => setInfo(null)} title={t("mp_market_info")} wide>
        {info !== null && <InfoEditor productId={info} onClose={() => { setInfo(null); load(); }} notify={notify} />}
      </Modal>
      <Modal open={!!linkFor} onClose={() => setLinkFor(null)} title={t("mp_link")} wide>
        {linkFor && acc && <LinkModal acc={acc} product={linkFor} listing={listings[linkFor.id]} onDone={() => { setLinkFor(null); notify(t("saved")); load(); }} />}
      </Modal>
      <Modal open={!!check} onClose={() => setCheck(null)} title={t("mp_check_ready")}>
        {check && (
          <div className="space-y-3">
            <div className="font-semibold">{p(check.p.name)}</div>
            {check.res.ok ? <div className="flex items-center gap-2 text-emerald-700"><CheckCircle2 className="w-5 h-5" />{t("mp_ready")}</div> : (
              <ul className="space-y-1.5">{check.res.errors.map((e: string, i: number) => <li key={i} className="flex gap-2 text-sm text-red-700"><XCircle className="w-4 h-4 shrink-0 mt-0.5" />{e}</li>)}</ul>
            )}
            {check.res.preview && <div className="text-sm text-ink-500">{money2(check.res.preview.price, check.res.preview.currency)} · {t("stock")}: {check.res.preview.stock}</div>}
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => { setInfo(check.p.id); setCheck(null); }}>{t("mp_market_info")}</Button>
              {check.res.ok && <Button onClick={() => { publish([check.p.id]); setCheck(null); }}><UploadCloud className="w-4 h-4" />{t("mp_publish")}</Button>}
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
