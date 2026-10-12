"use client";
import { useRef, useState } from "react";
import { Button } from "@/components/ui";
import { errText } from "@/lib/api";
import { suggestMissing } from "@/lib/ikpu";
import { useApp } from "@/lib/store";

/** Kodsiz mahsulotlarga IKPU tavsiyasi — qidiruv foydalanuvchi brauzeridan (server tasnif.soliq.uz ga ulana olmasa ham ishlaydi). */
export default function IkpuBulk({ onDone }: { onDone: () => void }) {
  const { t } = useApp();
  const [running, setRunning] = useState(false);
  const [prog, setProg] = useState<{ done: number; total: number; updated: number } | null>(null);
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");
  const stop = useRef({ stop: false });

  const start = async () => {
    stop.current = { stop: false };
    setRunning(true); setErr(""); setMsg(""); setProg(null);
    try {
      const r = await suggestMissing((done, total, updated) => setProg({ done, total, updated }), stop.current);
      setMsg(t("ik_bulk_done", { updated: r.updated }));
      onDone();
    } catch (e) { setErr(errText(e)); } finally { setRunning(false); }
  };

  return (
    <div className="space-y-4">
      <p className="text-sm text-ink-600">{t("ik_bulk_hint")}</p>
      {prog && (
        <div>
          <div className="h-2 rounded-full bg-ink-100 overflow-hidden">
            <div className="h-full bg-brand-600 transition-all" style={{ width: `${prog.total ? (100 * prog.done) / prog.total : 0}%` }} />
          </div>
          <div className="text-xs text-ink-500 mt-1.5">{t("ik_bulk_progress", prog)}</div>
        </div>
      )}
      {msg && <div className="text-sm text-emerald-800 bg-emerald-50 rounded-lg p-3">{msg}</div>}
      {err && <div className="text-sm text-red-700 bg-red-50 rounded-lg p-3">{err}</div>}
      <div className="flex justify-end gap-2">
        {running
          ? <Button variant="outline" onClick={() => { stop.current.stop = true; }}>{t("ik_bulk_stop")}</Button>
          : <Button onClick={start}>{t("ik_bulk_start")}</Button>}
      </div>
    </div>
  );
}
