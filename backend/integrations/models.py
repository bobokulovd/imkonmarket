"""Marketplace integratsiyasi.

ImkonMarket — faqat texnik platforma: muassasa o'z STIR'i bilan o'z kabinetida sotadi, pul to'g'ridan-to'g'ri
muassasaga tushadi. Biz kalitni (shifrlangan) saqlaymiz, kartochka joylaymiz, narx/qoldiqni sinxronlaymiz,
buyurtmalarni tortamiz.
"""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from market.models import Category, Product, Seller

from . import crypto
from .redact import mask

MARKETPLACES = [
    ("uzum", "Uzum Market"),
    ("ozon", "Ozon"),
    ("yandex", "Yandex Market"),
    ("wb", "Wildberries"),
]
MP_NAMES = dict(MARKETPLACES)

# Har bir marketplace uchun kalit maydonlari (formada so'raladi). Birinchisi — asosiy kalit (oxirgi 4 belgisi ko'rsatiladi).
CREDENTIAL_FIELDS = {
    "uzum": ["api_key"],
    "ozon": ["api_key"],     # Client-Id maxfiy emas — cabinet_id da
    "yandex": ["api_key"],
    "wb": ["api_key"],
}


class MarketplaceAccount(models.Model):
    ST_NEW, ST_ACTIVE, ST_INVALID, ST_DISABLED = "new", "active", "invalid", "disabled"
    STATUSES = [(ST_NEW, "Tekshirilmoqda"), (ST_ACTIVE, "Faol"), (ST_INVALID, "Kalit yaroqsiz"), (ST_DISABLED, "O'chirilgan")]
    RATE_CBU, RATE_MANUAL = "cbu", "manual"
    RATE_SOURCES = [(RATE_CBU, "Markaziy bank kursi (cbu.uz)"), (RATE_MANUAL, "Qo'lda kiritilgan kurs")]
    CURRENCIES = [("UZS", "so'm"), ("RUB", "rubl")]

    seller = models.ForeignKey(Seller, on_delete=models.CASCADE, related_name="mp_accounts")
    marketplace = models.CharField(max_length=16, choices=MARKETPLACES)
    title = models.CharField("Nomi (ichki)", max_length=128, blank=True)
    # Uzum: shopId · Ozon: Client-Id · Yandex: businessId · WB: —
    cabinet_id = models.CharField("Kabinet / do'kon ID", max_length=64, blank=True)
    campaign_id = models.CharField("Kampaniya (magazin) ID — Yandex", max_length=64, blank=True)
    warehouse_id = models.CharField("Ombor ID (FBS)", max_length=64, blank=True)
    credentials_enc = models.TextField(blank=True, editable=False)
    secret_last4 = models.CharField(max_length=4, blank=True, editable=False)
    status = models.CharField(max_length=12, choices=STATUSES, default=ST_NEW)
    status_message = models.CharField(max_length=500, blank=True)
    last_checked_at = models.DateTimeField(null=True, blank=True)
    key_expires_at = models.DateTimeField(null=True, blank=True)
    meta = models.JSONField("Kabinetdan olingan ma'lumot (do'konlar, omborlar, ruxsatlar)", default=dict, blank=True)
    options = models.JSONField("Marketplace'ga xos sozlamalar", default=dict, blank=True)
    # Narx
    currency = models.CharField("Kabinet valyutasi", max_length=3, choices=CURRENCIES, default="UZS")
    rate_source = models.CharField("Kurs manbai", max_length=8, choices=RATE_SOURCES, default=RATE_CBU)
    manual_rate = models.DecimalField("Qo'lda kurs (1 birlik = N so'm)", max_digits=14, decimal_places=4, null=True, blank=True)
    markup_percent = models.DecimalField("Ustama, %", max_digits=6, decimal_places=2, default=0)
    # Qoldiq
    stock_buffer = models.PositiveIntegerField("Zaxira (marketplace'ga ko'rsatilmaydi)", default=0)
    mto_stock = models.PositiveIntegerField(
        "«Buyurtma asosida» mahsulot uchun ko'rsatiladigan qoldiq", default=0,
        help_text="0 — bunday mahsulotlar marketplace'da 0 qoldiq bilan turadi")
    auto_sync = models.BooleanField("Narx/qoldiqni avtomatik yangilash", default=True)
    is_enabled = models.BooleanField("Yoqilgan", default=True)
    orders_synced_at = models.DateTimeField(null=True, blank=True)
    stock_synced_at = models.DateTimeField(null=True, blank=True)
    status_polled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["seller_id", "marketplace", "id"]
        verbose_name = "Marketplace kabineti"
        verbose_name_plural = "Marketplace kabinetlari"

    def __str__(self):
        return f"{MP_NAMES.get(self.marketplace, self.marketplace)} · {self.title or self.cabinet_id or self.pk} ({self.seller.code})"

    # --- kalitlar ---
    def set_credentials(self, data: dict):
        fields = CREDENTIAL_FIELDS[self.marketplace]
        clean = {k: str(v).strip() for k, v in data.items() if k in fields and v not in (None, "")}
        if fields[0] not in clean:
            raise ValidationError({fields[0]: "required"})
        self.credentials_enc = crypto.encrypt(clean)
        self.secret_last4 = clean[fields[0]][-4:]

    @property
    def credentials(self) -> dict:
        return crypto.decrypt(self.credentials_enc)

    @property
    def masked_key(self) -> str:
        return mask("x" * 8 + self.secret_last4) if self.secret_last4 else ""

    @property
    def is_usable(self):
        return self.is_enabled and self.status == self.ST_ACTIVE and bool(self.credentials_enc)


