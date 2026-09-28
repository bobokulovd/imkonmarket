"use client";
import clsx from "clsx";
import { FileSignature, Plus, Search, ShoppingBag, Trash2 } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import BuyerForm, { emptyBuyer, validateBuyer, type Buyer } from "@/components/BuyerForm";
import { useMe } from "@/components/CabinetShell";
import { Badge, Button, Empty, Input, Modal, Qty, Select, Spinner } from "@/components/ui";
import { api, errText, qs } from "@/lib/api";
import { useApp } from "@/lib/store";
import type { Paged, Product, SellerApplication } from "@/lib/types";

type Line = { product: Product; qty: number; price: string };

export default function AgentCatalogPage() {
  const { t, p, money, unit, meta, lang } = useApp();
  const { me } = useMe();
  const [data, setData] = useState<Paged<Product> | null>(null);
  const [f, setF] = useState({ q: "", category: "", seller: "", region: "", in_stock: "", page: 1 });
  const [deal, setDeal] = useState<Line[]>([]);
  const [open, setOpen] = useState(false);
  const [b, setB] = useState<Buyer>(() => ({ ...emptyBuyer(lang), buyer_type: "b2b", payment_method: "bank" }));
  const [errors, setErrors] = useState<Partial<Record<keyof Buyer, boolean>>>({});
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [result, setResult] = useState<SellerApplication[] | null>(null);

  const load = useCallback(() => {
    api<Paged<Product>>(`/seller/catalog/${qs({ ...f, page_size: 30, ordering: "name" })}`, { authed: true }).then(setData).catch(() => {});
  }, [f]);
  useEffect(() => { const id = setTimeout(load, 250); return () => clearTimeout(id); }, [load]);

  const add = (pr: Product) => setDeal((d) => (d.some((l) => l.product.id === pr.id) ? d : [...d, { product: pr, qty: pr.min_order || 1, price: pr.price ? String(Number(pr.price)) : "" }]));
  const total = deal.reduce((s, l) => s + Number(l.price || 0) * l.qty, 0);
  const owners = Array.from(new Set(deal.map((l) => l.product.seller.code)));

  const submit = async () => {
    const e = validateBuyer(b);
    setErrors(e);
    if (Object.keys(e).length) return;
    setBusy(true); setErr("");
    try {
      const r = await api<SellerApplication[]>("/seller/agent-order/", {
        method: "POST", authed: true,
        json: { ...b, items: deal.map((l) => ({ product: l.product.id, qty: l.qty, price: l.price || null })) },
      });
      setResult(r); setDeal([]); load();
    } catch (x) { setErr(errText(x)); } finally { setBusy(false); }
  };

  return (
    <div className="grid xl:grid-cols-[minmax(0,1fr)_340px] gap-5">
      <div className="min-w-0">
        <h1 className="text-2xl font-extrabold">{t("agent_title")}</h1>
        <p className="text-ink-500 mt-1 max-w-3xl text-sm">{t("agent_sub")}</p>
        <div className="flex flex-wrap gap-2 mt-4">
          <div className="relative flex-1 min-w-[200px]">
            <Search className="w-4 h-4 absolute left-3 top-3.5 text-ink-500" />
            <Input value={f.q} onChange={(e) => setF({ ...f, q: e.target.value, page: 1 })} placeholder={t("search_ph")} className="pl-9" />
          </div>
          <Select value={f.category} onChange={(e) => setF({ ...f, category: e.target.value, page: 1 })} className="w-auto max-w-[220px]">
            <option value="">{t("all_categories")}</option>{meta?.categories.map((c) => <option key={c.slug} value={c.slug}>{p(c.name)}</option>)}
          </Select>
          <Select value={f.seller} onChange={(e) => setF({ ...f, seller: e.target.value, page: 1 })} className="w-auto">
            <option value="">{t("sellers")}</option>{meta?.sellers.filter((s) => s.product_count).map((s) => <option key={s.code} value={s.code}>{p(s.name)}</option>)}
          </Select>
          <label className="h-11 px-3 rounded-xl border border-ink-300 bg-white inline-flex items-center gap-2 text-sm">
            <input type="checkbox" className="accent-brand-600" checked={!!f.in_stock} onChange={(e) => setF({ ...f, in_stock: e.target.checked ? "1" : "", page: 1 })} /> {t("only_in_stock")}
          </label>
        </div>
        <div className="card mt-4 overflow-hidden">
          {!data ? <div className="py-16 grid place-items-center"><Spinner /></div> : data.results.length === 0 ? <Empty title={t("nothing_found")} /> : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm min-w-[820px]">
                <thead className="bg-ink-100/60 text-ink-500 text-left">
                  <tr><th className="px-4 py-3">{t("name")}</th><th className="px-4 py-3">{t("owner")}</th><th className="px-4 py-3 text-right">{t("price")}</th><th className="px-4 py-3 text-right">{t("stock")}</th><th className="px-4 py-3 text-right">{t("reserved")}</th><th className="px-4 py-3 text-right">{t("available")}</th><th className="px-4 py-3" /></tr>
                </thead>
                <tbody className="divide-y divide-ink-100">
                  {data.results.map((pr) => {
                    const inDeal = deal.some((l) => l.product.id === pr.id);
                    const soldOut = pr.available !== null && pr.available <= 0;
                    return (
                      <tr key={pr.id} className={clsx(pr.seller.code === me.seller.code && "bg-brand-50/30")}>
                        <td className="px-4 py-2.5"><div className="font-medium">{p(pr.name)}</div><div className="text-xs text-ink-500">{p(pr.spec)} · {pr.sku}</div></td>
                        <td className="px-4 py-2.5"><div className="font-medium">{p(pr.seller.name)}</div><div className="text-xs text-ink-500">{p(pr.seller.region_i18n)}</div></td>
                        <td className="px-4 py-2.5 text-right tabular-nums whitespace-nowrap">{pr.price ? money(pr.price) : <Badge tone="amber">{t("price_on_request")}</Badge>}<div className="text-xs text-ink-500">/ {unit(pr.unit)}</div></td>
                        <td className="px-4 py-2.5 text-right tabular-nums">{pr.stock ?? "∞"}</td>
                        <td className="px-4 py-2.5 text-right tabular-nums text-ink-500">{pr.reserved ?? 0}</td>
                        <td className={clsx("px-4 py-2.5 text-right tabular-nums font-bold", soldOut ? "text-red-600" : "text-emerald-700")}>{pr.available ?? "∞"}</td>
                        <td className="px-4 py-2.5 text-right">
                          <Button size="sm" variant={inDeal ? "soft" : "primary"} disabled={soldOut || inDeal} onClick={() => add(pr)}><Plus className="w-4 h-4" /> {t("add_to_deal")}</Button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
        {data && data.count > 30 && (
          <div className="flex justify-center gap-2 mt-4">
            <Button size="sm" variant="outline" disabled={!data.previous} onClick={() => setF({ ...f, page: f.page - 1 })}>{t("prev")}</Button>
            <span className="text-sm text-ink-500 self-center">{f.page} / {Math.ceil(data.count / 30)}</span>
            <Button size="sm" variant="outline" disabled={!data.next} onClick={() => setF({ ...f, page: f.page + 1 })}>{t("next")}</Button>
          </div>
        )}
      </div>

      <aside>
        <div className="card p-5 xl:sticky xl:top-24">
          <div className="font-bold flex items-center gap-2"><ShoppingBag className="w-5 h-5 text-brand-600" /> {t("deal")} <span className="text-ink-500 font-normal">· {deal.length}</span></div>
          <p className="text-xs text-ink-500 mt-1">{t("deal_note")}</p>
          {deal.length === 0 ? <div className="text-sm text-ink-500 py-8 text-center">{t("no_data")}</div> : (
            <div className="mt-4 space-y-3 max-h-[50vh] overflow-y-auto pr-1">
              {deal.map((l) => (
                <div key={l.product.id} className="rounded-xl border border-ink-100 p-3">
                  <div className="flex justify-between gap-2">
                    <div className="min-w-0"><div className="font-medium text-sm truncate">{p(l.product.name)}</div><div className="text-xs text-ink-500">{t("owner")}: {p(l.product.seller.name)}</div></div>
                    <button onClick={() => setDeal(deal.filter((x) => x.product.id !== l.product.id))} className="p-1 text-ink-500 hover:text-red-600"><Trash2 className="w-4 h-4" /></button>
                  </div>
                  <div className="flex items-center gap-2 mt-2">
                    <Qty size="sm" value={l.qty} min={l.product.min_order || 1} max={l.product.available}
                      onChange={(v) => setDeal(deal.map((x) => (x.product.id === l.product.id ? { ...x, qty: Math.max(1, l.product.available != null ? Math.min(v, l.product.available) : v) } : x)))} />
                    <Input className="h-9 text-right" inputMode="decimal" placeholder={t("set_price")} value={l.price} disabled={!!l.product.price}
                      onChange={(e) => setDeal(deal.map((x) => (x.product.id === l.product.id ? { ...x, price: e.target.value.replace(/[^\d.]/g, "") } : x)))} />
                  </div>
                </div>
              ))}
            </div>
          )}
          <div className="flex justify-between items-baseline mt-4 pt-4 border-t border-ink-100">
            <span className="font-semibold">{t("total")}</span><span className="font-extrabold text-lg tabular-nums">{money(total)}</span>
          </div>
          <div className="text-xs text-ink-500 mt-1">{owners.length} × {t("contract")}</div>
          <Button className="w-full mt-4" variant="accent" disabled={!deal.length || deal.some((l) => !l.price)} onClick={() => { setResult(null); setOpen(true); }}>
            <FileSignature className="w-4 h-4" /> {t("create_deal")}
          </Button>
        </div>
      </aside>

      <Modal open={open} onClose={() => setOpen(false)} wide title={result ? t("deal_done") : t("create_deal")}>
        {result ? (
          <div className="space-y-3">
            {result.map((a) => (
              <div key={a.id} className="rounded-xl border border-ink-100 p-4 flex flex-wrap items-center gap-3">
                <div className="flex-1">
                  <div className="font-mono font-bold">{a.contract?.number}</div>
                  <div className="text-sm text-ink-500">{t("owner")}: {p(a.seller.name)} · {money(a.contract?.grand_total)}</div>
                </div>
                {a.contract && <a href={a.contract.pdf_url} target="_blank" rel="noreferrer"><Button variant="outline" size="sm">PDF</Button></a>}
                {a.contract && <Link href={`/cabinet/contracts?open=${a.contract.id}`}><Button size="sm">{t("view")}</Button></Link>}
              </div>
            ))}
          </div>
        ) : (
          <div>
            <BuyerForm b={b} set={(x) => setB({ ...b, ...x })} errors={errors} />
            {err && <div className="text-sm text-red-700 bg-red-50 rounded-lg p-3 mt-4">{err}</div>}
            <div className="flex justify-end gap-2 mt-5">
              <Button variant="ghost" onClick={() => setOpen(false)}>{t("cancel")}</Button>
              <Button loading={busy} onClick={submit}><FileSignature className="w-4 h-4" /> {t("create_deal")} · {money(total)}</Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
