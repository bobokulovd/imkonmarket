"""Mahsulot kartochkasi: xususiyatlarni tekshirish, variantlar, shtrix-kod va IKPU yordamchilari."""
import re
from decimal import Decimal, InvalidOperation

from django.db import transaction
from rest_framework.exceptions import ValidationError

from .models import ApplicationItem, AttributeDef, Product, ProductVariant
from .translit import pick

TRUE = (True, "true", "1", 1, "ha", "yes", "да")
FALSE = (False, "false", "0", 0, "yo'q", "no", "нет")


# ------------------------------------------------------------------ barcode
def ean_ok(code: str) -> bool:
    """EAN-8 / UPC-A (12) / EAN-13 / GTIN-14 nazorat raqami."""
    if not code.isdigit() or len(code) not in (8, 12, 13, 14):
        return False
    digits = [int(c) for c in code]
    body, check = digits[:-1], digits[-1]
    s = sum(d * (3 if i % 2 == 0 else 1) for i, d in enumerate(reversed(body)))
    return (10 - s % 10) % 10 == check


def clean_barcode(v) -> str:
    v = re.sub(r"\s+", "", str(v or ""))
    if v and not ean_ok(v):
        raise ValidationError({"barcode": f"«{v}» — shtrix-kod noto'g'ri (EAN-13: 13 raqam, oxirgisi nazorat raqami)"})
    return v


def clean_ikpu(v) -> str:
    v = re.sub(r"\D", "", str(v or ""))
    if v and len(v) != 17:
        raise ValidationError({"ikpu": "IKPU (MXIK) kodi 17 raqamdan iborat"})
    return v


# --------------------------------------------------------------- attributes
def _clean_one(d: AttributeDef, v):
    if d.type == AttributeDef.T_NUMBER:
        try:
            n = Decimal(str(v).replace(",", ".").strip())
        except (InvalidOperation, ValueError):
            raise ValidationError({"attributes": {d.code: f"«{pick(d.name, 'uz')}»: son kiriting"}})
        return int(n) if n == n.to_integral_value() else float(n)
    if d.type == AttributeDef.T_BOOL:
        if isinstance(v, str):
            v = v.strip().lower()
        if v in TRUE:
            return True
        if v in FALSE:
            return False
        raise ValidationError({"attributes": {d.code: f"«{pick(d.name, 'uz')}»: ha/yo'q"}})
    if d.type == AttributeDef.T_ENUM:
        codes = {o.get("v") for o in d.options or []}
        if v not in codes:
            # nomi bilan yuborilgan bo'lsa ("Qora" / "Черный") — kodga aylantiramiz
            low = str(v).strip().lower()
            hit = next((o["v"] for o in d.options or [] for n in (o.get("name") or {}).values() if str(n).lower() == low), None)
            if not hit:
                raise ValidationError({"attributes": {d.code: f"«{pick(d.name, 'uz')}»: ro'yxatda yo'q qiymat «{v}»"}})
            v = hit
        return v
    return str(v).strip()[:500]


def clean_attributes(category_id, data, variant=False) -> dict:
    """{code: value} -> tozalangan. variant=True — faqat variant o'qlari; False — oddiy xususiyatlar.
    Kategoriyada yo'q kodlar tashlab yuboriladi (kategoriya o'zgarganda eski qiymatlar qolmasin)."""
    if data in (None, ""):
        return {}
    if not isinstance(data, dict):
        raise ValidationError({"attributes": "object expected"})
    defs = {d.code: d for d in AttributeDef.objects.filter(category_id=category_id, variant=variant)}
    out = {}
    for k, v in data.items():
        d = defs.get(k)
        if d is None or v in (None, "", []):
            continue
        if d.multi and not variant:
            vals = v if isinstance(v, list) else [v]
            out[k] = list(dict.fromkeys(_clean_one(d, x) for x in vals if x not in (None, "")))
        else:
            out[k] = _clean_one(d, v[0] if isinstance(v, list) and v else v)
    return out


def characteristics(p: Product, lang="uz") -> list:
    """Vitrina uchun xususiyatlar jadvali: [{code, name, value}] (lug'at tartibida)."""
    out = []
    for d in AttributeDef.objects.filter(category_id=p.category_id, variant=False):
        val = (p.attributes or {}).get(d.code)
        if val in (None, "", []):
            continue
        out.append({"code": d.code, "name": d.name, "value": {lg: d.display(val, lg) for lg in (d.name or {})}})
    return out