class ExchangeRate(models.Model):
    """Markaziy bank kursi (1 birlik valyuta = rate so'm). Kuniga bir marta olinadi."""

    ccy = models.CharField(max_length=3)
    date = models.DateField()
    rate = models.DecimalField(max_digits=14, decimal_places=4)
    nominal = models.PositiveIntegerField(default=1)
    fetched_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("ccy", "date")]
        ordering = ["-date"]


class ExternalCategory(models.Model):
    """Marketplace kategoriyalari keshi (operator moslash uchun qidiradi)."""

    marketplace = models.CharField(max_length=16, choices=MARKETPLACES, db_index=True)
    external_id = models.CharField(max_length=64)
    type_id = models.CharField(max_length=64, blank=True)
    name = models.CharField(max_length=255)
    path = models.CharField(max_length=1000, blank=True)
    search = models.CharField(max_length=1000, blank=True, db_index=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("marketplace", "external_id", "type_id")]
        ordering = ["path"]


class CategoryMapping(models.Model):
    """ImkonMarket kategoriyasi → marketplace kategoriyasi/tipi (operator bir marta sozlaydi)."""

    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="mp_mappings")
    marketplace = models.CharField(max_length=16, choices=MARKETPLACES)
    external_id = models.CharField("Kategoriya ID (Ozon: description_category_id, WB: subjectID)", max_length=64)
    external_type_id = models.CharField("Tip ID (faqat Ozon type_id)", max_length=64, blank=True)
    external_name = models.CharField(max_length=255, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("category", "marketplace")]
        verbose_name = "Kategoriya moslash"
        verbose_name_plural = "Kategoriya moslash"

    def __str__(self):
        return f"{self.category.slug} → {self.marketplace}:{self.external_id} {self.external_name}"


