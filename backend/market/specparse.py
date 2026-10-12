"""Eski "spec" matnidan (masalan "250×120×65 mm", "PK 26-12-8", "100% paxta, 214×120 sm") xususiyatlarni taxminiy ajratish.
Natija — taklif: muassasa kartochkada tekshiradi va tuzatadi."""
import re

from .translit import pick

NUM = r"(\d+(?:[.,]\d+)?)"
DIMS = re.compile(NUM + r"\s*[×xх*]\s*" + NUM + r"(?:\s*[×xх*]\s*" + NUM + r")?\s*(mm|sm|см|мм|m|м)?(?![a-zа-я])", re.I)
SINGLE = re.compile(r"(?:^|\s)" + NUM + r"\s*(mm|sm|m)\b", re.I)
WEIGHT = re.compile(NUM + r"\s*(g|gr|kg)\b", re.I)
MARKA = re.compile(r"^\s*([A-ZА-Я]{1,4}[\s-]?\d[\w\-./]*)\s*$")
TO_SM = {"mm": 0.1, "мм": 0.1, "sm": 1, "см": 1, "m": 100, "м": 100}


def _f(x):
    return float(x.replace(",", "."))


def _num(v):
    v = round(v, 1)
    return int(v) if v == int(v) else v


def _norm(s):
    return (s or "").lower().replace("ʻ", "'").replace("‘", "'").replace("’", "'")


def parse_product(p, defs) -> dict:
    by = {d.code: d for d in defs if not d.variant}
    name = _norm(pick(p.name, "uz"))
    spec_raw = pick(p.spec, "uz") or ""
    spec = _norm(spec_raw)
    text = f"{name} {spec}"
    out = {}

    if "fraksiya" in spec and "fraksiya" in by:
        m = re.search(r"(\d+)\s*[×x-]\s*(\d+)", spec)
        if m:
            out["fraksiya"] = f"{m.group(1)}-{m.group(2)}"
    else:
        m = DIMS.search(spec)
        if m:
            vals = [_f(x) for x in m.groups()[:3] if x]
            unit = (m.group(4) or "").lower()
            if not unit:
                unit = "mm" if max(vals) >= 100 else "sm"
            sm = [_num(v * TO_SM[unit]) for v in vals]
            if "olcham" in by and by["olcham"].type == "text":
                out["olcham"] = m.group(0).strip()
            if "olcham_sm" in by:
                out["olcham_sm"] = spec_raw.strip()[:120]
            if "uzunlik" in by:
                if p.category.slug == "rom-eshik" and "eshik" in name and "rom" not in name:
                    keys = ["balandlik", "uzunlik"]
                elif "kenglik" in by:
                    keys = ["uzunlik", "kenglik", "balandlik"]
                else:
                    keys = ["uzunlik", "balandlik"]
                for k, v in zip(keys, sm):
                    if k in by:
                        out[k] = v
        else:
            m = SINGLE.search(spec)
            if m and "uzunlik" in by:
                out["uzunlik"] = _num(_f(m.group(1)) * TO_SM[m.group(2).lower()])
    m = WEIGHT.search(spec)
    if m:
        kg = _f(m.group(1)) / (1000 if m.group(2).lower().startswith("g") else 1)
        if "vazn" in by:
            out["vazn"] = _num(kg) if kg >= 0.1 else round(kg, 3)
        if "hajm" in by:
            out["hajm"] = m.group(0)
    if "marka" in by and MARKA.match(spec_raw or ""):
        out["marka"] = spec_raw.strip()
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*mm", spec)
    if m and "sim_qalinligi" in by and "sim" in name:
        out["sim_qalinligi"] = _f(m.group(1))
    # ro'yxat (enum) qiymatlarini matndan topish: eng uzun mos nom
    for d in by.values():
        if d.type != "enum" or d.code in out:
            continue
        best, best_len = None, 0
        for o in d.options or []:
            for lg in ("uz", "ru"):
                n = _norm((o.get("name") or {}).get(lg, ""))
                core = re.sub(r"\s*\(.*?\)", "", n).strip()
                for cand in {n, core, _norm(o.get("v", "")).replace("-", " ")}:
                    if len(cand) >= 3 and re.search(r"(?<![a-zа-я'])" + re.escape(cand), text) and len(cand) > best_len:
                        best, best_len = o["v"], len(cand)
        if best:
            out[d.code] = [best] if d.multi else best
    if "ichi_kovak" in by and ("pustotali" in name or "teshikli" in text or "kovak" in text):
        out["ichi_kovak"] = True
    if "narx_m2" in by and "m²" in spec:
        out["narx_m2"] = True
    if "maket" in by and "maket" in name:
        out["maket"] = True
    if "turi" in by and by["turi"].type == "text" and not out.get("turi"):
        out["turi"] = pick(p.name, "uz")[:100]
    return out
