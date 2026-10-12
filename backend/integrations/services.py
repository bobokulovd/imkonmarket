"""Integratsiya biznes-mantig'i: vazifa handlerlari, narx/qoldiq hisoblash, buyurtma → qoldiq band qilish.

Barcha tashqi chaqiruvlar shu yerdagi handlerlar orqali worker'da bajariladi (HTTP so'rovda emas).
"""
import logging
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from market.models import AttributeDef, Product, ProductVariant
from market.translit import pick

from . import currency
from .clients import get_client
from .clients.base import (CAP_CREATE, CAP_LINK, CAP_ORDERS, CAP_PRICES, CAP_STOCKS, ListingRef, MarketplaceError,
                           ProductPayload)
from .jobs import enqueue, handler
from .models import (AttributeMapping, CategoryMapping, ExternalCategory, MarketplaceAccount, MarketplaceListing,
                     MarketplaceOrder, ProductMarketInfo)
from .redact import redact

log = logging.getLogger("integrations")
L = MarketplaceListing
O = MarketplaceOrder
MP_LANG = {"uzum": "uz", "ozon": "ru", "yandex": "ru", "wb": "ru"}
NEEDS_DIMS = {"ozon", "wb"}
RESERVE_STATES = {O.S_NEW, O.S_PROCESSING}
DEDUCT_STATES = {O.S_SHIPPED, O.S_DELIVERED}
# Bu marketplace'lar bizga yuborilgan qoldiqni "ombordagi jami" deb oladi va o'z buyurtmalarini o'zi ayiradi
# (Ozon: "The system will deduct the old stock and calculate the new one"). Ularga o'z band buyurtmalarini qaytarib qo'shamiz.
# Boshqalari uchun kabinet sozlamasi: options["stock_add_own_reserved"] = true.
OWN_RESERVE_INCLUDED = {"ozon"}


# ------------------------------------------------------------------ helpers
def capabilities(account):
    from .clients import client_class
    return client_class(account.marketplace).capabilities


def public_media(path):
    base = (settings.PUBLIC_URL or settings.SITE_URL or "").rstrip("/")
    return base + path


def stock_key(product_id, variant_id=None) -> str:
    """Qoldiq snapshot kaliti: mahsulot — "12", variant — "v34"."""
    return f"v{variant_id}" if variant_id else str(product_id)


def stock_for(account: MarketplaceAccount, product: Product, own_reserved: int = 0, variant=None) -> int:
    if not product.is_active or not product.seller.is_active or (variant is not None and not variant.is_active):
        return 0
    h = variant or product
    if h.stock is None:
        return int(account.mto_stock or 0)
    return max((h.stock or 0) - (h.reserved or 0) + own_reserved - (account.stock_buffer or 0), 0)


def own_reserved(account: MarketplaceAccount) -> dict:
    """Shu kabinetning o'z band buyurtmalari {stock_key: qty} (faqat OWN_RESERVE_INCLUDED marketplace'lar uchun)."""
    if account.marketplace not in OWN_RESERVE_INCLUDED and not (account.options or {}).get("stock_add_own_reserved"):
        return {}
    out = {}
    for items in O.objects.filter(account=account, stock_state=O.STOCK_RESERVED).values_list("stock_items", flat=True):
        for k, q in (items or {}).items():
            out[str(k)] = out.get(str(k), 0) + int(q)
    return out


def listing_price(li):
    return li.variant.effective_price if li.variant_id else li.product.price


def price_for(account, product, variant=None):
    return currency.convert(account, variant.effective_price if variant is not None else product.price)


def listing_stock(li, own: dict) -> int:
    return stock_for(li.account, li.product, own.get(stock_key(li.product_id, li.variant_id), 0), variant=li.variant)


def ref(listing: L, price=None, stock=None) -> ListingRef:
    return ListingRef(listing_id=listing.pk, offer_id=listing.offer_id, external_id=listing.external_id,
                      external_sku=listing.external_sku, external_meta=listing.external_meta or {},
                      task_id=listing.task_id, price=price, currency=listing.account.currency, stock=stock)


def product_images(p, variant=None) -> list:
    """Marketplace'ga yuboriladigan rasmlar: faqat haqiqiy suratlar (namunaviy AI rasmlar yuborilmaydi).
    Variant rasmi bo'lsa — birinchi o'rinda."""
    imgs = [im for im in p.images.all() if not im.is_sample]
    if variant is not None and variant.image_id and not variant.image.is_sample:
        imgs = [variant.image] + [im for im in imgs if im.pk != variant.image_id]
    urls = [public_media(im.image.url) for im in imgs if im.image]
    if not urls and p.image and not p.image_is_sample:
        urls = [public_media(p.image.url)]
    return urls


def merged_attributes(p, variant=None) -> dict:
    return {**(p.attributes or {}), **((variant.attributes or {}) if variant is not None else {})}


