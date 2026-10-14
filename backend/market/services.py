"""Biznes-mantiq: ariza -> shartnoma -> to'lov -> jo'natish. Qoldiq (stock/reserved) shu yerda boshqariladi."""
from collections import defaultdict
from decimal import Decimal

from django.db import transaction
from django.db.models import F
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .contract_pdf import render_contract
from .models import Application, ApplicationItem, Contract, Payment, Product, ProductVariant, Seller, StatusLog


def _next_app_number():
    year = timezone.localdate().year
    last = Application.objects.filter(number__startswith=f"A-{year}-").order_by("-id").first()
    n = int(last.number.split("-")[-1]) + 1 if last else 1
    return f"A-{year}-{n:06d}"


def log(app, status, text="", user=None):
    StatusLog.objects.create(application=app, status=status, text=text[:255], user=user if user and user.is_authenticated else None)


BUYER_FIELDS = [
    "buyer_type", "buyer_name", "buyer_inn", "buyer_pinfl", "buyer_passport", "buyer_director", "buyer_phone",
    "buyer_email", "buyer_address", "buyer_region", "buyer_bank_name", "buyer_bank_account", "buyer_bank_mfo",
    "payment_method", "delivery_required", "delivery_address", "comment", "lang",
]


def validate_buyer(data):
    errors = {}
    bt = data.get("buyer_type")
    if bt not in ("b2b", "b2c"):
        errors["buyer_type"] = "b2b yoki b2c"
    if not (data.get("buyer_name") or "").strip():
        errors["buyer_name"] = "required"
    if not (data.get("buyer_phone") or "").strip():
        errors["buyer_phone"] = "required"
    if bt == "b2b" and not (data.get("buyer_inn") or "").strip():
        errors["buyer_inn"] = "required"
    if bt == "b2c" and not (data.get("buyer_pinfl") or "").strip():
        errors["buyer_pinfl"] = "required"
    pm = data.get("payment_method")
    if pm not in ("click", "payme", "bank"):
        errors["payment_method"] = "click | payme | bank"
    if data.get("delivery_required") and not (data.get("delivery_address") or "").strip():
        errors["delivery_address"] = "required"
    if errors:
        raise ValidationError(errors)


def _item_name(p, v):
    """Variantli pozitsiya nomi: "Kreslo — Qora, 48" (har bir tilda)."""
    if not v or not v.attributes:
        return p.name
    from .models import AttributeDef
    defs = {d.code: d for d in AttributeDef.objects.filter(category_id=p.category_id, code__in=list(v.attributes))}
    out = {}
    for lang, base in (p.name or {}).items():
        parts = [defs[k].display(val, lang) if k in defs else str(val) for k, val in v.attributes.items()]
        out[lang] = f"{base} — {', '.join(x for x in parts if x)}"
    return out


def _holder(it):
    """Qoldiq egasi: variant bo'lsa — variant, aks holda mahsulot (qulflangan holda)."""
    if it.variant_id:
        return ProductVariant.objects.select_for_update().get(pk=it.variant_id)
    return Product.objects.select_for_update().get(pk=it.product_id)


def _after_stock_change(holder):
    if isinstance(holder, ProductVariant):
        holder.product.sync_from_variants()


@transaction.atomic
def create_applications(data, user=None, agent: Seller | None = None):
    """Savatni sotuvchilar bo'yicha bo'lib arizalar yaratadi.

    agent berilsa (muassasa boshqa muassasa mahsuloti uchun rasmiylashtirsa) — ariza darhol
    shartnomaga aylanadi va shartnoma mahsulot egasi nomidan tuziladi.
    """
    validate_buyer(data)
    items = data.get("items") or []
    if not items:
        raise ValidationError({"items": "empty"})
    ids = [int(i["product"]) for i in items]
    products = {p.id: p for p in Product.objects.select_for_update().select_related("seller").filter(id__in=ids, is_active=True)}
    vids = [int(i["variant"]) for i in items if i.get("variant")]
    variants = {v.id: v for v in ProductVariant.objects.select_for_update().filter(id__in=vids, is_active=True)}
    by_seller = defaultdict(list)
    for it in items:
        p = products.get(int(it["product"]))
        if not p:
            raise ValidationError({"items": f"product {it['product']} not found"})
        v = None
        if it.get("variant"):
            v = variants.get(int(it["variant"]))
            if not v or v.product_id != p.id:
                raise ValidationError({"items": f"variant {it['variant']} not found"})
        elif p.has_variants:
            raise ValidationError({"items": f"{p.sku}: variant required", "code": "variant", "sku": p.sku})
        qty = int(it.get("qty") or 0)
        if qty < max(p.min_order, 1):
            raise ValidationError({"items": f"{p.sku}: min {p.min_order}"})
        h = v or p
        if h.available is not None and qty > h.available:
            raise ValidationError({"items": f"{h.sku}: available {h.available}", "code": "stock", "sku": h.sku, "available": h.available})
        base = v.effective_price if v else p.price
        # narxi kelishiladigan mahsulotda vositachi narxni kiritadi; narxi belgilangan mahsulot narxi o'zgarmaydi
        price = it.get("price") if (agent and base is None and it.get("price") not in (None, "")) else base
        by_seller[p.seller_id].append((p, v, qty, Decimal(str(price)) if price is not None else None))

    created = []
    for seller_id, rows in by_seller.items():
        seller = rows[0][0].seller
        app = Application(
            number=_next_app_number(), seller=seller, agent=agent if agent and agent.id != seller.id else None,
            created_by=user if user and user.is_authenticated else None,
            **{k: data.get(k) for k in BUYER_FIELDS if data.get(k) is not None},
        )
        app.lang = data.get("lang") or "uz"
        app.save()
        for p, v, qty, price in rows:
            ApplicationItem.objects.create(
                application=app, product=p, variant=v, name=_item_name(p, v), spec=p.spec, unit=p.unit, qty=qty, price=price,
            )
        app.recalc()
        app.save()
        log(app, "new", "Agent: " + str(agent) if agent else "", user)
        if agent:
            if app.has_unpriced:
                raise ValidationError({"items": "price required for made-to-order items"})
            confirm_application(app, {}, user=user)
        created.append(app)
    return created


