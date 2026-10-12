from django.conf import settings
from rest_framework import serializers

from .models import (Application, ApplicationItem, AttributeDef, Category, Contract, Payment, Product, ProductImage,
                     ProductVariant, Seller, StatusLog)
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
        fields = ["id", "slug", "icon", "name", "count", "ikpu_default", "ikpu_name"]


class AttributeDefSerializer(serializers.ModelSerializer):
    category = serializers.SlugRelatedField(slug_field="slug", queryset=Category.objects.all())
    name = I18nField()
    hint = I18nField(required=False)

    class Meta:
        model = AttributeDef
        fields = ["id", "category", "code", "name", "hint", "type", "unit", "required", "multi", "variant", "options",
                  "order"]

    def validate_options(self, v):
        if not isinstance(v, list):
            raise serializers.ValidationError("list expected")
        out, seen = [], set()
        for o in v:
            if not isinstance(o, dict) or not str(o.get("v") or "").strip():
                raise serializers.ValidationError("[{v, name}] expected")
            code = str(o["v"]).strip()[:48]
            if code in seen:
                raise serializers.ValidationError(f"takrorlangan kod: {code}")
            seen.add(code)
            name = o.get("name") or {"uz": code}
            out.append({"v": code, "name": fill_i18n(name if isinstance(name, dict) else {"uz": str(name)})})
        return out

    def validate(self, attrs):
        t = attrs.get("type", getattr(self.instance, "type", AttributeDef.T_TEXT))
        opts = attrs.get("options", getattr(self.instance, "options", []))
        if t == AttributeDef.T_ENUM and not opts:
            raise serializers.ValidationError({"options": "Ro'yxat turidagi xususiyatga variantlar kerak"})
        if attrs.get("variant", getattr(self.instance, "variant", False)) and t not in (AttributeDef.T_ENUM,
                                                                                        AttributeDef.T_NUMBER):
            raise serializers.ValidationError({"variant": "Variant o'qi ro'yxat yoki son turida bo'ladi"})
        return attrs


class ProductImageSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ["id", "url", "order", "is_sample", "width", "height"]

    def get_url(self, o):
        return abs_url(self.context.get("request"), o.image)


class VariantSerializer(serializers.ModelSerializer):
    label = serializers.SerializerMethodField()
    available = serializers.IntegerField(read_only=True)
    price = serializers.DecimalField(source="effective_price", max_digits=16, decimal_places=2, read_only=True)
    own_price = serializers.DecimalField(source="price", max_digits=16, decimal_places=2, read_only=True)
    image = serializers.PrimaryKeyRelatedField(read_only=True)
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = ProductVariant
        fields = ["id", "sku", "attributes", "label", "barcode", "price", "own_price", "stock", "reserved", "available", "sold",
                  "image", "image_url", "is_active", "order"]

    def get_label(self, o):
        from .catalog import variant_label
        return variant_label(o)

    def get_image_url(self, o):
        return abs_url(self.context.get("request"), o.image.image) if o.image_id else None


class PublicVariantSerializer(VariantSerializer):
    label = serializers.SerializerMethodField()

    class Meta(VariantSerializer.Meta):
        fields = ["id", "sku", "attributes", "label", "price", "available", "image", "image_url"]

    def get_label(self, o):
        from .catalog import variant_label
        return variant_label(o)


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
                  "image", "image_is_sample", "min_order", "lead_days", "sold", "address", "has_variants", "brand"]

    def get_image(self, o):
        return abs_url(self.context.get("request"), o.image)


