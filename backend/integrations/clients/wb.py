"""Wildberries API adapteri. Konspekt: docs/integrations/wb.md

Auth: `Authorization: <JWT token>` (Servis tokeni tavsiya etiladi — Personal token bulut xizmatlarida ishlatilmasin).
Kartochka: /content/v2/cards/upload (async) → /content/v2/cards/error/list + /content/v2/get/cards/list → media/save.
"""
import base64
import json
from datetime import datetime, timezone as dt_tz
from decimal import Decimal

from django.utils import timezone

from .base import (CAP_CATEGORIES, CAP_CREATE, CAP_ORDER_ACTIONS, CAP_ORDERS, CAP_PRICES, CAP_STOCKS,
                   MarketplaceClient, MarketplaceError, ProductPayload, chunks, num)

CONTENT = "https://content-api.wildberries.ru"
PRICES = "https://discounts-prices-api.wildberries.ru"
MARKET = "https://marketplace-api.wildberries.ru"

SUPPLIER_STATE = {"new": "new", "confirm": "processing", "complete": "shipped", "cancel": "cancelled"}
WB_CANCEL = {"canceled", "canceled_by_client", "declined_by_client", "defect"}


def jwt_claims(token: str) -> dict:
    try:
        part = token.split(".")[1]
        part += "=" * (-len(part) % 4)
        return json.loads(base64.urlsafe_b64decode(part.encode()))
    except Exception:  # noqa: BLE001
        return {}


