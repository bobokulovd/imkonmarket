"use client";
import clsx from "clsx";
import {
  Bed, Blocks, BrickWall, DoorOpen, Gift, Hammer, Loader2, Minus, Package, Plus, School, Shield, Shirt, Sofa,
  ShoppingBasket, Sparkles, Target, Trees, Wrench, X,
} from "lucide-react";
import { useEffect } from "react";

export const CAT_ICON: Record<string, any> = {
  brick: BrickWall, blocks: Blocks, sofa: Sofa, school: School, door: DoorOpen, wrench: Wrench, bed: Bed,
  shirt: Shirt, gift: Gift, tree: Trees, target: Target, shield: Shield, basket: ShoppingBasket, tools: Hammer,
};
export const CAT_TONE: Record<string, [string, string, string]> = {
  qurilish: ["#fff1e6", "#ffd9bd", "#c2410c"],
  "temir-beton": ["#eef2f6", "#d5dde7", "#475569"],
  mebel: ["#fdf2e9", "#f5dcc3", "#9a5b22"],
  "talim-mebeli": ["#eaf3ff", "#cfe2ff", "#1d4ed8"],
  "rom-eshik": ["#e8f7f6", "#c7ece8", "#0f766e"],
  metall: ["#f1f1f4", "#dadae3", "#3f3f55"],
  toqimachilik: ["#fdf0f6", "#f8d6e7", "#be185d"],
  kiyim: ["#eef0ff", "#d7dcff", "#4338ca"],
  suvenir: ["#fbf3e3", "#f3e0b5", "#a16207"],
  obodonlashtirish: ["#ecf8ee", "#cdeed3", "#15803d"],
  "oquv-jihozlar": ["#f0f4ea", "#d9e5c9", "#4d6b1f"],
  xavfsizlik: ["#fdeeee", "#f7d2d2", "#b91c1c"],
  xojalik: ["#fff8e1", "#ffeab0", "#b45309"],
  xizmatlar: ["#f3eefe", "#e0d4fb", "#6d28d9"],
};

export function CatIcon({ icon, className, color }: { icon?: string; className?: string; color?: string }) {
  const I = (icon && CAT_ICON[icon]) || Package;
  return <I className={className} strokeWidth={1.6} style={color ? { color } : undefined} />;
}

export function ProductImage({ src, category, icon, className, alt }: { src?: string | null; category?: string; icon?: string; className?: string; alt?: string }) {
  const tone = CAT_TONE[category || ""] || ["#f1f5f9", "#e2e8f0", "#64748b"];
  if (src) return <img src={src} alt={alt || ""} className={clsx("object-cover w-full h-full", className)} loading="lazy" />;
  return (
    <div className={clsx("w-full h-full flex items-center justify-center relative overflow-hidden", className)}
      style={{ background: `radial-gradient(120% 90% at 20% 10%, ${tone[0]} 0%, ${tone[1]} 100%)` }}>
      <div className="absolute -right-6 -bottom-6 w-28 h-28 rounded-full opacity-20" style={{ background: tone[2] }} />
      <CatIcon icon={icon} color={tone[2]} className="w-1/3 h-1/3 max-w-20 max-h-20 relative" />
    </div>
  );
}

export function Button({ variant = "primary", size = "md", className, loading, children, ...rest }:
  React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "accent" | "ghost" | "outline" | "danger" | "soft"; size?: "sm" | "md" | "lg"; loading?: boolean }) {
  return (
    <button
      {...rest}
      disabled={rest.disabled || loading}
      className={clsx(
        "inline-flex items-center justify-center gap-2 font-semibold rounded-xl transition active:scale-[.98] disabled:opacity-50 disabled:pointer-events-none whitespace-nowrap",
        size === "sm" && "h-9 px-3 text-sm",
        size === "md" && "h-11 px-4 text-sm",
        size === "lg" && "h-12 px-6 text-base",
        variant === "primary" && "bg-brand-600 text-white hover:bg-brand-700 shadow-sm",
        variant === "accent" && "bg-accent-500 text-white hover:bg-accent-600 shadow-sm",
        variant === "ghost" && "text-ink-700 hover:bg-ink-100",
        variant === "outline" && "border border-ink-300 text-ink-900 bg-white hover:bg-ink-100",
        variant === "danger" && "bg-red-600 text-white hover:bg-red-700",
        variant === "soft" && "bg-brand-50 text-brand-700 hover:bg-brand-100",
        className,
      )}
    >
      {loading && <Loader2 className="w-4 h-4 animate-spin" />}
      {children}
    </button>
  );
}

export function Field({ label, error, hint, children, className }: { label?: string; error?: string; hint?: string; children: React.ReactNode; className?: string }) {
  return (
    <label className={clsx("block", className)}>
      {label && <span className="block text-sm font-medium text-ink-700 mb-1.5">{label}</span>}
      {children}
      {hint && !error && <span className="block text-xs text-ink-500 mt-1">{hint}</span>}
      {error && <span className="block text-xs text-red-600 mt-1">{error}</span>}
    </label>
  );
}

export const inputCls =
  "w-full h-11 rounded-xl border border-ink-300 bg-white px-3.5 text-[15px] outline-none focus:border-brand-500 focus:ring-4 focus:ring-brand-100 transition placeholder:text-ink-500/70";