def build_payload(listing: L):
    """-> (ProductPayload | None, [xatolar]). Xatolar muassasaga tushunarli tilda."""
    acc, p, v = listing.account, listing.product, listing.variant
    errors = []
    info = ProductMarketInfo.objects.filter(product=p).first() or ProductMarketInfo(product=p)
    lang = MP_LANG[acc.marketplace]
    if acc.marketplace == "yandex" and (acc.options or {}).get("language") == "UZ":
        lang = "uz"
    defs = {d.code: d for d in AttributeDef.objects.filter(category_id=p.category_id)}
    attrs_all = merged_attributes(p, v)
    name = pick(p.name, lang)
    spec = pick(p.spec, lang)
    title = f"{name} {spec}".strip() if spec and spec not in name else name
    if v is not None and v.attributes:
        suffix = ", ".join(x for x in (defs[k].display(val, lang) if k in defs else str(val)
                                       for k, val in v.attributes.items()) if x)
        title = f"{title}, {suffix}" if suffix else title
    description = pick(p.description, lang) or title
    if listing_price(listing) is None:
        errors.append("Narx kiritilmagan (narx «kelishiladi»)")
    price = None
    try:
        price = price_for(acc, p, v)
    except currency.RateUnavailable as e:
        errors.append(str(e))
    images = product_images(p, v)
    if not images:
        if p.image_is_sample or any(im.is_sample for im in p.images.all()):
            errors.append("Namunaviy (AI) rasm marketpleysga yuborilmaydi — mahsulotning haqiqiy suratini yuklang")
        else:
            errors.append("Mahsulot rasmi yo'q")
    mapping = CategoryMapping.objects.filter(category=p.category, marketplace=acc.marketplace).first()
    if not mapping:
        errors.append(f"«{pick(p.category.name, 'uz')}» kategoriyasi {acc.get_marketplace_display()} kategoriyasiga moslanmagan")
    if acc.marketplace in NEEDS_DIMS and None in (p.weight_kg, p.length_cm, p.width_cm, p.height_cm):
        errors.append("Qadoq og'irligi va o'lchamlari (uzunlik, kenglik, balandlik) kiritilmagan")
    barcode = (v.barcode if v is not None and v.barcode else "") or (p.barcode if v is None else "") \
        or (listing.external_meta or {}).get("barcode", "")
    ctx = {"lang": lang, "name": name, "spec": spec, "description": description, "barcode": barcode,
           "attrs": attrs_all, "defs": defs, "info": info}
    attrs = []
    if mapping:
        for am in mapping.attributes.all():
            val, val_id = attribute_value(am, p, ctx, v)
            if val in (None, "", []) and not val_id:
                if am.required:
                    errors.append(f"Majburiy xususiyat to'ldirilmagan: {am.name}")
                continue
            if am.is_dictionary and not val_id:
                vals = val if isinstance(val, list) else [val]
                ids, names, missing = [], [], []
                for one in vals:
                    vm = _value_lookup(am, one, ctx)
                    if vm:
                        ids.append(vm.external_value_id)
                        names.append(vm.external_value or str(one))
                    else:
                        missing.append(str(one))
                if missing and am.required:
                    errors.append(f"«{am.name}» uchun «{', '.join(missing)}» qiymati lug'atda moslanmagan")
                    continue
                if not ids:
                    continue
                val, val_id = (names, ids) if am.multi and len(ids) > 1 else (names[0], ids[0])
            elif isinstance(val, list):
                val = val if am.multi else ", ".join(str(x) for x in val)
            attrs.append({"id": am.external_id, "value": val, "value_id": val_id, "multi": am.multi,
                          "type": "number" if (am.value_type or "").lower() in ("number", "numeric", "decimal", "integer") else "string"})
    if errors:
        return None, errors
    return ProductPayload(
        listing_id=listing.pk, offer_id=listing.offer_id, name=title, description=description, price=price,
        currency=acc.currency, images=images, category_id=mapping.external_id, type_id=mapping.external_type_id,
        attributes=attrs, barcode=barcode, brand=p.brand,
        country=p.country, weight_kg=p.weight_kg, length_cm=p.length_cm, width_cm=p.width_cm,
        height_cm=p.height_cm, vat=(acc.options or {}).get("vat", ""), external_id=listing.external_id,
        external_sku=listing.external_sku, external_meta=listing.external_meta or {},
        group_id=p.sku if v is not None else "", ikpu=p.ikpu,
    ), []


def _value_lookup(am, one, ctx):
    """Qiymat moslamasi: avval kod bo'yicha ("qora"), keyin nomi bo'yicha ("Черный" / "Qora")."""
    vm = am.value_map.filter(our_value__iexact=str(one)).first()
    d = ctx["defs"].get(am.field) if am.source == AttributeMapping.SRC_ATTR else None
    if vm is None and d is not None and d.type == AttributeDef.T_ENUM:
        for lang in ("ru", "uz"):
            vm = am.value_map.filter(our_value__iexact=d.option_name(one, lang)).first()
            if vm:
                break
    return vm


