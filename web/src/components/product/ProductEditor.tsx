"use client";
import clsx from "clsx";
import { FileText, Images, Layers, ListChecks, Store } from "lucide-react";
import { useEffect, useState } from "react";
import { Spinner } from "@/components/ui";
import { api } from "@/lib/api";
import { useApp } from "@/lib/store";
import type { SellerProduct } from "@/lib/types";
import AttributesTab from "./AttributesTab";
import GalleryTab from "./GalleryTab";
import MainTab from "./MainTab";
import MarketTab from "./MarketTab";
import { ErrorBox, useAttrDefs, errMsg } from "./shared";
import VariantsTab from "./VariantsTab";

export type EditorTab = "main" | "gallery" | "attrs" | "variants" | "market";

/** Mahsulot kartochkasi muharriri (tablar). Yangi mahsulot — avval faqat «Asosiy», saqlangach qolganlari ochiladi. */
export default function ProductEditor({ productId, defaultCategory, onSaved, onCreated, onClose }: {
  productId?: number; defaultCategory: string; onSaved: () => void; onCreated?: (id: number) => void; onClose: () => void;
}) {
  const { t } = useApp();
  const [product, setProduct] = useState<SellerProduct | null>(null);
  const [loadErr, setLoadErr] = useState("");
  const [tab, setTab] = useState<EditorTab>("main");
  const [visited, setVisited] = useState<Set<EditorTab>>(new Set(["main"]));
  const [version, setVersion] = useState(0);
  const { defs } = useAttrDefs(product?.category || defaultCategory);

  useEffect(() => {
    if (!productId || product?.id === productId) return;
    setLoadErr("");
    api<SellerProduct>(`/seller/products/${productId}/`, { authed: true }).then(setProduct).catch((e) => setLoadErr(errMsg(e)));
  }, [productId]); // eslint-disable-line react-hooks/exhaustive-deps

  const go = (k: EditorTab) => { setTab(k); setVisited((s) => new Set(s).add(k)); };
  const change = (pr: SellerProduct) => { setProduct(pr); setVersion((v) => v + 1); onSaved(); };

  if (productId && !product) return loadErr ? <ErrorBox text={loadErr} /> : <div className="py-16 grid place-items-center"><Spinner /></div>;

  const axes = (defs || []).filter((d) => d.variant).length;
  const tabs: { k: EditorTab; label: string; icon: typeof FileText; badge?: string | number }[] = [
    { k: "main", label: t("pe_tab_main"), icon: FileText },
    { k: "gallery", label: t("pe_tab_gallery"), icon: Images, badge: product?.images?.length || undefined },
    { k: "attrs", label: t("pe_tab_attrs"), icon: ListChecks },
    { k: "variants", label: t("pe_tab_variants"), icon: Layers, badge: product?.has_variants ? product.variants?.length : axes ? undefined : "—" },
    { k: "market", label: t("pe_tab_market"), icon: Store },
  ];

  return (
    <div className="space-y-5">
      <div className="flex gap-1 overflow-x-auto no-scrollbar -mx-5 px-5 border-b border-ink-100 sticky -top-5 bg-white z-10 pt-1">
        {tabs.map(({ k, label, icon: I, badge }) => {
          const disabled = k !== "main" && !product;
          return (
            <button key={k} type="button" disabled={disabled} onClick={() => go(k)} title={disabled ? t("pe_save_first") : undefined}
              className={clsx("flex items-center gap-1.5 px-3 py-2.5 text-sm font-semibold border-b-2 -mb-px whitespace-nowrap transition disabled:opacity-40 disabled:cursor-not-allowed",
                tab === k ? "border-brand-600 text-brand-700" : "border-transparent text-ink-500 hover:text-ink-900")}>
              <I className="w-4 h-4" />{label}
              {badge !== undefined && <span className={clsx("text-[11px] rounded-full px-1.5 min-w-[18px] text-center", tab === k ? "bg-brand-50 text-brand-700" : "bg-ink-100 text-ink-500")}>{badge}</span>}
            </button>
          );
        })}
      </div>

      {/* bir marta ochilgan tablar yashirin holda saqlanadi — kiritilgan (saqlanmagan) ma'lumot yo'qolmaydi */}
      <div className={clsx(tab !== "main" && "hidden")}>
        <MainTab product={product} defaultCategory={defaultCategory} onClose={onClose}
          onSaved={(pr, created) => { change(pr); if (created) { onCreated?.(pr.id); go("gallery"); } }} />
      </div>
      {product && (
        <>
          {visited.has("gallery") && <div className={clsx(tab !== "gallery" && "hidden")}><GalleryTab product={product} onChange={change} /></div>}
          {visited.has("attrs") && <div className={clsx(tab !== "attrs" && "hidden")}><AttributesTab key={product.category} product={product} defs={defs} onChange={change} /></div>}
          {visited.has("variants") && <div className={clsx(tab !== "variants" && "hidden")}><VariantsTab key={product.category} product={product} defs={defs} onChange={change} /></div>}
          {visited.has("market") && <div className={clsx(tab !== "market" && "hidden")}><MarketTab product={product} active={tab === "market"} version={version} /></div>}
        </>
      )}
    </div>
  );
}
