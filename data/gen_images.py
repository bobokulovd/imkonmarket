"""Namunaviy rasmlarni AI bilan yaratish (manifest.json dagi promptlar bo'yicha).

    export OPENAI_API_KEY=sk-...
    python data/gen_images.py                 # hali rasmi yo'qlarini yaratadi
    python data/gen_images.py --only choyshablar-toplami-1a2b3c --force
    python data/gen_images.py --limit 5       # sinov uchun

Natija: backend/market/seed/images/<key>.webp (1024 px, ~60–120 KB). Keyin:
    git add backend/market/seed/images && git commit -m "Namunaviy rasmlar" && git push
Deploydan keyin backend avtomatik ravishda rasmsiz mahsulotlarga shu rasmlarni qo'yadi (load_sample_images).
Boshqa generator ishlatsangiz ham bo'ladi — faqat fayl nomi <key>.webp/.png/.jpg bo'lsin.
"""
import argparse
import base64
import io
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIR = ROOT / "backend/market/seed/images"


def openai_image(prompt: str, model: str, quality: str) -> bytes:
    import requests
    r = requests.post("https://api.openai.com/v1/images/generations", timeout=300, headers={
        "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"}, json={
        "model": model, "prompt": prompt, "size": "1024x1024", "quality": quality, "n": 1})
    if r.status_code == 429 or r.status_code >= 500:
        raise RuntimeError(f"retry {r.status_code}")
    r.raise_for_status()
    d = r.json()["data"][0]
    if d.get("b64_json"):
        return base64.b64decode(d["b64_json"])
    return requests.get(d["url"], timeout=120).content


def to_webp(raw: bytes) -> bytes:
    from PIL import Image
    im = Image.open(io.BytesIO(raw)).convert("RGB")
    im.thumbnail((1024, 1024))
    buf = io.BytesIO()
    im.save(buf, "WEBP", quality=82, method=6)
    return buf.getvalue()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--model", default=os.environ.get("IMAGE_MODEL", "gpt-image-1"))
    ap.add_argument("--quality", default="medium")
    a = ap.parse_args()
    if not os.environ.get("OPENAI_API_KEY"):
        sys.exit("OPENAI_API_KEY kerak")
    items = json.loads((DIR / "manifest.json").read_text())["items"]
    if a.only:
        items = [i for i in items if i["key"] in a.only]
    todo = [i for i in items if a.force or not any((DIR / f"{i['key']}{e}").exists() for e in (".webp", ".png", ".jpg"))]
    if a.limit:
        todo = todo[:a.limit]
    print(f"yaratiladi: {len(todo)} / {len(items)}")
    for n, it in enumerate(todo, 1):
        for attempt in range(5):
            try:
                raw = openai_image(it["prompt"], a.model, a.quality)
                (DIR / f"{it['key']}.webp").write_bytes(to_webp(raw))
                print(f"[{n}/{len(todo)}] ✓ {it['name_uz']}")
                break
            except Exception as e:  # noqa: BLE001
                wait = 2 ** attempt * 5
                print(f"[{n}/{len(todo)}] {it['name_uz']}: {e} — {wait}s")
                time.sleep(wait)


if __name__ == "__main__":
    main()
