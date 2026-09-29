import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models, transaction
from django.utils import timezone

from .translit import fill_i18n, pick


def i18n_default():
    return {}


class Category(models.Model):
    slug = models.SlugField(unique=True)
    icon = models.CharField(max_length=32, default="box")
    name = models.JSONField(default=i18n_default)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "Kategoriya"
        verbose_name_plural = "Kategoriyalar"

    def save(self, *a, **kw):
        self.name = fill_i18n(self.name)
        super().save(*a, **kw)

    def __str__(self):
        return pick(self.name, "uz")


class Seller(models.Model):
    """Sotuvchi muassasa (JIEK / MK). Har biriga alohida login beriladi."""

    ROLE_SELLER = "seller"
    ROLE_OPERATOR = "operator"
    ROLES = [(ROLE_SELLER, "Sotuvchi muassasa"), (ROLE_OPERATOR, "Operator (JIED)")]

    code = models.SlugField(unique=True)
    role = models.CharField(max_length=16, choices=ROLES, default=ROLE_SELLER)
    name = models.JSONField(default=i18n_default)
    full_name = models.CharField("Rasmiy nomi (shartnoma uchun)", max_length=255, blank=True)
    inn = models.CharField("STIR", max_length=16, blank=True)
    region = models.CharField(max_length=64, blank=True)
    region_i18n = models.JSONField(default=i18n_default)
    district_i18n = models.JSONField(default=i18n_default)
    address = models.CharField("Yuridik manzil", max_length=255, blank=True)
    phone = models.CharField(max_length=64, blank=True)
    email = models.CharField(max_length=128, blank=True)
    director = models.CharField("Rahbar F.I.Sh.", max_length=128, blank=True)
    bank_name = models.CharField("Bank", max_length=128, blank=True)
    bank_account = models.CharField("Hisob raqami", max_length=32, blank=True)
    bank_mfo = models.CharField("MFO", max_length=16, blank=True)
    treasury_account = models.CharField("G'aznachilik sh/h", max_length=64, blank=True)
    description = models.JSONField(default=i18n_default, blank=True)
    logo = models.ImageField(upload_to="sellers/", blank=True, null=True)
    is_active = models.BooleanField(default=True)
    contract_seq = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["id"]
        verbose_name = "Sotuvchi muassasa"
        verbose_name_plural = "Sotuvchi muassasalar"

    def __str__(self):
        return pick(self.name, "uz")

    @property
    def number(self):
        import re
        m = re.search(r"(\d+)", self.code)
        return m.group(1) if m else self.code

    def next_contract_number(self):
        with transaction.atomic():
            s = Seller.objects.select_for_update().get(pk=self.pk)
            s.contract_seq += 1
            s.save(update_fields=["contract_seq"])
            year = timezone.localdate().year
            return f"{s.code.upper()}/{year}-{s.contract_seq:04d}"


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    seller = models.ForeignKey(Seller, on_delete=models.CASCADE, related_name="users")
    lang = models.CharField(max_length=8, default="uz")

    def __str__(self):
        return f"{self.user.username} → {self.seller}"


