"use client";
import clsx from "clsx";
import { ArrowDown, ArrowUp, Check, ListTree, Pencil, Plus, Receipt, Search, Trash2, X } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useMe } from "@/components/CabinetShell";
import { Badge, Button, CatIcon, Empty, Field, Input, Modal, Select, Spinner, Toast } from "@/components/ui";
import { ApiError, api, errText, qs } from "@/lib/api";
import { useApp } from "@/lib/store";
import type { AttrType, AttributeDef, I18n, IkpuItem } from "@/lib/types";

const TYPES: AttrType[] = ["text", "number", "enum", "bool"];
const TYPE_KEY = { text: "sv_type_text", number: "sv_type_number", enum: "sv_type_enum", bool: "sv_type_bool" } as const;
const CODE_RE = /^[a-z][a-z0-9_]*$/;

/** O'zbekcha nomdan kod: "Qora rang" → "qora_rang" */
function slugify(s: string) {
  return s.toLowerCase().replace(/[ʻʼ'`‘’]/g, "").replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "").slice(0, 48);
}
/** Faqat haqiqatan tarjima qilingan tilni ko'rsatamiz (backend bo'sh tillarni uz bilan to'ldiradi) */
const own = (d: I18n | undefined, lang: "ru" | "en" | "kaa") => (d?.[lang] && d[lang] !== d.uz ? d[lang]! : "");
/** Tahrirlangan nomni yuborish: avtomatik to'ldirilganlarni tashlab, qo'lda kiritilganlarni saqlaymiz */
function i18nOut(orig: I18n | undefined, edits: Partial<Record<"uz" | "ru" | "en" | "kaa", string>>): I18n {
  const out: I18n = {};
  (["en", "kaa"] as const).forEach((l) => { const v = own(orig, l); if (v) out[l] = v; });
  Object.entries(edits).forEach(([k, v]) => {
    const key = k as "uz" | "ru" | "en" | "kaa";
    if (v !== undefined) { if (v.trim()) out[key] = v.trim(); else delete out[key]; }
  });
  return out;
}

type OptRow = { v: string; uz: string; ru: string; orig?: I18n; key: number };
type Form = {
  code: string; uz: string; ru: string; en: string; kaa: string; hint_uz: string; hint_ru: string;
  type: AttrType; unit: string; required: boolean; multi: boolean; variant: boolean; order: string; options: OptRow[];
};
let seq = 1;
const toForm = (d: AttributeDef | null, nextOrder: number): Form => d ? {
  code: d.code, uz: d.name.uz || "", ru: own(d.name, "ru"), en: own(d.name, "en"), kaa: own(d.name, "kaa"),
  hint_uz: d.hint?.uz || "", hint_ru: own(d.hint, "ru"), type: d.type, unit: d.unit || "", required: d.required, multi: d.multi,
  variant: d.variant, order: String(d.order),
  options: (d.options || []).map((o) => ({ v: o.v, uz: o.name?.uz || "", ru: own(o.name, "ru"), orig: o.name, key: seq++ })),
} : {
  code: "", uz: "", ru: "", en: "", kaa: "", hint_uz: "", hint_ru: "", type: "text", unit: "", required: false, multi: false,
  variant: false, order: String(nextOrder), options: [],
};

function Flag({ on, label, onChange, hint, disabled }: { on: boolean; label: string; onChange: (v: boolean) => void; hint?: string; disabled?: boolean }) {
  return (
    <label className={clsx("flex items-start gap-2.5 rounded-xl border px-3 py-2.5 cursor-pointer text-sm", on ? "border-brand-500 bg-brand-50" : "border-ink-300 bg-white", disabled && "opacity-50 pointer-events-none")}>
      <input type="checkbox" className="accent-brand-600 mt-0.5" checked={on} disabled={disabled} onChange={(e) => onChange(e.target.checked)} />
      <span><span className="font-semibold text-ink-900">{label}</span>{hint && <span className="block text-xs text-ink-500 mt-0.5">{hint}</span>}</span>
    </label>
  );
}

function DefForm({ def, category, nextOrder, onSaved, onCancel }: { def: AttributeDef | null; category: string; nextOrder: number; onSaved: (d: AttributeDef) => void; onCancel: () => void }) {
  const { t } = useApp();
  const [f, setF] = useState<Form>(() => toForm(def, nextOrder));
  const [codeTouched, setCodeTouched] = useState(!!def);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const set = (patch: Partial<Form>) => setF((x) => ({ ...x, ...patch }));
  const setOpt = (key: number, patch: Partial<OptRow>) => set({ options: f.options.map((o) => (o.key === key ? { ...o, ...patch } : o)) });
  const moveOpt = (i: number, d: number) => {
    const j = i + d;
    if (j < 0 || j >= f.options.length) return;
    const arr = f.options.slice();
    [arr[i], arr[j]] = [arr[j], arr[i]];
    set({ options: arr });
  };
  const isEnum = f.type === "enum";
  const canVariant = f.type === "enum" || f.type === "number";

  const save = async () => {
    setErr("");
    if (!def && !CODE_RE.test(f.code)) return setErr(t("sv_err_code"));
    if (!f.uz.trim()) return setErr(t("sv_err_name"));
    const options = isEnum ? f.options.map((o) => ({ v: (o.v.trim() || slugify(o.uz)), name: i18nOut(o.orig, { uz: o.uz, ru: o.ru }) })) : [];
    if (isEnum) {
      if (!options.length) return setErr(t("sv_err_options"));
      if (options.some((o) => !o.v || !o.name.uz)) return setErr(t("sv_err_option_row"));
      const codes = options.map((o) => o.v);
      if (new Set(codes).size !== codes.length) return setErr(t("sv_err_option_dup"));
    }
    const body: Record<string, unknown> = {
      name: i18nOut(def?.name, { uz: f.uz, ru: f.ru, en: f.en, kaa: f.kaa }),
      hint: i18nOut(def?.hint, { uz: f.hint_uz, ru: f.hint_ru }),
      type: f.type, unit: f.unit.trim(), required: f.required, multi: f.multi, variant: canVariant && f.variant,
      order: Number(f.order) || 0, options,
    };
    setBusy(true);
    try {
      const r = def
        ? await api<AttributeDef>(`/attributes/${def.id}/`, { method: "PATCH", json: body, authed: true })
        : await api<AttributeDef>("/attributes/", { method: "POST", json: { ...body, category, code: f.code }, authed: true });
      onSaved(r);
    } catch (e) { setErr(errText(e)); } finally { setBusy(false); }
  };

  return (
    <div className="space-y-4">
      <div className="grid sm:grid-cols-[1fr_150px_110px] gap-3">
        <Field label={t("sv_attr_code")} hint={def ? t("sv_attr_code_locked") : t("sv_attr_code_hint")}>
          <Input value={f.code} disabled={!!def} className="font-mono" placeholder="rang"
            onChange={(e) => { setCodeTouched(true); set({ code: e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, "") }); }} />
        </Field>
        <Field label={t("sv_attr_type")}>
          <Select value={f.type} onChange={(e) => { const ty = e.target.value as AttrType; set({ type: ty, variant: ty === "enum" || ty === "number" ? f.variant : false }); }}>
            {TYPES.map((x) => <option key={x} value={x}>{t(TYPE_KEY[x])}</option>)}
          </Select>
        </Field>
        <Field label={t("sv_attr_unit")}><Input value={f.unit} onChange={(e) => set({ unit: e.target.value })} placeholder="sm, kg…" /></Field>
      </div>
      <div className="grid sm:grid-cols-2 gap-3">
        <Field label={`${t("sv_name_uz")} *`}><Input value={f.uz} onChange={(e) => set({ uz: e.target.value, ...(codeTouched ? {} : { code: slugify(e.target.value) }) })} placeholder="Rang" /></Field>
        <Field label={t("sv_name_ru")} hint={t("sv_name_ru_hint")}>
          <Input value={f.ru} onChange={(e) => set({ ru: e.target.value })} placeholder="Цвет" className="border-brand-500/60" />
        </Field>
        <Field label={t("sv_name_en")}><Input value={f.en} onChange={(e) => set({ en: e.target.value })} placeholder="Color" /></Field>
        <Field label={t("sv_name_kaa")}><Input value={f.kaa} onChange={(e) => set({ kaa: e.target.value })} /></Field>
      </div>
      <div className="grid sm:grid-cols-2 gap-3">
        <Field label={t("sv_hint_uz")}><Input value={f.hint_uz} onChange={(e) => set({ hint_uz: e.target.value })} /></Field>
        <Field label={t("sv_hint_ru")}><Input value={f.hint_ru} onChange={(e) => set({ hint_ru: e.target.value })} /></Field>
      </div>
      <div className="grid sm:grid-cols-[1fr_1fr_1fr_110px] gap-2 items-stretch">
        <Flag on={f.required} label={t("sv_flag_required")} onChange={(v) => set({ required: v })} />
        <Flag on={f.multi} label={t("sv_flag_multi")} onChange={(v) => set({ multi: v })} />
        <Flag on={f.variant && canVariant} label={t("sv_flag_variant")} hint={t("sv_flag_variant_hint")} disabled={!canVariant} onChange={(v) => set({ variant: v })} />
        <Field label={t("sv_order")}><Input inputMode="numeric" value={f.order} onChange={(e) => set({ order: e.target.value.replace(/[^\d-]/g, "") })} /></Field>
      </div>

      {isEnum && (
        <div className="rounded-xl border border-ink-100">
          <div className="px-3 py-2.5 border-b border-ink-100 flex items-center gap-2">
            <ListTree className="w-4 h-4 text-ink-500" /><span className="font-semibold text-sm">{t("sv_options")}</span>
            <span className="text-xs text-ink-500">({f.options.length})</span>
            <Button size="sm" variant="soft" className="ml-auto" onClick={() => set({ options: [...f.options, { v: "", uz: "", ru: "", key: seq++ }] })}>
              <Plus className="w-4 h-4" /> {t("sv_add_option")}
            </Button>
          </div>
          <div className="hidden sm:grid grid-cols-[130px_1fr_1fr_96px] gap-2 px-3 pt-2 text-xs text-ink-500">
            <span>{t("sv_option_code")}</span><span>{t("sv_name_uz")}</span><span>{t("sv_name_ru")}</span><span />
          </div>
          <div className="p-3 pt-2 space-y-2 max-h-[40vh] overflow-y-auto">
            {f.options.length === 0 && <div className="text-sm text-ink-500 py-3 text-center">{t("sv_options_empty")}</div>}
            {f.options.map((o, i) => (
              <div key={o.key} className="grid grid-cols-2 sm:grid-cols-[130px_1fr_1fr_96px] gap-2 items-center rounded-lg sm:rounded-none bg-ink-100/50 sm:bg-transparent p-2 sm:p-0">
                <Input className="!h-9 font-mono text-sm col-span-2 sm:col-span-1" value={o.v} placeholder={slugify(o.uz) || "qora"} aria-label={t("sv_option_code")}
                  onChange={(e) => setOpt(o.key, { v: e.target.value.toLowerCase().replace(/[^a-z0-9_.-]/g, "") })} />
                <Input className="!h-9 text-sm" value={o.uz} placeholder="Qora" aria-label={t("sv_name_uz")} onChange={(e) => setOpt(o.key, { uz: e.target.value })} />
                <Input className="!h-9 text-sm" value={o.ru} placeholder="Чёрный" aria-label={t("sv_name_ru")} onChange={(e) => setOpt(o.key, { ru: e.target.value })} />
                <div className="flex gap-0.5 justify-end col-span-2 sm:col-span-1">
                  <button type="button" onClick={() => moveOpt(i, -1)} disabled={i === 0} className="p-2 rounded-lg hover:bg-ink-100 disabled:opacity-30" aria-label={t("sv_move_up")}><ArrowUp className="w-4 h-4" /></button>
                  <button type="button" onClick={() => moveOpt(i, 1)} disabled={i === f.options.length - 1} className="p-2 rounded-lg hover:bg-ink-100 disabled:opacity-30" aria-label={t("sv_move_down")}><ArrowDown className="w-4 h-4" /></button>
                  <button type="button" onClick={() => set({ options: f.options.filter((x) => x.key !== o.key) })} className="p-2 rounded-lg text-ink-500 hover:text-red-600 hover:bg-red-50" aria-label={t("remove")}><X className="w-4 h-4" /></button>
                </div>
              </div>
            ))}
          </div>
          {def && <div className="px-3 pb-3 text-xs text-ink-500">{t("sv_option_code_warn")}</div>}
        </div>
      )}

      {err && <div className="text-sm text-red-700 bg-red-50 rounded-lg p-3" role="alert">{err}</div>}
      <div className="flex justify-end gap-2">
        <Button variant="ghost" onClick={onCancel}>{t("cancel")}</Button>
        <Button onClick={save} loading={busy}><Check className="w-4 h-4" /> {t("save")}</Button>
      </div>
    </div>
  );
}

function IkpuBox({ slug, code, name, onSaved }: { slug: string; code: string; name: string; onSaved: (code: string, name: string) => void }) {
  const { t } = useApp();
  const [q, setQ] = useState("");
  const [items, setItems] = useState<IkpuItem[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState("");
  useEffect(() => { setItems(null); setQ(""); setErr(""); }, [slug]);

  const search = async () => {
    if (q.trim().length < 2) return;
    setBusy(true); setErr("");
    try {
      const r = await api<{ items: IkpuItem[]; error?: string }>(`/seller/ikpu/search/${qs({ q: q.trim(), lang: "ru" })}`, { authed: true });
      setItems(r.items); if (r.error) setErr(r.error);
    } catch (e) {
      setItems([]);
      setErr(e instanceof ApiError && e.status === 502 ? t("sv_ikpu_down") : errText(e));
    } finally { setBusy(false); }
  };
  const save = async (c: string, n: string) => {
    setSaving(true); setErr("");
    try {
      const r = await api<{ ikpu_default?: string; ikpu_name?: string }>(`/seller/categories/${slug}/ikpu/`, { method: "PATCH", json: { ikpu_default: c, ikpu_name: n }, authed: true });
      onSaved(r.ikpu_default ?? c, r.ikpu_name ?? n); setItems(null); setQ("");
    } catch (e) { setErr(errText(e)); } finally { setSaving(false); }
  };
  const manual = /^\d{17}$/.test(q.trim());

  return (
    <div className="card p-4 sm:p-5">
      <div className="flex items-start gap-3">
        <div className="w-10 h-10 rounded-xl bg-brand-50 text-brand-700 grid place-items-center shrink-0"><Receipt className="w-5 h-5" /></div>
        <div className="min-w-0 flex-1">
          <div className="font-bold">{t("sv_ikpu_default")}</div>
          <div className="text-xs text-ink-500">{t("sv_ikpu_default_hint")}</div>
          {code ? (
            <div className="mt-2 flex flex-wrap items-center gap-2 text-sm">
              <span className="font-mono font-semibold bg-ink-100 rounded-lg px-2 py-0.5">{code}</span>
              <span className="text-ink-700 min-w-0">{name}</span>
              <Button size="sm" variant="ghost" className="!h-8 text-red-600" loading={saving} onClick={() => save("", "")}><X className="w-4 h-4" /> {t("clear")}</Button>
            </div>
          ) : <div className="mt-2 text-sm text-amber-700">{t("sv_ikpu_none")}</div>}
        </div>
      </div>
      <div className="flex gap-2 mt-4">
        <Input value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === "Enter" && search()} placeholder={t("sv_ikpu_search_ph")} aria-label={t("sv_ikpu_search_ph")} />
        <Button variant="outline" onClick={search} loading={busy} aria-label={t("search")}><Search className="w-4 h-4" /></Button>
      </div>
      {manual && <Button size="sm" variant="soft" className="mt-2" loading={saving} onClick={() => save(q.trim(), "")}><Check className="w-4 h-4" /> {t("sv_ikpu_use_code", { code: q.trim() })}</Button>}
      {err && <div className="text-sm text-red-700 mt-2">{err}</div>}
      {items && (
        items.length === 0 ? <div className="text-sm text-ink-500 mt-3">{t("nothing_found")}</div> : (
          <div className="mt-3 max-h-72 overflow-y-auto border border-ink-100 rounded-xl divide-y divide-ink-100">
            {items.map((it) => (
              <button key={it.code} type="button" disabled={saving} onClick={() => save(it.code, it.name)}
                className={clsx("block w-full text-left px-3 py-2 hover:bg-brand-50 text-sm", it.code === code && "bg-brand-50")}>
                <span className="font-mono text-xs font-semibold text-brand-700">{it.code}</span>
                <span className="block text-ink-900">{it.name}</span>
                {(it.group || it.class) && <span className="block text-xs text-ink-500 truncate">{[it.group, it.class, it.position].filter(Boolean).join(" › ")}</span>}
              </button>
            ))}
          </div>
        )
      )}
    </div>
  );
}

export default function AttributesPage() {
  const { t, p, meta } = useApp();
  const { me } = useMe();
  const isOperator = me.seller.role === "operator";
  const [cat, setCat] = useState("");
  const [defs, setDefs] = useState<AttributeDef[] | null>(null);
  const [edit, setEdit] = useState<AttributeDef | "new" | null>(null);
  const [del, setDel] = useState<AttributeDef | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [toast, setToast] = useState<string | null>(null);
  const clearToast = useCallback(() => setToast(null), []);
  const [ikpu, setIkpu] = useState<Record<string, { code: string; name: string }>>({});

  useEffect(() => {
    if (cat || !meta?.categories.length) return;
    let saved = "";
    try { saved = localStorage.getItem("sv_attr_cat") || ""; } catch {}
    setCat(meta.categories.some((c) => c.slug === saved) ? saved : meta.categories[0].slug);
  }, [meta, cat]);

  const load = useCallback(() => {
    if (!cat) return;
    setDefs(null);
    api<AttributeDef[]>(`/attributes/${qs({ category: cat })}`).then((x) => setDefs(x.slice().sort((a, b) => a.order - b.order || a.id - b.id))).catch((e) => { setDefs([]); setErr(errText(e)); });
  }, [cat]);
  useEffect(() => { load(); }, [load]);

  const category = meta?.categories.find((c) => c.slug === cat);
  const curIkpu = ikpu[cat] || { code: category?.ikpu_default || "", name: category?.ikpu_name || "" };
  const nextOrder = useMemo(() => (defs?.length ? Math.max(...defs.map((d) => d.order)) + 10 : 10), [defs]);
  const pickCat = (s: string) => { setCat(s); setErr(""); try { localStorage.setItem("sv_attr_cat", s); } catch {} };

  const move = async (i: number, d: number) => {
    if (!defs) return;
    const j = i + d;
    if (j < 0 || j >= defs.length) return;
    const arr = defs.slice();
    [arr[i], arr[j]] = [arr[j], arr[i]];
    const changed = arr.map((x, k) => ({ x, order: (k + 1) * 10 })).filter(({ x, order }) => x.order !== order);
    setDefs(arr.map((x, k) => ({ ...x, order: (k + 1) * 10 })));
    try {
      await Promise.all(changed.map(({ x, order }) => api(`/attributes/${x.id}/`, { method: "PATCH", json: { order }, authed: true })));
    } catch (e) { setErr(errText(e)); load(); }
  };
  const remove = async () => {
    if (!del) return;
    setBusy(true);
    try { await api(`/attributes/${del.id}/`, { method: "DELETE", authed: true }); setDel(null); setToast(t("sv_deleted")); load(); }
    catch (e) { setErr(errText(e)); setDel(null); } finally { setBusy(false); }
  };

  if (!isOperator) return <Empty title={t("sv_operator_only")} sub={t("sv_operator_only_sub")} />;

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-extrabold">{t("sv_attrs_title")}</h1>
        <p className="text-ink-500 mt-1 max-w-3xl text-sm">{t("sv_attrs_sub")}</p>
      </div>

      <div className="flex gap-2 overflow-x-auto no-scrollbar -mx-4 px-4 lg:mx-0 lg:px-0 lg:flex-wrap" role="tablist" aria-label={t("categories")}>
        {meta?.categories.map((c) => (
          <button key={c.slug} role="tab" aria-selected={c.slug === cat} onClick={() => pickCat(c.slug)}
            className={clsx("inline-flex items-center gap-2 h-10 px-3 rounded-xl border text-sm font-semibold whitespace-nowrap transition",
              c.slug === cat ? "border-brand-600 bg-brand-600 text-white" : "border-ink-300 bg-white text-ink-700 hover:bg-ink-100")}>
            <CatIcon icon={c.icon} className="w-4 h-4" /> {p(c.name)}
          </button>
        ))}
      </div>

      {err && <div className="text-sm text-red-700 bg-red-50 rounded-lg p-3 flex gap-2" role="alert"><span className="flex-1">{err}</span><button onClick={() => setErr("")} aria-label={t("close")}><X className="w-4 h-4" /></button></div>}

      {cat && (
        <div className="grid xl:grid-cols-[minmax(0,1fr)_360px] gap-5 items-start">
          <div className="card overflow-hidden">
            <div className="px-4 sm:px-5 py-3 border-b border-ink-100 flex items-center gap-3">
              <div className="font-bold min-w-0 truncate">{p(category?.name)} <span className="text-ink-500 font-normal">· {defs?.length ?? "…"}</span></div>
              <Button size="sm" className="ml-auto" onClick={() => setEdit("new")}><Plus className="w-4 h-4" /> {t("sv_add_attr")}</Button>
            </div>
            {!defs ? <div className="py-16 grid place-items-center"><Spinner /></div> : defs.length === 0 ? (
              <Empty icon={<ListTree className="w-7 h-7" />} title={t("sv_no_defs")} action={<Button onClick={() => setEdit("new")}><Plus className="w-4 h-4" /> {t("sv_add_attr")}</Button>} />
            ) : (
              <>
                <div className="hidden md:grid grid-cols-[64px_minmax(0,1.4fr)_110px_minmax(0,1.2fr)_88px] gap-3 px-5 py-2 text-xs text-ink-500 bg-ink-100/60">
                  <span>{t("sv_order")}</span><span>{t("name")}</span><span>{t("sv_attr_type")}</span><span>{t("sv_options")}</span><span />
                </div>
                <ul className="divide-y divide-ink-100">
                  {defs.map((d, i) => (
                    <li key={d.id} className="px-4 sm:px-5 py-3 grid grid-cols-[auto_minmax(0,1fr)_auto] md:grid-cols-[64px_minmax(0,1.4fr)_110px_minmax(0,1.2fr)_88px] gap-x-3 gap-y-1.5 items-center">
                      <div className="flex md:flex-col gap-0.5 row-span-2 md:row-span-1">
                        <button onClick={() => move(i, -1)} disabled={i === 0} className="p-1 rounded-md hover:bg-ink-100 disabled:opacity-30" aria-label={t("sv_move_up")}><ArrowUp className="w-4 h-4" /></button>
                        <button onClick={() => move(i, 1)} disabled={i === defs.length - 1} className="p-1 rounded-md hover:bg-ink-100 disabled:opacity-30" aria-label={t("sv_move_down")}><ArrowDown className="w-4 h-4" /></button>
                      </div>
                      <div className="min-w-0">
                        <div className="font-semibold text-ink-900 truncate">{p(d.name)}{d.unit && <span className="text-ink-500 font-normal">, {d.unit}</span>}</div>
                        <div className="text-xs text-ink-500 truncate"><span className="font-mono">{d.code}</span>{own(d.name, "ru") && <> · {d.name.ru}</>}</div>
                        <div className="flex flex-wrap gap-1 mt-1">
                          {d.required && <Badge tone="red">{t("sv_flag_required")}</Badge>}
                          {d.multi && <Badge tone="blue">{t("sv_flag_multi")}</Badge>}
                          {d.variant && <Badge tone="violet">{t("sv_flag_variant")}</Badge>}
                          {!own(d.name, "ru") && <Badge tone="amber">{t("sv_no_ru")}</Badge>}
                        </div>
                      </div>
                      <div className="hidden md:block"><Badge>{t(TYPE_KEY[d.type])}</Badge></div>
                      <div className="hidden md:block text-xs text-ink-500 min-w-0 line-clamp-2">
                        {d.type === "enum" ? d.options.map((o) => p(o.name) || o.v).join(", ") : "—"}
                      </div>
                      <div className="flex justify-end gap-0.5 row-span-2 md:row-span-1">
                        <button onClick={() => setEdit(d)} className="p-2 rounded-lg hover:bg-ink-100 text-ink-700" aria-label={t("edit")}><Pencil className="w-4 h-4" /></button>
                        <button onClick={() => setDel(d)} className="p-2 rounded-lg hover:bg-red-50 text-ink-500 hover:text-red-600" aria-label={t("remove")}><Trash2 className="w-4 h-4" /></button>
                      </div>
                      <div className="md:hidden col-start-2 text-xs text-ink-500 min-w-0 line-clamp-2">
                        {t(TYPE_KEY[d.type])}{d.type === "enum" && `: ${d.options.map((o) => p(o.name) || o.v).join(", ")}`}
                      </div>
                    </li>
                  ))}
                </ul>
              </>
            )}
          </div>
          <IkpuBox slug={cat} code={curIkpu.code} name={curIkpu.name}
            onSaved={(code, name) => { setIkpu({ ...ikpu, [cat]: { code, name } }); setToast(t("saved")); }} />
        </div>
      )}

      <Modal open={!!edit} onClose={() => setEdit(null)} wide
        title={edit === "new" ? `${t("sv_add_attr")} · ${p(category?.name)}` : edit ? `${t("edit")}: ${p(edit.name)}` : ""}>
        {edit && <DefForm def={edit === "new" ? null : edit} category={cat} nextOrder={nextOrder}
          onCancel={() => setEdit(null)} onSaved={() => { setEdit(null); setToast(t("saved")); load(); }} />}
      </Modal>

      <Modal open={!!del} onClose={() => setDel(null)} title={t("sv_delete_attr")}>
        {del && (
          <div className="space-y-4">
            <p className="text-ink-700">{t("sv_delete_confirm", { name: p(del.name) })}</p>
            <div className="text-sm text-amber-800 bg-amber-50 rounded-lg p-3">{t("sv_delete_warn")}</div>
            <div className="flex justify-end gap-2">
              <Button variant="ghost" onClick={() => setDel(null)}>{t("cancel")}</Button>
              <Button variant="danger" loading={busy} onClick={remove}><Trash2 className="w-4 h-4" /> {t("remove")}</Button>
            </div>
          </div>
        )}
      </Modal>
      <Toast text={toast} onDone={clearToast} />
    </div>
  );
}