def attribute_value(am: AttributeMapping, p, ctx, variant=None):
    """-> (qiymat, lug'at_id). attr manbasida enum qiymati — AttributeValueMap'dagi our_value (variant kodi)."""
    if am.source == AttributeMapping.SRC_CONST:
        return am.value, am.value_id
    if am.source == AttributeMapping.SRC_PRODUCT:
        return (ctx["info"].attributes or {}).get(f"{am.mapping.marketplace}:{am.external_id}"), ""
    if am.source == AttributeMapping.SRC_ATTR:
        d = ctx["defs"].get(am.field)
        val = ctx["attrs"].get(am.field)
        if val in (None, "", []):
            return None, ""
        if d is None:
            return val, ""
        if d.type == AttributeDef.T_ENUM:
            vals = val if isinstance(val, list) else [val]
            if am.is_dictionary:
                return (vals if len(vals) > 1 else vals[0]), ""
            names = [d.option_name(x, ctx["lang"]) for x in vals]
            return (names if am.multi else ", ".join(names)), ""
        if d.type == AttributeDef.T_BOOL:
            yes = val in (True, "true", "1", 1)
            if am.is_dictionary:
                return ("true" if yes else "false"), ""
            return ({"ru": "Да", "uz": "Ha"}.get(ctx["lang"], "Да") if yes else {"ru": "Нет", "uz": "Yo'q"}.get(ctx["lang"], "Нет")), ""
        return (val if not isinstance(val, list) else ", ".join(str(x) for x in val)), ""
    f = am.field
    num = lambda x: str(x) if x is not None else None  # noqa: E731
    return {
        "name": ctx["name"], "spec": ctx["spec"], "description": ctx["description"], "unit": p.unit,
        "sku": variant.sku if variant is not None else p.sku, "group": p.sku,
        "brand": p.brand, "country": p.country, "barcode": ctx["barcode"], "ikpu": p.ikpu,
        "weight_kg": num(p.weight_kg), "length_cm": num(p.length_cm), "width_cm": num(p.width_cm),
        "height_cm": num(p.height_cm),
    }.get(f), ""


# ---------------------------------------------------------- public actions
def ensure_listings(product, account) -> list:
    """Mahsulot uchun kabinetdagi listinglar: variantli bo'lsa — har bir faol variantga bittadan (offer_id = variant SKU)."""
    out = []
    variants = list(product.variants.filter(is_active=True)) if product.has_variants else []
    if variants:
        for v in variants:
            li, _ = L.objects.get_or_create(product=product, variant=v, account=account, defaults={"offer_id": v.sku})
            out.append(li)
    else:
        li, _ = L.objects.get_or_create(product=product, variant=None, account=account, defaults={"offer_id": product.sku})
        out.append(li)
    return out


def card_checks(p) -> list:
    """Marketplace'dan qat'i nazar kartochka to'liqligi: [{key, ok, label, weight}]."""
    from market.models import AttributeDef
    defs = list(AttributeDef.objects.filter(category_id=p.category_id))
    variants = list(p.variants.filter(is_active=True)) if p.has_variants else []
    imgs = [im for im in p.images.all()]
    real = [im for im in imgs if not im.is_sample]
    attrs = p.attributes or {}
    req_plain = [d for d in defs if d.required and not d.variant]
    missing = [pick(d.name, "uz") for d in req_plain if attrs.get(d.code) in (None, "", [])]
    axes = [d for d in defs if d.variant]
    var_missing = [v.sku for v in variants for d in axes if d.required and (v.attributes or {}).get(d.code) in (None, "")]
    if variants:
        no_bc = [v.sku for v in variants if not v.barcode]
    else:
        no_bc = [] if p.barcode else [p.sku]
    no_price = [v.sku for v in variants if v.effective_price is None] if variants else ([] if p.price is not None else [p.sku])
    desc = pick(p.description, "ru") or pick(p.description, "uz")
    return [
        {"key": "images", "ok": len(real) >= 1, "weight": 3,
         "label": f"Haqiqiy suratlar: {len(real)} ta" + (" (tavsiya: 3+)" if len(real) < 3 else "")
         + (" — namunaviy (AI) rasm marketpleysga yuborilmaydi" if imgs and not real else "")},
        {"key": "description", "ok": len(desc or "") >= 50, "weight": 1, "label": "Tavsif (kamida 50 belgi)"},
        {"key": "price", "ok": not no_price, "weight": 2, "label": "Narx" + (f": yo'q — {', '.join(no_price[:5])}" if no_price else "")},
        {"key": "brand", "ok": bool(p.brand), "weight": 1, "label": "Brend / ishlab chiqaruvchi"},
        {"key": "ikpu", "ok": bool(p.ikpu) and p.ikpu_confirmed, "weight": 2,
         "label": "IKPU (MXIK) kodi" + (" — tavsiya, tasdiqlang" if p.ikpu and not p.ikpu_confirmed else "")},
        {"key": "barcode", "ok": not no_bc, "weight": 1,
         "label": "Shtrix-kod (EAN-13)" + (f": yo'q — {', '.join(no_bc[:5])}" if no_bc else "")},
        {"key": "dims", "ok": None not in (p.weight_kg, p.length_cm, p.width_cm, p.height_cm), "weight": 2,
         "label": "Qadoq og'irligi va o'lchamlari"},
        {"key": "attributes", "ok": not missing, "weight": 3,
         "label": "Majburiy xususiyatlar" + (f": {', '.join(missing)}" if missing else "")},
        {"key": "variants", "ok": not var_missing, "weight": 1,
         "label": "Variantlar" + (f": o'q qiymati yo'q — {', '.join(var_missing[:5])}" if var_missing else "")},
    ]


