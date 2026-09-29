"""Mahsulot rasmlari: normallashtirish (1024 px WebP), fayl nomi bo'yicha mahsulotga bog'lash, namunaviy rasmlar."""
import io
import json
import re
import zipfile
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from PIL import Image, ImageOps

from .models import Product

EXTS = (".jpg", ".jpeg", ".png", ".webp", ".heic", ".bmp", ".gif")
SEED_DIR = Path(settings.BASE_DIR) / "market" / "seed" / "images"


def normalize(raw: bytes, max_side=1400) -> bytes:
    im = Image.open(io.BytesIO(raw))
    im = ImageOps.exif_transpose(im).convert("RGB")
    im.thumbnail((max_side, max_side))
    buf = io.BytesIO()
    im.save(buf, "WEBP", quality=84, method=6)
    return buf.getvalue()


def sku_from_filename(name: str) -> str:
    """'MK-49-001.jpg', 'mk-49-001 (2).JPG', 'MK-49-001_old.png' -> 'MK-49-001'"""
    stem = Path(name).stem.upper()
    m = re.match(r"\s*([A-Z]+-\d+-\d+(?:-[A-Z0-9]{3})?)", stem)
    return m.group(1) if m else stem.strip()


def set_image(product: Product, raw: bytes, sample=False):
    data = normalize(raw)
    if product.image:
        product.image.delete(save=False)
    product.image.save(f"{product.sku.lower()}.webp", ContentFile(data), save=False)
    product.image_is_sample = sample
    product.save(update_fields=["image", "image_is_sample", "updated_at"])


def iter_files(files):
    """[(filename, bytes)] — ZIP arxivlar ichidagi rasmlar ham ochiladi."""
    for name, raw in files:
        if name.lower().endswith(".zip"):
            with zipfile.ZipFile(io.BytesIO(raw)) as z:
                for info in z.infolist():
                    n = info.filename
                    if info.is_dir() or "__MACOSX" in n or Path(n).name.startswith("."):
                        continue
                    if n.lower().endswith(EXTS):
                        yield Path(n).name, z.read(info)
        elif name.lower().endswith(EXTS):
            yield Path(name).name, raw


def import_files(files, products_qs):
    """Fayl nomi = SKU. -> {"matched": [...], "unmatched": [...], "errors": [...]}"""
    by_sku = {p.sku.upper(): p for p in products_qs}
    res = {"matched": [], "unmatched": [], "errors": []}
    for name, raw in iter_files(files):
        p = by_sku.get(sku_from_filename(name))
        if not p:
            res["unmatched"].append(name)
            continue
        try:
            set_image(p, raw, sample=False)
            res["matched"].append({"file": name, "sku": p.sku, "id": p.id})
        except Exception as e:  # noqa: BLE001 — buzilgan fayl
            res["errors"].append(f"{name}: {e}")
    return res


def load_samples(overwrite_samples=False) -> int:
    """seed/images/manifest.json bo'yicha rasmsiz mahsulotlarga namunaviy (AI) rasm qo'yadi."""
    mf = SEED_DIR / "manifest.json"
    if not mf.exists():
        return 0
    n = 0
    for it in json.loads(mf.read_text())["items"]:
        f = next((SEED_DIR / f"{it['key']}{e}" for e in (".webp", ".png", ".jpg") if (SEED_DIR / f"{it['key']}{e}").exists()), None)
        if not f:
            continue
        raw = None
        for p in Product.objects.filter(sku__in=it["skus"]):
            if p.image and not (overwrite_samples and p.image_is_sample):
                continue
            raw = raw or f.read_bytes()
            set_image(p, raw, sample=True)
            n += 1
    return n
