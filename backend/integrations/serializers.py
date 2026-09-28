from rest_framework import serializers

from market.serializers import SellerShortSerializer, abs_url

from .clients import client_class
from .models import (CREDENTIAL_FIELDS, AttributeMapping, AttributeValueMap, CategoryMapping, ExternalCategory, Job,
                     MarketplaceAccount, MarketplaceListing, MarketplaceOrder, ProductMarketInfo, SyncLog)


class AccountSerializer(serializers.ModelSerializer):
    """API kalit faqat YOZILADI (write_only). Javobda — faqat oxirgi 4 belgi (masked_key)."""

    api_key = serializers.CharField(write_only=True, required=False, allow_blank=False, trim_whitespace=True)
    masked_key = serializers.CharField(read_only=True)
    seller = SellerShortSerializer(read_only=True)
    marketplace_name = serializers.CharField(source="get_marketplace_display", read_only=True)
    capabilities = serializers.SerializerMethodField()
    counts = serializers.SerializerMethodField()
    info = serializers.SerializerMethodField()

    class Meta:
        model = MarketplaceAccount
        fields = ["id", "seller", "marketplace", "marketplace_name", "title", "cabinet_id", "campaign_id", "warehouse_id",
                  "api_key", "masked_key", "status", "status_message", "last_checked_at", "key_expires_at", "options",
                  "currency", "rate_source", "manual_rate", "markup_percent", "stock_buffer", "mto_stock", "auto_sync",
                  "is_enabled", "orders_synced_at", "stock_synced_at", "capabilities", "counts", "info", "created_at"]
        read_only_fields = ["status", "status_message", "last_checked_at", "key_expires_at", "orders_synced_at",
                            "stock_synced_at", "created_at"]

    def validate_options(self, v):
        if not isinstance(v, dict):
            raise serializers.ValidationError("object expected")
        allowed = {"domain", "language", "vat", "fbo", "stock_add_own_reserved"}
        return {k: val for k, val in v.items() if k in allowed}

    def get_capabilities(self, o):
        return sorted(client_class(o.marketplace).capabilities)

    def get_counts(self, o):
        c = {s: 0 for s, _ in MarketplaceListing.STATUSES}
        for row in o.listings.values("status"):
            c[row["status"]] = c.get(row["status"], 0) + 1
        c["orders_new"] = o.orders.filter(state__in=["new", "processing"]).count()
        return c

    def get_info(self, o):
        """Kabinetdan olingan ro'yxatlar (do'kon/kampaniya/ombor) — tanlash uchun. Maxfiy narsa yo'q."""
        m = o.meta or {}
        return {k: m.get(k) for k in ("shops", "campaigns", "warehouses", "roles", "scopes", "token_type", "key_name")
                if m.get(k) is not None} | {"remote_count": len(m.get("remote_products") or [])}

    def validate(self, attrs):
        mp = attrs.get("marketplace") or getattr(self.instance, "marketplace", None)
        if mp not in dict(MarketplaceAccount._meta.get_field("marketplace").choices):
            raise serializers.ValidationError({"marketplace": "unknown"})
        if not self.instance and not attrs.get("api_key"):
            raise serializers.ValidationError({"api_key": "required"})
        if mp == "ozon" and not (attrs.get("cabinet_id") or getattr(self.instance, "cabinet_id", "")):
            raise serializers.ValidationError({"cabinet_id": "Ozon Client-Id kerak"})
        if attrs.get("rate_source") == MarketplaceAccount.RATE_MANUAL and attrs.get("currency", "UZS") != "UZS" \
                and not attrs.get("manual_rate") and not getattr(self.instance, "manual_rate", None):
            raise serializers.ValidationError({"manual_rate": "Qo'lda kurs kiriting"})
        opts = attrs.get("options")
        if opts is not None and not isinstance(opts, dict):
            raise serializers.ValidationError({"options": "object expected"})
        return attrs

    def _apply_key(self, obj, key):
        if key:
            obj.set_credentials({CREDENTIAL_FIELDS[obj.marketplace][0]: key})
            obj.status, obj.status_message = MarketplaceAccount.ST_NEW, ""

    def create(self, data):
        key = data.pop("api_key", None)
        obj = MarketplaceAccount(**data)
        self._apply_key(obj, key)
        obj.save()
        return obj

    def update(self, obj, data):
        key = data.pop("api_key", None)
        data.pop("marketplace", None)  # marketplace o'zgarmaydi
        if "options" in data:  # ichki (worker yozgan) kalitlarni saqlab qolish
            data["options"] = {**(obj.options or {}), **data["options"]}
        for k, v in data.items():
            setattr(obj, k, v)
        self._apply_key(obj, key)
        obj.save()
        return obj