def readiness(p) -> dict:
    """Mahsulot kartochkasining to'liqligi va har bir kabinet bo'yicha joylashga tayyorligi (tashqi so'rovsiz)."""
    checks = card_checks(p)
    total = sum(c["weight"] for c in checks)
    score = round(100 * sum(c["weight"] for c in checks if c["ok"]) / total) if total else 0
    mps = []
    accounts = MarketplaceAccount.objects.filter(seller_id=p.seller_id, is_enabled=True)
    variants = list(p.variants.filter(is_active=True)) if p.has_variants else [None]
    existing = {(li.account_id, li.variant_id): li for li in p.mp_listings.select_related("variant")}
    for acc in accounts:
        caps = capabilities(acc)
        errors, listings = [], []
        for v in variants:
            li = existing.get((acc.pk, v.pk if v else None)) or L(product=p, variant=v, account=acc,
                                                                    offer_id=v.sku if v else p.sku)
            if li.pk:
                listings.append({"id": li.pk, "offer_id": li.offer_id, "status": li.status, "error": li.last_error})
            if CAP_CREATE in caps:
                _, errs = build_payload(li)
                errors += [e for e in errs if e not in errors]
            elif not li.external_sku:
                msg = f"{acc.get_marketplace_display()}: kartochkani kabinetda yarating, keyin «Kabinetdan bog'lash»"
                if msg not in errors:
                    errors.append(msg)
        mps.append({"account": acc.pk, "marketplace": acc.marketplace, "name": str(acc), "status": acc.status,
                    "can_create": CAP_CREATE in caps, "ok": not errors, "errors": errors, "listings": listings})
    return {"score": score, "checks": checks, "marketplaces": mps}


def notify_products_changed(product_ids, delay=20):
    """Qoldiq/narx o'zgardi → barcha kabinetlardagi faol listinglar sinxronlanadi (debounce)."""
    ids = list(product_ids)
    if not ids:
        return
    rows = (L.objects.filter(product_id__in=ids, status=L.ST_ACTIVE, account__auto_sync=True,
                             account__is_enabled=True, account__status=MarketplaceAccount.ST_ACTIVE)
            .values_list("account_id", "id"))
    by_acc = {}
    for acc_id, lid in rows:
        by_acc.setdefault(acc_id, []).append(lid)
    for acc_id, lids in by_acc.items():
        enqueue("sync_listings", account=MarketplaceAccount(pk=acc_id), payload={"ids": lids},
                delay=delay, dedupe=f"sync:{acc_id}")


def request_publish(listings):
    by_acc = {}
    for li in listings:
        by_acc.setdefault(li.account_id, []).append(li.pk)
    jobs = []
    for acc_id, ids in by_acc.items():
        jobs.append(enqueue("publish", account=MarketplaceAccount(pk=acc_id), payload={"ids": ids},
                            dedupe=f"publish:{acc_id}"))
    return jobs


# ------------------------------------------------------------------ handlers
@handler("check_account")
def h_check_account(job):
    acc = job.account
    res = get_client(acc, job=job).check_credentials()
    acc.last_checked_at = timezone.now()
    acc.meta = {**(acc.meta or {}), **(res.get("meta") or {})}
    acc.key_expires_at = res.get("expires_at")
    for f in ("cabinet_id", "campaign_id", "warehouse_id"):
        if res.get(f) and not getattr(acc, f):
            setattr(acc, f, str(res[f]))
    acc.status = MarketplaceAccount.ST_ACTIVE if res.get("ok") else MarketplaceAccount.ST_INVALID
    acc.status_message = redact(res.get("message") or "")[:500]
    # faqat tekshiruv natijasi yoziladi — shu payt foydalanuvchi o'zgartirgan maydonlar (kalit, sozlamalar) buzilmaydi
    acc.save(update_fields=["last_checked_at", "meta", "key_expires_at", "cabinet_id", "campaign_id", "warehouse_id",
                            "status", "status_message"])
    if acc.status == MarketplaceAccount.ST_ACTIVE and CAP_LINK in capabilities(acc) and acc.cabinet_id:
        enqueue("fetch_remote", account=acc, dedupe=f"remote:{acc.pk}")
    return {"ok": res.get("ok"), "message": acc.status_message}


@handler("fetch_categories")
def h_fetch_categories(job):
    acc = job.account
    cats = get_client(acc, job=job).fetch_categories()
    mp = acc.marketplace
    seen = set()
    objs = []
    for c in cats:
        key = (c["id"], c.get("type_id") or "")
        if key in seen:
            continue
        seen.add(key)
        objs.append(ExternalCategory(marketplace=mp, external_id=c["id"], type_id=c.get("type_id") or "",
                                     name=c["name"][:255], path=c.get("path", "")[:1000],
                                     search=(c.get("path") or c["name"]).lower()[:1000]))
    with transaction.atomic():
        ExternalCategory.objects.filter(marketplace=mp).delete()
        ExternalCategory.objects.bulk_create(objs, batch_size=1000)
    return {"count": len(objs)}


@handler("fetch_attributes")
def h_fetch_attributes(job):
    mapping = CategoryMapping.objects.get(pk=job.payload["mapping_id"])
    attrs = get_client(job.account, job=job).fetch_category_attributes(mapping.external_id, mapping.external_type_id)
    n = 0
    for a in attrs:
        am, created = AttributeMapping.objects.get_or_create(mapping=mapping, external_id=a["id"], defaults={
            "name": (a.get("name") or "")[:255], "required": a.get("required", False)})
        am.name = (a.get("name") or am.name)[:255]
        am.required = bool(a.get("required"))
        am.is_dictionary = bool(a.get("dictionary"))
        am.multi = bool(a.get("multi"))
        am.value_type = str(a.get("type") or "")[:32]
        am.unit = str(a.get("unit") or "")[:64]
        am.values = a.get("values") or []
        am.save()
        n += 1
    from .automap import auto_map
    auto = auto_map(mapping)
    return {"count": n, "required": sum(1 for a in attrs if a.get("required")), "auto": auto}


