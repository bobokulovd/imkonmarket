"""Yandex Market Partner API adapteri. Konspekt: docs/integrations/yandex.md

Manba: rasmiy OpenAPI (github.com/yandex-market/yandex-market-partner-api). Auth: `Api-Key` sarlavhasi.
O'zbekiston (Market Yandex Go) sotuvchilari uchun domen .net (account.options["domain"] = "net").
"""
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from .base import (CAP_CATEGORIES, CAP_CREATE, CAP_ORDER_ACTIONS, CAP_ORDERS, CAP_PRICES, CAP_STOCKS,
                   MarketplaceClient, MarketplaceError, ProductPayload, chunks, num)

STATE = {
    "PLACING": "new", "RESERVED": "new", "UNPAID": "new", "PENDING": "new",
    "PROCESSING": "processing",
    "DELIVERY": "shipped", "PICKUP": "shipped",
    "DELIVERED": "delivered",
    "CANCELLED": "cancelled",
    "PARTIALLY_RETURNED": "returned", "RETURNED": "returned",
}
ACTIVE_CARD = {"HAS_CARD_CAN_UPDATE", "HAS_CARD_CAN_NOT_UPDATE", "HAS_CARD_CAN_UPDATE_ERRORS", "NO_CARD_ADD_TO_CAMPAIGN"}
PENDING_CARD = {"HAS_CARD_CAN_UPDATE_PROCESSING", "NO_CARD_PROCESSING", "NO_CARD_MARKET_WILL_CREATE"}
REJECTED_CARD = {"NO_CARD_NEED_CONTENT", "NO_CARD_ERRORS"}


def ycur(code):
    """Yandex CurrencyType'da rubl — RUR (RUB emas)."""
    return "RUR" if code == "RUB" else code


def _errs(items):
    out = []
    for e in items or []:
        if isinstance(e, dict):
            out.append(" ".join(str(x) for x in (e.get("message"), e.get("comment")) if x) or str(e))
        else:
            out.append(str(e))
    return "; ".join(out)