export function Input(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={clsx(inputCls, props.className)} />;
}
export function Select(props: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return <select {...props} className={clsx(inputCls, "pr-8", props.className)} />;
}
export function Textarea(props: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea {...props} className={clsx(inputCls, "h-auto py-2.5 min-h-[88px]", props.className)} />;
}

export function Qty({ value, onChange, min = 1, max, size = "md" }: { value: number; onChange: (v: number) => void; min?: number; max?: number | null; size?: "sm" | "md" }) {
  const h = size === "sm" ? "h-9" : "h-11";
  return (
    <div className={clsx("inline-flex items-center rounded-xl border border-ink-300 bg-white", h)}>
      <button type="button" className="w-9 h-full grid place-items-center text-ink-700 hover:text-brand-600 disabled:opacity-30"
        disabled={value <= min} onClick={() => onChange(value - 1)} aria-label="-"><Minus className="w-4 h-4" /></button>
      <input
        className="w-16 text-center font-semibold outline-none bg-transparent tabular-nums"
        inputMode="numeric" value={value}
        onChange={(e) => { const n = parseInt(e.target.value.replace(/\D/g, "") || "0", 10); onChange(n); }}
      />
      <button type="button" className="w-9 h-full grid place-items-center text-ink-700 hover:text-brand-600 disabled:opacity-30"
        disabled={max != null && value >= max} onClick={() => onChange(value + 1)} aria-label="+"><Plus className="w-4 h-4" /></button>
    </div>
  );
}

const TONES: Record<string, string> = {
  gray: "bg-ink-100 text-ink-700", blue: "bg-brand-50 text-brand-700", green: "bg-emerald-50 text-emerald-700",
  amber: "bg-amber-50 text-amber-700", red: "bg-red-50 text-red-700", violet: "bg-violet-50 text-violet-700",
  orange: "bg-orange-50 text-orange-700",
};
export function Badge({ tone = "gray", children, className }: { tone?: keyof typeof TONES | string; children: React.ReactNode; className?: string }) {
  return <span className={clsx("inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold", TONES[tone] || TONES.gray, className)}>{children}</span>;
}

export const STATUS_TONE: Record<string, string> = {
  new: "blue", review: "amber", contract: "green", rejected: "red", cancelled: "gray",
  active: "amber", paid: "green", shipped: "violet", done: "gray",
};

export function Modal({ open, onClose, title, children, wide }: { open: boolean; onClose: () => void; title?: React.ReactNode; children: React.ReactNode; wide?: boolean }) {
  useEffect(() => {
    if (!open) return;
    const h = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", h);
    document.body.style.overflow = "hidden";
    return () => { window.removeEventListener("keydown", h); document.body.style.overflow = ""; };
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center">
      <div className="absolute inset-0 bg-ink-900/50 backdrop-blur-[2px]" onClick={onClose} />
      <div className={clsx("relative bg-white w-full sm:rounded-2xl rounded-t-2xl shadow-pop max-h-[92vh] flex flex-col", wide ? "sm:max-w-4xl" : "sm:max-w-lg")}>
        <div className="flex items-center justify-between px-5 py-4 border-b border-ink-100">
          <div className="font-bold text-lg text-ink-900 pr-4">{title}</div>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-ink-100" aria-label="close"><X className="w-5 h-5" /></button>
        </div>
        <div className="overflow-y-auto p-5">{children}</div>
      </div>
    </div>
  );
}

/** AI yaratgan namunaviy rasm belgisi — haqiqiy surat yuklanguncha ko'rinadi. */
export function SampleBadge({ label, hint, className }: { label: string; hint?: string; className?: string }) {
  return (
    <span title={hint} className={clsx("inline-flex items-center gap-1 rounded-md bg-ink-900/60 backdrop-blur px-1.5 py-0.5 text-[10px] font-semibold text-white pointer-events-auto", className)}>
      <Sparkles className="w-3 h-3" />{label}
    </span>
  );
}

export function Spinner({ className }: { className?: string }) {
  return <Loader2 className={clsx("animate-spin text-brand-600", className || "w-6 h-6")} />;
}

export function Empty({ icon, title, sub, action }: { icon?: React.ReactNode; title: string; sub?: string; action?: React.ReactNode }) {
  return (
    <div className="text-center py-16 px-6">
      <div className="mx-auto w-16 h-16 rounded-2xl bg-ink-100 grid place-items-center text-ink-500 mb-4">{icon || <Package className="w-7 h-7" />}</div>
      <div className="font-semibold text-ink-900 text-lg">{title}</div>
      {sub && <div className="text-ink-500 mt-1">{sub}</div>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

export function Toast({ text, onDone }: { text: string | null; onDone: () => void }) {
  useEffect(() => {
    if (!text) return;
    const id = setTimeout(onDone, 2200);
    return () => clearTimeout(id);
  }, [text, onDone]);
  if (!text) return null;
  return (
    <div className="fixed z-[60] left-1/2 -translate-x-1/2 bottom-24 md:bottom-8 bg-ink-900 text-white text-sm font-medium px-4 py-2.5 rounded-xl shadow-pop">
      {text}
    </div>
  );
}