@handler("search_values")
def h_search_values(job):
    mapping = CategoryMapping.objects.get(pk=job.payload["mapping_id"])
    vals = get_client(job.account, job=job).search_attribute_values(
        mapping.external_id, mapping.external_type_id, job.payload["attribute_id"], job.payload.get("query", ""))
    return {"values": vals[:100]}


@handler("fetch_remote")
def h_fetch_remote(job):
    """Kabinetdagi mavjud kartochkalarni olib, bizdagi mahsulotlarga avtomatik bog'lash (SKU/shtrix-kod)."""
    acc = job.account
    items = get_client(acc, job=job).fetch_remote_products()
    acc.meta = {**(acc.meta or {}), "remote_products": items[:3000], "remote_fetched_at": timezone.now().isoformat()}
    acc.save(update_fields=["meta"])
    # SKU yoki shtrix-kod bo'yicha: (mahsulot, variant | None)
    products = {}
    barcodes = {}
    for p in Product.objects.filter(seller=acc.seller):
        products[p.sku.lower()] = (p, None)
        if p.barcode:
            barcodes[p.barcode] = (p, None)
    for v in ProductVariant.objects.filter(product__seller=acc.seller).select_related("product"):
        products[v.sku.lower()] = (v.product, v)
        if v.barcode:
            barcodes[v.barcode] = (v.product, v)
    linked = 0
    for it in items:
        p, v = products.get((it.get("offer_id") or "").lower()) or barcodes.get(it.get("barcode")) or (None, None)
        if not p:
            continue
        same = {"product": p, "variant": v}
        if L.objects.filter(account=acc, external_sku=it["external_sku"]).exclude(**same).exists():
            continue
        offer = it.get("offer_id") or (v.sku if v else p.sku)
        if L.objects.filter(account=acc, offer_id=offer).exclude(**same).exists():
            continue
        li, _ = L.objects.get_or_create(product=p, variant=v, account=acc, defaults={"offer_id": offer})
        if li.external_sku and li.external_sku != it["external_sku"]:
            continue
        link_listing(li, it)
        linked += 1
    return {"remote": len(items), "linked": linked}


def link_listing(li: L, it: dict):
    li.external_id = it.get("external_id") or ""
    li.external_sku = it.get("external_sku") or ""
    li.external_meta = {**(li.external_meta or {}), **(it.get("meta") or {})}
    li.status, li.last_error, li.last_synced_at = L.ST_ACTIVE, "", timezone.now()
    li.save()
    if li.account.auto_sync:
        enqueue("sync_listings", account=li.account, payload={"ids": [li.pk]}, delay=5, dedupe=f"sync:{li.account_id}")


@handler("publish")
def h_publish(job):
    acc = job.account
    caps = capabilities(acc)
    listings = list(L.objects.filter(pk__in=job.payload.get("ids", []), account=acc)
                    .select_related("product__category", "product__seller", "account", "variant__image")
                    .prefetch_related("product__images"))
    if CAP_CREATE not in caps:
        for li in listings:
            if not li.external_sku:
                li.set_error(f"{acc.get_marketplace_display()} API orqali kartochka yaratib bo'lmaydi: kartochkani kabinetda "
                             "yarating, keyin «Kabinetdan bog'lash» tugmasini bosing", status=L.ST_DRAFT)
                li.save()
        return {"skipped": len(listings)}
    payloads = []
    for li in listings:
        payload, errors = build_payload(li)
        if errors:
            li.set_error("; ".join(errors))
            li.save()
        else:
            payloads.append(payload)
    if not payloads:
        return {"sent": 0}
    res = get_client(acc, job=job).upsert_products(payloads)
    by_offer = {li.offer_id: li for li in listings}
    retry, sent = [], 0
    for offer_id, r in (res.get("results") or {}).items():
        li = by_offer.get(offer_id)
        if not li:
            continue
        if r.get("barcode"):
            li.external_meta = {**(li.external_meta or {}), "barcode": r["barcode"]}
            h = li.holder
            if not h.barcode:
                type(h).objects.filter(pk=h.pk).update(barcode=r["barcode"])
        if r.get("status") == "retry":
            retry.append(li.pk)
            li.last_error = r.get("error", "")
        elif r.get("status") == "error":
            li.set_error(r.get("error") or "xato")
        else:
            li.status, li.last_error = L.ST_PENDING, ""
            li.task_id = r.get("task_id") or res.get("task_id") or ""
            li.pushed_price, li.pushed_currency = next((pl.price for pl in payloads if pl.offer_id == offer_id), None), acc.currency
            sent += 1
        li.last_synced_at = timezone.now()
        li.save()
    retry_n = int(job.payload.get("retry_n", 0))
    if retry and retry_n < 3:
        enqueue("publish", account=acc, payload={"ids": retry, "retry_n": retry_n + 1}, delay=30 * (retry_n + 1))
    elif retry:
        L.objects.filter(pk__in=retry).update(status=L.ST_ERROR, last_synced_at=timezone.now())
    if sent:
        enqueue("poll_status", account=acc, delay=60, dedupe=f"poll:{acc.pk}")
    return {"sent": sent, "retry": len(retry)}


