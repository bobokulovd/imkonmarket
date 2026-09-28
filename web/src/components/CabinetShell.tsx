"use client";
import clsx from "clsx";
import { ClipboardList, ExternalLink, FileSignature, LayoutDashboard, LogOut, Package, Settings, Store, Warehouse } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { LangSwitch, Logo } from "@/components/Shell";
import { Badge, Spinner } from "@/components/ui";
import { api, auth } from "@/lib/api";
import { useApp } from "@/lib/store";
import type { SellerProfile } from "@/lib/types";

type Me = { username: string; seller: SellerProfile };
const MeCtx = createContext<{ me: Me; reload: () => void }>(null as any);
export const useMe = () => useContext(MeCtx);

export default function CabinetShell({ children }: { children: React.ReactNode }) {
  const { t, p } = useApp();
  const path = usePathname();
  const router = useRouter();
  const [me, setMe] = useState<Me | null | undefined>(undefined);
  const isLogin = path === "/cabinet/login";

  const reload = useCallback(() => {
    if (!auth.token) { setMe(null); return; }
    api<Me>("/auth/me/", { authed: true }).then(setMe).catch(() => { auth.clear(); setMe(null); });
  }, []);
  useEffect(() => { if (!isLogin) reload(); }, [isLogin, reload]);
  useEffect(() => { if (me === null && !isLogin) router.replace("/cabinet/login"); }, [me, isLogin, router]);

  if (isLogin) return <>{children}</>;
  if (!me) return <div className="min-h-screen grid place-items-center"><Spinner /></div>;

  const nav = [
    { href: "/cabinet", icon: LayoutDashboard, label: t("dashboard") },
    { href: "/cabinet/applications", icon: ClipboardList, label: t("applications") },
    { href: "/cabinet/contracts", icon: FileSignature, label: t("contracts") },
    { href: "/cabinet/products", icon: Package, label: t("my_products") },
    { href: "/cabinet/catalog", icon: Warehouse, label: t("general_catalog") },
    { href: "/cabinet/marketplaces", icon: Store, label: t("marketplaces") },
    { href: "/cabinet/profile", icon: Settings, label: t("profile") },
  ];
  const logout = () => { auth.clear(); router.replace("/cabinet/login"); };
  const active = (h: string) => (h === "/cabinet" ? path === h : path.startsWith(h));

  return (
    <MeCtx.Provider value={{ me, reload }}>
      <div className="min-h-screen lg:grid lg:grid-cols-[250px_1fr]">
        <aside className="hidden lg:flex flex-col bg-white border-r border-ink-100 sticky top-0 h-screen">
          <div className="h-16 px-5 flex items-center border-b border-ink-100"><Logo /></div>
          <div className="px-5 py-4 border-b border-ink-100">
            <div className="text-xs text-ink-500">{t("cabinet")}</div>
            <div className="font-bold text-ink-900 flex items-center gap-2">{p(me.seller.name)} {me.seller.role === "operator" && <Badge tone="violet">{t("operator")}</Badge>}</div>
            <div className="text-xs text-ink-500">{p(me.seller.region_i18n)}</div>
          </div>
          <nav className="p-3 space-y-1 flex-1">
            {nav.map((n) => (
              <Link key={n.href} href={n.href} className={clsx("flex items-center gap-3 px-3 h-10 rounded-xl text-sm font-medium", active(n.href) ? "bg-brand-600 text-white" : "text-ink-700 hover:bg-ink-100")}>
                <n.icon className="w-[18px] h-[18px]" /> {n.label}
              </Link>
            ))}
          </nav>
          <div className="p-3 border-t border-ink-100 space-y-1">
            <Link href="/" target="_blank" className="flex items-center gap-3 px-3 h-10 rounded-xl text-sm text-ink-700 hover:bg-ink-100"><ExternalLink className="w-4 h-4" /> {t("home")}</Link>
            <button onClick={logout} className="w-full flex items-center gap-3 px-3 h-10 rounded-xl text-sm text-ink-700 hover:bg-red-50 hover:text-red-700"><LogOut className="w-4 h-4" /> {t("logout")} <span className="ml-auto text-xs text-ink-500">{me.username}</span></button>
          </div>
        </aside>
        <div className="min-w-0 pb-20 lg:pb-0">
          <header className="sticky top-0 z-30 bg-white/95 backdrop-blur border-b border-ink-100 h-14 lg:h-16 px-4 lg:px-8 flex items-center gap-3">
            <div className="lg:hidden"><Logo /></div>
            <div className="hidden lg:block font-semibold text-ink-700">{nav.find((n) => active(n.href))?.label}</div>
            <div className="flex-1" />
            <span className="lg:hidden text-sm font-semibold truncate max-w-[40%]">{p(me.seller.name)}</span>
            <LangSwitch compact />
            <button onClick={logout} className="lg:hidden p-2 rounded-lg hover:bg-ink-100" aria-label={t("logout")}><LogOut className="w-5 h-5" /></button>
          </header>
          <main className="p-4 lg:p-8 max-w-[1400px]">{children}</main>
        </div>
        <nav className="lg:hidden fixed bottom-0 inset-x-0 z-40 bg-white border-t border-ink-100 grid grid-cols-7 pb-[env(safe-area-inset-bottom)]">
          {nav.map((n) => (
            <Link key={n.href} href={n.href} className={clsx("flex flex-col items-center py-2 text-[10px] font-medium", active(n.href) ? "text-brand-600" : "text-ink-500")}>
              <n.icon className="w-5 h-5 mb-0.5" /><span className="truncate max-w-full px-0.5">{n.label}</span>
            </Link>
          ))}
        </nav>
      </div>
    </MeCtx.Provider>
  );
}