class Product(models.Model):
    UNITS = ["dona", "juft", "kg", "m²", "m³", "p/m", "to'plam", "tonna", "xizmat"]

    seller = models.ForeignKey(Seller, on_delete=models.CASCADE, related_name="products")
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    sku = models.CharField(max_length=32, unique=True)
    name = models.JSONField(default=i18n_default)
    spec = models.JSONField("Xususiyati", default=i18n_default, blank=True)
    description = models.JSONField(default=i18n_default, blank=True)
    unit = models.CharField(max_length=16, default="dona")
    price = models.DecimalField("Narx (so'm, QQSsiz)", max_digits=16, decimal_places=2, null=True, blank=True)
    min_order = models.PositiveIntegerField(default=1)
    stock = models.PositiveIntegerField("Omborda bor", null=True, blank=True, help_text="Bo'sh = buyurtma asosida")
    reserved = models.PositiveIntegerField("Band qilingan", default=0)
    daily_capacity = models.PositiveIntegerField("Kunlik quvvat", null=True, blank=True)
    lead_days = models.PositiveIntegerField("Tayyorlash muddati (kun)", default=3)
    delivery = models.BooleanField("Yetkazib berish bor", default=True)
    address = models.JSONField("Ishlab chiqarilgan manzil", default=i18n_default, blank=True)
    image = models.ImageField(upload_to="products/", blank=True, null=True)
    image_is_sample = models.BooleanField("Namunaviy (AI) rasm", default=False,
                                          help_text="Haqiqiy surat yuklanganda avtomatik o'chadi")
    note = models.CharField("Ichki izoh", max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    search = models.TextField(blank=True, editable=False)
    views = models.PositiveIntegerField(default=0)
    sold = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-id"]
        verbose_name = "Mahsulot"
        verbose_name_plural = "Mahsulotlar"

    def save(self, *a, **kw):
        self.name = fill_i18n(self.name)
        self.spec = fill_i18n(self.spec)
        self.description = fill_i18n(self.description)
        if not self.sku:
            n = Product.objects.filter(seller=self.seller).count() + 1
            self.sku = f"{self.seller.code.upper()}-{n:03d}-{uuid.uuid4().hex[:3].upper()}"
        parts = [self.sku, *self.name.values(), *self.spec.values(), *(self.seller.name or {}).values()]
        self.search = " ".join(str(x) for x in parts if x).lower()
        super().save(*a, **kw)

    def __str__(self):
        return f"{pick(self.name, 'uz')} ({self.sku})"

    @property
    def available(self):
        if self.stock is None:
            return None
        return max(self.stock - self.reserved, 0)


class Application(models.Model):
    """Ariza. Savatdagi mahsulotlar sotuvchi bo'yicha bo'linib, har biriga alohida ariza tuziladi."""

    B2B, B2C = "b2b", "b2c"
    BUYER_TYPES = [(B2B, "Yuridik shaxs (B2B)"), (B2C, "Jismoniy shaxs (B2C)")]
    PAY_CLICK, PAY_PAYME, PAY_BANK = "click", "payme", "bank"
    PAY_METHODS = [(PAY_CLICK, "Click"), (PAY_PAYME, "Payme"), (PAY_BANK, "Bank o'tkazmasi (perechisleniye)")]
    ST_NEW, ST_REVIEW, ST_CONTRACT, ST_REJECTED, ST_CANCELLED = "new", "review", "contract", "rejected", "cancelled"
    STATUSES = [
        (ST_NEW, "Yangi"),
        (ST_REVIEW, "Ko'rib chiqilmoqda"),
        (ST_CONTRACT, "Shartnoma tuzildi"),
        (ST_REJECTED, "Rad etildi"),
        (ST_CANCELLED, "Bekor qilindi"),
    ]

    number = models.CharField(max_length=32, unique=True)
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    seller = models.ForeignKey(Seller, on_delete=models.PROTECT, related_name="applications")
    agent = models.ForeignKey(
        Seller, on_delete=models.SET_NULL, null=True, blank=True, related_name="agent_applications",
        help_text="Boshqa muassasa nomidan ariza/shartnoma yaratgan muassasa",
    )
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    buyer_type = models.CharField(max_length=4, choices=BUYER_TYPES)
    buyer_name = models.CharField("Tashkilot nomi yoki F.I.Sh.", max_length=255)
    buyer_inn = models.CharField("STIR", max_length=16, blank=True)
    buyer_pinfl = models.CharField("JShShIR", max_length=16, blank=True)
    buyer_passport = models.CharField("Pasport", max_length=16, blank=True)
    buyer_director = models.CharField("Rahbar", max_length=128, blank=True)
    buyer_phone = models.CharField(max_length=32)
    buyer_email = models.CharField(max_length=128, blank=True)
    buyer_address = models.CharField(max_length=255, blank=True)
    buyer_region = models.CharField(max_length=64, blank=True)
    buyer_bank_name = models.CharField(max_length=128, blank=True)
    buyer_bank_account = models.CharField(max_length=32, blank=True)
    buyer_bank_mfo = models.CharField(max_length=16, blank=True)
    payment_method = models.CharField(max_length=8, choices=PAY_METHODS)
    delivery_required = models.BooleanField(default=False)
    delivery_address = models.CharField(max_length=255, blank=True)
    comment = models.TextField(blank=True)
    seller_comment = models.TextField(blank=True)
    lang = models.CharField(max_length=8, default="uz")
    status = models.CharField(max_length=12, choices=STATUSES, default=ST_NEW)
    total = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    has_unpriced = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-id"]
        verbose_name = "Ariza"
        verbose_name_plural = "Arizalar"

    def __str__(self):
        return self.number

    def recalc(self):
        items = list(self.items.all())
        self.total = sum((i.amount for i in items), Decimal("0"))
        self.has_unpriced = any(i.price is None for i in items)


class ApplicationItem(models.Model):
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    name = models.JSONField(default=i18n_default)
    spec = models.JSONField(default=i18n_default)
    unit = models.CharField(max_length=16)
    qty = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=16, decimal_places=2, null=True, blank=True)

    @property
    def amount(self):
        return (self.price or Decimal("0")) * self.qty