@handler("poll_status")
def h_poll_status(job):
    acc = job.account
    qs = L.objects.filter(account=acc, status=L.ST_PENDING)
    if job.payload.get("ids"):
        qs = L.objects.filter(account=acc, pk__in=job.payload["ids"])
    listings = list(qs.select_related("product", "account", "variant__image").prefetch_related("product__images"))
    acc.status_polled_at = timezone.now()
    acc.save(update_fields=["status_polled_at"])
    if not listings:
        return {"checked": 0}
    client = get_client(acc, job=job)
    res = client.get_product_status([ref(li) for li in listings])
    activated = []
    for li in listings:
        r = res.get(li.offer_id)
        if not r:
            continue
        if r.get("external_id"):
            li.external_id = r["external_id"]
        if r.get("external_sku"):
            li.external_sku = r["external_sku"]
        if r.get("external_meta"):
            li.external_meta = {**(li.external_meta or {}), **r["external_meta"]}
        status = r.get("status")
        if status in ("error", "rejected"):
            li.set_error(r.get("error") or status, status=L.ST_REJECTED if status == "rejected" else L.ST_ERROR)
        elif status == "active":
            was = li.status
            li.status, li.last_error = L.ST_ACTIVE, r.get("error") or ""
            if was != L.ST_ACTIVE:
                activated.append(li.pk)
            # WB: rasm kartochka yaratilgandan keyin (nmID bilan) yuklanadi
            imgs = product_images(li.product, li.variant) if acc.marketplace == "wb" else []
            if acc.marketplace == "wb" and li.external_id and not (li.external_meta or {}).get("photos") \
                    and not (li.external_meta or {}).get("media_sent") and imgs:
                try:
                    client.upload_media(li.external_id, imgs[:30])
                    li.external_meta = {**li.external_meta, "media_sent": True}
                except MarketplaceError as e:
                    li.last_error = f"Rasm yuklanmadi: {e}"
        else:
            li.last_error = r.get("error") or ""
        li.last_synced_at = timezone.now()
        li.save()
    if activated:
        enqueue("sync_listings", account=acc, payload={"ids": activated, "force": True}, dedupe=f"sync:{acc.pk}")
    if L.objects.filter(account=acc, status=L.ST_PENDING).exists():
        enqueue("poll_status", account=acc, delay=settings.MP_STATUS_INTERVAL, dedupe=f"poll:{acc.pk}")
    return {"checked": len(listings), "activated": len(activated)}


@handler("sync_listings")
def h_sync_listings(job):
    """Narx va qoldiqni hisoblab, faqat o'zgarganlarini yuboradi (force — hammasini)."""
    acc = MarketplaceAccount.objects.get(pk=job.account_id)
    if not acc.is_usable:
        return {"skipped": "account not active"}
    caps = capabilities(acc)
    qs = L.objects.filter(account=acc, status=L.ST_ACTIVE).select_related("product__seller", "account", "variant")
    ids = job.payload.get("ids")
    if ids:
        qs = qs.filter(pk__in=ids)
    force = job.payload.get("force", False)
    listings = list(qs)
    client = get_client(acc, job=job)
    own = own_reserved(acc)
    price_refs, stock_refs = [], []
    for li in listings:
        if CAP_PRICES in caps and listing_price(li) is not None:
            try:
                pr = price_for(acc, li.product, li.variant)
                if force or li.pushed_price != pr or li.pushed_currency != acc.currency:
                    price_refs.append(ref(li, price=pr))
            except currency.RateUnavailable as e:  # kurs bo'lmasa ham qoldiq yuborilaversin
                li.last_error = str(e)
                li.save(update_fields=["last_error"])
        if CAP_STOCKS in caps:
            st = listing_stock(li, own)
            if force or li.pushed_stock != st:
                stock_refs.append(ref(li, stock=st))
    by_id = {li.pk: li for li in listings}
    now = timezone.now()
    errors = 0
    if price_refs:
        res = _safe_batch(client.update_prices, price_refs)
        for r in price_refs:
            li, err = by_id[r.listing_id], res.get(r.offer_id)
            if err:
                li.last_error, errors = f"Narx: {redact(err)}"[:2000], errors + 1
            else:
                li.pushed_price, li.pushed_currency, li.price_synced_at = r.price, acc.currency, now
    if stock_refs:
        res = _safe_batch(client.update_stocks, stock_refs)
        for r in stock_refs:
            li, err = by_id[r.listing_id], res.get(r.offer_id)
            if err:
                li.last_error, errors = f"Qoldiq: {redact(err)}"[:2000], errors + 1
            else:
                li.pushed_stock, li.stock_synced_at = r.stock, now
    for li in {by_id[r.listing_id] for r in price_refs + stock_refs}:
        li.last_synced_at = now
        li.save()
    if not ids:
        acc.stock_synced_at = now
        acc.save(update_fields=["stock_synced_at"])
    return {"prices": len(price_refs), "stocks": len(stock_refs), "errors": errors}


def _safe_batch(fn, refs):
    """Narx xatosi qoldiqni to'xtatmasin (va aksincha): doimiy xato har bir listingga yoziladi.
    Vaqtinchalik xato (429/5xx) — butun vazifa qayta uriniladi."""
    from .clients.base import RetryableError
    try:
        return fn(refs)
    except RetryableError:
        raise
    except MarketplaceError as e:
        return {r.offer_id: str(e) for r in refs}