class AttributeMapping(models.Model):
    SRC_CONST, SRC_FIELD, SRC_PRODUCT = "const", "field", "product"
    SOURCES = [(SRC_CONST, "Doimiy qiymat"), (SRC_FIELD, "Mahsulot maydoni"), (SRC_PRODUCT, "Har bir mahsulotda kiritiladi")]
    FIELDS = ["name", "spec", "description", "unit", "sku", "brand", "country", "barcode", "weight_kg"]

    mapping = models.ForeignKey(CategoryMapping, on_delete=models.CASCADE, related_name="attributes")
    external_id = models.CharField(max_length=64)
    name = models.CharField(max_length=255, blank=True)
    required = models.BooleanField(default=False)
    is_dictionary = models.BooleanField("Qiymat lug'atdan tanlanadi", default=False)
    multi = models.BooleanField(default=False)
    value_type = models.CharField(max_length=32, blank=True, help_text="marketplace qaytargan tur (string/number/...)")
    source = models.CharField(max_length=8, choices=SOURCES, default=SRC_CONST)
    field = models.CharField(max_length=32, blank=True)
    value = models.CharField("Doimiy qiymat", max_length=500, blank=True)
    value_id = models.CharField("Doimiy qiymat ID (lug'at)", max_length=64, blank=True)
    unit = models.CharField(max_length=64, blank=True)
    values = models.JSONField("Lug'at qiymatlari (marketplace bergan bo'lsa)", default=list, blank=True)

    class Meta:
        unique_together = [("mapping", "external_id")]
        ordering = ["-required", "name"]


class AttributeValueMap(models.Model):
    """Bizdagi qiymat → marketplace lug'atidagi qiymat ID (masalan, «Qora» → dictionary_value_id 61574)."""

    attribute = models.ForeignKey(AttributeMapping, on_delete=models.CASCADE, related_name="value_map")
    our_value = models.CharField(max_length=255)
    external_value_id = models.CharField(max_length=64, blank=True)
    external_value = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = [("attribute", "our_value")]


class ProductMarketInfo(models.Model):
    """Marketplace'lar talab qiladigan, lekin vitrinada kerak bo'lmagan ma'lumotlar."""

    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name="market_info")
    brand = models.CharField(max_length=128, blank=True)
    barcode = models.CharField("Shtrix-kod", max_length=64, blank=True)
    country = models.CharField("Ishlab chiqarilgan mamlakat", max_length=64, blank=True, default="O'zbekiston")
    weight_kg = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    length_cm = models.DecimalField(max_digits=10, decimal_places=1, null=True, blank=True)
    width_cm = models.DecimalField(max_digits=10, decimal_places=1, null=True, blank=True)
    height_cm = models.DecimalField(max_digits=10, decimal_places=1, null=True, blank=True)
    # {"<marketplace>:<attribute_id>": "qiymat"} — AttributeMapping.source == product bo'lganda
    attributes = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)


class MarketplaceListing(models.Model):
    ST_DRAFT, ST_PENDING, ST_ACTIVE, ST_REJECTED, ST_ERROR = "draft", "pending", "active", "rejected", "error"
    STATUSES = [(ST_DRAFT, "Qoralama"), (ST_PENDING, "Tekshiruvda"), (ST_ACTIVE, "Faol"),
                (ST_REJECTED, "Rad etilgan"), (ST_ERROR, "Xato")]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="mp_listings")
    account = models.ForeignKey(MarketplaceAccount, on_delete=models.CASCADE, related_name="listings")
    offer_id = models.CharField("Sotuvchi artikuli (offer_id / vendorCode)", max_length=64)
    external_id = models.CharField("Marketplace ID (product_id / nmID / productId)", max_length=64, blank=True)
    external_sku = models.CharField("SKU (Ozon sku / WB chrtID / Uzum skuId)", max_length=64, blank=True)
    external_meta = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=12, choices=STATUSES, default=ST_DRAFT)
    last_error = models.TextField(blank=True)
    task_id = models.CharField(max_length=128, blank=True)
    pushed_price = models.DecimalField(max_digits=16, decimal_places=2, null=True, blank=True)
    pushed_currency = models.CharField(max_length=3, blank=True)
    pushed_stock = models.IntegerField(null=True, blank=True)
    price_synced_at = models.DateTimeField(null=True, blank=True)
    stock_synced_at = models.DateTimeField(null=True, blank=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("product", "account"), ("account", "offer_id")]
        ordering = ["-id"]

    def clean(self):
        if self.product_id and self.account_id and self.product.seller_id != self.account.seller_id:
            raise ValidationError("Mahsulot va kabinet bitta muassasaga tegishli bo'lishi kerak")

    def set_error(self, text, status=None):
        from .redact import redact
        self.last_error = redact(text)[:2000]
        self.status = status or self.ST_ERROR
        self.last_synced_at = timezone.now()