class Contract(models.Model):
    ST_ACTIVE, ST_PAID, ST_SHIPPED, ST_DONE, ST_CANCELLED = "active", "paid", "shipped", "done", "cancelled"
    STATUSES = [
        (ST_ACTIVE, "Imzolandi — to'lov kutilmoqda"),
        (ST_PAID, "To'landi"),
        (ST_SHIPPED, "Jo'natildi"),
        (ST_DONE, "Yakunlandi"),
        (ST_CANCELLED, "Bekor qilindi"),
    ]

    application = models.OneToOneField(Application, on_delete=models.PROTECT, related_name="contract")
    number = models.CharField(max_length=40, unique=True)
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    seller = models.ForeignKey(Seller, on_delete=models.PROTECT, related_name="contracts")
    agent = models.ForeignKey(Seller, on_delete=models.SET_NULL, null=True, blank=True, related_name="agent_contracts")
    buyer_type = models.CharField(max_length=4, choices=Application.BUYER_TYPES)
    payment_method = models.CharField(max_length=8, choices=Application.PAY_METHODS)
    lang = models.CharField(max_length=8, default="uz")
    date = models.DateField(default=timezone.localdate)
    total = models.DecimalField(max_digits=18, decimal_places=2)
    delivery_cost = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    prepayment_percent = models.PositiveIntegerField(default=100)
    payment_days = models.PositiveIntegerField(default=10)
    delivery_days = models.PositiveIntegerField(default=15)
    status = models.CharField(max_length=12, choices=STATUSES, default=ST_ACTIVE)
    paid_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    pdf = models.FileField(upload_to="contracts/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    shipped_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-id"]
        verbose_name = "Shartnoma"
        verbose_name_plural = "Shartnomalar"

    def __str__(self):
        return self.number

    @property
    def grand_total(self):
        return self.total + self.delivery_cost

    @property
    def due_amount(self):
        return max(self.grand_total - self.paid_amount, Decimal("0"))


class Payment(models.Model):
    ST_PENDING, ST_PAID, ST_CANCELLED = "pending", "paid", "cancelled"
    STATUSES = [(ST_PENDING, "Kutilmoqda"), (ST_PAID, "To'langan"), (ST_CANCELLED, "Bekor")]

    contract = models.ForeignKey(Contract, on_delete=models.PROTECT, related_name="payments")
    method = models.CharField(max_length=8, choices=Application.PAY_METHODS)
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    status = models.CharField(max_length=12, choices=STATUSES, default=ST_PENDING)
    is_demo = models.BooleanField(default=False)
    # Payme / Click tranzaksiya ma'lumotlari
    provider_txn_id = models.CharField(max_length=64, blank=True, db_index=True)
    provider_state = models.IntegerField(default=0)
    provider_create_time = models.BigIntegerField(default=0)
    provider_perform_time = models.BigIntegerField(default=0)
    provider_cancel_time = models.BigIntegerField(default=0)
    provider_reason = models.IntegerField(null=True, blank=True)
    # Bank o'tkazmasi uchun
    document_no = models.CharField("To'lov topshiriqnomasi №", max_length=64, blank=True)
    note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-id"]
        verbose_name = "To'lov"
        verbose_name_plural = "To'lovlar"


class StatusLog(models.Model):
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="logs")
    status = models.CharField(max_length=32)
    text = models.CharField(max_length=255, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