@handler("fetch_orders")
def h_fetch_orders(job):
    acc = MarketplaceAccount.objects.get(pk=job.account_id)
    first_sync = acc.orders_synced_at is None
    now = timezone.now()
    since = (acc.orders_synced_at - timedelta(hours=2)) if acc.orders_synced_at else now - timedelta(days=14)
    # Uzum/Ozon/WB ro'yxati yaratilgan sana bo'yicha — ochiq buyurtmalar holati kuzatilishi uchun oynani kengaytiramiz
    oldest_open = (O.objects.filter(account=acc, state__in=[O.S_NEW, O.S_PROCESSING, O.S_SHIPPED],
                                    ordered_at__isnull=False).order_by("ordered_at").values_list("ordered_at", flat=True).first())
    if oldest_open:
        since = min(since, oldest_open - timedelta(hours=1))
    since = max(since, now - timedelta(days=29))
    started = now
    orders = get_client(acc, job=job).fetch_orders(since)
    touched = set()
    new = 0
    for o in orders:
        with transaction.atomic():
            obj, created = O.objects.select_for_update().get_or_create(
                account=acc, external_id=o["external_id"], defaults={"items": []})
            new += int(created)
            obj.scheme = (o.get("scheme") or "")[:8]
            obj.status = (o.get("status") or "")[:64]
            obj.state = o.get("state") or O.S_NEW
            obj.items = resolve_items(acc, o.get("items") or [])
            obj.total = Decimal(str(o.get("total") or 0))
            obj.currency = (o.get("currency") or acc.currency or "")[:3]
            dt = o.get("ordered_at")
            obj.ordered_at = parse_datetime(dt) if isinstance(dt, str) else dt
            obj.raw = o.get("raw") or {}
            touched |= apply_order_stock(obj, historical=created and first_sync)
            obj.save()
    acc.orders_synced_at = started
    acc.save(update_fields=["orders_synced_at"])
    if touched:
        transaction.on_commit(lambda: notify_products_changed(touched, delay=5))
    return {"orders": len(orders), "new": new, "products": len(touched)}


def resolve_items(acc, items):
    lis = list(L.objects.filter(account=acc).values_list("offer_id", "external_sku", "product_id", "variant_id"))
    offers = {o: (pid, vid) for o, _, pid, vid in lis}
    skus = {e: (pid, vid) for _, e, pid, vid in lis if e}
    by_sku = {p.sku: (p.pk, None) for p in Product.objects.filter(seller=acc.seller).only("id", "sku")}
    by_sku.update({v.sku: (v.product_id, v.pk) for v in ProductVariant.objects.filter(product__seller=acc.seller)
                   .only("id", "sku", "product_id")})
    out = []
    for it in items:
        pid, vid = offers.get(it.get("offer_id")) or skus.get(it.get("external_sku")) or by_sku.get(it.get("offer_id")) \
            or (None, None)
        out.append({**it, "product_id": pid, "variant_id": vid})
    return out


def _qty_map(items) -> dict:
    out = {}
    for it in items or []:
        if it.get("product_id"):
            k = stock_key(it["product_id"], it.get("variant_id"))
            out[k] = out.get(k, 0) + int(it.get("qty") or 0)
    return out


def apply_order_stock(order: O, historical=False) -> set:
    """Marketplace buyurtmasi bizdagi qoldiqqa ta'sir qiladi (faqat FBS/DBS — FBO marketplace omboridan).

    none/released → reserved (yangi, yig'ilmoqda) → deducted (jo'natildi, yetkazildi); bekor → released.
    Band qilingan miqdor order.stock_items da saqlanadi va bo'shatish aynan shu bo'yicha qilinadi.
    Kabinet birinchi marta ulanganda kelgan yakunlangan buyurtmalar — "historical" (qoldiqqa tegmaydi).
    Qaytarilgan (returned) buyurtma qoldiqni avtomatik tiklamaydi — tovar qaytib kelganda muassasa o'zi kiritadi.
    """
    if order.scheme.upper() in ("FBO", "FBY", "FBW"):
        return set()
    cur = order.stock_state
    if cur == O.STOCK_HISTORICAL:
        return set()
    if historical and order.state not in RESERVE_STATES:
        order.stock_state = O.STOCK_HISTORICAL
        return set()
    if order.state in RESERVE_STATES:
        target = O.STOCK_RESERVED
    elif order.state in DEDUCT_STATES:
        target = O.STOCK_DEDUCTED
    elif order.state == O.S_CANCELLED:
        target = O.STOCK_RELEASED if cur == O.STOCK_RESERVED else cur
    else:  # returned va boshqalar
        target = cur
    if target == cur:
        return set()
    current = _qty_map(order.items)
    snap = {str(k): int(v) for k, v in (order.stock_items or {}).items()}
    d_reserved, d_stock, d_sold = {}, {}, {}
    if target == O.STOCK_RESERVED:
        d_reserved = current
        new_snap = current
    elif target == O.STOCK_DEDUCTED:
        if cur == O.STOCK_RESERVED:
            d_reserved = {k: -v for k, v in snap.items()}
        d_stock = {k: -v for k, v in current.items()}
        d_sold = current
        new_snap = {}
    else:  # released
        d_reserved = {k: -v for k, v in snap.items()}
        new_snap = {}
    keys = {*d_reserved, *d_stock, *d_sold}
    pids = {int(k) for k in keys if not k.startswith("v")}
    vids = {int(k[1:]) for k in keys if k.startswith("v")}
    touched = set()
    holders = [(str(p.pk), p) for p in Product.objects.select_for_update().filter(pk__in=pids)] + \
        [(f"v{v.pk}", v) for v in ProductVariant.objects.select_for_update().select_related("product").filter(pk__in=vids)]
    for k, h in holders:
        if h.stock is not None:
            h.reserved = max(h.reserved + d_reserved.get(k, 0), 0)
            h.stock = max(h.stock + d_stock.get(k, 0), 0)
        h.sold = max(h.sold + d_sold.get(k, 0), 0)
        type(h).objects.filter(pk=h.pk).update(reserved=h.reserved, stock=h.stock, sold=h.sold)
        if isinstance(h, ProductVariant):
            h.product.sync_from_variants()
            touched.add(h.product_id)
        else:
            touched.add(h.pk)
    order.stock_state = target
    order.stock_items = new_snap
    return touched


