"""Shifrlash kalitini almashtirish.

1) MARKETPLACE_ENC_KEYS="<yangi>,<eski>" qilib qo'ying va qayta ishga tushiring;
2) python manage.py mp_rotate_keys — barcha kalitlar yangi kalit bilan qayta shifrlanadi;
3) eski kalitni env'dan olib tashlang.
"""
from django.core.management.base import BaseCommand

from integrations import crypto
from integrations.models import MarketplaceAccount


class Command(BaseCommand):
    help = "Marketplace API kalitlarini birinchi MARKETPLACE_ENC_KEYS kaliti bilan qayta shifrlaydi"

    def handle(self, *args, **opts):
        n = 0
        for acc in MarketplaceAccount.objects.exclude(credentials_enc=""):
            acc.credentials_enc = crypto.rotate(acc.credentials_enc)
            acc.save(update_fields=["credentials_enc"])
            n += 1
        self.stdout.write(self.style.SUCCESS(f"Qayta shifrlandi: {n}"))
