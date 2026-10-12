"""Haqiqiy suratlarning fonini tekshiradi (hali tekshirilmaganlar). Konteyner startida ishlaydi.

    python manage.py analyze_images [--all]
"""
from django.core.management.base import BaseCommand

from market.images import analyze
from market.models import ProductImage


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--all", action="store_true")

    def handle(self, *a, **o):
        qs = ProductImage.objects.filter(is_sample=False)
        if not o["all"]:
            qs = qs.filter(bg_ok__isnull=True)
        n = bad = 0
        for img in qs.iterator():
            try:
                with img.image.open("rb") as f:
                    q = analyze(f.read())
            except Exception:  # noqa: BLE001 — fayl yo'q / buzilgan
                continue
            ProductImage.objects.filter(pk=img.pk).update(bg_ok=q["bg_ok"], quality=q)
            n += 1
            bad += not q["bg_ok"]
        self.stdout.write(f"Rasm fonlari tekshirildi: {n} (oq/toza emas: {bad})")