def release_account_reservations(account) -> set:
    """Kabinet o'chirilganda uning band buyurtmalari bo'shatiladi."""
    touched = set()
    with transaction.atomic():
        for o in O.objects.select_for_update().filter(account=account, stock_state=O.STOCK_RESERVED):
            o.state = O.S_CANCELLED
            touched |= apply_order_stock(o)
            o.save(update_fields=["state", "stock_state", "stock_items"])
    return touched


@handler("zero_stock")
def h_zero_stock(job):
    """Listing ImkonMarket'dan uzilganda marketplace'dagi qoldiq 0 qilinadi (sotuvda qolib ketmasin)."""
    acc = job.account
    if CAP_STOCKS not in capabilities(acc):
        return {"skipped": True}
    refs = [ListingRef(listing_id=0, offer_id=r["offer_id"], external_id=r.get("external_id", ""),
                       external_sku=r.get("external_sku", ""), external_meta=r.get("external_meta") or {}, stock=0)
            for r in job.payload.get("refs", [])]
    res = get_client(acc, job=job).update_stocks(refs) if refs else {}
    return {"errors": {k: v for k, v in res.items() if v}}


@handler("order_action")
def h_order_action(job):
    order = O.objects.select_related("account").get(pk=job.payload["order_id"])
    client = get_client(order.account, job=job)
    client.update_order_status(order, job.payload["action"], **(job.payload.get("kw") or {}))
    enqueue("fetch_orders", account=order.account, delay=10, dedupe=f"orders:{order.account_id}")
    return {"ok": True}


@handler("fetch_rates")
def h_fetch_rates(job):
    return {"count": currency.fetch_cbu_rates()}


# ---------------------------------------------------------------- scheduler
def schedule_periodic(now=None):
    """Worker har ~30 soniyada chaqiradi: vaqti kelgan davriy vazifalarni navbatga qo'yadi."""
    from .models import ExchangeRate, Job
    now = now or timezone.now()
    accs = MarketplaceAccount.objects.filter(is_enabled=True).exclude(credentials_enc="")
    recent_checks = set(Job.objects.filter(kind="check_account", created_at__gte=now - timedelta(minutes=10))
                        .values_list("account_id", flat=True))
    for acc in accs:
        caps = capabilities(acc)
        due = acc.status == MarketplaceAccount.ST_NEW or acc.last_checked_at is None or \
            acc.last_checked_at < now - timedelta(seconds=settings.MP_CHECK_INTERVAL)
        if due and acc.pk not in recent_checks and (acc.status != MarketplaceAccount.ST_INVALID or acc.last_checked_at is None):
            enqueue("check_account", account=acc, dedupe=f"check:{acc.pk}", max_attempts=3)
        if acc.status != MarketplaceAccount.ST_ACTIVE:
            continue
        if CAP_ORDERS in caps and (acc.orders_synced_at is None or
                                   acc.orders_synced_at < now - timedelta(seconds=settings.MP_ORDERS_INTERVAL)):
            enqueue("fetch_orders", account=acc, dedupe=f"orders:{acc.pk}")
        if acc.auto_sync and (acc.stock_synced_at is None or
                              acc.stock_synced_at < now - timedelta(seconds=settings.MP_STOCK_INTERVAL)):
            if L.objects.filter(account=acc, status=L.ST_ACTIVE).exists():
                enqueue("sync_listings", account=acc, dedupe=f"sync:{acc.pk}")
            else:
                MarketplaceAccount.objects.filter(pk=acc.pk).update(stock_synced_at=now)
        if L.objects.filter(account=acc, status=L.ST_PENDING).exists() and (
                acc.status_polled_at is None or acc.status_polled_at < now - timedelta(seconds=settings.MP_STATUS_INTERVAL)):
            enqueue("poll_status", account=acc, dedupe=f"poll:{acc.pk}")
    needs_rate = accs.filter(rate_source=MarketplaceAccount.RATE_CBU).exclude(currency="UZS").exists()
    if needs_rate and not ExchangeRate.objects.filter(date__gte=timezone.localdate() - timedelta(days=0)).exists():
        recent = Job.objects.filter(kind="fetch_rates", created_at__gte=now - timedelta(hours=3)).exists()
        if not recent:
            enqueue("fetch_rates", dedupe="rates", max_attempts=4)
    # eski yozuvlarni tozalash
    from .models import SyncLog
    Job.objects.filter(status=Job.DONE, finished_at__lt=now - timedelta(days=7)).delete()
    SyncLog.objects.filter(created_at__lt=now - timedelta(days=30)).delete()
