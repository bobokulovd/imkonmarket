"""Narxni marketplace kabineti valyutasiga o'tkazish.

Mahsulot narxi bizda so'mda. Kabinet valyutasi UZS bo'lsa — faqat ustama qo'shiladi.
RUB bo'lsa: kurs manbai tanlanadi — Markaziy bank (cbu.uz, kuniga bir marta olinadi) yoki qo'lda kiritilgan kurs.
"""
import logging
from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

import requests
from django.utils import timezone

from .models import ExchangeRate, MarketplaceAccount

log = logging.getLogger("integrations.currency")
CBU_URL = "https://cbu.uz/uz/arkhiv-kursov-valyut/json/"
WATCH = ("RUB", "USD", "EUR", "KZT")


class RateUnavailable(Exception):
    pass


def fetch_cbu_rates(session=None) -> int:
    s = session or requests
    r = s.get(CBU_URL, timeout=20)
    r.raise_for_status()
    n = 0
    for row in r.json():
        ccy = row.get("Ccy")
        if ccy not in WATCH:
            continue
        date = datetime.strptime(row["Date"], "%d.%m.%Y").date()
        ExchangeRate.objects.update_or_create(ccy=ccy, date=date, defaults={
            "rate": Decimal(str(row["Rate"])), "nominal": int(row.get("Nominal") or 1)})
        n += 1
    return n


def cbu_rate(ccy) -> Decimal:
    """1 birlik valyuta necha so'm (eng so'nggi, 7 kundan eski bo'lmagan)."""
    er = ExchangeRate.objects.filter(ccy=ccy, date__gte=timezone.localdate() - timedelta(days=7)).first()
    if not er:
        raise RateUnavailable(f"Markaziy bank {ccy} kursi hali olinmagan")
    return er.rate / (er.nominal or 1)


def account_rate(account: MarketplaceAccount) -> Decimal:
    if account.currency == "UZS":
        return Decimal(1)
    if account.rate_source == MarketplaceAccount.RATE_MANUAL:
        if not account.manual_rate or account.manual_rate <= 0:
            raise RateUnavailable("Qo'lda kurs kiritilmagan")
        return account.manual_rate
    return cbu_rate(account.currency)


def convert(account: MarketplaceAccount, price_uzs) -> Decimal | None:
    if price_uzs is None:
        return None
    price = Decimal(price_uzs) * (1 + Decimal(account.markup_percent or 0) / 100)
    price = price / account_rate(account)
    return price.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
