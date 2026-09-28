"""MarketplaceClient — barcha adapterlar uchun umumiy asos.

Adapter metodlari normallashtirilgan ma'lumot qaytaradi (quyidagi docstring'larga qarang), shuning uchun
servis qatlami qaysi marketplace ekanini bilmasdan ishlaydi. Qo'llanmaydigan amal — NotSupported.
"""
import logging
import time
from dataclasses import dataclass, field
from decimal import Decimal

import requests
from django.conf import settings

from ..redact import redact, register_secret

log = logging.getLogger("integrations.http")


class MarketplaceError(Exception):
    def __init__(self, message, status=None, retry_after=None):
        super().__init__(redact(message))
        self.status = status
        self.retry_after = retry_after


class RetryableError(MarketplaceError):
    """429 / 420 / 5xx / timeout — keyinroq qayta urinish mumkin."""


class AuthError(MarketplaceError):
    """401 / 403 — kalit yaroqsiz yoki ruxsat yetarli emas."""


class NotSupported(MarketplaceError):
    pass


# Imkoniyatlar (UI tugmalari shunga qarab ko'rsatiladi)
CAP_CATEGORIES = "categories"          # kategoriya/atributlarni API'dan olish
CAP_CREATE = "create_cards"            # kartochkani API orqali yaratish
CAP_LINK = "link_existing"             # kabinetdagi mavjud kartochkaga bog'lash
CAP_PRICES = "prices"
CAP_STOCKS = "stocks"
CAP_ORDERS = "orders"
CAP_ORDER_ACTIONS = "order_actions"


@dataclass
class ProductPayload:
    """Marketplace'ga yuboriladigan mahsulot (servis qatlami yig'adi)."""

    listing_id: int
    offer_id: str
    name: str
    description: str
    price: Decimal | None
    currency: str
    images: list[str]
    category_id: str = ""
    type_id: str = ""
    attributes: list[dict] = field(default_factory=list)   # [{id, value, value_id, multi}]
    barcode: str = ""
    brand: str = ""
    country: str = ""
    weight_kg: Decimal | None = None
    length_cm: Decimal | None = None
    width_cm: Decimal | None = None
    height_cm: Decimal | None = None
    vat: str = ""
    external_id: str = ""
    external_sku: str = ""
    external_meta: dict = field(default_factory=dict)


@dataclass
class ListingRef:
    """Narx/qoldiq/status uchun listing havolasi."""

    listing_id: int
    offer_id: str
    external_id: str = ""
    external_sku: str = ""
    external_meta: dict = field(default_factory=dict)
    task_id: str = ""
    price: Decimal | None = None
    currency: str = ""
    stock: int | None = None


