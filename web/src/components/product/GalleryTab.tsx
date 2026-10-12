"use client";
import clsx from "clsx";
import { ArrowLeft, ArrowRight, ImageUp, Info, Star, Trash2 } from "lucide-react";
import { useState } from "react";
import { SampleBadge, Spinner } from "@/components/ui";
import { api, API_URL, ApiError, auth } from "@/lib/api";
import { useApp } from "@/lib/store";
import type { GalleryImage, SellerProduct } from "@/lib/types";
import { ErrorBox, type ProductChange, errMsg } from "./shared";

export const MAX_IMAGES = 15;

export default function GalleryTab({ product, onChange }: { product: SellerProduct; onChange: ProductChange }) {
  const { t } = useApp();
  const [busy, setBusy] = useState<string | null>(null); // "upload" | `img:<id>`
  const [drag, setDrag] = useState(false);
  const [err, setErr] = useState("");
  const images = product.images || [];
  const real = images.filter((i) => !i.is_sample);
  const hasSample = images.some((i) => i.is_sample);
  const left = MAX_IMAGES - real.length;

  const apply = (list: GalleryImage[]) => onChange({ ...product, images: list, image_url: list[0]?.url ?? null, image_is_sample: !!list[0]?.is_sample });

  const upload = async (files: FileList | File[] | null) => {
    const arr = Array.from(files || []).filter((f) => f.type.startsWith("image/") || /\.(jpe?g|png|webp|heic)$/i.test(f.name));
    if (!arr.length) return;
    if (arr.length > left) { setErr(t("pe_gal_max", { n: MAX_IMAGES })); return; }
    setBusy("upload"); setErr("");
    try {
      const fd = new FormData();
      arr.forEach((f) => fd.append("files", f, f.name));
      const res = await fetch(`${API_URL}/api/seller/products/${product.id}/images/`, { method: "POST", body: fd, headers: auth.token ? { Authorization: `Bearer ${auth.token}` } : {} });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new ApiError(res.status, data);
      apply(data as GalleryImage[]);
    } catch (e) { setErr(errMsg(e)); } finally { setBusy(null); }
  };

  const run = async (key: string, fn: () => Promise<GalleryImage[]>) => {
    setBusy(key); setErr("");
    try { apply(await fn()); } catch (e) { setErr(errMsg(e)); } finally { setBusy(null); }
  };
  const remove = (img: GalleryImage) => {
    if (!window.confirm(t("pe_gal_delete_q"))) return;
    run(`img:${img.id}`, () => api<GalleryImage[]>(`/seller/products/${product.id}/images/${img.id}/`, { method: "DELETE", authed: true }));
  };
  const reorder = (img: GalleryImage, ids: number[]) =>
    run(`img:${img.id}`, () => api<GalleryImage[]>(`/seller/products/${product.id}/images/reorder/`, { method: "POST", json: { ids }, authed: true }));
  const move = (idx: number, dir: -1 | 1) => {
    const ids = images.map((i) => i.id);
    const j = idx + dir;
    if (j < 0 || j >= ids.length) return;
    [ids[idx], ids[j]] = [ids[j], ids[idx]];
    reorder(images[idx], ids);
  };
  const makeCover = (idx: number) => reorder(images[idx], [images[idx].id, ...images.filter((_, i) => i !== idx).map((i) => i.id)]);

  return (
    <div className="space-y-4">
      <div className="rounded-xl bg-ink-100/60 p-3 text-sm text-ink-700 flex gap-2">
        <Info className="w-4 h-4 shrink-0 mt-0.5 text-brand-600" />
        <div>{t("pe_gal_tips")}</div>
      </div>
      {hasSample && (
        <div className="rounded-xl bg-amber-50 text-amber-800 p-3 text-sm flex gap-2 items-start">
          <SampleBadge label="AI" className="shrink-0" />
          <div>{t("pe_gal_sample")}</div>
        </div>
      )}

      <label
        onDragOver={(e) => { e.preventDefault(); setDrag(true); }} onDragLeave={() => setDrag(false)}
        onDrop={(e) => { e.preventDefault(); setDrag(false); upload(e.dataTransfer.files); }}
        className={clsx("block rounded-2xl border-2 border-dashed p-6 text-center transition", left <= 0 ? "opacity-50 pointer-events-none border-ink-300" : "cursor-pointer",
          drag ? "border-brand-500 bg-brand-50" : "border-ink-300 hover:bg-ink-50")}>
        {busy === "upload" ? <Spinner className="w-8 h-8 mx-auto" /> : <ImageUp className="w-8 h-8 mx-auto text-brand-600" />}
        <div className="mt-2 font-semibold">{t("pe_gal_drop")}</div>
        <div className="text-xs text-ink-500 mt-1">JPG · PNG · WEBP · {real.length}/{MAX_IMAGES}</div>
        <input type="file" multiple accept="image/*" className="hidden" disabled={left <= 0 || !!busy}
          onChange={(e) => { upload(e.target.files); e.target.value = ""; }} />
      </label>
      <ErrorBox text={err} />

      {images.length === 0 ? (
        <div className="text-center text-sm text-ink-500 py-6">{t("pe_gal_empty")}</div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
          {images.map((img, idx) => (
            <div key={img.id} className={clsx("relative rounded-xl overflow-hidden border bg-white group", idx === 0 ? "border-brand-500 ring-2 ring-brand-100" : "border-ink-100")}>
              <div className="aspect-square bg-ink-50">
                <img src={img.url} alt="" className="w-full h-full object-contain" loading="lazy" />
              </div>
              <div className="absolute top-1.5 left-1.5 flex gap-1">
                {idx === 0 && <span className="rounded-md bg-brand-600 text-white text-[10px] font-bold px-1.5 py-0.5">{t("pe_gal_cover")}</span>}
                {img.is_sample && <SampleBadge label="AI" hint={t("sample_image_hint")} />}
              </div>
              {busy === `img:${img.id}` && <div className="absolute inset-0 bg-white/60 grid place-items-center"><Spinner /></div>}
              <div className="flex items-center justify-between gap-1 p-1.5 border-t border-ink-100">
                <div className="flex gap-0.5">
                  <IconBtn title={t("pe_gal_left")} disabled={idx === 0 || !!busy} onClick={() => move(idx, -1)}><ArrowLeft className="w-4 h-4" /></IconBtn>
                  <IconBtn title={t("pe_gal_right")} disabled={idx === images.length - 1 || !!busy} onClick={() => move(idx, 1)}><ArrowRight className="w-4 h-4" /></IconBtn>
                  {idx !== 0 && <IconBtn title={t("pe_gal_make_cover")} disabled={!!busy} onClick={() => makeCover(idx)}><Star className="w-4 h-4" /></IconBtn>}
                </div>
                <IconBtn title={t("remove")} disabled={!!busy} onClick={() => remove(img)} danger><Trash2 className="w-4 h-4" /></IconBtn>
              </div>
            </div>
          ))}
        </div>
      )}
      {real.length > 0 && real.length < 3 && <p className="text-xs text-amber-700">{t("pe_gal_need3", { n: real.length })}</p>}
    </div>
  );
}

function IconBtn({ children, danger, ...rest }: React.ButtonHTMLAttributes<HTMLButtonElement> & { danger?: boolean }) {
  return (
    <button type="button" {...rest} aria-label={rest.title}
      className={clsx("p-1.5 rounded-lg disabled:opacity-30 disabled:pointer-events-none", danger ? "text-red-600 hover:bg-red-50" : "text-ink-700 hover:bg-ink-100")}>
      {children}
    </button>
  );
}
