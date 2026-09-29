from django.conf import settings
from rest_framework import serializers

from .models import Application, ApplicationItem, Category, Contract, Payment, Product, Seller, StatusLog
from .translit import LANGS, fill_i18n


def abs_url(request, f):
    if not f:
        return None
    try:
        url = f.url
    except ValueError:
        return None
    return public_url(request, url)


def public_url(request, path):
    """Tashqi (brauzer/ilova) uchun to'liq URL. PUBLIC_URL berilsa — o'sha (reverse-proxy ortida ham to'g'ri)."""
    if settings.PUBLIC_URL:
        return settings.PUBLIC_URL.rstrip("/") + path
    return request.build_absolute_uri(path) if request else path


class I18nField(serializers.JSONField):
    """{uz, uz_cyrl, uz_new, ru, kaa, en}. Yozishda satr berilsa — uz deb qabul qilinadi."""

    def to_internal_value(self, data):
        if isinstance(data, str):
            data = {"uz": data}
        if not isinstance(data, dict):
            raise serializers.ValidationError("object expected")
        return fill_i18n({k: v for k, v in data.items() if k in LANGS})


class CategorySerializer(serializers.ModelSerializer):
    count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Category
        fields = ["id", "slug", "icon", "name", "count"]


class SellerShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Seller
        fields = ["id", "code", "name", "region", "region_i18n", "district_i18n"]


class SellerPublicSerializer(serializers.ModelSerializer):
    product_count = serializers.IntegerField(read_only=True, default=0)
    logo = serializers.SerializerMethodField()

    class Meta:
        model = Seller
        fields = ["id", "code", "name", "region", "region_i18n", "district_i18n", "description", "phone", "email",
                  "logo", "product_count", "inn"]

    def get_logo(self, o):
        return abs_url(self.context.get("request"), o.logo)


class ProductListSerializer(serializers.ModelSerializer):
    seller = SellerShortSerializer(read_only=True)
    category = serializers.SlugRelatedField(slug_field="slug", read_only=True)
    available = serializers.IntegerField(read_only=True)
    image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ["id", "sku", "name", "spec", "unit", "price", "available", "category", "seller", "delivery",
                  "image", "image_is_sample", "min_order", "lead_days", "sold", "address"]

    def get_image(self, o):
        return abs_url(self.context.get("request"), o.image)


class ProductDetailSerializer(ProductListSerializer):
    class Meta(ProductListSerializer.Meta):
        fields = ProductListSerializer.Meta.fields + ["description", "daily_capacity", "views"]


class SellerProductSerializer(serializers.ModelSerializer):
    """Sotuvchi kabineti: o'z mahsulotlarini qo'shish/tahrirlash."""

    name = I18nField()
    spec = I18nField(required=False)
    description = I18nField(required=False)
    address = I18nField(required=False)
    category = serializers.SlugRelatedField(slug_field="slug", queryset=Category.objects.all())
    available = serializers.IntegerField(read_only=True)
    image_url = serializers.SerializerMethodField()
    seller = SellerShortSerializer(read_only=True)

    class Meta:
        model = Product
        fields = ["id", "sku", "name", "spec", "description", "category", "unit", "price", "min_order", "stock",
                  "reserved", "available", "daily_capacity", "lead_days", "delivery", "address", "image",
                  "image_url", "image_is_sample", "note", "is_active", "sold", "views", "seller", "updated_at"]
        read_only_fields = ["sku", "reserved", "sold", "views", "updated_at", "image_is_sample"]

    def update(self, instance, data):
        if data.get("image"):  # muassasa haqiqiy surat yukladi
            instance.image_is_sample = False
        return super().update(instance, data)
        extra_kwargs = {"image": {"write_only": True, "required": False}}

    def get_image_url(self, o):
        return abs_url(self.context.get("request"), o.image)

    def validate_unit(self, v):
        if v not in Product.UNITS:
            raise serializers.ValidationError(f"one of {Product.UNITS}")
        return v


class AgentCatalogSerializer(ProductListSerializer):
    """Umumiy katalog (boshqa muassasa nomidan shartnoma uchun) — qoldiqlar bilan."""

    class Meta(ProductListSerializer.Meta):
        fields = ProductListSerializer.Meta.fields + ["stock", "reserved", "daily_capacity"]