class MarketplaceOrder(models.Model):
    S_NEW, S_PROCESSING, S_SHIPPED, S_DELIVERED, S_CANCELLED, S_RETURNED = (
        "new", "processing", "shipped", "delivered", "cancelled", "returned")
    STATES = [(S_NEW, "Yangi"), (S_PROCESSING, "Yig'ilmoqda"), (S_SHIPPED, "Jo'natildi"),
              (S_DELIVERED, "Yetkazildi"), (S_CANCELLED, "Bekor qilindi"), (S_RETURNED, "Qaytarildi")]
    STOCK_NONE, STOCK_RESERVED, STOCK_DEDUCTED, STOCK_RELEASED = "none", "reserved", "deducted", "released"
    STOCK_HISTORICAL = "historical"  # kabinet ulanishidan oldingi (yakunlangan) buyurtma — qoldiqqa ta'sir qilmaydi

    account = models.ForeignKey(MarketplaceAccount, on_delete=models.CASCADE, related_name="orders")
    external_id = models.CharField(max_length=64)
    scheme = models.CharField("Model (FBS/FBO/DBS)", max_length=8, blank=True)
    status = models.CharField("Marketplace statusi", max_length=64, blank=True)
    state = models.CharField(max_length=12, choices=STATES, default=S_NEW)
    # [{offer_id, external_sku, name, qty, price, product_id}]
    items = models.JSONField(default=list)
    total = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, blank=True)
    ordered_at = models.DateTimeField(null=True, blank=True)
    raw = models.JSONField(default=dict, blank=True)
    stock_state = models.CharField(max_length=10, default=STOCK_NONE)
    # band qilingan paytdagi {product_id: qty} — bo'shatish/yechish aynan shu miqdor bo'yicha
    stock_items = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("account", "external_id")]
        ordering = ["-ordered_at", "-id"]


class Job(models.Model):
    """Fon vazifasi (bazadagi navbat — Celery/RQ o'rniga). Worker: manage.py run_worker."""

    QUEUED, RUNNING, DONE, FAILED = "queued", "running", "done", "failed"

    kind = models.CharField(max_length=48, db_index=True)
    account = models.ForeignKey(MarketplaceAccount, on_delete=models.CASCADE, null=True, blank=True, related_name="jobs")
    payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=10, default=QUEUED, db_index=True)
    attempts = models.PositiveIntegerField(default=0)
    max_attempts = models.PositiveIntegerField(default=6)
    run_after = models.DateTimeField(default=timezone.now, db_index=True)
    locked_until = models.DateTimeField(null=True, blank=True)
    dedupe_key = models.CharField(max_length=128, blank=True, db_index=True)
    last_error = models.TextField(blank=True)
    result = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-id"]


class SyncLog(models.Model):
    """Har bir tashqi API chaqiruvi. Kalitlar, sarlavhalar va so'rov tanasi YOZILMAYDI."""

    account = models.ForeignKey(MarketplaceAccount, on_delete=models.CASCADE, null=True, blank=True, related_name="logs")
    job = models.ForeignKey(Job, on_delete=models.SET_NULL, null=True, blank=True, related_name="logs")
    operation = models.CharField(max_length=48)
    method = models.CharField(max_length=8, blank=True)
    endpoint = models.CharField(max_length=255, blank=True)
    http_status = models.PositiveIntegerField(null=True, blank=True)
    ok = models.BooleanField(default=False)
    duration_ms = models.PositiveIntegerField(default=0)
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-id"]


def as_decimal(v) -> Decimal:
    try:
        return Decimal(str(v))
    except Exception:  # noqa: BLE001
        return Decimal(0)
