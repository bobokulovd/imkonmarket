"""Mahsulot narxi/qoldig'i o'zgarsa — marketplace'larga yuborish (debounce bilan, worker orqali)."""
from django.db import transaction
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from market.models import Product

from .models import MarketplaceAccount


@receiver(pre_delete, sender=MarketplaceAccount)
def account_deleted(sender, instance, **kwargs):
    """Kabinet o'chirilsa — uning buyurtmalari band qilgan qoldiq bo'shatiladi (admin orqali o'chirilsa ham)."""
    from .services import notify_products_changed, release_account_reservations
    touched = release_account_reservations(instance)
    if touched:
        transaction.on_commit(lambda: notify_products_changed(touched))


@receiver(post_save, sender=Product)
def product_saved(sender, instance, created, **kwargs):
    if created:
        return
    from .services import notify_products_changed
    pk = instance.pk
    transaction.on_commit(lambda: notify_products_changed([pk]))
