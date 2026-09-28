"""Marketplace integratsiyasi testlari — tashqi API'lar soxta HTTP sessiya bilan almashtiriladi."""
import json
import re
import tempfile
from datetime import timedelta
from decimal import Decimal
from unittest import mock

from cryptography.fernet import Fernet
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from market.models import Category, Product, Seller

from . import jobs, services
from .clients.base import MarketplaceClient
from .models import (AttributeMapping, CategoryMapping, ExchangeRate, Job, MarketplaceAccount, MarketplaceListing,
                     MarketplaceOrder, ProductMarketInfo, SyncLog)

KEY = Fernet.generate_key().decode()
SECRET = "ACMA:SuperSecretApiKey-1234567890abcdefWXYZ"


class FakeResp:
    def __init__(self, status=200, data=None, headers=None):
        self.status_code = status
        self._data = data
        self.headers = headers or {}
        self.content = b"" if data is None else json.dumps(data).encode()
        self.text = self.content.decode()

    def json(self):
        if self._data is None:
            raise ValueError("no json")
        return self._data


class FakeSession:
    """routes: [(METHOD, regex, handler)] — handler(params, json) -> FakeResp | (status, data[, headers]) | data"""

    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    def request(self, method, url, params=None, json=None, headers=None, timeout=None):
        self.calls.append({"method": method, "url": url, "params": params, "json": json, "headers": headers})
        for m, rx, h in self.routes:
            if m == method and re.search(rx, url):
                r = h(params, json) if callable(h) else h
                if isinstance(r, FakeResp):
                    return r
                if isinstance(r, tuple):
                    return FakeResp(*r)
                return FakeResp(200, r)
        return FakeResp(404, {"message": f"no route {method} {url}"})


def use_session(session):
    """Barcha adapterlar shu sessiyadan foydalanadi."""
    orig = MarketplaceClient.__init__

    def init(self, account, job=None, session_=None, **kw):
        orig(self, account, job=job, session=session)
    return mock.patch.object(MarketplaceClient, "__init__", init)


