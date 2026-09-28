"use client";
import clsx from "clsx";
import { Check, RefreshCw, Search } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Badge, Button, CatIcon, Field, Input, Modal, Select, Spinner } from "@/components/ui";
import { api, errText, qs } from "@/lib/api";
import { useApp } from "@/lib/store";
import type { I18n, Paged } from "@/lib/types";
import { type MpCode, type MpMeta, MpBadge, waitJob } from "./common";

type Overview = { slug: string; name: I18n; icon: string; maps: Record<MpCode, { id: number; external_name: string; missing: number } | null> }[];
type Attr = { id: number; external_id: string; name: string; required: boolean; is_dictionary: boolean; multi: boolean; value_type: string; unit: string;
  source: string; field: string; value: string; value_id: string; values: { id: string; value: string }[]; value_map: { id: number; our_value: string; external_value_id: string; external_value: string }[] };
type Mapping = { id: number; category: string; marketplace: MpCode; external_id: string; external_type_id: string; external_name: string; attributes: Attr[]; required_missing: number };

function ValuePicker({ attr, onPick }: { attr: Attr; onPick: (id: string, value: string) => void }) {
  const { t } = useApp();
  const [q, setQ] = useState("");
  const [found, setFound] = useState<{ id: string; value: string }[] | null>(null);
  const [busy, setBusy] = useState(false);
  const local = attr.values?.length ? attr.values.filter((v) => !q || v.value.toLowerCase().includes(q.toLowerCase())).slice(0, 50) : null;
  const search = async () => {
    setBusy(true);
    try {
      const r = await api<any>(`/mp/attributes/${attr.id}/search/`, { method: "POST", json: { query: q }, authed: true });
      const job = await waitJob(r.job.id, 30000);
      setFound(job.result?.values || []);
    } catch (e) { setFound([]); } finally { setBusy(false); }
  };
  const list = local || found;
  return (
    <div className="space-y-2">
      <div className="flex gap-2">
        <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder={t("search")} onKeyDown={(e) => e.key === "Enter" && !local && search()} />
        {!local && <Button variant="outline" onClick={search} loading={busy}><Search className="w-4 h-4" /></Button>}
      </div>
      {list && <div className="max-h-48 overflow-y-auto divide-y divide-ink-100 border border-ink-100 rounded-lg">
        {list.map((v) => <button key={v.id} type="button" onClick={() => onPick(v.id, v.value)} className="block w-full text-left px-3 py-1.5 text-sm hover:bg-brand-50">{v.value} <span className="text-ink-400 text-xs">#{v.id}</span></button>)}
      </div>}
    </div>
  );
}

function AttrRow({ a, fields, onSaved }: { a: Attr; fields: string[]; onSaved: () => void }) {
  const { t } = useApp();
  const [f, setF] = useState(a);
  const [pick, setPick] = useState(false);
  const [our, setOur] = useState("");
  const [busy, setBusy] = useState(false);
  const dirty = f.source !== a.source || f.field !== a.field || f.value !== a.value || f.value_id !== a.value_id;
  const save = async () => {
    setBusy(true);
    try { await api(`/mp/attributes/${a.id}/`, { method: "PATCH", json: { source: f.source, field: f.field, value: f.value, value_id: f.value_id }, authed: true }); onSaved(); }
    finally { setBusy(false); }
  };
  const addMap = async (id: string, value: string) => {
    if (!our) return;
    await api(`/mp/attributes/${a.id}/value-map/`, { method: "POST", json: { our_value: our, external_value_id: id, external_value: value }, authed: true });
    setOur(""); onSaved();
  };
  const needsValue = a.required && f.source === "const" && !f.value && !f.value_id;
  return (
    <div className={clsx("p-3 space-y-2", needsValue && "bg-amber-50/60")}>
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-medium text-sm">{a.name}{a.required && <span className="text-red-600"> *</span>}</span>
        <span className="text-xs text-ink-400">#{a.external_id} {a.value_type} {a.unit}</span>
        {a.is_dictionary && <Badge tone="violet">{t("mp_value_map")}</Badge>}
      </div>
      <div className="grid sm:grid-cols-[180px_1fr_auto] gap-2 items-start">
        <Select value={f.source} onChange={(e) => setF({ ...f, source: e.target.value })}>
          <option value="const">{t("mp_src_const")}</option><option value="field">{t("mp_src_field")}</option><option value="product">{t("mp_src_product")}</option>
        </Select>
        {f.source === "field" ? (
          <Select value={f.field} onChange={(e) => setF({ ...f, field: e.target.value })}><option value="">—</option>{fields.map((x) => <option key={x} value={x}>{x}</option>)}</Select>
        ) : f.source === "const" ? (
          <div className="space-y-2">
            <div className="flex gap-2">
              <Input value={f.value} onChange={(e) => setF({ ...f, value: e.target.value, value_id: "" })} />
              {(a.is_dictionary || a.values?.length > 0) && <Button variant="outline" onClick={() => setPick(!pick)}><Search className="w-4 h-4" /></Button>}
            </div>
            {f.value_id && <div className="text-xs text-ink-500">ID: {f.value_id}</div>}
            {pick && <ValuePicker attr={a} onPick={(id, v) => { setF({ ...f, value: v, value_id: id }); setPick(false); }} />}
          </div>
        ) : <div className="text-xs text-ink-500 pt-3">{t("mp_market_info")}</div>}
        <Button onClick={save} loading={busy} disabled={!dirty}><Check className="w-4 h-4" /></Button>
      </div>
      {a.is_dictionary && f.source !== "const" && (
        <div className="rounded-lg border border-ink-100 p-2 space-y-2">
          {a.value_map.map((m) => <div key={m.id} className="text-xs">{m.our_value} → <b>{m.external_value}</b> <span className="text-ink-400">#{m.external_value_id}</span></div>)}
          <Input value={our} onChange={(e) => setOur(e.target.value)} placeholder="ImkonMarket → …" />
          {our && <ValuePicker attr={a} onPick={addMap} />}
        </div>
      )}
    </div>
  );
}

function Editor({ slug, mp, mappingId, meta, onChanged }: { slug: string; mp: MpCode; mappingId: number | null; meta: MpMeta; onChanged: () => void }) {
  const { t } = useApp();
  const [mapping, setMapping] = useState<Mapping | null>(null);
  const [q, setQ] = useState("");
  const [cats, setCats] = useState<Paged<any> | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const loadMapping = useCallback(async (id: number | null) => { if (id) setMapping(await api<Mapping>(`/mp/mappings/${id}/`, { authed: true })); }, []);
  useEffect(() => { loadMapping(mappingId); }, [mappingId, loadMapping]);
  const search = useCallback(() => api<Paged<any>>(`/mp/categories/${qs({ marketplace: mp, q, page_size: 50 })}`, { authed: true }).then(setCats), [mp, q]);
  useEffect(() => { search(); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  const refreshCats = async () => {
    setBusy(true); setErr("");
    try { const r = await api<any>("/mp/categories/refresh/", { method: "POST", json: { marketplace: mp }, authed: true }); const j = await waitJob(r.job.id, 120000); if (j.last_error) setErr(j.last_error); await search(); }
    catch (e) { setErr(errText(e)); } finally { setBusy(false); }
  };
  const choose = async (c: any) => {
    setBusy(true); setErr("");
    const body = { category: slug, marketplace: mp, external_id: c.external_id, external_type_id: c.type_id || "", external_name: c.path || c.name };
    try {
      const m = mapping ? await api<Mapping>(`/mp/mappings/${mapping.id}/`, { method: "PATCH", json: body, authed: true })
        : await api<Mapping>("/mp/mappings/", { method: "POST", json: body, authed: true });
      setMapping(m); onChanged();
      const r = await api<any>(`/mp/mappings/${m.id}/fetch-attributes/`, { method: "POST", authed: true }).catch(() => null);
      if (r?.job) { const j = await waitJob(r.job.id, 60000); if (j.last_error) setErr(j.last_error); }
      await loadMapping(m.id); onChanged();
    } catch (e) { setErr(errText(e)); } finally { setBusy(false); }
  };
  return (
    <div className="space-y-4">
      {mapping && <div className="rounded-xl bg-brand-50 p-3 text-sm"><b>{mapping.external_name}</b> <span className="text-ink-500">#{mapping.external_id}{mapping.external_type_id && `/${mapping.external_type_id}`}</span></div>}
      <div className="flex gap-2">
        <Input value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === "Enter" && search()} placeholder={t("mp_search_cat")} />
        <Button variant="outline" onClick={search}><Search className="w-4 h-4" /></Button>
        <Button variant="outline" onClick={refreshCats} loading={busy} title={t("mp_refresh_cats")}><RefreshCw className="w-4 h-4" /></Button>
      </div>
      {cats && cats.results.length > 0 && (
        <div className="max-h-56 overflow-y-auto border border-ink-100 rounded-xl divide-y divide-ink-100">
          {cats.results.map((c) => <button key={c.id} onClick={() => choose(c)} className="block w-full text-left px-3 py-2 text-sm hover:bg-brand-50">{c.path || c.name} <span className="text-xs text-ink-400">#{c.external_id}{c.type_id && `/${c.type_id}`}</span></button>)}
        </div>
      )}
      {cats && cats.count === 0 && <div className="text-sm text-ink-500">{t("mp_refresh_cats")} ↻</div>}
      {err && <div className="text-sm text-red-600">{err}</div>}
      {mapping && mapping.attributes.length > 0 && (
        <div>
          <div className="font-semibold mb-2">{t("mp_attrs")} ({mapping.attributes.length})</div>
          <div className="border border-ink-100 rounded-xl divide-y divide-ink-100 max-h-[50vh] overflow-y-auto">
            {mapping.attributes.map((a) => <AttrRow key={a.id + a.source + a.value} a={a} fields={meta.attribute_fields} onSaved={() => { loadMapping(mapping.id); onChanged(); }} />)}
          </div>
        </div>
      )}
    </div>
  );
}

export default function MappingTab({ meta }: { meta: MpMeta }) {
  const { t, p } = useApp();
  const [rows, setRows] = useState<Overview | null>(null);
  const [open, setOpen] = useState<{ slug: string; mp: MpCode; id: number | null; name: string } | null>(null);
  const load = useCallback(() => api<Overview>("/mp/overview/", { authed: true }).then(setRows), []);
  useEffect(() => { load(); }, [load]);
  const mps = meta.marketplaces.filter((m) => m.capabilities.includes("categories"));
  if (!rows) return <Spinner />;
  return (
    <div className="space-y-3">
      <div className="card overflow-x-auto">
        <table className="w-full text-sm">
          <thead><tr className="text-left text-xs text-ink-500">
            <th className="p-3">{t("categories")}</th>
            {mps.map((m) => <th key={m.code} className="p-3"><span className="inline-flex items-center gap-2"><MpBadge code={m.code} size={22} />{m.name}</span></th>)}
          </tr></thead>
          <tbody className="divide-y divide-ink-100">
            {rows.map((r) => (
              <tr key={r.slug}>
                <td className="p-3 font-medium"><span className="inline-flex items-center gap-2"><CatIcon icon={r.icon} className="w-4 h-4 text-ink-500" />{p(r.name)}</span></td>
                {mps.map((m) => {
                  const x = r.maps[m.code];
                  return (
                    <td key={m.code} className="p-2">
                      <button disabled={!meta.is_operator} onClick={() => setOpen({ slug: r.slug, mp: m.code, id: x?.id || null, name: p(r.name) })}
                        className={clsx("w-full text-left rounded-lg px-2.5 py-1.5 text-xs border", x ? (x.missing ? "border-amber-300 bg-amber-50" : "border-emerald-200 bg-emerald-50") : "border-dashed border-ink-300 text-ink-500")}>
                        {x ? <><div className="line-clamp-2">{x.external_name}</div>{x.missing > 0 && <div className="text-amber-700 font-semibold">{x.missing} {t("mp_req_missing")}</div>}</> : t("mp_not_mapped")}
                      </button>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Modal open={!!open} onClose={() => setOpen(null)} wide title={open ? <span className="inline-flex items-center gap-2"><MpBadge code={open.mp} size={24} />{open.name}</span> : ""}>
        {open && <Editor slug={open.slug} mp={open.mp} mappingId={open.id} meta={meta} onChanged={load} />}
      </Modal>
    </div>
  );
}
