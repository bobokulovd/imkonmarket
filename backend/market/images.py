"""Mahsulot rasmlari: normallashtirish (1024 px WebP), fayl nomi bo'yicha mahsulotga bog'lash, namunaviy rasmlar."""
import io
import json
import re
import uuid
import zipfile
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone
from PIL import Image, ImageOps

from .models import Product, ProductImage, sync_cover

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


def add_image(product: Product, raw: bytes, sample=False, first=False) -> ProductImage | None:
    """Galereyaga rasm qo'shadi. Haqiqiy surat qo'shilganda namunaviy (AI) rasmlar o'chiriladi.
    Namunaviy rasm faqat galereya bo'sh bo'lsa qo'yiladi. first=True — asosiy (muqova) rasm qilib qo'yadi."""
    if sample and product.images.exists():
        return None
    data = normalize(raw)
    if not sample:
        for old in product.images.filter(is_sample=True):
            old.image.delete(save=False)
            old.delete()
    w = h = 0
    try:
        w, h = Image.open(io.BytesIO(data)).size
    except Exception:  # noqa: BLE001
        pass
    n = product.images.count()
    if first and n:
        for i, im in enumerate(product.images.order_by("order", "id"), start=1):
            ProductImage.objects.filter(pk=im.pk).update(order=i)
    img = ProductImage(product=product, order=0 if first else n, is_sample=sample, width=w, height=h)
    img.image.save(f"{product.sku.lower()}-{uuid.uuid4().hex[:6]}.webp", ContentFile(data), save=False)
    img.save()
    sync_cover(product)
    Product.objects.filter(pk=product.pk).update(updated_at=timezone.now())
    return img


def delete_image(img: ProductImage):
    product = img.product
    img.image.delete(save=False)
    img.delete()
    for i, im in enumerate(product.images.order_by("order", "id")):
        ProductImage.objects.filter(pk=im.pk).update(order=i)
    sync_cover(product)


def reorder_images(product: Product, ids):
    order = {int(i): n for n, i in enumerate(ids)}
    rest = len(order)
    for im in product.images.order_by("order", "id"):
        ProductImage.objects.filter(pk=im.pk).update(order=order.get(im.pk, rest))
        rest += im.pk not in order
    sync_cover(product)


def set_image(product: Product, raw: bytes, sample=False):
    """Eski interfeys: asosiy rasmni o'rnatish (galereya boshiga qo'shadi)."""
    return add_image(product, raw, sample=sample, first=True)


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
    """Fayl nomi = SKU (bir mahsulotga bir nechta rasm: MK-49-001.jpg, MK-49-001_2.jpg, MK-49-001 (3).jpg).
    -> {"matched": [...], "unmatched": [...], "errors": [...]}"""
    by_sku = {p.sku.upper(): p for p in products_qs}
    res = {"matched": [], "unmatched": [], "errors": []}
    for name, raw in iter_files(files):
        p = by_sku.get(sku_from_filename(name))
        if not p:
            res["unmatched"].append(name)
            continue
        try:
            add_image(p, raw, sample=False)
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
            imgs = list(p.images.all())
            if imgs and not (overwrite_samples and all(i.is_sample for i in imgs)):
                continue
            for old in imgs:
                delete_image(old)
            raw = raw or f.read_bytes()
            if add_image(p, raw, sample=True):
                n += 1
    return n
