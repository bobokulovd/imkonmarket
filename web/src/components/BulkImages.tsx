"use client";
import clsx from "clsx";
import { CheckCircle2, ImageUp, XCircle } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui";
import { api, errText } from "@/lib/api";
import { useApp } from "@/lib/store";

type Res = { matched: { file: string; sku: string }[]; unmatched: string[]; errors: string[] };

/** Ko'p rasmni bir yo'la yuklash: fayl nomi = SKU (MK-49-001.jpg). 10 tadan bo'lib yuboriladi. */
export default function BulkImages({ onDone }: { onDone: () => void }) {
  const { t } = useApp();
  const [files, setFiles] = useState<File[]>([]);
  const [drag, setDrag] = useState(false);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(0);
  const [res, setRes] = useState<Res | null>(null);
  const [err, setErr] = useState("");

  const add = (list: FileList | null) => list && setFiles((f) => [...f, ...Array.from(list)]);
  const upload = async () => {
    setBusy(true); setErr(""); setDone(0);
    const total: Res = { matched: [], unmatched: [], errors: [] };
    try {
      // so'rov hajmi ~40 MB dan oshmasin: fayllar paketlarga bo'linadi; juda katta fayllar yuborilmaydi
      const MAX_FILE = 15 * 1024 * 1024, MAX_ZIP = 200 * 1024 * 1024, MAX_BATCH = 40 * 1024 * 1024;
      const batches: File[][] = [];
      let cur: File[] = [], size = 0;
      for (const f of files) {
        const isZip = /\.zip$/i.test(f.name);
        if (f.size > (isZip ? MAX_ZIP : MAX_FILE)) { total.errors.push(`${f.name}: ${t("im_too_big", { mb: (f.size / 1048576).toFixed(1), max: isZip ? 200 : 15 })}`); continue; }
        if (cur.length && (size + f.size > MAX_BATCH || cur.length >= 10)) { batches.push(cur); cur = []; size = 0; }
        cur.push(f); size += f.size;
      }
      if (cur.length) batches.push(cur);
      let sent = 0;
      for (const b of batches) {
        const fd = new FormData();
        b.forEach((f) => fd.append("files", f, f.name));
        const r = await api<Res>("/seller/products/bulk-images/", { method: "POST", body: fd, authed: true });
        total.matched.push(...r.matched); total.unmatched.push(...r.unmatched); total.errors.push(...r.errors);
        sent += b.length;
        setDone(sent);
      }
      setRes(total); setFiles([]); onDone();
    } catch (e) { setErr(errText(e)); } finally { setBusy(false); }
  };

  return (
    <div className="space-y-4">
      <p className="text-sm text-ink-500">{t("bulk_images_hint")}</p>
      <p className="text-xs text-ink-500">{t("im_bulk_rules")}</p>
      <label
        onDragOver={(e) => { e.preventDefault(); setDrag(true); }} onDragLeave={() => setDrag(false)}
        onDrop={(e) => { e.preventDefault(); setDrag(false); add(e.dataTransfer.files); }}
        className={clsx("block rounded-2xl border-2 border-dashed p-8 text-center cursor-pointer transition", drag ? "border-brand-500 bg-brand-50" : "border-ink-300 hover:bg-ink-50")}>
        <ImageUp className="w-8 h-8 mx-auto text-brand-600" />
        <div className="mt-2 font-semibold">{t("bulk_images_drop")}</div>
        <div className="text-xs text-ink-500 mt-1">JPG · PNG · WEBP · ZIP</div>
        <input type="file" multiple accept="image/*,.zip" className="hidden" onChange={(e) => add(e.target.files)} />
      </label>
      {files.length > 0 && <div className="text-sm">{files.length} · {files.slice(0, 6).map((f) => f.name).join(", ")}{files.length > 6 ? "…" : ""}</div>}
      {busy && <div className="h-2 rounded-full bg-ink-100 overflow-hidden"><div className="h-full bg-brand-600 transition-all" style={{ width: `${(done / Math.max(files.length, 1)) * 100}%` }} /></div>}
      {res && (
        <div className="space-y-2 text-sm">
          <div className="flex items-center gap-2 text-emerald-700"><CheckCircle2 className="w-4 h-4" />{t("bulk_matched")}: {res.matched.length}</div>
          {res.unmatched.length > 0 && <div className="text-amber-700"><div className="flex items-center gap-2"><XCircle className="w-4 h-4" />{t("bulk_unmatched")}: {res.unmatched.length}</div>
            <div className="text-xs mt-1 max-h-28 overflow-y-auto">{res.unmatched.join(", ")}</div></div>}
          {res.errors.length > 0 && <div className="text-xs text-red-600">{res.errors.join("; ")}</div>}
        </div>
      )}
      {err && <div className="text-sm text-red-600">{err}</div>}
      <div className="flex justify-end gap-2">
        {files.length > 0 && <Button variant="ghost" onClick={() => setFiles([])} disabled={busy}>{t("clear")}</Button>}
        <Button onClick={upload} loading={busy} disabled={!files.length}><ImageUp className="w-4 h-4" />{t("upload")}</Button>
      </div>
    </div>
  );
}
