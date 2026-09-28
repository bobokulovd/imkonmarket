"use client";
import clsx from "clsx";
import { ChevronDown, Globe, Home, LayoutGrid, Menu, PackageSearch, Search, ShoppingCart, Store, UserRound, X } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";
import { LANGS, useApp, useCart } from "@/lib/store";
import { CatIcon } from "./ui";

export function Logo({ light }: { light?: boolean }) {
  const { meta } = useApp();
  return (
    <Link href="/" className="flex items-center gap-2 shrink-0">
      <span className="w-9 h-9 rounded-xl bg-gradient-to-br from-brand-500 to-brand-800 grid place-items-center shadow-sm">
        <svg viewBox="0 0 24 24" className="w-5 h-5 text-white" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M3 21V10l5 3V10l5 3V7l8 4v10z" /><path d="M7 17h2M12 17h2M17 17h1" />
        </svg>
      </span>
      <span className={clsx("font-extrabold text-xl tracking-tight", light ? "text-white" : "text-ink-900")}>
        {meta?.brand || "UstaBozor"}
      </span>
    </Link>
  );
}

export function LangSwitch({ compact }: { compact?: boolean }) {
  const { lang, setLang } = useApp();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const h = (e: MouseEvent) => ref.current && !ref.current.contains(e.target as Node) && setOpen(false);
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, []);
  const cur = LANGS.find((l) => l.code === lang)!;
  return (
    <div className="relative" ref={ref}>
      <button onClick={() => setOpen(!open)} className="h-10 px-2.5 rounded-xl hover:bg-ink-100 inline-flex items-center gap-1.5 text-sm font-semibold text-ink-700" aria-label="language">
        <Globe className="w-4 h-4" /> {compact ? cur.short : cur.label} <ChevronDown className="w-3.5 h-3.5" />
      </button>
      {open && (
        <div className="absolute right-0 mt-1 w-52 bg-white rounded-xl shadow-pop border border-ink-100 p-1 z-50">
          {LANGS.map((l) => (
            <button key={l.code} onClick={() => { setLang(l.code); setOpen(false); }}
              className={clsx("w-full text-left px-3 py-2 rounded-lg text-sm flex justify-between", l.code === lang ? "bg-brand-50 text-brand-700 font-semibold" : "hover:bg-ink-100")}>
              {l.label} <span className="text-ink-500 text-xs">{l.short}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function SearchBox({ className }: { className?: string }) {
  const { t } = useApp();
  const router = useRouter();
  const sp = useSearchParams();
  const [q, setQ] = useState(sp.get("q") || "");
  useEffect(() => setQ(sp.get("q") || ""), [sp]);
  return (
    <form className={clsx("relative", className)} onSubmit={(e) => { e.preventDefault(); router.push(`/catalog?q=${encodeURIComponent(q)}`); }}>
      <input value={q} onChange={(e) => setQ(e.target.value)} placeholder={t("search_ph")}
        className="w-full h-11 rounded-xl border-2 border-brand-600 bg-white pl-4 pr-28 text-[15px] outline-none focus:ring-4 focus:ring-brand-100" />
      <button className="absolute right-1 top-1 bottom-1 px-4 rounded-lg bg-brand-600 text-white font-semibold text-sm inline-flex items-center gap-1.5 hover:bg-brand-700">
        <Search className="w-4 h-4" /> <span className="hidden sm:inline">{t("search")}</span>
      </button>
    </form>
  );
}

function CatalogMenu() {
  const { t, p, meta } = useApp();
  const [open, setOpen] = useState(false);
  const pathname = usePathname();
  useEffect(() => setOpen(false), [pathname]);
  return (
    <div className="relative" onMouseLeave={() => setOpen(false)}>
      <button onClick={() => setOpen(!open)} onMouseEnter={() => setOpen(true)}
        className="h-11 px-4 rounded-xl bg-brand-50 text-brand-700 font-semibold text-sm inline-flex items-center gap-2 hover:bg-brand-100">
        {open ? <X className="w-4 h-4" /> : <Menu className="w-4 h-4" />} {t("catalog")}
      </button>
      {open && meta && (
        <div className="absolute left-0 top-full pt-2 z-50">
          <div className="w-[640px] bg-white rounded-2xl shadow-pop border border-ink-100 p-3 grid grid-cols-2 gap-1">
            {meta.categories.map((c) => (
              <Link key={c.slug} href={`/catalog?category=${c.slug}`} className="flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-ink-100">
                <span className="w-9 h-9 rounded-lg bg-ink-100 grid place-items-center text-brand-700"><CatIcon icon={c.icon} className="w-5 h-5" /></span>
                <span className="flex-1 text-sm font-medium text-ink-900 leading-tight">{p(c.name)}</span>
                <span className="text-xs text-ink-500">{c.count}</span>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export function Header() {
  const { t } = useApp();
  const cart = useCart();
  return (
    <header className="sticky top-0 z-40 bg-white/95 backdrop-blur border-b border-ink-100">
      <div className="hidden md:block bg-ink-900 text-ink-300 text-xs">
        <div className="max-w-7xl mx-auto px-4 h-8 flex items-center justify-between">
          <span className="truncate">{t("tagline")}</span>
          <div className="flex items-center gap-5">
            <Link href="/track" className="hover:text-white">{t("track")}</Link>
            <Link href="/sellers" className="hover:text-white">{t("sellers")}</Link>
            <Link href="/cabinet" className="hover:text-white">{t("cabinet")}</Link>
          </div>
        </div>
      </div>
      <div className="max-w-7xl mx-auto px-4 h-16 flex items-center gap-3">
        <Logo />
        <div className="hidden md:block ml-3"><CatalogMenu /></div>
        <Suspense><SearchBox className="flex-1 hidden md:block" /></Suspense>
        <div className="flex-1 md:hidden" />
        <LangSwitch compact />
        <Link href="/cart" className="relative h-11 px-3 rounded-xl hover:bg-ink-100 hidden md:inline-flex items-center gap-2 text-sm font-semibold text-ink-700">
          <ShoppingCart className="w-5 h-5" /> {t("cart")}
          {cart.count > 0 && <span className="absolute -top-0.5 left-6 min-w-5 h-5 px-1 rounded-full bg-accent-500 text-white text-[11px] font-bold grid place-items-center">{cart.count}</span>}
        </Link>
        <Link href="/cabinet" className="hidden lg:inline-flex h-11 px-3 rounded-xl hover:bg-ink-100 items-center gap-2 text-sm font-semibold text-ink-700">
          <UserRound className="w-5 h-5" /> {t("login")}
        </Link>
      </div>
      <div className="md:hidden px-4 pb-3"><Suspense><SearchBox /></Suspense></div>
    </header>
  );
}

export function MobileNav() {
  const { t } = useApp();
  const cart = useCart();
  const path = usePathname();
  const items = [
    { href: "/", icon: Home, label: t("home") },
    { href: "/catalog", icon: LayoutGrid, label: t("catalog") },
    { href: "/cart", icon: ShoppingCart, label: t("cart"), badge: cart.count },
    { href: "/track", icon: PackageSearch, label: t("nav_track") },
    { href: "/cabinet", icon: Store, label: t("nav_cabinet") },
  ];
  return (
    <nav className="md:hidden fixed bottom-0 inset-x-0 z-40 bg-white border-t border-ink-100 pb-[env(safe-area-inset-bottom)]">
      <div className="grid grid-cols-5">
        {items.map((it) => {
          const active = it.href === "/" ? path === "/" : path.startsWith(it.href);
          return (
            <Link key={it.href} href={it.href} className={clsx("flex flex-col items-center justify-center py-2 text-[11px] font-medium relative", active ? "text-brand-600" : "text-ink-500")}>
              <it.icon className="w-5 h-5 mb-0.5" />
              <span className="truncate max-w-full px-1">{it.label}</span>
              {!!it.badge && <span className="absolute top-1 left-1/2 ml-1.5 min-w-4 h-4 px-1 rounded-full bg-accent-500 text-white text-[10px] font-bold grid place-items-center">{it.badge}</span>}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}

export function Footer() {
  const { t, meta, p } = useApp();
  return (
    <footer className="bg-ink-900 text-ink-300 mt-16 pb-20 md:pb-0">
      <div className="max-w-7xl mx-auto px-4 py-12 grid gap-10 md:grid-cols-4">
        <div className="md:col-span-2">
          <Logo light />
          <p className="mt-4 text-sm max-w-md leading-relaxed">{t("footer_about")}</p>
          <div className="mt-4 flex gap-2 text-xs">
            {["Click", "Payme", t("pay_bank")].map((x) => <span key={x} className="px-2.5 py-1 rounded-lg bg-white/10 text-white font-semibold">{x}</span>)}
          </div>
        </div>
        <div>
          <div className="text-white font-semibold mb-3">{t("footer_buyers")}</div>
          <ul className="space-y-2 text-sm">
            <li><Link href="/catalog" className="hover:text-white">{t("catalog")}</Link></li>
            <li><Link href="/track" className="hover:text-white">{t("track")}</Link></li>
            <li><Link href="/catalog?category=talim-mebeli" className="hover:text-white">{p(meta?.categories.find((c) => c.slug === "talim-mebeli")?.name)}</Link></li>
            <li><Link href="/catalog?category=qurilish" className="hover:text-white">{p(meta?.categories.find((c) => c.slug === "qurilish")?.name)}</Link></li>
          </ul>
        </div>
        <div>
          <div className="text-white font-semibold mb-3">{t("footer_sellers")}</div>
          <ul className="space-y-2 text-sm">
            <li><Link href="/cabinet" className="hover:text-white">{t("cabinet")}</Link></li>
            <li><Link href="/sellers" className="hover:text-white">{t("sellers")}</Link></li>
          </ul>
        </div>
      </div>
      <div className="border-t border-white/10 text-xs text-ink-500">
        <div className="max-w-7xl mx-auto px-4 py-4">© {new Date().getFullYear()} {meta?.brand || "UstaBozor"}</div>
      </div>
    </footer>
  );
}

export function PublicShell({ children }: { children: React.ReactNode }) {
  return (
    <>
      <Header />
      <main className="min-h-[60vh]">{children}</main>
      <Footer />
      <MobileNav />
    </>
  );
}