class WBClient(MarketplaceClient):
    code = "wb"
    base_url = CONTENT
    capabilities = {CAP_CATEGORIES, CAP_CREATE, CAP_PRICES, CAP_STOCKS, CAP_ORDERS, CAP_ORDER_ACTIONS}
    # content upload/update/error-list: 10/min (6 s); content boshqa: 100/min; prices: 10 / 6 s; marketplace: 300/min
    intervals = {"content_write": 6.2, "content": 0.65, "prices": 0.65, "market": 0.21}

    def auth_headers(self):
        return {"Authorization": self._creds.get("api_key", "")}

    # ---------------------------------------------------------------- auth
    def check_credentials(self):
        token = self._creds.get("api_key", "")
        claims = jwt_claims(token)
        exp = datetime.fromtimestamp(claims["exp"], tz=dt_tz.utc) if claims.get("exp") else None
        acc = str(claims.get("acc", ""))
        token_type = {"1": "base", "2": "test", "3": "personal"}.get(acc, "service" if acc.startswith("asid") else acc)
        self.request("GET", "/ping", op="check_credentials", base=CONTENT)
        wh = self.request("GET", "/api/v3/warehouses", op="check_credentials", base=MARKET, bucket="market") or []
        warehouses = [{"id": str(w.get("id")), "name": w.get("name"), "office_id": w.get("officeId")}
                      for w in wh if isinstance(w, dict) and not w.get("isDeleting")]
        msg = ""
        if token_type == "personal":
            msg = "Personal token: WB qoidasiga ko'ra bulut xizmatlarida Servis tokeni ishlatilishi kerak"
        return {"ok": True, "message": msg, "expires_at": exp,
                "meta": {"token_type": token_type, "warehouses": warehouses},
                "warehouse_id": warehouses[0]["id"] if len(warehouses) == 1 else None}

    # ----------------------------------------------------------- catalogue
    def fetch_categories(self):
        out, offset = [], 0
        while offset < 50000:
            d = self.request("GET", "/content/v2/object/all", op="fetch_categories", base=CONTENT, bucket="content",
                             params={"limit": 1000, "offset": offset, "locale": "ru"}) or {}
            rows = d.get("data") or []
            for s in rows:
                out.append({"id": str(s.get("subjectID")), "type_id": "", "name": s.get("subjectName") or "",
                            "path": f"{s.get('parentName') or ''} / {s.get('subjectName') or ''}", "leaf": True})
            if len(rows) < 1000:
                break
            offset += 1000
        return out

    def fetch_category_attributes(self, category_id, type_id=""):
        d = self.request("GET", f"/content/v2/object/charcs/{category_id}", op="fetch_category_attributes",
                         base=CONTENT, bucket="content", params={"locale": "ru"}) or {}
        return [{"id": str(c.get("charcID")), "name": c.get("name"), "required": bool(c.get("required")),
                 "multi": (c.get("maxCount") or 0) != 1, "dictionary": False,
                 "type": "number" if c.get("charcType") == 4 else "string", "unit": c.get("unitName"), "values": []}
                for c in d.get("data") or []]

    # ------------------------------------------------------------- products
    def _barcodes(self, count):
        d = self.request("POST", "/content/v2/barcodes", op="upsert_products", base=CONTENT, bucket="content",
                         json={"count": count}) or {}
        return list(d.get("data") or [])

    @staticmethod
    def _characteristics(it: ProductPayload):
        chars = {}
        for a in it.attributes:
            v = a.get("value")
            if a.get("type") == "number":
                try:
                    v = float(v)
                    v = int(v) if v.is_integer() else v
                except (TypeError, ValueError):
                    pass
                chars[int(a["id"])] = v
            else:
                chars.setdefault(int(a["id"]), []).append(str(v))
        return [{"id": k, "value": v} for k, v in chars.items()]

    def _dims(self, it):
        d = {}
        if it.length_cm is not None:
            d.update(length=num(it.length_cm), width=num(it.width_cm), height=num(it.height_cm))
        if it.weight_kg is not None:
            d["weightBrutto"] = num(it.weight_kg)
        return d

    def upsert_products(self, items):
        results = {}
        new = [i for i in items if not i.external_id]
        upd = [i for i in items if i.external_id]
        missing = [i for i in new if not i.barcode]
        codes = self._barcodes(len(missing)) if missing else []
        for it, code in zip(missing, codes):
            it.barcode = code
            results.setdefault(it.offer_id, {})["barcode"] = code
        for part in chunks(new, 100):
            body = [{"subjectID": int(i.category_id), "variants": [{
                "vendorCode": i.offer_id, "title": i.name[:60], "description": i.description[:5000],
                "brand": i.brand or "", "dimensions": self._dims(i), "characteristics": self._characteristics(i),
                "sizes": [{"price": int(i.price) if i.price is not None else 0, "skus": [i.barcode] if i.barcode else []}],
            }]} for i in part]
            self.request("POST", "/content/v2/cards/upload", op="upsert_products", base=CONTENT, bucket="content_write",
                         json=body)
            for i in part:
                results[i.offer_id] = {**results.get(i.offer_id, {}), "status": "pending", "error": ""}
        for part in chunks(upd, 100):
            body = []
            for i in part:
                card = {"nmID": int(i.external_id), "vendorCode": i.offer_id, "title": i.name[:60],
                        "description": i.description[:5000], "brand": i.brand or "", "dimensions": self._dims(i),
                        "characteristics": self._characteristics(i)}
                if i.external_sku:  # o'lchamsiz yuborilsa WB mavjud o'lchamlarni o'chirib yuborishi mumkin
                    card["sizes"] = [{"chrtID": int(i.external_sku), "skus": [i.barcode] if i.barcode else []}]
                body.append(card)
            self.request("POST", "/content/v2/cards/update", op="upsert_products", base=CONTENT, bucket="content_write",
                         json=body)
            for i in part:
                results[i.offer_id] = {"status": "pending", "error": ""}
        return {"task_id": "", "results": results}

    def get_product_status(self, refs):
        out = {}
        wanted = {r.offer_id: r for r in refs}
        # 1) yaratilmagan kartochkalar xatolari
        d = self.request("POST", "/content/v2/cards/error/list", op="get_product_status", base=CONTENT,
                         bucket="content_write", json={"cursor": {"limit": 100}, "order": {"ascending": False}}) or {}
        data = d.get("data") or {}
        rows = data.get("items") if isinstance(data, dict) else data
        for row in rows or []:
            errs = row.get("errors")
            text = "; ".join(sum(errs.values(), [])) if isinstance(errs, dict) else "; ".join(map(str, errs or []))
            for vc in row.get("vendorCodes") or ([row.get("vendorCode")] if row.get("vendorCode") else []):
                if vc in wanted:
                    out[vc] = {"status": "error", "error": text or "WB kartochkani qabul qilmadi"}
        # 2) yaratilganlari (nmID, chrtID)
        for r in refs:
            d = self.request("POST", "/content/v2/get/cards/list", op="get_product_status", base=CONTENT,
                             bucket="content", json={"settings": {"cursor": {"limit": 10},
                                                                  "filter": {"textSearch": r.offer_id, "withPhoto": -1}}}) or {}
            card = next((c for c in d.get("cards") or [] if c.get("vendorCode") == r.offer_id), None)
            if card:
                size = (card.get("sizes") or [{}])[0]
                out[r.offer_id] = {
                    "status": "active", "error": "", "external_id": str(card.get("nmID")),
                    "external_sku": str(size.get("chrtID") or ""),
                    "external_meta": {"imtID": card.get("imtID"), "photos": len(card.get("photos") or []),
                                      "barcode": (size.get("skus") or [""])[0]},
                }
        return out

    def upload_media(self, nm_id, urls):
        self.request("POST", "/content/v3/media/save", op="upload_media", base=CONTENT, bucket="content",
                     json={"nmId": int(nm_id), "data": urls[:30]})

    def update_prices(self, refs):
        out, rows = {}, []
        for r in refs:
            if not r.external_id:
                out[r.offer_id] = "nmID hali yo'q"
            else:
                rows.append(r)
        for part in chunks(rows, 1000):
            self.request("POST", "/api/v2/upload/task", op="update_prices", base=PRICES, bucket="prices",
                         json={"data": [{"nmID": int(r.external_id), "price": int(r.price), "discount": 0} for r in part]},
                         ok_statuses={208})  # 208 — xuddi shu narxlar allaqachon yuborilgan
            out.update({r.offer_id: None for r in part})
        return out

    def update_stocks(self, refs):
        wh = self.account.warehouse_id
        if not wh:
            raise MarketplaceError("WB sotuvchi ombori tanlanmagan")
        out, rows = {}, []
        for r in refs:
            if not r.external_sku:
                out[r.offer_id] = "chrtID hali yo'q"
            else:
                rows.append(r)
        for part in chunks(rows, 1000):
            self.request("PATCH", f"/api/v3/stocks/{wh}", op="update_stocks", base=MARKET, bucket="market",
                         json={"stocks": [{"chrtId": int(r.external_sku), "amount": max(r.stock, 0)} for r in part]})
            out.update({r.offer_id: None for r in part})
        return out

    # --------------------------------------------------------------- orders
    def fetch_orders(self, since):
        raw, nxt = [], 0
        for _ in range(100):
            d = self.request("GET", "/api/v3/orders", op="fetch_orders", base=MARKET, bucket="market",
                             params={"limit": 1000, "next": nxt, "dateFrom": int(since.timestamp())}) or {}
            raw += d.get("orders") or []
            nxt = d.get("next") or 0
            if not d.get("orders") or len(d["orders"]) < 1000 or not nxt:
                break
        statuses = {}
        for part in chunks([o["id"] for o in raw], 1000):
            d = self.request("POST", "/api/v3/orders/status", op="fetch_orders", base=MARKET, bucket="market",
                             json={"orders": part}) or {}
            statuses.update({s.get("id"): s for s in d.get("orders") or []})
        out = []
        for o in raw:
            st = statuses.get(o["id"]) or {}
            sup, wbs = st.get("supplierStatus") or "new", st.get("wbStatus") or ""
            state = SUPPLIER_STATE.get(sup, "new")
            if wbs == "sold":
                state = "delivered"
            elif wbs in WB_CANCEL:
                state = "cancelled"
            price = Decimal(str(o.get("convertedPrice") or o.get("price") or 0)) / 100  # WB narxni tiyinda beradi
            out.append({
                "external_id": str(o["id"]), "scheme": "FBS", "status": f"{sup}/{wbs}" if wbs else sup, "state": state,
                "items": [{"offer_id": o.get("article"), "external_sku": str(o.get("chrtId") or ""),
                           "name": o.get("article"), "qty": 1, "price": str(price)}],
                "total": str(price), "currency": {"643": "RUB", "860": "UZS", "933": "BYN"}.get(
                    str(o.get("convertedCurrencyCode") or o.get("currencyCode") or ""), ""),
                "ordered_at": o.get("createdAt"), "raw": {**o, "_status": st},
            })
        return out

    @classmethod
    def order_actions(cls, order):
        sup = (order.status or "").split("/")[0]
        return {"new": ["confirm", "cancel"], "confirm": ["ship", "cancel"]}.get(sup, [])

    def _options(self):
        from ..models import MarketplaceAccount
        return MarketplaceAccount.objects.filter(pk=self.account.pk).values_list("options", flat=True).first() or {}

    def _save_options(self, opts):
        from ..models import MarketplaceAccount
        MarketplaceAccount.objects.filter(pk=self.account.pk).update(options=opts)
        self.account.options = opts

    def _supply(self):
        opts = self._options()
        if opts.get("wb_supply_id"):
            return opts["wb_supply_id"]
        d = self.request("POST", "/api/v3/supplies", op="update_order_status", base=MARKET, bucket="market",
                         json={"name": f"ImkonMarket {timezone.localdate():%Y-%m-%d}"}) or {}
        sid = d.get("id")
        if not sid:
            raise MarketplaceError("WB postavka yaratilmadi")
        self._save_options({**opts, "wb_supply_id": sid})
        return sid

    def update_order_status(self, order, action, **kw):
        oid = int(order.external_id)
        if action == "confirm":
            sid = self._supply()
            self.request("POST", f"/api/marketplace/v3/supplies/{sid}/orders", op="update_order_status", base=MARKET,
                         bucket="market", json={"orders": [oid]})
        elif action == "ship":
            opts = self._options()
            sid = opts.get("wb_supply_id")
            if not sid:
                raise MarketplaceError("Ochiq postavka yo'q")
            self.request("PATCH", f"/api/v3/supplies/{sid}/deliver", op="update_order_status", base=MARKET, bucket="market")
            self._save_options({k: v for k, v in opts.items() if k != "wb_supply_id"})
        elif action == "cancel":
            self.request("PATCH", f"/api/v3/orders/{oid}/cancel", op="update_order_status", base=MARKET, bucket="market")
        else:
            raise MarketplaceError(f"Noma'lum amal: {action}")