# ----------------------------------------------------------------- variants
def variant_label(v: ProductVariant, defs=None) -> dict:
    """{til: "Qora, 48"} — variant o'qlari qiymatlari nomi."""
    if defs is None:
        defs = {d.code: d for d in AttributeDef.objects.filter(category_id=v.product.category_id, variant=True)}
    from .translit import LANGS
    out = {}
    for lg in LANGS:
        out[lg] = ", ".join(x for x in (defs[k].display(val, lg) if k in defs else str(val)
                                        for k, val in (v.attributes or {}).items()) if x)
    return out


def _slug(v) -> str:
    s = re.sub(r"[^A-Z0-9]+", "", str(v).upper().replace("'", ""))
    return s[:8] or "X"


def variant_sku(p: Product, attrs: dict, taken: set) -> str:
    base = f"{p.sku}-" + "-".join(_slug(v) for v in attrs.values()) if attrs else f"{p.sku}-V"
    base = base[:36]
    sku, n = base, 2
    while sku in taken or ProductVariant.objects.filter(sku=sku).exists():
        sku = f"{base[:33]}-{n}"
        n += 1
    taken.add(sku)
    return sku


@transaction.atomic
def save_variants(p: Product, rows: list) -> list:
    """Variantlar ro'yxatini to'liq almashtiradi: [{id?, sku?, attributes, barcode, price, stock, image, is_active}].
    Ro'yxatda yo'q variant: buyurtmalarda ishlatilgan bo'lsa — nofaol qilinadi, aks holda o'chiriladi.
    Band qilingan (reserved) va sotilgan (sold) miqdorlar saqlanadi."""
    if not isinstance(rows, list):
        raise ValidationError({"variants": "list expected"})
    p = Product.objects.select_for_update().get(pk=p.pk)
    axes = list(AttributeDef.objects.filter(category_id=p.category_id, variant=True))
    if rows and not axes:
        raise ValidationError({"variants": "Bu kategoriyada variant o'qi (rang/o'lcham) yo'q"})
    existing = {v.pk: v for v in p.variants.select_for_update()}
    images = set(p.images.values_list("pk", flat=True))
    seen_keys, taken, keep = set(), set(), []
    for i, r in enumerate(rows):
        attrs = clean_attributes(p.category_id, r.get("attributes") or {}, variant=True)
        if not attrs:
            raise ValidationError({"variants": f"{i + 1}-qator: rang/o'lcham tanlanmagan"})
        key = tuple(sorted(attrs.items()))
        if key in seen_keys:
            raise ValidationError({"variants": f"{i + 1}-qator: bunday variant takrorlangan"})
        seen_keys.add(key)
        v = existing.get(int(r["id"])) if str(r.get("id") or "").isdigit() else None
        if v is None:
            v = ProductVariant(product=p)
        v.attributes = attrs
        v.barcode = clean_barcode(r.get("barcode"))
        price = r.get("price")
        # narx berilmasa — mahsulotning hozirgi narxi variantga yoziladi (keyin mahsulot narxi = eng arzon variant)
        v.price = (v.price if v.pk and v.price is not None else p.price) if price in (None, "") else Decimal(str(price))
        if v.price is not None and v.price < 0:
            raise ValidationError({"variants": f"{i + 1}-qator: narx manfiy"})
        stock = r.get("stock")
        v.stock = None if stock in (None, "") else max(int(stock), 0)
        img = r.get("image")
        v.image_id = int(img) if str(img or "").isdigit() and int(img) in images else None
        v.is_active = bool(r.get("is_active", True))
        v.order = i
        want = (r.get("sku") or "").strip().upper()
        if not v.sku:
            if want and not ProductVariant.objects.filter(sku=want).exists() and not Product.objects.filter(sku=want).exists():
                v.sku = want[:40]
                taken.add(v.sku)
            else:
                v.sku = variant_sku(p, attrs, taken)
        if v.barcode and ProductVariant.objects.filter(barcode=v.barcode).exclude(pk=v.pk).exists():
            raise ValidationError({"variants": f"{v.sku}: shtrix-kod {v.barcode} boshqa variantda bor"})
        v.save()
        keep.append(v.pk)
    for pk, v in existing.items():
        if pk in keep:
            continue
        if ApplicationItem.objects.filter(variant=v).exists() or v.reserved or v.mp_listings.exists():
            v.is_active = False
            v.save(update_fields=["is_active"])
        else:
            v.delete()
    p.sync_from_variants()
    return list(p.variants.all())