def _notify_marketplaces(product_ids):
    """Band qilingan qoldiq marketplace'larga ham yetib borsin (integrations ilovasi, worker orqali)."""
    ids = list(product_ids)

    def go():
        from integrations.services import notify_products_changed
        notify_products_changed(ids)
    transaction.on_commit(go)


@transaction.atomic
def confirm_application(app: Application, payload: dict, user=None) -> Contract:
    """Sotuvchi arizani tasdiqlaydi: narx/miqdorni aniqlashtiradi, shartnoma yaratiladi, qoldiq band qilinadi."""
    app = Application.objects.select_for_update().get(pk=app.pk)
    if app.status in (Application.ST_CONTRACT, Application.ST_REJECTED, Application.ST_CANCELLED):
        raise ValidationError({"status": f"application is {app.status}"})
    upd = {int(i["id"]): i for i in payload.get("items", [])}
    for it in app.items.select_related("product").select_for_update():
        u = upd.get(it.id)
        if u:
            if u.get("qty") is not None:
                it.qty = int(u["qty"])
            if u.get("price") not in (None, ""):
                it.price = Decimal(str(u["price"]))
            it.save()
    app.recalc()
    if app.has_unpriced:
        raise ValidationError({"items": "set price for all items"})
    # qoldiqni band qilish
    for it in app.items.select_related("product"):
        h = _holder(it)
        if h.available is not None:
            if it.qty > h.available:
                raise ValidationError({"items": f"{h.sku}: available {h.available}"})
            type(h).objects.filter(pk=h.pk).update(reserved=F("reserved") + it.qty)
            _after_stock_change(h)
    _notify_marketplaces([it.product_id for it in app.items.all()])

    def _int(key, default, lo, hi):
        try:
            v = int(payload.get(key) if payload.get(key) not in (None, "") else default)
        except (TypeError, ValueError):
            raise ValidationError({key: "number"})
        if not lo <= v <= hi:
            raise ValidationError({key: f"{lo}..{hi}"})
        return v

    prepay = _int("prepayment_percent", 100, 0, 100)
    pay_days = _int("payment_days", 10, 0, 365)
    del_days = _int("delivery_days", 15, 0, 365)
    delivery_cost = Decimal(str(payload.get("delivery_cost") or 0))
    if delivery_cost < 0:
        raise ValidationError({"delivery_cost": ">= 0"})
    app.status = Application.ST_CONTRACT
    if payload.get("seller_comment"):
        app.seller_comment = payload["seller_comment"]
    app.save()
    b2b = app.buyer_type == Application.B2B
    contract = Contract.objects.create(
        application=app,
        number=app.seller.next_contract_number(),
        seller=app.seller,
        agent=app.agent,
        buyer_type=app.buyer_type,
        payment_method=app.payment_method,
        lang=payload.get("lang") or app.lang,
        total=app.total,
        delivery_cost=delivery_cost,
        prepayment_percent=prepay if b2b else 100,
        payment_days=pay_days,
        delivery_days=del_days,
    )
    render_contract(contract)
    log(app, "contract", contract.number, user)
    return contract


@transaction.atomic
def reject_application(app, reason, user=None):
    if app.status == Application.ST_CONTRACT:
        raise ValidationError({"status": "contract exists — cancel the contract"})
    app.status = Application.ST_REJECTED
    app.seller_comment = reason or app.seller_comment
    app.save()
    log(app, "rejected", reason or "", user)


def _refresh_contract_status(c: Contract):
    if c.status in (Contract.ST_CANCELLED, Contract.ST_SHIPPED, Contract.ST_DONE):
        return
    need = c.grand_total * Decimal(c.prepayment_percent) / Decimal(100)
    if c.paid_amount >= need and c.paid_amount > 0:
        c.status = Contract.ST_PAID