class MarketplaceClient:
    code = ""
    base_url = ""
    capabilities: set = set()
    # (bucket) -> minimal interval, soniya — client tomonidagi yumshoq throttling
    intervals: dict = {}
    _last_call: dict = {}

    def __init__(self, account, job=None, session=None):
        self.account = account
        self.job = job
        self.session = session or requests.Session()
        self.timeout = getattr(settings, "MP_HTTP_TIMEOUT", 40)
        self._creds = account.credentials if account.credentials_enc else {}
        for v in self._creds.values():
            register_secret(v)

    # ------------------------------------------------------------------ http
    def auth_headers(self) -> dict:
        raise NotImplementedError

    def throttle(self, bucket):
        interval = self.intervals.get(bucket)
        if not interval:
            return
        key = (self.account.pk, bucket)
        last = MarketplaceClient._last_call.get(key, 0)
        wait = last + interval - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        MarketplaceClient._last_call[key] = time.monotonic()

    def request(self, method, path, *, op, params=None, json=None, base=None, bucket=None, ok_statuses=None):
        from ..models import SyncLog

        url = (base or self.base_url).rstrip("/") + path
        if bucket:
            self.throttle(bucket)
        headers = {"Accept": "application/json", **self.auth_headers()}
        if json is not None:
            headers["Content-Type"] = "application/json"
        t0 = time.monotonic()
        status, err, resp = None, "", None
        try:
            resp = self.session.request(method, url, params=params, json=json, headers=headers, timeout=self.timeout)
            status = resp.status_code
        except requests.RequestException as e:
            err = f"{type(e).__name__}: {e}"
        dur = int((time.monotonic() - t0) * 1000)
        ok = status is not None and (status < 400 or status in (ok_statuses or ()))
        if resp is not None and not ok:
            err = self.error_text(resp)
        SyncLog.objects.create(
            account=self.account if self.account.pk else None, job=self.job, operation=op, method=method,
            endpoint=path[:255], http_status=status, ok=ok, duration_ms=dur, error=redact(err)[:2000])
        if status is None:
            raise RetryableError(err or "network error")
        if not ok:
            retry_after = self.retry_after(resp)
            if status in (420, 429) or status >= 500:
                raise RetryableError(f"HTTP {status}: {err}", status=status, retry_after=retry_after)
            if status in (401, 403):
                raise AuthError(f"HTTP {status}: {err}", status=status)
            raise MarketplaceError(f"HTTP {status}: {err}", status=status)
        if not resp.content:
            return None
        try:
            return resp.json()
        except ValueError:
            return resp.text

    @staticmethod
    def retry_after(resp):
        for h in ("Retry-After", "X-Ratelimit-Retry", "X-RateLimit-Retry"):
            v = resp.headers.get(h)
            if v:
                try:
                    return float(v)
                except ValueError:
                    pass
        return None

    @staticmethod
    def error_text(resp) -> str:
        try:
            d = resp.json()
        except ValueError:
            return resp.text[:500]
        if isinstance(d, dict):
            for k in ("message", "errorText", "detail", "title", "error"):
                if d.get(k) and isinstance(d[k], str):
                    return d[k][:500]
            errs = d.get("errors")
            if isinstance(errs, list) and errs:
                return "; ".join(str(e.get("message") or e.get("code") or e) if isinstance(e, dict) else str(e)
                                 for e in errs)[:500]
        return str(d)[:500]

    # ------------------------------------------------------------ interface
    def check_credentials(self) -> dict:
        """-> {"ok": bool, "message": str, "expires_at": datetime|None, "meta": {...},
               "cabinet_id": str|None, "campaign_id": str|None, "warehouse_id": str|None}"""
        raise NotSupported("check_credentials")

    def fetch_categories(self) -> list[dict]:
        """-> [{"id", "type_id", "name", "path", "leaf": bool}] — faqat mahsulot joylash mumkin bo'lgan (barg) tugunlar."""
        raise NotSupported("Bu marketplace kategoriyalarni API orqali bermaydi")

    def fetch_category_attributes(self, category_id, type_id="") -> list[dict]:
        """-> [{"id", "name", "required", "multi", "dictionary": bool, "type", "values": [{"id","value"}]}]"""
        raise NotSupported("Bu marketplace atributlarni API orqali bermaydi")

    def search_attribute_values(self, category_id, type_id, attribute_id, query) -> list[dict]:
        raise NotSupported("search_attribute_values")

    def upsert_products(self, items: list[ProductPayload]) -> dict:
        """-> {"task_id": str, "results": {offer_id: {"status": pending|error|active, "error": str,
               "external_id": str, "external_sku": str}}}"""
        raise NotSupported("Bu marketplace kartochkani API orqali yaratishga ruxsat bermaydi")

    def get_product_status(self, refs: list[ListingRef]) -> dict:
        """-> {offer_id: {"status": pending|active|rejected|error, "error", "external_id", "external_sku", "external_meta"}}"""
        raise NotSupported("get_product_status")

    def fetch_remote_products(self) -> list[dict]:
        """Kabinetdagi mavjud kartochkalar -> [{"external_id","external_sku","offer_id","title","barcode","meta"}]"""
        raise NotSupported("fetch_remote_products")

    def update_prices(self, refs: list[ListingRef]) -> dict:
        """-> {offer_id: None | "xato matni"}"""
        raise NotSupported("update_prices")

    def update_stocks(self, refs: list[ListingRef]) -> dict:
        """-> {offer_id: None | "xato matni"}"""
        raise NotSupported("update_stocks")

    def fetch_orders(self, since) -> list[dict]:
        """-> [{"external_id","scheme","status","state","items":[{"offer_id","external_sku","name","qty","price"}],
                "total","currency","ordered_at","raw"}]"""
        raise NotSupported("fetch_orders")

    def update_order_status(self, order, action: str, **kw) -> None:
        """action: confirm | ship | cancel | deliver"""
        raise NotSupported("update_order_status")

    @classmethod
    def order_actions(cls, order) -> list[str]:
        return []


def chunks(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def num(v):
    """Decimal -> JSON uchun son (butun bo'lsa int)."""
    if v is None:
        return None
    d = Decimal(v)
    return int(d) if d == d.to_integral_value() else float(d)
