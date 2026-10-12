"use client";
import clsx from "clsx";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { useCallback, useEffect, useRef } from "react";
import { ProductImage, SampleBadge } from "@/components/ui";
import { useApp } from "@/lib/store";

export type GalleryItem = { key: string | number; url: string; is_sample?: boolean };

/**
 * Marketplace uslubidagi galereya: asosiy rasm (mobil — barmoq bilan surish, scroll-snap),
 * strelkalar, eskizlar qatori (lg — chapda vertikal), mobil — nuqtalar.
 */
export default function Gallery({ items, active, onChange, alt, category, icon }: {
  items: GalleryItem[]; active: number; onChange: (i: number) => void; alt: string; category?: string; icon?: string;
}) {
  const { t } = useApp();
  const track = useRef<HTMLDivElement>(null);
  const lock = useRef<number | null>(null); // dasturiy surish paytida oraliq indekslarni e'tiborsiz qoldiramiz
  const n = items.length;
  const cur = Math.min(Math.max(active, 0), Math.max(n - 1, 0));

  // tashqi o'zgarish (strelka, eskiz, variant) — lentani kerakli rasmga suramiz
  useEffect(() => {
    const el = track.current;
    if (!el || !el.clientWidth) return;
    const target = cur * el.clientWidth;
    if (Math.abs(el.scrollLeft - target) <= 2) { lock.current = null; return; }
    lock.current = cur;
    el.scrollTo({ left: target, behavior: "smooth" });
    const id = setTimeout(() => { lock.current = null; }, 900);
    return () => clearTimeout(id);
  }, [cur]);

  const onScroll = useCallback(() => {
    const el = track.current;
    if (!el || !el.clientWidth) return;
    const i = Math.round(el.scrollLeft / el.clientWidth);
    if (lock.current !== null) { if (i === lock.current) lock.current = null; return; }
    if (i !== cur && i >= 0 && i < n) onChange(i);
  }, [cur, n, onChange]);

  const go = (d: number) => onChange((cur + d + n) % n);

  if (!n)
    return (
      <div className="card overflow-hidden aspect-square relative">
        <ProductImage category={category} icon={icon} alt={alt} />
      </div>
    );

  return (
    <div className="flex flex-col lg:flex-row-reverse gap-3">
      <div className="relative card overflow-hidden aspect-square flex-1 min-w-0 group"
        onKeyDown={(e) => { if (e.key === "ArrowLeft") go(-1); if (e.key === "ArrowRight") go(1); }}>
        <div ref={track} onScroll={onScroll}
          className="h-full w-full flex overflow-x-auto snap-x snap-mandatory no-scrollbar scroll-smooth"
          aria-roledescription="carousel" aria-label={alt}>
          {items.map((im, i) => (
            <div key={im.key} className="relative h-full w-full shrink-0 snap-center bg-white" aria-hidden={i !== cur}>
              <ProductImage src={im.url} category={category} icon={icon} alt={`${alt} — ${i + 1}/${n}`} className="!object-contain" />
              {im.is_sample && <SampleBadge label={t("sample_image")} hint={t("sample_image_hint")} className="absolute right-3 bottom-3 text-xs" />}
            </div>
          ))}
        </div>
        {n > 1 && (
          <>
            <button type="button" onClick={() => go(-1)} aria-label={t("sv_prev_image")}
              className="hidden sm:grid absolute left-3 top-1/2 -translate-y-1/2 w-10 h-10 place-items-center rounded-full bg-white/90 shadow-card text-ink-900 opacity-0 group-hover:opacity-100 focus:opacity-100 transition hover:bg-white">
              <ChevronLeft className="w-5 h-5" />
            </button>
            <button type="button" onClick={() => go(1)} aria-label={t("sv_next_image")}
              className="hidden sm:grid absolute right-3 top-1/2 -translate-y-1/2 w-10 h-10 place-items-center rounded-full bg-white/90 shadow-card text-ink-900 opacity-0 group-hover:opacity-100 focus:opacity-100 transition hover:bg-white">
              <ChevronRight className="w-5 h-5" />
            </button>
            <span className="absolute left-3 top-3 rounded-lg bg-ink-900/60 text-white text-xs font-semibold px-2 py-0.5 tabular-nums">{cur + 1} / {n}</span>
            <div className="sm:hidden absolute bottom-3 inset-x-0 flex justify-center gap-1.5 pointer-events-none">
              {items.map((im, i) => <span key={im.key} className={clsx("h-1.5 rounded-full transition-all", i === cur ? "w-5 bg-brand-600" : "w-1.5 bg-ink-900/25")} />)}
            </div>
          </>
        )}
      </div>
      {n > 1 && (
        <div className="hidden sm:flex lg:flex-col gap-2 overflow-x-auto lg:overflow-y-auto lg:max-h-[min(560px,80vh)] no-scrollbar lg:w-[76px] shrink-0">
          {items.map((im, i) => (
            <button key={im.key} type="button" onClick={() => onChange(i)} aria-label={`${i + 1}`} aria-current={i === cur}
              className={clsx("relative w-[68px] h-[68px] lg:w-[76px] lg:h-[76px] shrink-0 rounded-xl overflow-hidden border-2 transition bg-white",
                i === cur ? "border-brand-600" : "border-transparent hover:border-ink-300")}>
              <ProductImage src={im.url} category={category} icon={icon} />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
