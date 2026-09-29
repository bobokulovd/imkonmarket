"""Haqiqiy suratlarni ommaviy yuklash: fayl nomi = mahsulot SKU (masalan MK-49-001.jpg). Papka yoki ZIP.

    python manage.py import_images /path/to/photos
    python manage.py import_images photos.zip
"""
from pathlib import Path

from django.core.management.base import BaseCommand

from market.images import import_files
from market.models import Product


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("path")

    def handle(self, *a, **o):
        p = Path(o["path"])
        paths = [p] if p.is_file() else [x for x in p.rglob("*") if x.is_file()]
        res = import_files(((x.name, x.read_bytes()) for x in paths), Product.objects.all())
        self.stdout.write(f"bog'landi: {len(res['matched'])}, topilmadi: {len(res['unmatched'])}, xato: {len(res['errors'])}")
        for n in res["unmatched"][:50]:
            self.stdout.write(f"  ? {n}")
        for e in res["errors"]:
            self.stdout.write(f"  ! {e}")
