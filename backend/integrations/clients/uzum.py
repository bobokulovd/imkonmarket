"""Uzum Market Seller OpenAPI adapteri. Konspekt: docs/integrations/uzum.md

Muhim: Uzum ochiq API'sida kartochka yaratish YO'Q — muassasa kartochkani seller.uzum.uz kabinetida yaratadi,
ImkonMarket esa uni SKU orqali bog'laydi (link_existing) va narx, qoldiq (FBS/DBS) hamda buyurtmalarni yuritadi.
Auth: `Authorization: <token>` (Bearer prefiksisiz). Javoblar ba'zan {payload, errors} konvertida keladi.
"""
from datetime import datetime, timezone as dt_tz
from decimal import Decimal

from .base import (CAP_LINK, CAP_ORDER_ACTIONS, CAP_ORDERS, CAP_PRICES, CAP_STOCKS, MarketplaceClient,
                   MarketplaceError, chunks, num)

STATE = {
    "CREATED": "new", "PACKING": "processing",
    "PENDING_DELIVERY": "shipped", "DELIVERING": "shipped", "ACCEPTED_AT_DP": "shipped",
    "DELIVERED_TO_CUSTOMER_DELIVERY_POINT": "shipped",
    "DELIVERED": "delivered", "COMPLETED": "delivered",
    "CANCELED": "cancelled", "PENDING_CANCELLATION": "cancelled",
    "RETURNED": "returned",
}
# Uzum `status` bo'lmasa bo'sh ro'yxat qaytaradi — har bir status alohida so'raladi
ORDER_STATUSES = list(STATE)


def unwrap(d):
    if isinstance(d, dict):
        errs = d.get("errors")
        if isinstance(errs, list) and errs:
            e = errs[0]
            raise MarketplaceError(str(e.get("message") or e.get("code") or e) if isinstance(e, dict) else str(e))
        if "payload" in d:
            return d["payload"]
    return d


