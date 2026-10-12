"""Mahsulot rasmlari: tekshirish va normallashtirish, fayl nomi bo'yicha mahsulotga bog'lash, namunaviy rasmlar.

Haqiqiy surat talablari (marketplace'lar talabiga mos — Ozon faqat JPG/PNG qabul qiladi, WB kamida 700 px):
  format JPG/PNG/WEBP, hajmi ≤ 15 MB, qisqa tomoni ≥ 700 px, tomonlar nisbati ≤ 1:3, ≤ 50 megapiksel.
Saqlanadi: JPEG, uzun tomoni ≤ 2000 px (katalog va marketplace'lar uchun bitta fayl).
"""
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

EXTS = (".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".bmp", ".gif")
MAX_BYTES = 15 * 1024 * 1024
MIN_SIDE = 700
MAX_RATIO = 3.0
MAX_PIXELS = 50_000_000
MAX_SIDE_OUT = 2000
ZIP_MAX_FILES = 500
Image.MAX_IMAGE_PIXELS = MAX_PIXELS * 2  # "dekompressiya bombasi"dan himoya


class ImageRejected(ValueError):
    """Foydalanuvchiga ko'rsatiladigan tushunarli sabab."""


def check(raw: bytes, name: str = "") -> tuple[int, int]:
    """Haqiqiy surat talablarini tekshiradi -> (eni, bo'yi). Mos kelmasa ImageRejected."""
    mb = len(raw) / 1024 / 1024
    if len(raw) > MAX_BYTES:
        raise ImageRejected(f"Fayl juda katta: {mb:.1f} MB (ko'pi bilan {MAX_BYTES // 1024 // 1024} MB)")
    if name.lower().endswith((".heic", ".heif")):
        raise ImageRejected("HEIC (iPhone) formati qo'llanmaydi — JPG qilib saqlang yoki iPhone sozlamalarida "
                            "Kamera → Formatlar → «Eng mos» ni tanlang")
    try:
        im = Image.open(io.BytesIO(raw))
        fmt = (im.format or "").upper()
        w, h = ImageOps.exif_transpose(im).size
    except Image.DecompressionBombError:
        raise ImageRejected("Rasm o'lchami juda katta (50 megapikseldan oshmasin)")
    except Exception:  # noqa: BLE001
        raise ImageRejected("Rasm fayli ochilmadi (buzilgan yoki rasm emas)")
    if fmt not in ("JPEG", "PNG", "WEBP", "MPO", "BMP", "GIF"):
        raise ImageRejected(f"{fmt or 'Bu'} formati qo'llanmaydi — JPG, PNG yoki WEBP yuklang")
    if w * h > MAX_PIXELS:
        raise ImageRejected(f"Rasm o'lchami juda katta: {w}×{h} (50 megapikseldan oshmasin)")
    if min(w, h) < MIN_SIDE:
        raise ImageRejected(f"Rasm juda kichik: {w}×{h} px — qisqa tomoni kamida {MIN_SIDE} px bo'lsin "
                            "(marketplace'lar kichik rasmni qabul qilmaydi)")
    if max(w, h) / min(w, h) > MAX_RATIO:
        raise ImageRejected(f"Rasm juda cho'zinchoq: {w}×{h} — tomonlar nisbati 1:3 dan oshmasin")
    return w, h
SEED_DIR = Path(settings.BASE_DIR) / "market" / "seed" / "images"


def analyze(raw: bytes) -> dict:
    """Fon va kompozitsiya tekshiruvi (marketplace talablari: asosiy rasm oq/och, bir xil fonda, mahsulot kadrni to'ldirsin).

    -> {"bg_ok": bool, "bg": "white"|"light"|"color"|"busy", "fill": 0..1, "warnings": [matn, ...]}
    Rad etmaydi — faqat ogohlantiradi (tayyorlik foizida hisobga olinadi).
    """
    from PIL import ImageFilter
    im = ImageOps.exif_transpose(Image.open(io.BytesIO(raw)))
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        bg = Image.new("RGB", im.size, (255, 255, 255))
        bg.paste(im, mask=im.split()[-1])
        im = bg
    im = im.convert("RGB")
    im.thumbnail((256, 256))
    w, h = im.size
    b = max(2, int(min(w, h) * 0.04))
    px = im.load()
    border = [px[x, y] for y in range(h) for x in range(w) if x < b or y < b or x >= w - b or y >= h - b]
    med = tuple(sorted(c[i] for c in border)[len(border) // 2] for i in range(3))
    near = sum(1 for c in border if max(abs(c[i] - med[i]) for i in range(3)) <= 30) / len(border)
    uniform = near >= 0.85
    light = min(med) >= 215 and max(med) - min(med) <= 25
    white = min(med) >= 240 and max(med) - min(med) <= 12
    # mahsulot chegarasi: fondan sezilarli farq qiladigan piksellar
    mask = Image.new("L", (w, h))
    mp = mask.load()
    for y in range(h):
        for x in range(w):
            c = px[x, y]
            if max(abs(c[i] - med[i]) for i in range(3)) > 40:
                mp[x, y] = 255
    mask = mask.filter(ImageFilter.MinFilter(3))  # mayda shovqin
    box = mask.getbbox()
    fill = ((box[2] - box[0]) * (box[3] - box[1]) / (w * h)) if box else 0.0
    warnings = []
    if not uniform:
        kind = "busy"
        warnings.append("Fon bir xil emas (xona, stol yoki boshqa narsalar ko'rinmoqda) — mahsulotni oq yoki bir xil "
                        "och rangli fonda suratga oling")
    elif not light:
        kind = "color"
        warnings.append("Fon oq emas — marketplace'lar asosiy rasm uchun oq yoki och fon talab qiladi")
    else:
        kind = "white" if white else "light"
    if uniform and box and fill < 0.3:
        warnings.append("Mahsulot kadrda juda kichik — yaqinroqdan oling (mahsulot kadrning kamida yarmini egallasin)")
    return {"bg_ok": uniform and light, "bg": kind, "fill": round(fill, 2), "warnings": warnings}


def normalize(raw: bytes, max_side=MAX_SIDE_OUT) -> bytes:
    """JPEG (barcha marketplace'lar qabul qiladi), shaffof fon oq bilan to'ldiriladi."""
    im = ImageOps.exif_transpose(Image.open(io.BytesIO(raw)))
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        bg = Image.new("RGB", im.size, (255, 255, 255))
        bg.paste(im, mask=im.split()[-1])
        im = bg
    else:
        im = im.convert("RGB")
    im.thumbnail((max_side, max_side), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=88, optimize=True, progressive=True)
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
    if not sample:
        check(raw)
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
    quality = {}
    if not sample:
        try:
            quality = analyze(data)
        except Exception:  # noqa: BLE001 — tahlil ixtiyoriy
            quality = {}
    img = ProductImage(product=product, order=0 if first else n, is_sample=sample, width=w, height=h,
                       bg_ok=quality.get("bg_ok"), quality=quality)
    img.image.save(f"{product.sku.lower()}-{uuid.uuid4().hex[:6]}.jpg", ContentFile(data), save=False)
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
                count = 0
                for info in z.infolist():
                    n = info.filename
                    if info.is_dir() or "__MACOSX" in n or Path(n).name.startswith("."):
                        continue
                    if n.lower().endswith(EXTS):
                        count += 1
                        if count > ZIP_MAX_FILES:
                            raise ImageRejected(f"ZIP ichida {ZIP_MAX_FILES} tadan ko'p rasm")
                        if info.file_size > MAX_BYTES:  # ochmasdan oldin — zip-bombadan himoya
                            yield Path(n).name, b"\0" * (MAX_BYTES + 1)
                            continue
                        yield Path(n).name, z.read(info)
        elif name.lower().endswith(EXTS):
            yield Path(name).name, raw


def import_files(files, products_qs):
    """Fayl nomi = SKU (bir mahsulotga bir nechta rasm: MK-49-001.jpg, MK-49-001_2.jpg, MK-49-001 (3).jpg).
    -> {"matched": [...], "unmatched": [...], "errors": [...]}"""
    by_sku = {p.sku.upper(): p for p in products_qs}
    res = {"matched": [], "unmatched": [], "errors": []}
    try:
        _import(files, by_sku, res)
    except ImageRejected as e:
        res["errors"].append(str(e))
    except zipfile.BadZipFile:
        res["errors"].append("ZIP arxiv buzilgan")
    return res


def _import(files, by_sku, res):
    for name, raw in iter_files(files):
        p = by_sku.get(sku_from_filename(name))
        if not p:
            res["unmatched"].append(name)
            continue
        if p.images.filter(is_sample=False).count() >= 15:
            res["errors"].append(f"{name}: {p.sku} da 15 ta rasm bor — ortig'i qo'shilmadi")
            continue
        try:
            check(raw, name)
            add_image(p, raw, sample=False)
            res["matched"].append({"file": name, "sku": p.sku, "id": p.id})
        except ImageRejected as e:
            res["errors"].append(f"{name}: {e}")
        except Exception as e:  # noqa: BLE001 — buzilgan fayl
            res["errors"].append(f"{name}: {e}")


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