class YandexClient(MarketplaceClient):
    code = "yandex"
    capabilities = {CAP_CATEGORIES, CAP_CREATE, CAP_PRICES, CAP_STOCKS, CAP_ORDERS, CAP_ORDER_ACTIONS}
    # stocks v3: 50 so'rov/min; offer-cards: 100/min; categories/tree: 50/soat (keshlanadi)
    intervals = {"stocks": 1.3, "cards": 0.7, "default": 0.25}

    @property
    def base_url(self):
        domain = (self.account.options or {}).get("domain", "ru")
        return f"https://api.partner.market.yandex.{'net' if domain == 'net' else 'ru'}"

    def auth_headers(self):
        return {"Api-Key": self._creds.get("api_key", "")}

    @property
    def business(self):
        if not self.account.cabinet_id:
            raise MarketplaceError("businessId aniqlanmagan — avval kalitni tekshiring")
        return self.account.cabinet_id

    # ---------------------------------------------------------------- auth
    def check_credentials(self):
        tok = self.request("POST", "/v2/auth/token", op="check_credentials") or {}
        key = (tok.get("result") or {}).get("apiKey") or {}
        camps, page = [], 1
        while True:
            d = self.request("GET", "/v2/campaigns", op="check_credentials", params={"page": page, "pageSize": 100}) or {}
            camps += d.get("campaigns") or []
            pager = d.get("pager") or {}
            if not pager or page >= (pager.get("pagesCount") or 1):
                break
            page += 1
        campaigns = [{
            "id": str(c.get("id")), "domain": c.get("domain"), "placement": c.get("placementType"),
            "api": c.get("apiAvailability"), "business_id": str((c.get("business") or {}).get("id") or ""),
            "business_name": (c.get("business") or {}).get("name"),
        } for c in camps]
        business_id = self.account.cabinet_id or next((c["business_id"] for c in campaigns if c["business_id"]), "")
        mine = [c for c in campaigns if c["business_id"] == business_id]
        campaign_id = self.account.campaign_id or (mine[0]["id"] if len(mine) == 1 else None)
        warehouses = []
        if business_id:
            w = self.request("POST", f"/v3/businesses/{business_id}/warehouses", op="check_credentials", json={}) or {}
            warehouses = [{"id": str(x.get("id")), "name": x.get("name"), "models": x.get("models")}
                          for x in ((w.get("result") or {}).get("warehouses") or [])]
        disabled = [c for c in mine if c["api"] and c["api"] != "AVAILABLE"]
        ok = bool(mine) and len(disabled) < len(mine)
        return {
            "ok": ok,
            "message": "" if ok else ("Kabinetda API uchun ochiq magazin topilmadi" + (
                f" ({', '.join(c['api'] for c in disabled)})" if disabled else "")),
            "expires_at": None,
            "meta": {"scopes": key.get("authScopes") or [], "key_name": key.get("name"), "campaigns": campaigns,
                     "warehouses": warehouses},
            "cabinet_id": business_id or None,
            "campaign_id": campaign_id,
            "warehouse_id": warehouses[0]["id"] if len(warehouses) == 1 else None,
        }

    # ----------------------------------------------------------- catalogue
    def fetch_categories(self):
        d = self.request("POST", "/v2/categories/tree", op="fetch_categories", json={"language": "RU"}) or {}
        out = []

        def walk(node, path):
            name = node.get("name") or ""
            p = f"{path} / {name}" if path else name
            kids = node.get("children") or []
            if not kids:
                out.append({"id": str(node.get("id")), "type_id": "", "name": name, "path": p, "leaf": True})
            for k in kids:
                walk(k, p)

        root = d.get("result") or {}
        for k in root.get("children") or ([root] if root else []):
            walk(k, "")
        return out

    def fetch_category_attributes(self, category_id, type_id=""):
        d = self.request("POST", f"/v2/category/{category_id}/parameters", op="fetch_category_attributes",
                         params={"businessId": self.account.cabinet_id} if self.account.cabinet_id else None) or {}
        res = []
        for p in (d.get("result") or {}).get("parameters") or []:
            res.append({
                "id": str(p.get("id")), "name": p.get("name"), "required": bool(p.get("required")),
                "multi": bool(p.get("multivalue")), "dictionary": p.get("type") == "ENUM" and not p.get("allowCustomValues"),
                "type": p.get("type"), "unit": ((p.get("unit") or {}).get("defaultUnitId")),
                "values": [{"id": str(v.get("id")), "value": v.get("value")} for v in (p.get("values") or [])][:500],
            })
        return res

    # ------------------------------------------------------------- products
    def _offer(self, it: ProductPayload):
        offer = {
            "offerId": it.offer_id, "name": it.name[:256], "marketCategoryId": int(it.category_id),
            "pictures": it.images[:30], "vendor": it.brand or "ImkonMarket", "description": it.description[:6000],
        }
        if it.barcode:
            offer["barcodes"] = [it.barcode]
        if it.country:
            offer["manufacturerCountries"] = [it.country]
        if all(x is not None for x in (it.length_cm, it.width_cm, it.height_cm, it.weight_kg)):
            offer["weightDimensions"] = {"length": num(it.length_cm), "width": num(it.width_cm),
                                         "height": num(it.height_cm), "weight": num(it.weight_kg)}
        params = []
        for a in it.attributes:
            pv = {"parameterId": int(a["id"])}
            if a.get("value_id"):
                pv["valueId"] = int(a["value_id"])
            else:
                pv["value"] = str(a.get("value"))
            params.append(pv)
        m = {"offer": offer}
        if params:
            m["offer"]["parameterValues"] = params
        if it.price is not None:
            m["offer"]["basicPrice"] = {"value": num(it.price), "currencyId": ycur(it.currency)}
        return m

    def upsert_products(self, items):
        lang = (self.account.options or {}).get("language", "RU")
        results = {}
        for part in chunks(items, 100):  # hujjat: 100 dan oshirmang
            d = self.request("POST", f"/v2/businesses/{self.business}/offer-mappings/update", op="upsert_products",
                             params={"language": lang}, json={"offerMappings": [self._offer(i) for i in part]}) or {}
            bad = {r.get("offerId"): _errs(r.get("errors")) for r in (d.get("results") or []) if r.get("errors")}
            for it in part:
                if it.offer_id in bad:
                    results[it.offer_id] = {"status": "error", "error": bad[it.offer_id]}
                elif bad:
                    # Paketda xato bo'lsa, Market birortasini ham qo'llamaydi — bular qayta yuboriladi
                    results[it.offer_id] = {"status": "retry", "error": "Paketdagi boshqa tovar xatosi sabab qo'llanmadi"}
                else:
                    results[it.offer_id] = {"status": "pending", "error": ""}
        return {"task_id": "", "results": results}

    def get_product_status(self, refs):
        out = {}
        for part in chunks(refs, 200):
            self.throttle("cards")
            d = self.request("POST", f"/v2/businesses/{self.business}/offer-cards", op="get_product_status",
                             json={"offerIds": [r.offer_id for r in part]}) or {}
            for c in (d.get("result") or {}).get("offerCards") or []:
                st = c.get("cardStatus")
                status = ("active" if st in ACTIVE_CARD else "pending" if st in PENDING_CARD
                          else "rejected" if st in REJECTED_CARD else "pending")
                out[c.get("offerId")] = {
                    "status": status, "error": _errs(c.get("errors")),
                    "external_id": str((c.get("mapping") or {}).get("marketSku") or ""),
                    "external_meta": {"cardStatus": st},
                }
        return out

    def update_prices(self, refs):
        out = {}
        for part in chunks(refs, 500):
            self.request("POST", f"/v2/businesses/{self.business}/offer-prices/updates", op="update_prices",
                         json={"offers": [{"offerId": r.offer_id, "price": {"value": num(r.price), "currencyId": ycur(r.currency)}}
                                          for r in part]})
            out.update({r.offer_id: None for r in part})
        return out

    def update_stocks(self, refs):
        out = {}
        now = timezone.now().isoformat()
        wh = self.account.warehouse_id
        if wh:
            for part in chunks(refs, 2000):
                self.throttle("stocks")
                self.request("POST", f"/v3/businesses/{self.business}/offers/stocks/update", op="update_stocks",
                             json={"skuItems": [{"sku": r.offer_id, "partnerWarehouseId": int(wh), "count": max(r.stock, 0),
                                                 "updatedAt": now} for r in part]})
                out.update({r.offer_id: None for r in part})
        elif self.account.campaign_id:  # sklad guruhlari rejimi
            for part in chunks(refs, 2000):
                self.request("PUT", f"/v2/campaigns/{self.account.campaign_id}/offers/stocks", op="update_stocks",
                             json={"skus": [{"sku": r.offer_id, "items": [{"count": max(r.stock, 0), "updatedAt": now}]}
                                            for r in part]})
                out.update({r.offer_id: None for r in part})
        else:
            raise MarketplaceError("Ombor (partnerWarehouseId) yoki kampaniya tanlanmagan")
        return out

    # --------------------------------------------------------------- orders
    def fetch_orders(self, since):
        since = max(since, timezone.now() - timedelta(days=29))
        body = {"dates": {"updateDateFrom": since.isoformat(timespec="seconds")}}
        if self.account.campaign_id:
            body["campaignIds"] = [int(self.account.campaign_id)]
        out, token = [], None
        for _ in range(200):
            params = {"limit": 50}
            if token:
                params["pageToken"] = token
            d = self.request("POST", f"/v1/businesses/{self.business}/orders", op="fetch_orders", params=params, json=body) or {}
            for o in d.get("orders") or []:
                if o.get("fake"):
                    continue
                items = []
                for it in o.get("items") or []:
                    pr = it.get("prices") or {}
                    line = sum(Decimal(str((pr.get(k) or {}).get("value") or 0)) for k in ("payment", "cashback"))
                    qty = int(it.get("count") or 0)
                    items.append({"offer_id": it.get("offerId"), "external_sku": str(it.get("id") or ""),
                                  "name": it.get("offerName"), "qty": qty,
                                  "price": str((line / qty).quantize(Decimal("0.01"))) if qty else "0"})
                pay = ((o.get("prices") or {}).get("payment") or {})
                total = Decimal(str(pay.get("value") or 0)) or sum(Decimal(i["price"]) * i["qty"] for i in items)
                program = o.get("programType") or ""
                out.append({
                    "external_id": str(o.get("orderId")), "scheme": "FBO" if program == "FBY" else program,
                    "status": f"{o.get('status')}/{o.get('substatus')}", "state": STATE.get(o.get("status"), "new"),
                    "items": items, "total": str(total), "currency": {"RUR": "RUB"}.get(pay.get("currencyId"), pay.get("currencyId") or ""),
                    "ordered_at": o.get("creationDate"), "raw": o,
                })
            token = (d.get("paging") or {}).get("nextPageToken")
            if not token:
                break
        return out

    @classmethod
    def order_actions(cls, order):
        raw = order.raw or {}
        if order.scheme == "FBO":
            return []
        st, sub = raw.get("status"), raw.get("substatus")
        acts = []
        if st == "PROCESSING" and sub == "STARTED":
            acts.append("confirm")
        if st == "PROCESSING" and sub in ("STARTED", "READY_TO_SHIP"):
            acts.append("cancel")
        if order.scheme == "DBS" and st == "PROCESSING" and sub == "READY_TO_SHIP":
            acts.append("ship")
        if order.scheme == "DBS" and st in ("DELIVERY", "PICKUP"):
            acts.append("deliver")
        return acts

    def update_order_status(self, order, action, **kw):
        campaign = str((order.raw or {}).get("campaignId") or self.account.campaign_id)
        change = {
            "confirm": {"status": "PROCESSING", "substatus": "READY_TO_SHIP"},
            "cancel": {"status": "CANCELLED", "substatus": "SHOP_FAILED"},
            "ship": {"status": "DELIVERY"},
            "deliver": {"status": "DELIVERED"},
        }.get(action)
        if not change:
            raise MarketplaceError(f"Noma'lum amal: {action}")
        self.request("PUT", f"/v2/campaigns/{campaign}/orders/{order.external_id}/status", op="update_order_status",
                     json={"order": change})