class UzumClient(MarketplaceClient):
    code = "uzum"
    base_url = "https://api-seller.uzum.uz/api/seller-openapi"
    capabilities = {CAP_LINK, CAP_PRICES, CAP_STOCKS, CAP_ORDERS, CAP_ORDER_ACTIONS}
    intervals = {"default": 0.3}

    def auth_headers(self):
        return {"Authorization": self._creds.get("api_key", "")}

    def call(self, method, path, **kw):
        return unwrap(self.request(method, path, bucket="default", **kw))

    @property
    def shop(self):
        if not self.account.cabinet_id:
            raise MarketplaceError("Do'kon (shopId) tanlanmagan")
        return self.account.cabinet_id

    def check_credentials(self):
        shops = self.call("GET", "/v1/shops", op="check_credentials") or []
        if isinstance(shops, dict):
            shops = shops.get("shops") or shops.get("list") or []
        shops = [{"id": str(s.get("id")), "name": s.get("name") or s.get("shopTitle")} for s in shops if isinstance(s, dict)]
        ids = [s["id"] for s in shops]
        cabinet = self.account.cabinet_id if self.account.cabinet_id in ids else (ids[0] if len(ids) == 1 else None)
        return {"ok": bool(shops), "message": "" if shops else "Token ishlaydi, lekin do'kon topilmadi",
                "expires_at": None, "meta": {"shops": shops}, "cabinet_id": cabinet}

    def fetch_remote_products(self):
        out, page = [], 0
        while page < 500:
            d = self.call("GET", f"/v1/product/shop/{self.shop}", op="fetch_remote_products",
                          params={"size": 100, "page": page, "filter": "ALL"}) or {}
            products = d.get("productList") or d.get("products") or (d if isinstance(d, list) else [])
            for p in products:
                for s in p.get("skuList") or []:
                    out.append({
                        "external_id": str(p.get("productId") or ""), "external_sku": str(s.get("skuId") or ""),
                        "offer_id": s.get("sellerItemCode") or s.get("sellerSkuCode") or "",
                        "title": s.get("skuFullTitle") or s.get("skuTitle") or p.get("title") or "",
                        "barcode": str(s.get("barcode") or ""),
                        "meta": {"sku_title": s.get("skuTitle") or "", "barcode": str(s.get("barcode") or ""),
                                 "product_title": p.get("title") or ""},
                    })
            if len(products) < 100:
                break
            page += 1
        return out

    def get_product_status(self, refs):
        """Moderatsiya statusi endpointi yo'q: bog'langan SKU kabinetda bor-yo'qligini tekshiramiz."""
        remote = {r["external_sku"]: r for r in self.fetch_remote_products()}
        out = {}
        for r in refs:
            m = remote.get(r.external_sku)
            out[r.offer_id] = ({"status": "active", "error": "", "external_id": m["external_id"], "external_meta": m["meta"]}
                               if m else {"status": "error", "error": "SKU Uzum kabinetida topilmadi"})
        return out

    def update_prices(self, refs):
        out = {}
        by_product = {}
        for r in refs:
            if not r.external_id or not r.external_sku:
                out[r.offer_id] = "Uzum SKU bog'lanmagan"
                continue
            by_product.setdefault(r.external_id, []).append(r)
        for product_id, items in by_product.items():
            self.call("POST", f"/v1/product/{self.shop}/sendPriceData", op="update_prices", json={
                "productId": int(product_id),
                "skuList": [{"skuId": int(r.external_sku), "skuTitle": r.external_meta.get("sku_title", ""),
                             "sellPrice": num(r.price), "fullPrice": num(r.price)} for r in items],
            })
            out.update({r.offer_id: None for r in items})
        return out

    def update_stocks(self, refs):
        out, rows = {}, []
        for r in refs:
            barcode = r.external_meta.get("barcode")
            if not barcode:
                out[r.offer_id] = "Uzum SKU shtrix-kodi yo'q (qoldiq barcode bo'yicha yangilanadi)"
                continue
            rows.append((r, {"barcode": str(barcode), "amount": max(r.stock, 0)}))
        for part in chunks(rows, 100):
            self.call("POST", "/v2/fbs/sku/stocks", op="update_stocks", json={"skuAmountList": [x[1] for x in part]})
            out.update({x[0].offer_id: None for x in part})
        return out

    def fetch_orders(self, since):
        out = {}
        date_from = int(since.timestamp())
        for status in ORDER_STATUSES:
            page = 0
            while page < 100:
                d = self.call("GET", "/v2/fbs/orders", op="fetch_orders", params={
                    "shopIds": self.shop, "status": status, "dateFrom": date_from, "page": page, "size": 50}) or {}
                orders = d.get("orders") or []
                for o in orders:
                    items = [{"offer_id": it.get("sellerSkuCode") or it.get("sellerItemCode") or "",
                              "external_sku": str(it.get("skuId") or ""), "name": it.get("skuTitle") or it.get("productTitle"),
                              "qty": int(it.get("amount") or 1),
                              "price": str(it.get("sellerPrice") or it.get("sellPrice") or it.get("price") or 0)}
                             for it in o.get("orderItems") or []]
                    created = o.get("dateCreated")
                    if isinstance(created, (int, float)):
                        created = datetime.fromtimestamp(created / 1000, tz=dt_tz.utc).isoformat()
                    out[str(o.get("id"))] = {
                        "external_id": str(o.get("id")), "scheme": o.get("scheme") or "FBS", "status": o.get("status"),
                        "state": STATE.get(o.get("status"), "new"), "items": items,
                        "total": str(o.get("price") or sum(Decimal(i["price"]) * i["qty"] for i in items)),
                        "currency": "UZS", "ordered_at": created, "raw": o,
                    }
                if len(orders) < 50:
                    break
                page += 1
        return list(out.values())

    @classmethod
    def order_actions(cls, order):
        st = (order.raw or {}).get("status") or order.status
        acts = []
        if st == "CREATED":
            acts.append("confirm")
        if st not in ("CANCELED", "COMPLETED", "RETURNED", "DELIVERED", "PENDING_CANCELLATION"):
            acts.append("cancel")
        if order.scheme == "DBS" and st == "PACKING":
            acts.append("ship")
        if order.scheme == "DBS" and st in ("DELIVERING", "DELIVERED"):
            acts.append("deliver")
        return acts

    def update_order_status(self, order, action, **kw):
        oid = order.external_id
        if action == "confirm":
            self.call("POST", f"/v1/fbs/order/{oid}/confirm", op="update_order_status")
        elif action == "cancel":
            self.call("POST", f"/v1/fbs/order/{oid}/cancel", op="update_order_status",
                      json={"reason": kw.get("reason") or "OUT_OF_STOCK", "comment": kw.get("comment") or ""})
        elif action == "ship":
            self.call("POST", f"/v1/dbs/order/{oid}/delivering", op="update_order_status")
        elif action == "deliver":
            params = {"issueCode": kw["issue_code"]} if kw.get("issue_code") else None
            self.call("POST", f"/v1/dbs/order/{oid}/completed", op="update_order_status", params=params)
        else:
            raise MarketplaceError(f"Noma'lum amal: {action}")
