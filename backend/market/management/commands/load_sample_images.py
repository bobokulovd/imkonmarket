"""Rasmsiz mahsulotlarga namunaviy (AI) rasmlarni qo'yadi: market/seed/images/<key>.webp (manifest.json).
Haqiqiy surat yuklangan mahsulotlarga tegmaydi. Konteyner startida avtomatik ishlaydi.

    python manage.py load_sample_images [--refresh]   # --refresh: eski namunaviy rasmlarni ham yangilaydi
"""
from django.core.management.base import BaseCommand

from market.images import load_samples


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--refresh", action="store_true")

    def handle(self, *a, **o):
        n = load_samples(overwrite_samples=o["refresh"])
        self.stdout.write(f"Namunaviy rasm qo'yildi: {n}")
