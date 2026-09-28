"use client";
import { ArrowRight, ClipboardList, Eye, FileSignature, PackageX, TrendingUp, Wallet } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useMe } from "@/components/CabinetShell";
import { Badge, Spinner, STATUS_TONE } from "@/components/ui";
import { api } from "@/lib/api";
import { useApp } from "@/lib/store";
import type { SellerApplication, SellerProduct } from "@/lib/types";
import { fmtDate } from "@/lib/util";

type D = {
  applications_new: number; applications_total: number; contracts_active: number; contracts_total: number;
  revenue_month: string; paid_month: string; receivable: string; products: number; products_out_of_stock: number;
  agent_contracts: number; recent: SellerApplication[]; top_products: SellerProduct[];
};

export default function Dashboard() {
  const { t, p, money, unit } = useApp();
  const { me } = useMe();
  const [d, setD] = useState<D | null>(null);
  useEffect(() => { api<D>("/seller/dashboard/", { authed: true }).then(setD).catch(() => {}); }, []);
  if (!d) return <div className="py-20 grid place-items-center"><Spinner /></div>;
  const kpis = [
    { icon: ClipboardList, label: t("new_apps"), value: d.applications_new, href: "/cabinet/applications?status=new,review", tone: "bg-brand-50 text-brand-700" },
    { icon: FileSignature, label: t("active_contracts"), value: d.contracts_active, href: "/cabinet/contracts?status=active,paid", tone: "bg-emerald-50 text-emerald-700" },
    { icon: TrendingUp, label: t("month_revenue"), value: money(d.revenue_month), href: "/cabinet/contracts", tone: "bg-violet-50 text-violet-700" },
    { icon: Wallet, label: t("receivable"), value: money(d.receivable), href: "/cabinet/contracts?status=active,paid,shipped", tone: "bg-amber-50 text-amber-700" },
  ];
  return (
    <div>
      <h1 className="text-2xl font-extrabold">{p(me.seller.name)}</h1>
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-3 md:gap-4 mt-5">
        {kpis.map((k) => (
          <Link key={k.label} href={k.href} className="card p-4 md:p-5 hover:shadow-pop transition">
            <span className={`w-10 h-10 rounded-xl grid place-items-center ${k.tone}`}><k.icon className="w-5 h-5" /></span>
            <div className="text-xl md:text-2xl font-extrabold mt-3 tabular-nums truncate">{k.value}</div>
            <div className="text-sm text-ink-500">{k.label}</div>
          </Link>
        ))}
      </div>
      <div className="grid xl:grid-cols-[1.4fr_1fr] gap-5 mt-5">
        <div className="card">
          <div className="px-5 py-4 flex justify-between items-center border-b border-ink-100">
            <div className="font-bold">{t("recent_apps")}</div>
            <Link href="/cabinet/applications" className="text-sm text-brand-700 font-semibold inline-flex items-center gap-1">{t("see_all")} <ArrowRight className="w-4 h-4" /></Link>
          </div>
          {d.recent.length === 0 ? <div className="p-8 text-center text-ink-500">{t("no_data")}</div> : (
            <div className="divide-y divide-ink-100">
              {d.recent.map((a) => (
                <Link key={a.id} href={`/cabinet/applications?open=${a.id}`} className="px-5 py-3 flex items-center gap-3 hover:bg-ink-100/50">
                  <div className="flex-1 min-w-0">
                    <div className="font-mono text-sm font-semibold">{a.number}</div>
                    <div className="text-sm text-ink-500 truncate">{a.buyer_name} · {a.buyer_type.toUpperCase()}{a.agent ? ` · ${t("agent")}: ${p(a.agent.name)}` : ""}</div>
                  </div>
                  <div className="text-right">
                    <div className="text-sm font-semibold tabular-nums">{money(a.total)}</div>
                    <Badge tone={STATUS_TONE[a.status]}>{t(`st_${a.status}` as any)}</Badge>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
        <div className="card">
          <div className="px-5 py-4 flex justify-between items-center border-b border-ink-100">
            <div className="font-bold">{t("top_products")}</div>
            <span className="text-sm text-ink-500 inline-flex items-center gap-1"><PackageX className="w-4 h-4" /> {t("out_of_stock_n")}: {d.products_out_of_stock}</span>
          </div>
          <div className="divide-y divide-ink-100">
            {d.top_products.map((pr) => (
              <div key={pr.id} className="px-5 py-3 flex gap-3 items-center text-sm">
                <div className="flex-1 min-w-0"><div className="font-medium truncate">{p(pr.name)}</div><div className="text-ink-500 truncate">{p(pr.spec)}</div></div>
                <div className="text-right tabular-nums"><div>{pr.available ?? "∞"} {unit(pr.unit)}</div><div className="text-xs text-ink-500">{pr.sold} · <Eye className="inline w-3 h-3" /> {pr.views}</div></div>
              </div>
            ))}
          </div>
        </div>
      </div>
      <div className="text-xs text-ink-500 mt-4">{t("contracts")}: {d.contracts_total} · {t("applications")}: {d.applications_total} · {t("agent")}: {d.agent_contracts} · {fmtDate(new Date().toISOString())}</div>
    </div>
  );
}
