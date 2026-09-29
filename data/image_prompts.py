"""Har bir noyob mahsulot nomi uchun AI rasm prompti (namunaviy rasm) — manifest yaratadi.

    python data/image_prompts.py   ->  backend/market/seed/images/manifest.json

Bir xil nomli mahsulotlar (masalan, 13 ta muassasadagi "pustotali plita") bitta rasmni ulashadi.
Rasm fayli: backend/market/seed/images/<key>.webp  (gen_images.py yaratadi yoki qo'lda qo'yiladi).
"""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "backend/market/seed/catalog.json"
OUT = ROOT / "backend/market/seed/images/manifest.json"

STYLE = (
    "Realistic e-commerce catalog product photo. Single product centered, 3/4 view, "
    "on a clean seamless light-gray studio background, soft diffused daylight, gentle shadow, "
    "sharp focus, natural materials and colors, simple honest factory-made product from Uzbekistan. "
    "No text, no letters, no logos, no watermark, no people, no hands."
)
# Katta/qurilish mahsulotlari studiyaga sig'maydi — tashqi sahna
OUTDOOR = {"temir-beton", "qurilish", "obodonlashtirish"}
SERVICE = {"xizmatlar"}


def key_for(name_uz: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name_uz.lower().replace("'", "").replace("ʻ", "")).strip("-")[:40]
    return f"{base}-{hashlib.sha1(name_uz.strip().lower().encode()).hexdigest()[:6]}"


def prompt_for(p: dict) -> str:
    en, ru = p["name"]["en"], p["name"]["ru"]
    spec = (p.get("spec") or {}).get("en") or ""
    subject = f"{en} ({ru})" + (f", {spec}" if spec else "")
    cat = p["category"]
    if cat in SERVICE:
        return (f"Realistic photo illustrating the service: {subject}. Clean tidy workshop or work site, "
                "tools and result of the work in focus, soft daylight. No text, no logos, no faces.")
    if cat in OUTDOOR:
        return (f"Realistic catalog photo of {subject}, neatly stacked or placed at a clean production yard, "
                "overcast soft daylight, product in sharp focus, simple background. "
                "No text, no letters, no logos, no watermark, no people.")
    return f"{subject}. {STYLE}"


def main():
    data = json.loads(CATALOG.read_text())
    groups = {}
    for p in data["products"]:
        k = key_for(p["name"]["uz"])
        g = groups.setdefault(k, {"key": k, "name_uz": p["name"]["uz"], "name_en": p["name"]["en"],
                                  "category": p["category"], "prompt": prompt_for(p), "skus": []})
        g["skus"].append(p["sku"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    items = sorted(groups.values(), key=lambda g: (g["category"], g["key"]))
    OUT.write_text(json.dumps({"style": STYLE, "items": items}, ensure_ascii=False, indent=1))
    print(f"{len(items)} ta rasm ({sum(len(g['skus']) for g in items)} mahsulot) -> {OUT}")


if __name__ == "__main__":
    main()