class ItemSerializer(serializers.ModelSerializer):
    amount = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    product_id = serializers.IntegerField(source="product.id", read_only=True)
    sku = serializers.CharField(source="product.sku", read_only=True)
    available = serializers.IntegerField(source="product.available", read_only=True)

    class Meta:
        model = ApplicationItem
        fields = ["id", "product_id", "sku", "name", "spec", "unit", "qty", "price", "amount", "available"]


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ["id", "method", "amount", "status", "is_demo", "document_no", "note", "created_at", "paid_at"]


class LogSerializer(serializers.ModelSerializer):
    class Meta:
        model = StatusLog
        fields = ["status", "text", "created_at"]


class ContractShortSerializer(serializers.ModelSerializer):
    grand_total = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    due_amount = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    pdf_url = serializers.SerializerMethodField()

    class Meta:
        model = Contract
        fields = ["id", "number", "token", "status", "date", "total", "delivery_cost", "grand_total", "paid_amount",
                  "due_amount", "payment_method", "buyer_type", "lang", "pdf_url", "prepayment_percent",
                  "payment_days", "delivery_days", "shipped_at"]

    def get_pdf_url(self, o):
        req = self.context.get("request")
        path = f"/api/contracts/{o.token}/pdf/"
        return public_url(req, path)


class PublicOrderSerializer(serializers.ModelSerializer):
    """Xaridor uchun ariza holati (token orqali)."""

    seller = SellerPublicSerializer(read_only=True)
    agent = SellerShortSerializer(read_only=True)
    items = ItemSerializer(many=True, read_only=True)
    contract = serializers.SerializerMethodField()
    logs = LogSerializer(many=True, read_only=True)

    class Meta:
        model = Application
        fields = ["number", "token", "seller", "agent", "buyer_type", "buyer_name", "buyer_phone", "payment_method",
                  "delivery_required", "delivery_address", "status", "total", "has_unpriced", "items", "contract",
                  "logs", "seller_comment", "created_at", "lang"]

    def get_contract(self, o):
        c = getattr(o, "contract", None)
        if not c:
            return None
        data = ContractShortSerializer(c, context=self.context).data
        data["payments"] = PaymentSerializer(c.payments.filter(status="paid"), many=True).data
        return data


class SellerApplicationSerializer(serializers.ModelSerializer):
    seller = SellerShortSerializer(read_only=True)
    agent = SellerShortSerializer(read_only=True)
    items = ItemSerializer(many=True, read_only=True)
    contract = ContractShortSerializer(read_only=True)
    logs = LogSerializer(many=True, read_only=True)
    items_count = serializers.SerializerMethodField()

    class Meta:
        model = Application
        exclude = ["created_by"]

    def get_items_count(self, o):
        return len(o.items.all())


class ContractSerializer(ContractShortSerializer):
    seller = SellerShortSerializer(read_only=True)
    agent = SellerShortSerializer(read_only=True)
    application = serializers.SerializerMethodField()
    payments = PaymentSerializer(many=True, read_only=True)

    class Meta(ContractShortSerializer.Meta):
        fields = ContractShortSerializer.Meta.fields + ["seller", "agent", "application", "payments", "created_at"]

    def get_application(self, o):
        a = o.application
        return {
            "id": a.id, "number": a.number, "token": str(a.token), "buyer_name": a.buyer_name,
            "buyer_phone": a.buyer_phone, "buyer_inn": a.buyer_inn, "buyer_pinfl": a.buyer_pinfl,
            "delivery_required": a.delivery_required, "delivery_address": a.delivery_address,
            "items": ItemSerializer(a.items.select_related("product"), many=True).data,
        }


class SellerProfileSerializer(serializers.ModelSerializer):
    name = I18nField(read_only=True)
    description = I18nField(required=False)

    class Meta:
        model = Seller
        fields = ["id", "code", "role", "name", "full_name", "inn", "region", "region_i18n", "district_i18n",
                  "address", "phone", "email", "director", "bank_name", "bank_account", "bank_mfo",
                  "treasury_account", "description", "logo"]
        read_only_fields = ["code", "role", "inn", "region", "region_i18n", "district_i18n"]