@transaction.atomic
def register_payment(contract: Contract, amount, method, *, document_no="", note="", is_demo=False,
                     user=None, payment: Payment | None = None) -> Payment:
    c = Contract.objects.select_for_update().get(pk=contract.pk)
    amount = Decimal(str(amount))
    if amount <= 0:
        raise ValidationError({"amount": "must be > 0"})
    if payment is None:
        payment = Payment.objects.create(contract=c, method=method, amount=amount, is_demo=is_demo,
                                         document_no=document_no, note=note)
    payment.status = Payment.ST_PAID
    payment.paid_at = timezone.now()
    payment.save()
    c.paid_amount = sum((p.amount for p in c.payments.filter(status=Payment.ST_PAID)), Decimal("0"))
    _refresh_contract_status(c)
    c.save()
    log(c.application, "payment", f"{method}: {amount}{' (DEMO)' if is_demo else ''}", user)
    return payment


@transaction.atomic
def ship_contract(contract: Contract, user=None):
    c = Contract.objects.select_for_update().get(pk=contract.pk)
    if c.status not in (Contract.ST_PAID, Contract.ST_ACTIVE):
        raise ValidationError({"status": f"contract is {c.status}"})
    if c.buyer_type == "b2c" and c.status != Contract.ST_PAID:
        raise ValidationError({"status": "b2c requires payment before shipping"})
    for it in c.application.items.all():
        h = _holder(it)
        if h.stock is not None:
            h.stock = max(h.stock - it.qty, 0)
            h.reserved = max(h.reserved - it.qty, 0)
        h.sold += it.qty
        h.save(update_fields=["stock", "reserved", "sold"])
        _after_stock_change(h)
    c.status = Contract.ST_SHIPPED
    c.shipped_at = timezone.now()
    c.save()
    log(c.application, "shipped", "", user)


@transaction.atomic
def complete_contract(contract: Contract, user=None):
    c = Contract.objects.select_for_update().get(pk=contract.pk)
    if c.status != Contract.ST_SHIPPED:
        raise ValidationError({"status": "ship first"})
    c.status = Contract.ST_DONE
    c.save()
    log(c.application, "done", "", user)


@transaction.atomic
def cancel_contract(contract: Contract, reason="", user=None):
    c = Contract.objects.select_for_update().get(pk=contract.pk)
    if c.status in (Contract.ST_SHIPPED, Contract.ST_DONE, Contract.ST_CANCELLED):
        raise ValidationError({"status": f"contract is {c.status}"})
    for it in c.application.items.all():
        h = _holder(it)
        if h.stock is not None:
            h.reserved = max(h.reserved - it.qty, 0)
            h.save(update_fields=["reserved"])
            _after_stock_change(h)
    c.status = Contract.ST_CANCELLED
    c.save()
    app = c.application
    app.status = Application.ST_CANCELLED
    app.save()
    log(app, "cancelled", reason, user)


def delete_products(products) -> dict:
    """Mahsulotlarni o'chirish. Ariza/shartnomada yoki marketplace buyurtmasida ishlatilgani — arxivlanadi
    (sotuvdan olinadi, kabinetda ko'rinmaydi, tarix saqlanadi), qolganlari butunlay o'chiriladi (rasmlari bilan).
    Faol band (reserved) qoldig'i bor mahsulot o'chirilmaydi — avval shartnomani yakunlang yoki bekor qiling."""
    from integrations.models import MarketplaceListing
    from integrations.jobs import enqueue
    deleted, archived, blocked = [], [], []
    for p in products:
        if p.reserved or any(v.reserved for v in p.variants.all()):
            blocked.append({"id": p.id, "sku": p.sku, "reason": "band qilingan qoldiq bor (ochiq shartnoma yoki buyurtma)"})
            continue
        # marketplace'larda sotuvda qolib ketmasin — qoldiq 0 qilinadi (kartochka marketplace'da qoladi)
        for li in MarketplaceListing.objects.filter(product=p).select_related("account"):
            if li.status == MarketplaceListing.ST_ACTIVE and li.account.is_usable:
                enqueue("zero_stock", account=li.account, payload={"refs": [{
                    "offer_id": li.offer_id, "external_id": li.external_id, "external_sku": li.external_sku,
                    "external_meta": li.external_meta}]})
        used = ApplicationItem.objects.filter(product=p).exists() or _in_mp_orders(p.id)
        with transaction.atomic():
            if used:
                MarketplaceListing.objects.filter(product=p).delete()
                Product.objects.filter(pk=p.pk).update(is_active=False, deleted_at=timezone.now())
                archived.append({"id": p.id, "sku": p.sku})
            else:
                for im in p.images.all():
                    im.image.delete(save=False)
                MarketplaceListing.objects.filter(product=p).delete()
                pid, sku = p.id, p.sku
                p.delete()
                deleted.append({"id": pid, "sku": sku})
    return {"deleted": deleted, "archived": archived, "blocked": blocked}


def _in_mp_orders(pid) -> bool:
    from integrations.models import MarketplaceOrder
    if _json_contains():
        return MarketplaceOrder.objects.filter(items__contains=[{"product_id": pid}]).exists()
    return any(it.get("product_id") == pid for items in MarketplaceOrder.objects.values_list("items", flat=True)
               for it in (items or []))


def _json_contains():
    from django.db import connection
    return connection.vendor == "postgresql"
