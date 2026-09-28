// O'zbek lotin -> kirill va yangi alifbo (backenddagi market/translit.py bilan bir xil qoidalar)
const MULTI: [string, string][] = [
  ["o'", "ў"], ["g'", "ғ"], ["sh", "ш"], ["ch", "ч"], ["yo", "ё"], ["yu", "ю"], ["ya", "я"], ["ts", "ц"],
];
const SINGLE: Record<string, string> = {
  a: "а", b: "б", d: "д", e: "е", f: "ф", g: "г", h: "ҳ", i: "и", j: "ж", k: "к", l: "л", m: "м", n: "н",
  o: "о", p: "п", q: "қ", r: "р", s: "с", t: "т", u: "у", v: "в", x: "х", y: "й", z: "з", c: "с", w: "в",
};
const VOW = new Set("aeiouAEIOU".split(""));
const isAlpha = (c: string) => /\p{L}/u.test(c);
const up = (s: string, u: boolean) => (u ? s.toUpperCase() : s);

function cyrlChunk(src: string): string {
  const s = src.replace(/[ʻʼ’‘`´]/g, "'");
  let out = "";
  for (let i = 0; i < s.length; ) {
    const ch = s[i];
    const low2 = s.slice(i, i + 2).toLowerCase();
    const prev = i > 0 ? s[i - 1] : " ";
    const wordStart = !isAlpha(prev);
    const U = ch !== ch.toLowerCase();
    if (low2 === "ye" && wordStart) { out += up("е", U); i += 2; continue; }
    const m = MULTI.find(([l]) => l === low2);
    if (m) { out += up(m[1], U); i += 2; continue; }
    const low = ch.toLowerCase();
    if (low === "e") out += up(wordStart || VOW.has(prev) ? "э" : "е", U);
    else if (ch === "'") out += isAlpha(prev) ? "ъ" : ch;
    else if (SINGLE[low]) out += up(SINGLE[low], U);
    else out += ch;
    i++;
  }
  return out;
}

function newChunk(src: string): string {
  return src
    .replace(/[ʻʼ’‘`´]/g, "'")
    .replace(/O'/g, "Ó").replace(/o'/g, "ó").replace(/G'/g, "Ǵ").replace(/g'/g, "ǵ")
    .replace(/S[hH]/g, "Ş").replace(/sh/g, "ş").replace(/C[hH]/g, "Ç").replace(/ch/g, "ç")
    .replace(/'/g, "’");
}

// {placeholder}, brendlar va texnik so'zlar o'girilmaydi
const KEEP = /(\{[a-zA-Z_]+\}|Click|Payme|E-IMZO|QR|B2B|B2C|PDF|ImkonMarket|SMS|ID)/;

function convert(s: string, fn: (x: string) => string) {
  return s.split(KEEP).map((p) => (KEEP.test(p) ? p : fn(p))).join("");
}
export const toCyrl = (s: string) => convert(s, cyrlChunk);
export const toNew = (s: string) => convert(s, newChunk);
