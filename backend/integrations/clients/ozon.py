"""Ozon Seller API adapteri. Konspekt: docs/integrations/ozon.md

Auth: `Client-Id` (account.cabinet_id) + `Api-Key`. Kalit muddati bor (3–6 oy) — /v1/roles dagi expires_at saqlanadi.
Kartochka: /v3/product/import (async task_id) → /v1/product/import/info → /v3/product/info/list.
"""
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .base import (CAP_CATEGORIES, CAP_CREATE, CAP_ORDER_ACTIONS, CAP_ORDERS, CAP_PRICES, CAP_STOCKS,
                   MarketplaceClient, MarketplaceError, ProductPayload, chunks, num)

FBS_STATE = {
    "awaiting_registration": "new", "acceptance_in_progress": "new", "awaiting_approve": "new",
    "awaiting_packaging": "new", "awaiting_deliver": "processing", "arbitration": "processing",
    "client_arbitration": "processing", "delivering": "shipped", "driver_pickup": "shipped",
    "sent_by_seller": "shipped", "delivered": "delivered", "cancelled": "cancelled", "not_accepted": "cancelled",
}


def _errs(items):
    out = []
    for e in items or []:
        if isinstance(e, dict):
            out.append(str(e.get("message") or e.get("description") or e.get("code") or e))
        else:
            out.append(str(e))
    return "; ".join(out)


def _dim_mm(cm):
    return int(round(float(cm) * 10)) if cm is not None else None