@override_settings(MARKETPLACE_ENC_KEYS=KEY, PUBLIC_URL="https://imkon-market.uz", MP_STATUS_INTERVAL=0)
class IntegrationTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed", credentials=f"{tempfile.mkdtemp()}/c.xlsx", verbosity=0)

    def setUp(self):
        patcher = mock.patch.object(MarketplaceClient, "throttle", lambda self, bucket: None)
        patcher.start()
        self.addCleanup(patcher.stop)

    def login(self, username):
        u = get_user_model().objects.get(username=username)
        u.set_password("test-pass-123")
        u.save()
        c = APIClient()
        r = c.post("/api/auth/login/", {"username": username, "password": "test-pass-123"}, format="json")
        c.credentials(HTTP_AUTHORIZATION="Bearer " + r.data["access"])
        return c

    def product(self, sku="MK-49-001", stock=20, reserved=0, price=Decimal("150000")):
        p = Product.objects.get(sku=sku)
        p.stock, p.reserved, p.price = stock, reserved, price
        p.image.save("t.jpg", ContentFile(b"\xff\xd8\xff"), save=False)
        p.save()
        return p

    # ------------------------------------------------------------ security
    def test_key_encrypted_masked_and_never_returned(self):
        c = self.login("mk49")
        r = c.post("/api/mp/accounts/", {"marketplace": "yandex", "api_key": SECRET, "title": "YM"}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        body = json.dumps(r.json())
        self.assertNotIn(SECRET, body)
        self.assertNotIn("SuperSecret", body)
        self.assertEqual(r.json()["masked_key"], "••••WXYZ")
        acc = MarketplaceAccount.objects.get(pk=r.json()["id"])
        self.assertNotIn(SECRET, acc.credentials_enc)          # DB'da shifrlangan
        self.assertEqual(acc.credentials["api_key"], SECRET)   # ochiladi
        self.assertTrue(Job.objects.filter(kind="check_account", account=acc).exists())  # HTTP'da tashqi so'rov yo'q
        # Kalit xato matnida qaytsa ham log/SyncLog'ga to'liq tushmaydi
        sess = FakeSession([("POST", r"/v2/auth/token$", (401, {"errors": [{"message": f"bad key {SECRET}"}]}))])
        with use_session(sess):
            jobs.run_pending()
        acc.refresh_from_db()
        self.assertEqual(acc.status, MarketplaceAccount.ST_INVALID)
        for row in SyncLog.objects.all():
            self.assertNotIn(SECRET, row.error)
        self.assertNotIn(SECRET, acc.status_message)
        self.assertEqual(sess.calls[0]["headers"]["Api-Key"], SECRET)
        # Boshqa muassasa bu kabinetni ko'rmaydi
        other = self.login("jiek14")
        self.assertEqual(other.get("/api/mp/accounts/").json(), [])
        self.assertEqual(other.get(f"/api/mp/accounts/{acc.pk}/").status_code, 404)

    @override_settings(MARKETPLACE_ENC_KEYS="")
    def test_no_encryption_key_refuses(self):
        c = self.login("mk49")
        r = c.post("/api/mp/accounts/", {"marketplace": "wb", "api_key": SECRET}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertFalse(MarketplaceAccount.objects.exists())

    # ------------------------------------------------------------ yandex: full flow
    def yandex_routes(self, state):
        def upsert(params, body):
            state["upsert"] = body
            return {"status": "OK", "results": []}

        def cards(params, body):
            return {"status": "OK", "result": {"offerCards": [
                {"offerId": o, "cardStatus": "HAS_CARD_CAN_UPDATE", "mapping": {"marketSku": 555}} for o in body["offerIds"]]}}

        def prices(params, body):
            state["prices"] = body
            return {"status": "OK"}

        def stocks(params, body):
            state["stocks"] = body
            return {"status": "OK"}

        return [
            ("POST", r"/v2/auth/token$", {"status": "OK", "result": {"apiKey": {"name": "k", "authScopes": ["ALL_METHODS"]}}}),
            ("GET", r"/v2/campaigns$", {"campaigns": [{"id": 111, "domain": "shop", "placementType": "FBS",
                                                       "apiAvailability": "AVAILABLE", "business": {"id": 999, "name": "MK"}}],
                                        "pager": {"pagesCount": 1}}),
            ("POST", r"/v3/businesses/999/warehouses$", {"status": "OK", "result": {"warehouses": [{"id": 77, "name": "Ombor"}]}}),
            ("POST", r"/offer-mappings/update$", upsert),
            ("POST", r"/v2/businesses/999/offer-cards$", cards),
            ("POST", r"/offer-prices/updates$", prices),
            ("POST", r"/offers/stocks/update$", stocks),
        ]

    def test_yandex_publish_sync_flow(self):
        c = self.login("mk49")
        p = self.product(stock=20, reserved=3)
        ProductMarketInfo.objects.create(product=p, brand="MK-49", weight_kg=Decimal("1.2"), length_cm=30, width_cm=20,
                                         height_cm=5)
        # operator kategoriyani moslaydi
        op = self.login("jied")
        m = op.post("/api/mp/mappings/", {"category": p.category.slug, "marketplace": "yandex", "external_id": "15685",
                                          "external_name": "Постельное белье"}, format="json")
        self.assertEqual(m.status_code, 201, m.content)
        mapping = CategoryMapping.objects.get(pk=m.json()["id"])
        AttributeMapping.objects.create(mapping=mapping, external_id="100", name="Material", required=True,
                                        source="const", value="Paxta")
        self.assertEqual(c.post("/api/mp/mappings/", {"category": "mebel", "marketplace": "yandex", "external_id": "1"},
                                format="json").status_code, 403)
        r = c.post("/api/mp/accounts/", {"marketplace": "yandex", "api_key": SECRET, "stock_buffer": 2}, format="json")
        acc_id = r.json()["id"]
        state = {}
        sess = FakeSession(self.yandex_routes(state))
        with use_session(sess):
            jobs.run_pending()
            acc = MarketplaceAccount.objects.get(pk=acc_id)
            self.assertEqual(acc.status, "active", acc.status_message)
            self.assertEqual((acc.cabinet_id, acc.campaign_id, acc.warehouse_id), ("999", "111", "77"))
            # tekshiruv (tashqi so'rovsiz)
            r = c.post("/api/mp/listings/", {"account": acc_id, "product_ids": [p.id]}, format="json")
            self.assertEqual(r.status_code, 201, r.content)
            lid = r.json()["listings"][0]["id"]
            chk = c.get(f"/api/mp/listings/{lid}/check/").json()
            self.assertTrue(chk["ok"], chk)
            jobs.run_pending()
            offer = state["upsert"]["offerMappings"][0]["offer"]
            self.assertEqual(offer["offerId"], p.sku)
            self.assertEqual(offer["marketCategoryId"], 15685)
            self.assertEqual(offer["pictures"][0][:26], "https://imkon-market.uz/me")
            self.assertEqual(offer["parameterValues"], [{"parameterId": 100, "value": "Paxta"}])
            self.assertEqual(offer["basicPrice"], {"value": 150000, "currencyId": "UZS"})
            li = MarketplaceListing.objects.get(pk=lid)
            self.assertEqual(li.status, "pending")
            Job.objects.filter(status="queued").update(run_after=timezone.now())
            jobs.run_pending()
            li.refresh_from_db()
            self.assertEqual(li.status, "active", li.last_error)
            self.assertEqual(li.external_id, "555")
            self.assertEqual(state["stocks"]["skuItems"][0]["count"], 20 - 3 - 2)  # available - bufer
            self.assertEqual(state["stocks"]["skuItems"][0]["partnerWarehouseId"], 77)
            self.assertEqual(li.pushed_stock, 15)
            # Saytda shartnoma bo'yicha band qilish -> marketplace qoldig'i yangilanadi
            state.pop("stocks")
            with self.captureOnCommitCallbacks(execute=True):
                p.reserved = 10
                p.save()
            Job.objects.filter(status="queued").update(run_after=timezone.now())
            jobs.run_pending()
            self.assertEqual(state["stocks"]["skuItems"][0]["count"], 8)
            self.assertNotIn(SECRET, json.dumps(c.get(f"/api/mp/logs/?account={acc_id}").json()))

    def test_listing_validation_errors(self):
        p = Product.objects.get(sku="MK-49-001")
        p.price = None
        p.save()
        acc = MarketplaceAccount(seller=p.seller, marketplace="ozon", cabinet_id="1", status="active")
        acc.set_credentials({"api_key": SECRET})
        acc.save()
        li = MarketplaceListing.objects.create(product=p, account=acc, offer_id=p.sku)
        payload, errors = services.build_payload(li)
        self.assertIsNone(payload)
        text = " ".join(errors)
        self.assertIn("Narx", text)
        self.assertIn("rasmi", text)
        self.assertIn("moslanmagan", text)
        self.assertIn("o'lcham", text)

    # ------------------------------------------------------------ currency
    def test_currency_manual_and_cbu(self):
        seller = Seller.objects.get(code="mk-49")
        acc = MarketplaceAccount(seller=seller, marketplace="ozon", currency="RUB", rate_source="manual",
                                 manual_rate=Decimal("140"), markup_percent=Decimal("10"))
        self.assertEqual(services.currency.convert(acc, Decimal("140000")), Decimal("1100"))
        acc.rate_source = "cbu"
        with self.assertRaises(services.currency.RateUnavailable):
            services.currency.convert(acc, Decimal("140000"))
        sess = mock.Mock()
        sess.get.return_value = mock.Mock(status_code=200, json=lambda: [
            {"Ccy": "USD", "Rate": "11825.40", "Nominal": "1", "Date": timezone.localdate().strftime("%d.%m.%Y")},
            {"Ccy": "RUB", "Rate": "140.34", "Nominal": "1", "Date": timezone.localdate().strftime("%d.%m.%Y")},
            {"Ccy": "XYZ", "Rate": "1", "Nominal": "1", "Date": "01.01.2026"}])
        self.assertEqual(services.currency.fetch_cbu_rates(sess), 2)
        self.assertEqual(services.currency.convert(acc, Decimal("140340")), Decimal("1100"))
        acc.currency = "UZS"
        self.assertEqual(services.currency.convert(acc, Decimal("100000")), Decimal("110000"))

    # ------------------------------------------------------------ orders & stock
    def test_uzum_orders_reserve_deduct_release_and_cross_channel(self):
        p = self.product(sku="MK-49-001", stock=10)
        seller = p.seller
        uz = MarketplaceAccount(seller=seller, marketplace="uzum", cabinet_id="42", status="active")
        uz.set_credentials({"api_key": SECRET})
        uz.save()
        ym = MarketplaceAccount(seller=seller, marketplace="yandex", cabinet_id="999", warehouse_id="77", status="active")
        ym.set_credentials({"api_key": "other-key-000011112222"})
        ym.save()
        MarketplaceListing.objects.create(product=p, account=uz, offer_id=p.sku, external_id="9", external_sku="901",
                                          status="active", external_meta={"barcode": "478000", "sku_title": "X"})
        ym_li = MarketplaceListing.objects.create(product=p, account=ym, offer_id=p.sku, status="active", pushed_stock=10)
        order = {"id": 5001, "status": "CREATED", "scheme": "FBS", "dateCreated": 1790000000000, "price": 300000,
                 "orderItems": [{"skuId": 901, "skuTitle": "X", "amount": 3, "sellerPrice": 100000}]}

        def orders(params, body):
            return {"payload": {"orders": [order] if params["status"] == order["status"] else [], "totalAmount": 1}}

        stock_calls = []
        sess = FakeSession([
            ("GET", r"/v2/fbs/orders$", orders),
            ("POST", r"/offers/stocks/update$", lambda pa, b: stock_calls.append(b) or {"status": "OK"}),
            ("POST", r"/v2/fbs/sku/stocks$", {"payload": {}}),
            ("POST", r"/v1/product/42/sendPriceData$", {"payload": {}}),
        ])
        with use_session(sess):
            jobs.enqueue("fetch_orders", account=uz)
            with self.captureOnCommitCallbacks(execute=True):
                jobs.run_pending()
            p.refresh_from_db()
            self.assertEqual((p.stock, p.reserved), (10, 3))
            o = MarketplaceOrder.objects.get(account=uz, external_id="5001")
            self.assertEqual((o.state, o.stock_state, o.items[0]["product_id"]), ("new", "reserved", p.pk))
            # boshqa kanal (Yandex) qoldig'i ham tushadi
            Job.objects.filter(status="queued").update(run_after=timezone.now())
            jobs.run_pending()
            self.assertEqual(stock_calls[-1]["skuItems"][0]["count"], 7)
            ym_li.refresh_from_db()
            self.assertEqual(ym_li.pushed_stock, 7)
            # jo'natildi -> ombordan yechiladi
            order["status"] = "DELIVERING"
            jobs.enqueue("fetch_orders", account=uz)
            with self.captureOnCommitCallbacks(execute=True):
                jobs.run_pending()
            p.refresh_from_db()
            self.assertEqual((p.stock, p.reserved, p.sold), (7, 0, 3))
            # ikkinchi buyurtma bekor qilinadi -> band qaytariladi
            order.update({"id": 5002, "status": "CREATED"})
            jobs.enqueue("fetch_orders", account=uz)
            jobs.run_pending()
            p.refresh_from_db()
            self.assertEqual(p.reserved, 3)
            order["status"] = "CANCELED"
            jobs.enqueue("fetch_orders", account=uz)
            jobs.run_pending()
            p.refresh_from_db()
            self.assertEqual((p.stock, p.reserved), (7, 0))
            self.assertEqual(MarketplaceOrder.objects.get(external_id="5002").stock_state, "released")

    def test_order_action_via_api(self):
        seller = Seller.objects.get(code="mk-49")
        acc = MarketplaceAccount(seller=seller, marketplace="uzum", cabinet_id="42", status="active")
        acc.set_credentials({"api_key": SECRET})
        acc.save()
        o = MarketplaceOrder.objects.create(account=acc, external_id="77", scheme="FBS", status="CREATED",
                                            raw={"status": "CREATED"})
        c = self.login("mk49")
        self.assertEqual(c.post(f"/api/mp/orders/{o.pk}/action/", {"action": "deliver"}, format="json").status_code, 400)
        r = c.post(f"/api/mp/orders/{o.pk}/action/", {"action": "confirm"}, format="json")
        self.assertEqual(r.status_code, 202, r.content)
        sess = FakeSession([("POST", r"/v1/fbs/order/77/confirm$", {"payload": True}),
                            ("GET", r"/v2/fbs/orders$", {"payload": {"orders": []}})])
        with use_session(sess):
            jobs.run_pending()
        self.assertTrue(any(c["url"].endswith("/v1/fbs/order/77/confirm") for c in sess.calls))
        self.assertEqual(sess.calls[0]["headers"]["Authorization"], SECRET)  # Bearer prefiksisiz

    # ------------------------------------------------------------ retry / backoff
    def test_retry_on_429_then_fail(self):
        seller = Seller.objects.get(code="mk-49")
        acc = MarketplaceAccount(seller=seller, marketplace="wb", status="active")
        acc.set_credentials({"api_key": SECRET})
        acc.save()
        job = jobs.enqueue("fetch_orders", account=acc, max_attempts=2)
        sess = FakeSession([("GET", r"/api/v3/orders$", (429, {"detail": "limit"}, {"X-Ratelimit-Retry": "7"}))])
        with use_session(sess):
            jobs.run_pending()
            job.refresh_from_db()
            self.assertEqual((job.status, job.attempts), ("queued", 1))
            delay = (job.run_after - timezone.now()).total_seconds()
            self.assertTrue(5 < delay < 10, delay)  # X-Ratelimit-Retry hisobga olindi
            Job.objects.filter(pk=job.pk).update(run_after=timezone.now())
            jobs.run_pending()
        job.refresh_from_db()
        self.assertEqual(job.status, "failed")
        self.assertEqual(SyncLog.objects.filter(account=acc, http_status=429).count(), 2)

    def test_backoff_grows(self):
        vals = [jobs.backoff_seconds(a) for a in (1, 3, 6, 12)]
        self.assertTrue(vals[0] < vals[1] < vals[2])
        self.assertLessEqual(vals[3], 450)

    # ------------------------------------------------------------ uzum link mode
    def test_uzum_link_mode(self):
        p = self.product()
        c = self.login("mk49")
        r = c.post("/api/mp/accounts/", {"marketplace": "uzum", "api_key": SECRET}, format="json")
        acc_id = r.json()["id"]
        prices = []
        sess = FakeSession([
            ("GET", r"/v1/shops$", {"payload": [{"id": 42, "name": "MK-49 do'koni"}]}),
            ("GET", r"/v1/product/shop/42$", {"payload": {"productList": [{"productId": 9, "title": "Choyshab", "skuList": [
                {"skuId": 901, "skuTitle": "Choyshab-oq", "sellerItemCode": p.sku, "barcode": "4780001"}]}]}}),
            ("POST", r"/v1/product/42/sendPriceData$", lambda pa, b: prices.append(b) or {"payload": {}}),
            ("POST", r"/v2/fbs/sku/stocks$", {"payload": {}}),
        ])
        with use_session(sess):
            jobs.run_pending()
            Job.objects.filter(status="queued").update(run_after=timezone.now())
            jobs.run_pending()
        acc = MarketplaceAccount.objects.get(pk=acc_id)
        self.assertEqual((acc.status, acc.cabinet_id), ("active", "42"))
        li = MarketplaceListing.objects.get(account=acc)
        self.assertEqual((li.product_id, li.external_sku, li.status), (p.pk, "901", "active"))
        self.assertEqual(prices[0], {"productId": 9, "skuList": [{"skuId": 901, "skuTitle": "Choyshab-oq",
                                                                 "sellPrice": 150000, "fullPrice": 150000}]})
        stock_body = next(c["json"] for c in sess.calls if c["url"].endswith("/v2/fbs/sku/stocks"))
        self.assertEqual(stock_body, {"skuAmountList": [{"barcode": "4780001", "amount": 20}]})
        # Uzum'da kartochka yaratib bo'lmaydi -> tushunarli xabar
        p2 = Product.objects.filter(seller=p.seller).exclude(pk=p.pk).first()
        c.post("/api/mp/listings/", {"account": acc_id, "product_ids": [p2.id]}, format="json")
        with use_session(sess):
            jobs.run_pending()
        li2 = MarketplaceListing.objects.get(account=acc, product=p2)
        self.assertEqual(li2.status, "draft")
        self.assertIn("kabinetda", li2.last_error)

    # ------------------------------------------------------------ parsers
    def test_ozon_and_wb_parsers(self):
        from .clients.ozon import OzonClient
        from .clients.wb import WBClient, jwt_claims
        seller = Seller.objects.get(code="mk-49")
        oz = MarketplaceAccount(seller=seller, marketplace="ozon", cabinet_id="123", status="active", warehouse_id="5")
        oz.set_credentials({"api_key": SECRET})
        oz.save()
        sess = FakeSession([
            ("POST", r"/v4/posting/fbs/list$", {"postings": [{"posting_number": "0001-1", "status": "awaiting_packaging",
                                                               "in_process_at": "2026-09-28T10:00:00Z",
                                                               "products": [{"offer_id": "MK-49-001", "sku": 777, "quantity": 2,
                                                                             "price": "1000.00", "currency_code": "UZS"}]}],
                                                "has_next": False}),
            ("POST", r"/v3/posting/fbo/list$", {"result": []}),
            ("POST", r"/v3/product/info/list$", {"items": [{"offer_id": "A", "id": 10, "sku": 20,
                                                            "statuses": {"moderate_status": "approved"}},
                                                           {"offer_id": "B", "id": 11, "statuses": {"status_failed": "x",
                                                                                                     "status_description": "Rasm sifatsiz"}}]}),
            ("POST", r"/v1/product/import/info$", {"result": {"items": [{"offer_id": "C", "status": "failed",
                                                                         "errors": [{"message": "Atribut yo'q"}]}]}}),
        ])
        cl = OzonClient(oz, session=sess)
        orders = cl.fetch_orders(timezone.now() - timedelta(days=1))
        self.assertEqual(orders[0]["state"], "new")
        self.assertEqual(orders[0]["total"], "2000.00")
        self.assertEqual(sess.calls[0]["headers"]["Client-Id"], "123")
        from .clients.base import ListingRef
        st = cl.get_product_status([ListingRef(1, "A"), ListingRef(2, "B"), ListingRef(3, "C", task_id="99")])
        self.assertEqual((st["A"]["status"], st["A"]["external_sku"]), ("active", "20"))
        self.assertEqual(st["B"]["status"], "rejected")
        self.assertEqual((st["C"]["status"], st["C"]["error"]), ("error", "Atribut yo'q"))
        self.assertEqual(OzonClient.order_actions(MarketplaceOrder(scheme="FBS", status="awaiting_packaging")),
                         ["confirm", "cancel"])

        import base64
        tok = "x." + base64.urlsafe_b64encode(json.dumps({"exp": 1900000000, "acc": 3}).encode()).decode().rstrip("=") + ".y"
        self.assertEqual(jwt_claims(tok)["acc"], 3)
        wb = MarketplaceAccount(seller=seller, marketplace="wb", status="active")
        wb.set_credentials({"api_key": tok})
        wb.save()
        sess = FakeSession([
            ("GET", r"/ping$", {"TS": "x", "Status": "OK"}),
            ("GET", r"/api/v3/warehouses$", [{"id": 1, "name": "Toshkent"}]),
            ("GET", r"/api/v3/orders$", {"next": 0, "orders": [{"id": 1, "article": "MK-49-001", "chrtId": 5,
                                                                "createdAt": "2026-09-28T10:00:00Z", "price": 1250000,
                                                                "convertedPrice": 1250000, "currencyCode": 860,
                                                                "convertedCurrencyCode": 860}]}),
            ("POST", r"/api/v3/orders/status$", {"orders": [{"id": 1, "supplierStatus": "confirm", "wbStatus": "waiting"}]}),
        ])
        w = WBClient(wb, session=sess)
        chk = w.check_credentials()
        self.assertEqual((chk["meta"]["token_type"], chk["warehouse_id"]), ("personal", "1"))
        self.assertIn("Servis", chk["message"])
        o = w.fetch_orders(timezone.now())[0]
        self.assertEqual((o["state"], o["total"], o["currency"]), ("processing", "12500", "UZS"))

    # ------------------------------------------------------------ review fixes
    def _acc(self, mp="uzum", **kw):
        seller = Seller.objects.get(code="mk-49")
        acc = MarketplaceAccount(seller=seller, marketplace=mp, status="active", cabinet_id="42", **kw)
        acc.set_credentials({"api_key": SECRET})
        acc.save()
        return acc

    def test_stock_snapshot_history_and_account_delete(self):
        p = self.product(stock=10)
        acc = self._acc(orders_synced_at=timezone.now())
        o = MarketplaceOrder(account=acc, external_id="1", scheme="FBS", state="new",
                             items=[{"product_id": p.pk, "qty": 2}])
        services.apply_order_stock(o)
        o.save()
        p.refresh_from_db()
        self.assertEqual((p.reserved, o.stock_items), (2, {str(p.pk): 2}))
        # items o'zgarib ketdi (masalan, bitta tovar bekor) — bo'shatish snapshot bo'yicha
        o.items, o.state = [{"product_id": p.pk, "qty": 1}], "cancelled"
        services.apply_order_stock(o)
        p.refresh_from_db()
        self.assertEqual((p.reserved, o.stock_state), (0, "released"))
        # released -> yana yig'ilmoqda: qaytadan band qilinadi
        o.state = "processing"
        services.apply_order_stock(o)
        p.refresh_from_db()
        self.assertEqual(p.reserved, 1)
        o.save()
        # birinchi sinxronda kelgan yakunlangan buyurtma — tarixiy, qoldiqqa tegmaydi
        h = MarketplaceOrder(account=acc, external_id="2", scheme="FBS", state="delivered",
                             items=[{"product_id": p.pk, "qty": 5}])
        self.assertEqual(services.apply_order_stock(h, historical=True), set())
        self.assertEqual(h.stock_state, "historical")
        # returned avtomatik qoldiq qo'shmaydi
        r = MarketplaceOrder(account=acc, external_id="3", scheme="FBS", state="shipped", items=[{"product_id": p.pk, "qty": 1}])
        services.apply_order_stock(r)
        p.refresh_from_db()
        self.assertEqual((p.stock, p.sold), (9, 1))
        r.state = "returned"
        self.assertEqual(services.apply_order_stock(r), set())
        # kabinet o'chirilsa — band qilingan qoldiq bo'shaydi
        with self.captureOnCommitCallbacks(execute=True):
            acc.delete()
        p.refresh_from_db()
        self.assertEqual(p.reserved, 0)

    def test_ozon_adds_back_own_reservations(self):
        p = self.product(stock=10, reserved=0)
        oz = self._acc("ozon", warehouse_id="5")
        ym = self._acc("yandex", warehouse_id="7")
        o = MarketplaceOrder(account=oz, external_id="P-1", scheme="FBS", state="new", items=[{"product_id": p.pk, "qty": 3}])
        services.apply_order_stock(o)
        o.save()
        p.refresh_from_db()
        self.assertEqual(p.reserved, 3)
        self.assertEqual(services.stock_for(oz, p, services.own_reserved(oz).get(p.pk, 0)), 10)  # Ozon o'zi ayiradi
        self.assertEqual(services.stock_for(ym, p, services.own_reserved(ym).get(p.pk, 0)), 7)

    def test_dedupe_merge_and_disabled_account(self):
        acc = self._acc()
        a = jobs.enqueue("sync_listings", account=acc, payload={"ids": [1]}, dedupe="d")
        jobs.enqueue("sync_listings", account=acc, payload={"ids": [2], "force": True}, dedupe="d")
        a.refresh_from_db()
        self.assertEqual(a.payload, {"ids": [1, 2], "force": True})
        jobs.enqueue("sync_listings", account=acc, payload={}, dedupe="d")  # "hammasi" ustun
        a.refresh_from_db()
        self.assertNotIn("ids", a.payload)
        jobs.enqueue("sync_listings", account=acc, payload={"ids": [3]}, dedupe="d")
        a.refresh_from_db()
        self.assertNotIn("ids", a.payload)
        MarketplaceAccount.objects.filter(pk=acc.pk).update(is_enabled=False)
        sess = FakeSession([])
        with use_session(sess):
            jobs.run_pending()
        a.refresh_from_db()
        self.assertEqual((a.status, a.result), ("done", {"skipped": "account disabled"}))
        self.assertEqual(sess.calls, [])

    def test_scheduler_enqueues_periodic(self):
        seller = Seller.objects.get(code="mk-49")
        acc = MarketplaceAccount(seller=seller, marketplace="yandex", status="active", cabinet_id="1",
                                 last_checked_at=timezone.now(), currency="RUB")
        acc.set_credentials({"api_key": SECRET})
        acc.save()
        services.schedule_periodic()
        kinds = set(Job.objects.values_list("kind", flat=True))
        self.assertIn("fetch_orders", kinds)
        self.assertIn("fetch_rates", kinds)
        self.assertNotIn("check_account", kinds)
        services.schedule_periodic()  # dedupe — takrorlanmaydi
        self.assertEqual(Job.objects.filter(kind="fetch_orders").count(), 1)
        self.assertFalse(ExchangeRate.objects.exists())
        _ = Category  # noqa
