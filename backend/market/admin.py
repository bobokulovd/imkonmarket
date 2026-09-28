from django.contrib import admin

from .models import Application, ApplicationItem, Category, Contract, Payment, Product, Profile, Seller, StatusLog
from .translit import pick


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["slug", "title", "order"]
    list_editable = ["order"]

    def title(self, o):
        return pick(o.name, "uz")


class ProfileInline(admin.TabularInline):
    model = Profile
    extra = 0


@admin.register(Seller)
class SellerAdmin(admin.ModelAdmin):
    list_display = ["code", "title", "inn", "region", "role", "is_active"]
    list_filter = ["role", "region", "is_active"]
    search_fields = ["code", "inn", "full_name"]
    inlines = [ProfileInline]

    def title(self, o):
        return pick(o.name, "uz")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["sku", "title", "seller", "category", "price", "stock", "reserved", "unit", "is_active"]
    list_filter = ["category", "seller", "is_active", "delivery"]
    search_fields = ["sku", "search"]
    list_editable = ["price", "stock", "is_active"]
    list_select_related = ["seller", "category"]

    def title(self, o):
        return pick(o.name, "uz")


class ItemInline(admin.TabularInline):
    model = ApplicationItem
    extra = 0


class LogInline(admin.TabularInline):
    model = StatusLog
    extra = 0
    readonly_fields = ["status", "text", "user", "created_at"]


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ["number", "seller", "agent", "buyer_type", "buyer_name", "status", "total", "created_at"]
    list_filter = ["status", "buyer_type", "payment_method", "seller"]
    search_fields = ["number", "buyer_name", "buyer_phone", "buyer_inn"]
    inlines = [ItemInline, LogInline]


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = ["number", "seller", "agent", "buyer_type", "status", "total", "paid_amount", "date"]
    list_filter = ["status", "buyer_type", "payment_method", "seller"]
    search_fields = ["number"]
    inlines = [PaymentInline]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ["id", "contract", "method", "amount", "status", "is_demo", "created_at", "paid_at"]
    list_filter = ["method", "status", "is_demo"]