class OzonClient(MarketplaceClient):
    code = "ozon"
    base_url = "https://api-seller.ozon.ru"
    capabilities = {CAP_CATEGORIES, CAP_CREATE, CAP_PRICES, CAP_STOCKS, CAP_ORDERS, CAP_ORDER_ACTIONS}
    # umumiy 50 rps; stocks 80/min
    intervals = {"default": 0.05, "stocks": 0.8}

    def auth_headers(self):
        return {"Client-Id": str(self.account.cabinet_id or ""), "Api-Key": self._creds.get("api_key", "")}

    def post(self, path, body=None, op="", bucket="default"):
        return self.request("POST", path, op=op, json=body if body is not None else {}, bucket=bucket) or {}

    # ---------------------------------------------------------------- auth
    def check_credentials(self):
        if not self.account.cabinet_id:
            raise MarketplaceError("Client-Id kiritilmagan")
        d = self.post("/v1/roles", op="check_credentials")
        roles = d.get("roles") or []
        exp = parse_datetime(d["expires_at"]) if d.get("expires_at") else None
        wh = self.post("/v2/warehouse/list", {"limit": 100}, op="check_credentials")
        warehouses = [{"id": str(w.get("warehouse_id")), "name": w.get("name"), "status": w.get("status"),
                       "rfbs": w.get("is_rfbs")}
                      for w in (wh.get("warehouses") or wh.get("result") or []) if isinstance(w, dict)]
        active = [w for w in warehouses if (w.get("status") or "").lower() not in ("disabled", "archived", "blocked")]
        return {
            "ok": True, "message": "", "expires_at": exp,
            "meta": {"roles": [r.get("name") for r in roles], "warehouses": warehouses},
            "warehouse_id": active[0]["id"] if len(active) == 1 else None,
        }

    # ----------------------------------------------------------- catalogue
    def fetch_categories(self):
        d = self.post("/v1/description-category/tree", {"language": "DEFAULT"}, op="fetch_categories")
        out = []

        def walk(node, path, cat_id):
            if node.get("type_id"):
                out.append({"id": str(cat_id), "type_id": str(node["type_id"]), "name": node.get("type_name") or "",
                            "path": f"{path} / {node.get('type_name')}", "leaf": True})
                return
            if node.get("disabled"):
                return
            name = node.get("category_name") or ""
            p = f"{path} / {name}" if path else name
            for k in node.get("children") or []:
                walk(k, p, node.get("description_category_id") or cat_id)

        for n in d.get("result") or []:
            walk(n, "", n.get("description_category_id"))
        return out

    def fetch_category_attributes(self, category_id, type_id=""):
        if not type_id:
            raise MarketplaceError("Ozon uchun type_id kerak")
        d = self.post("/v1/description-category/attribute", {
            "description_category_id": int(category_id), "type_id": int(type_id), "language": "DEFAULT"},
            op="fetch_category_attributes")
        return [{"id": str(a.get("id")), "name": a.get("name"), "required": bool(a.get("is_required")),
                 "multi": bool(a.get("is_collection")), "dictionary": bool(a.get("dictionary_id")),
                 "type": a.get("type"), "values": []} for a in d.get("result") or []]

    def search_attribute_values(self, category_id, type_id, attribute_id, query):
        body = {"attribute_id": int(attribute_id), "description_category_id": int(category_id),
                "type_id": int(type_id), "limit": 50}
        if query and len(query) >= 2:
            d = self.post("/v1/description-category/attribute/values/search", {**body, "value": query},
                          op="search_attribute_values")
        else:
            d = self.post("/v1/description-category/attribute/values", {**body, "language": "DEFAULT"},
                          op="search_attribute_values")
        return [{"id": str(v.get("id")), "value": v.get("value")} for v in d.get("result") or []]

    # ------------------------------------------------------------- products
    def _item(self, it: ProductPayload):
        attrs = {}
        for a in it.attributes:
            v = {"dictionary_value_id": int(a["value_id"])} if a.get("value_id") else {"value": str(a.get("value"))}
            attrs.setdefault(int(a["id"]), []).append(v)
        item = {
            "offer_id": it.offer_id, "name": it.name[:500], "description_category_id": int(it.category_id),
            "type_id": int(it.type_id), "price": str(num(it.price)), "old_price": "0",
            "currency_code": it.currency, "vat": it.vat or "0", "images": it.images[1:15],
            "primary_image": it.images[0] if it.images else "",
            "attributes": [{"complex_id": 0, "id": k, "values": v} for k, v in attrs.items()],
            "depth": _dim_mm(it.length_cm), "width": _dim_mm(it.width_cm), "height": _dim_mm(it.height_cm),
            "dimension_unit": "mm",
            "weight": int(round(float(it.weight_kg) * 1000)) if it.weight_kg is not None else None, "weight_unit": "g",
        }
        if it.barcode:
            item["barcode"] = it.barcode
        return item

    def upsert_products(self, items):
        results, task_ids = {}, []
        for part in chunks(items, 100):
            d = self.post("/v3/product/import", {"items": [self._item(i) for i in part]}, op="upsert_products")
            task = str((d.get("result") or {}).get("task_id") or "")
            if not task:
                raise MarketplaceError("Ozon task_id qaytarmadi")
            task_ids.append(task)
            for it in part:
                results[it.offer_id] = {"status": "pending", "error": "", "task_id": task}
        return {"task_id": ",".join(task_ids), "results": results}

    def get_product_status(self, refs):
        out = {}
        # 1) import vazifasi natijasi
        for task in sorted({r.task_id for r in refs if r.task_id}):
            d = self.post("/v1/product/import/info", {"task_id": int(task)}, op="get_product_status")
            for it in (d.get("result") or {}).get("items") or []:
                st = (it.get("status") or "").lower()
                errs = [e for e in it.get("errors") or [] if (e.get("level") or "error") != "warning"] \
                    if isinstance(it.get("errors"), list) else []
                if st == "failed" or (errs and st not in ("imported", "pending", "")):
                    out[it.get("offer_id")] = {"status": "error", "error": _errs(errs) or st}
                elif it.get("product_id"):
                    out[it.get("offer_id")] = {"status": "pending", "error": "", "external_id": str(it["product_id"])}
        # 2) moderatsiya holati
        ids = [r.offer_id for r in refs if out.get(r.offer_id, {}).get("status") != "error"]
        for part in chunks(ids, 1000):
            d = self.post("/v3/product/info/list", {"offer_id": part}, op="get_product_status")
            for p in d.get("items") or []:
                st = p.get("statuses") or {}
                moderate = (st.get("moderate_status") or "").lower()
                failed = st.get("status_failed") or ""
                if failed or moderate in ("declined", "rejected"):
                    status = "rejected"
                elif moderate == "approved" or (st.get("status") or "").lower() in ("price_sent", "published", "imported_to_market"):
                    status = "active"
                else:
                    status = "pending"
                sku = p.get("sku") or next((s.get("sku") for s in p.get("sources") or [] if s.get("sku")), "")
                out[p.get("offer_id")] = {
                    "status": status,
                    "error": _errs(p.get("errors")) or st.get("status_description") or failed,
                    "external_id": str(p.get("id") or ""), "external_sku": str(sku or ""),
                    "external_meta": {"status": st.get("status"), "moderate_status": st.get("moderate_status")},
                }
        return out

    def update_prices(self, refs):
        out = {}
        for part in chunks(refs, 1000):
            d = self.post("/v1/product/import/prices", {"prices": [
                {"offer_id": r.offer_id, "price": str(num(r.price)), "old_price": "0", "currency_code": r.currency}
                for r in part]}, op="update_prices")
            got = {x.get("offer_id"): x for x in d.get("result") or []}
            for r in part:
                x = got.get(r.offer_id)
                out[r.offer_id] = None if (x is None or x.get("updated")) else (_errs(x.get("errors")) or "not updated")
        return out

    def update_stocks(self, refs):
        wh = self.account.warehouse_id
        if not wh:
            raise MarketplaceError("Ozon FBS ombori tanlanmagan")
        out = {}
        for part in chunks(refs, 100):
            d = self.post("/v2/products/stocks", {"stocks": [
                {"offer_id": r.offer_id, "stock": max(r.stock, 0), "warehouse_id": int(wh)} for r in part]},
                op="update_stocks", bucket="stocks")
            got = {x.get("offer_id"): x for x in d.get("result") or []}
            for r in part:
                x = got.get(r.offer_id)
                out[r.offer_id] = None if (x is None or x.get("updated")) else (_errs(x.get("errors")) or "not updated")
        return out

    # --------------------------------------------------------------- orders
    @staticmethod
    def _posting(p, scheme):
        items = [{"offer_id": x.get("offer_id"), "external_sku": str(x.get("sku") or ""), "name": x.get("name"),
                  "qty": int(x.get("quantity") or 0), "price": str(x.get("price") or 0),
                  "currency": x.get("currency_code") or ""} for x in p.get("products") or []]
        status = p.get("status") or ""
        state = FBS_STATE.get(status, "new")
        return {
            "external_id": p.get("posting_number"), "scheme": scheme, "status": status, "state": state,
            "items": items, "total": str(sum(Decimal(i["price"]) * i["qty"] for i in items)),
            "currency": items[0]["currency"] if items else "", "ordered_at": p.get("in_process_at") or p.get("created_at"),
            "raw": p,
        }

    def fetch_orders(self, since):
        now = timezone.now()
        since = max(since, now - timedelta(days=90))
        flt = {"since": since.strftime("%Y-%m-%dT%H:%M:%SZ"), "to": now.strftime("%Y-%m-%dT%H:%M:%SZ")}
        out = []
        # FBS (v4 — kursorli pagination, postings yuqori darajada)
        cursor = ""
        for _ in range(200):
            body = {"dir": "ASC", "filter": flt, "limit": 100, "with": {"analytics_data": False}}
            if cursor:
                body["cursor"] = cursor
            d = self.post("/v4/posting/fbs/list", body, op="fetch_orders")
            postings = d.get("postings") or (d.get("result") or {}).get("postings") or []
            scheme = "FBS"
            out += [self._posting(p, "rFBS" if p.get("is_rfbs") or (p.get("delivery_method") or {}).get("tpl_provider") == "seller"
                                  else scheme) for p in postings]
            cursor = d.get("cursor") or ""
            if not d.get("has_next") or not cursor:
                break
        # FBO (Ozon ombori — faqat ko'rish, qoldiqqa ta'sir qilmaydi)
        if (self.account.options or {}).get("fbo", True):
            offset = 0
            for _ in range(100):
                d = self.post("/v3/posting/fbo/list", {"dir": "ASC", "filter": flt, "limit": 100, "offset": offset,
                                                       "with": {"analytics_data": False}}, op="fetch_orders")
                res = d.get("result")
                postings = res if isinstance(res, list) else (res or {}).get("postings") or d.get("postings") or []
                for p in postings:
                    o = self._posting(p, "FBO")
                    o["state"] = {"delivered": "delivered", "cancelled": "cancelled", "delivering": "shipped"}.get(
                        p.get("status"), "processing")
                    out.append(o)
                if len(postings) < 100:
                    break
                offset += 100
        return out

    @classmethod
    def order_actions(cls, order):
        if order.scheme == "FBO":
            return []
        st = order.status
        acts = []
        if st == "awaiting_packaging":
            acts += ["confirm", "cancel"]
        if order.scheme == "rFBS" and st == "awaiting_deliver":
            acts.append("ship")
        if order.scheme == "rFBS" and st in ("delivering", "sent_by_seller"):
            acts.append("deliver")
        return acts

    def _cancel_reason(self):
        d = self.post("/v2/posting/fbs/cancel-reason/list", op="update_order_status")
        reasons = [r for r in d.get("result") or [] if r.get("is_available_for_cancellation", True)]
        for r in reasons:
            t = (r.get("title") or "").lower()
            if "нет в наличии" in t or "закончил" in t or "out of stock" in t:
                return r.get("id")
        if not reasons:
            raise MarketplaceError("Ozon bekor qilish sabablarini qaytarmadi")
        return reasons[0].get("id")

    def update_order_status(self, order, action, **kw):
        pn = order.external_id
        if action == "confirm":  # yig'ildi (awaiting_packaging -> awaiting_deliver)
            products = [{"product_id": int(i["external_sku"]), "quantity": int(i["qty"])}
                        for i in order.items if i.get("external_sku")]
            self.post("/v4/posting/fbs/ship", {"posting_number": pn, "packages": [{"products": products}]},
                      op="update_order_status")
        elif action == "cancel":
            reason = kw.get("reason_id") or self._cancel_reason()
            self.post("/v2/posting/fbs/cancel", {"posting_number": pn, "cancel_reason_id": int(reason),
                                                  "cancel_reason_message": kw.get("comment") or "ImkonMarket"},
                      op="update_order_status")
        elif action == "ship":
            self.post("/v2/fbs/posting/delivering", {"posting_number": [pn]}, op="update_order_status")
        elif action == "deliver":
            self.post("/v2/fbs/posting/delivered", {"posting_number": [pn]}, op="update_order_status")
        else:
            raise MarketplaceError(f"Noma'lum amal: {action}")
