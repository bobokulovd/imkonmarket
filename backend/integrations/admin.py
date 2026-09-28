"""Admin: API kalit hech qachon ko'rsatilmaydi va tahrirlanmaydi — faqat oxirgi 4 belgi."""
from django.contrib import admin

from .models import (AttributeMapping, CategoryMapping, ExchangeRate, Job, MarketplaceAccount, MarketplaceListing,
                     MarketplaceOrder, SyncLog)


@admin.register(MarketplaceAccount)
class AccountAdmin(admin.ModelAdmin):
    list_display = ["id", "seller", "marketplace", "title", "cabinet_id", "masked_key", "status", "last_checked_at",
                    "key_expires_at", "is_enabled"]
    list_filter = ["marketplace", "status", "is_enabled"]
    search_fields = ["title", "cabinet_id", "seller__code"]
    exclude = ["credentials_enc", "meta"]
    readonly_fields = ["masked_key", "status", "status_message", "last_checked_at", "key_expires_at",
                       "orders_synced_at", "stock_synced_at", "status_polled_at"]

    @admin.display(description="API kalit")
    def masked_key(self, o):
        return o.masked_key


@admin.register(MarketplaceListing)
class ListingAdmin(admin.ModelAdmin):
    list_display = ["id", "product", "account", "offer_id", "external_id", "status", "pushed_price", "pushed_stock",
                    "last_synced_at"]
    list_filter = ["status", "account__marketplace"]
    search_fields = ["offer_id", "external_id", "product__sku"]
    raw_id_fields = ["product", "account"]


@admin.register(MarketplaceOrder)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["id", "account", "external_id", "scheme", "status", "state", "total", "currency", "ordered_at",
                    "stock_state"]
    list_filter = ["state", "account__marketplace", "scheme"]
    search_fields = ["external_id"]
    raw_id_fields = ["account"]


class AttributeInline(admin.TabularInline):
    model = AttributeMapping
    extra = 0
    fields = ["external_id", "name", "required", "is_dictionary", "source", "field", "value", "value_id"]
    readonly_fields = ["external_id", "name", "required", "is_dictionary"]


@admin.register(CategoryMapping)
class MappingAdmin(admin.ModelAdmin):
    list_display = ["category", "marketplace", "external_id", "external_type_id", "external_name"]
    list_filter = ["marketplace"]
    inlines = [AttributeInline]


@admin.register(SyncLog)
class SyncLogAdmin(admin.ModelAdmin):
    list_display = ["created_at", "account", "operation", "method", "endpoint", "http_status", "ok", "duration_ms"]
    list_filter = ["ok", "operation", "account__marketplace"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ["id", "kind", "account", "status", "attempts", "run_after", "finished_at"]
    list_filter = ["status", "kind"]
    readonly_fields = [f.name for f in Job._meta.fields]


admin.site.register(ExchangeRate)