class ProductDetailSerializer(ProductListSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    variants = serializers.SerializerMethodField()
    variant_axes = serializers.SerializerMethodField()
    characteristics = serializers.SerializerMethodField()

    class Meta(ProductListSerializer.Meta):
        fields = ProductListSerializer.Meta.fields + ["description", "daily_capacity", "views", "images", "variants",
                                                      "variant_axes", "characteristics", "country", "ikpu",
                                                      "weight_kg", "length_cm", "width_cm", "height_cm"]

    def get_variants(self, o):
        if not o.has_variants:
            return []
        return PublicVariantSerializer(o.variants.filter(is_active=True).select_related("image"), many=True,
                                       context=self.context).data

    def get_variant_axes(self, o):
        """Variant tanlagich: faqat mavjud variantlarda uchraydigan qiymatlar."""
        if not o.has_variants:
            return []
        used = {}
        for v in o.variants.filter(is_active=True):
            for k, val in (v.attributes or {}).items():
                used.setdefault(k, []).append(val)
        out = []
        for d in AttributeDef.objects.filter(category_id=o.category_id, variant=True, code__in=list(used)):
            opts = [x for x in d.options or [] if x.get("v") in used[d.code]]
            out.append({"code": d.code, "name": d.name, "options": opts})
        return out

    def get_characteristics(self, o):
        from .catalog import characteristics
        return characteristics(o)


class SellerProductSerializer(serializers.ModelSerializer):
    """Sotuvchi kabineti: o'z mahsulotlarini qo'shish/tahrirlash."""

    name = I18nField()
    spec = I18nField(required=False)
    description = I18nField(required=False)
    address = I18nField(required=False)
    category = serializers.SlugRelatedField(slug_field="slug", queryset=Category.objects.all())
    available = serializers.IntegerField(read_only=True)
    image = serializers.ImageField(write_only=True, required=False, allow_null=True)
    image_url = serializers.SerializerMethodField()
    seller = SellerShortSerializer(read_only=True)
    attributes = serializers.JSONField(required=False)
    images = serializers.SerializerMethodField()
    variants = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ["id", "sku", "name", "spec", "description", "category", "unit", "price", "min_order", "stock",
                  "reserved", "available", "daily_capacity", "lead_days", "delivery", "address", "image",
                  "image_url", "image_is_sample", "note", "is_active", "sold", "views", "seller", "updated_at",
                  "brand", "country", "ikpu", "ikpu_name", "ikpu_confirmed", "barcode", "weight_kg", "length_cm",
                  "width_cm", "height_cm", "attributes", "has_variants", "images", "variants"]
        read_only_fields = ["sku", "reserved", "sold", "views", "updated_at", "image_is_sample", "has_variants"]

    def get_image_url(self, o):
        return abs_url(self.context.get("request"), o.image)

    def get_images(self, o):
        return ProductImageSerializer(o.images.all(), many=True, context=self.context).data

    def get_variants(self, o):
        return VariantSerializer(o.variants.all().select_related("image"), many=True, context=self.context).data

    def validate_unit(self, v):
        if v not in Product.UNITS:
            raise serializers.ValidationError(f"one of {Product.UNITS}")
        return v

    def validate_barcode(self, v):
        from .catalog import clean_barcode
        return clean_barcode(v)

    def validate_ikpu(self, v):
        from .catalog import clean_ikpu
        return clean_ikpu(v)

    def validate(self, attrs):
        from .catalog import clean_attributes
        cat = attrs.get("category") or getattr(self.instance, "category", None)
        if "attributes" in attrs:
            attrs["attributes"] = clean_attributes(cat.pk if cat else None, attrs["attributes"])
        elif self.instance is not None and "category" in attrs and attrs["category"] != self.instance.category:
            attrs["attributes"] = clean_attributes(cat.pk, self.instance.attributes)
        if self.instance is not None and self.instance.has_variants:
            # variantli mahsulotda qoldiq va narx variantlardan hisoblanadi
            attrs.pop("stock", None)
            attrs.pop("price", None)
        if "ikpu" in attrs and self.instance is not None and attrs["ikpu"] != self.instance.ikpu \
                and "ikpu_confirmed" not in attrs:
            attrs["ikpu_confirmed"] = bool(attrs["ikpu"])  # muassasa o'zi kiritdi — tasdiqlangan
        return attrs

    def _save_image(self, p, f):
        if f:
            from .images import add_image
            add_image(p, f.read(), sample=False, first=True)

    def create(self, data):
        f = data.pop("image", None)
        p = super().create(data)
        self._save_image(p, f)
        return p

    def update(self, instance, data):
        f = data.pop("image", None)
        p = super().update(instance, data)
        self._save_image(p, f)
        return p


class AgentCatalogSerializer(ProductListSerializer):
    """Umumiy katalog (boshqa muassasa nomidan shartnoma uchun) — qoldiqlar bilan."""

    variants = serializers.SerializerMethodField()

    class Meta(ProductListSerializer.Meta):
        fields = ProductListSerializer.Meta.fields + ["stock", "reserved", "daily_capacity", "variants"]

    def get_variants(self, o):
        if not o.has_variants:
            return []
        return PublicVariantSerializer(o.variants.filter(is_active=True), many=True, context=self.context).data


class ItemSerializer(serializers.ModelSerializer):
    amount = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    product_id = serializers.IntegerField(source="product.id", read_only=True)
    sku = serializers.SerializerMethodField()
    available = serializers.SerializerMethodField()
    variant_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = ApplicationItem
        fields = ["id", "product_id", "variant_id", "sku", "name", "spec", "unit", "qty", "price", "amount", "available"]

    def get_sku(self, o):
        return o.variant.sku if o.variant_id else o.product.sku

    def get_available(self, o):
        return o.variant.available if o.variant_id else o.product.available


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
