// Sayt lug'atini Flutter ilovasi uchun JSON ga eksport qiladi: node scripts/export-i18n.mjs
import { writeFileSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { build } from "esbuild";

const here = dirname(fileURLToPath(import.meta.url));
const out = resolve(here, "../../mobile/assets/i18n");
mkdirSync(out, { recursive: true });
const res = await build({
  stdin: { contents: `export * from "./src/lib/dict.ts"; export { toCyrl, toNew } from "./src/lib/translit.ts";`, resolveDir: resolve(here, ".."), loader: "ts" },
  bundle: true, write: false, format: "esm", platform: "node",
});
const mod = await import("data:text/javascript;base64," + Buffer.from(res.outputFiles[0].text).toString("base64"));
const conv = (fn) => Object.fromEntries(Object.entries(mod.uz).map(([k, v]) => [k, fn(v)]));
const all = { uz: mod.uz, uz_cyrl: conv(mod.toCyrl), uz_new: conv(mod.toNew), ru: mod.ru, kaa: mod.kaa, en: mod.en };
for (const [lang, d] of Object.entries(all)) writeFileSync(`${out}/${lang}.json`, JSON.stringify(d, null, 1));
console.log("i18n ->", out, Object.keys(all).join(", "));
