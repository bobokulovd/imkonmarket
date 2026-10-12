"""Xususiyatlar lug'atini (market/seed/attributes.json) bazaga yuklaydi va mahsulotlar xususiyatlarini to'ldiradi.

    python manage.py load_attributes            # yangi xususiyat/variantlarni qo'shadi + bo'sh mahsulotlarni to'ldiradi
    python manage.py load_attributes --no-fill  # faqat lug'at

Idempotent: operator tahrirlagan nom/turlar o'zgarmaydi, faqat yetishmayotgan xususiyat va variant(option)lar qo'shiladi.
Mahsulot xususiyatlari faqat hali bo'sh bo'lsa (attributes = {}) "spec" matnidan taxminiy to'ldiriladi.
Konteyner startida avtomatik ishlaydi.
"""
import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from market.models import AttributeDef, Category, Product
from market.specparse import parse_product

SEED = Path(settings.BASE_DIR) / "market" / "seed" / "attributes.json"


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--no-fill", action="store_true")

    @transaction.atomic
    def handle(self, *a, **o):
        data = json.loads(SEED.read_text())
        created = opts_added = 0
        cats = {c.slug: c for c in Category.objects.all()}
        for slug, attrs in data.items():
            c = cats.get(slug)
            if not c:
                continue
            for i, a in enumerate(attrs):
                d, new = AttributeDef.objects.get_or_create(category=c, code=a["code"], defaults={
                    "name": a["name"], "hint": a.get("hint") or {}, "type": a["type"], "unit": a.get("unit", ""),
                    "required": a.get("required", False), "multi": a.get("multi", False),
                    "variant": a.get("variant", False), "options": a.get("options") or [], "order": i})
                if new:
                    created += 1
                    continue
                have = {x.get("v") for x in d.options or []}
                extra = [x for x in a.get("options") or [] if x["v"] not in have]
                if extra and d.type == AttributeDef.T_ENUM:
                    d.options = list(d.options or []) + extra
                    d.save()
                    opts_added += len(extra)
        filled = 0
        if not o["no_fill"]:
            defs = {}
            for d in AttributeDef.objects.all():
                defs.setdefault(d.category_id, []).append(d)
            for p in Product.objects.select_related("category").filter(attributes={}):
                attrs = parse_product(p, defs.get(p.category_id, []))
                if attrs:
                    Product.objects.filter(pk=p.pk).update(attributes=attrs)
                    filled += 1
        self.stdout.write(f"Xususiyatlar: +{created}, variantlar: +{opts_added}, to'ldirilgan mahsulotlar: {filled}")
