"""Kodsiz mahsulotlarga IKPU (MXIK) tavsiya qiladi — tasnif.soliq.uz orqali (internet kerak, prod serverda ishlaydi).

    python manage.py suggest_ikpu            # faqat kodi yo'q mahsulotlar
    python manage.py suggest_ikpu --once     # bir marta (media/.ikpu_suggested belgisi) — konteyner startida
    python manage.py suggest_ikpu --dry-run

Tavsiya ikpu_confirmed=False bilan saqlanadi — muassasa kartochkada "Tasdiqlash" bosadi yoki boshqasini tanlaydi.
Topilmasa — kategoriyaning tavsiya kodi (operator belgilagan Category.ikpu_default) qo'yiladi.
"""
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from market.ikpu import suggest
from market.models import Product
from market.translit import pick


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--limit", type=int)

    def handle(self, *a, **o):
        mark = Path(settings.MEDIA_ROOT) / ".ikpu_suggested"
        if o["once"] and mark.exists():
            self.stdout.write("IKPU tavsiyasi avval bajarilgan")
            return
        qs = Product.objects.filter(ikpu="").select_related("category").order_by("id")
        if o["limit"]:
            qs = qs[:o["limit"]]
        memo, found, fallback, miss = {}, 0, 0, 0
        for p in qs:
            key = (pick(p.name, "ru"), pick(p.name, "uz"))
            if key not in memo:
                memo[key] = suggest(*key)
            s = memo[key]
            if s:
                code, name = s["code"], s["name"]
                found += 1
            elif p.category.ikpu_default:
                code, name = p.category.ikpu_default, p.category.ikpu_name
                fallback += 1
            else:
                miss += 1
                continue
            self.stdout.write(f"{p.sku}: {key[0]} → {code} {name[:60]}")
            if not o["dry_run"]:
                Product.objects.filter(pk=p.pk, ikpu="").update(ikpu=code, ikpu_name=name[:255], ikpu_confirmed=False)
        if o["once"] and not o["dry_run"]:
            mark.parent.mkdir(parents=True, exist_ok=True)
            mark.write_text("ok")
        self.stdout.write(f"IKPU: topildi {found}, kategoriya bo'yicha {fallback}, topilmadi {miss}")