class ListingSerializer(serializers.ModelSerializer):
    product = serializers.SerializerMethodField()
    account_name = serializers.CharField(source="account.__str__", read_only=True)
    marketplace = serializers.CharField(source="account.marketplace", read_only=True)

    class Meta:
        model = MarketplaceListing
        fields = ["id", "product", "account", "account_name", "marketplace", "offer_id", "external_id", "external_sku",
                  "status", "last_error", "pushed_price", "pushed_currency", "pushed_stock", "price_synced_at",
                  "stock_synced_at", "last_synced_at", "created_at"]
        read_only_fields = fields

    def get_product(self, o):
        p = o.product
        return {"id": p.id, "sku": p.sku, "name": p.name, "price": p.price, "stock": p.stock, "reserved": p.reserved,
                "available": p.available, "unit": p.unit, "category": p.category.slug,
                "image": abs_url(self.context.get("request"), p.image)}


class OrderSerializer(serializers.ModelSerializer):
    account_name = serializers.CharField(source="account.__str__", read_only=True)
    marketplace = serializers.CharField(source="account.marketplace", read_only=True)
    seller = serializers.CharField(source="account.seller.code", read_only=True)
    actions = serializers.SerializerMethodField()

    class Meta:
        model = MarketplaceOrder
        fields = ["id", "account", "account_name", "marketplace", "seller", "external_id", "scheme", "status", "state",
                  "items", "total", "currency", "ordered_at", "stock_state", "actions", "updated_at"]

    def get_actions(self, o):
        return client_class(o.account.marketplace).order_actions(o)


class LogSerializer(serializers.ModelSerializer):
    class Meta:
        model = SyncLog
        fields = ["id", "account", "operation", "method", "endpoint", "http_status", "ok", "duration_ms", "error",
                  "created_at"]


class JobSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = ["id", "kind", "account", "status", "attempts", "max_attempts", "run_after", "last_error", "result",
                  "created_at", "finished_at"]


class ProductInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductMarketInfo
        fields = ["brand", "barcode", "country", "weight_kg", "length_cm", "width_cm", "height_cm", "attributes"]

    def validate_attributes(self, v):
        if not isinstance(v, dict):
            raise serializers.ValidationError("object expected")
        return {str(k)[:80]: str(val)[:500] for k, val in v.items()}


class ValueMapSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttributeValueMap
        fields = ["id", "our_value", "external_value_id", "external_value"]


class AttributeSerializer(serializers.ModelSerializer):
    value_map = ValueMapSerializer(many=True, read_only=True)

    class Meta:
        model = AttributeMapping
        fields = ["id", "external_id", "name", "required", "is_dictionary", "multi", "value_type", "unit", "source",
                  "field", "value", "value_id", "values", "value_map"]
        read_only_fields = ["external_id", "name", "required", "is_dictionary", "multi", "value_type", "unit", "values"]

    def validate(self, attrs):
        if attrs.get("source") == AttributeMapping.SRC_FIELD and attrs.get("field") not in AttributeMapping.FIELDS:
            raise serializers.ValidationError({"field": f"one of {AttributeMapping.FIELDS}"})
        return attrs


class MappingSerializer(serializers.ModelSerializer):
    category = serializers.SlugRelatedField(slug_field="slug", queryset=CategoryMapping._meta.get_field("category").related_model.objects.all())
    attributes = AttributeSerializer(many=True, read_only=True)
    required_missing = serializers.SerializerMethodField()

    class Meta:
        model = CategoryMapping
        fields = ["id", "category", "marketplace", "external_id", "external_type_id", "external_name", "attributes",
                  "required_missing", "updated_at"]

    def get_required_missing(self, o):
        return sum(1 for a in o.attributes.all() if a.required and a.source == AttributeMapping.SRC_CONST
                   and not (a.value or a.value_id))


class ExternalCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ExternalCategory
        fields = ["id", "marketplace", "external_id", "type_id", "name", "path"]
