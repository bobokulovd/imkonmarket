import base64
from decimal import Decimal

from django.core.management import call_command
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .models import Contract, Product
from .translit import LANGS


@override_settings(PAYME_MERCHANT_ID="", PAYME_KEY="", CLICK_SERVICE_ID="")
class FlowTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        import tempfile
        cls.tmp = tempfile.mkdtemp()
        call_command("seed", credentials=f"{cls.tmp}/c.xlsx", verbosity=0)

    def login(self, username):
        from django.contrib.auth import get_user_model
        u = get_user_model().objects.get(username=username)
        u.set_password("test-pass-123")
        u.save()
        c = APIClient()
        r = c.post("/api/auth/login/", {"username": username, "password": "test-pass-123"}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        c.credentials(HTTP_AUTHORIZATION="Bearer " + r.data["access"])
        return c

    def test_catalog_and_filters(self):
        c = APIClient()
        meta = c.get("/api/meta/").json()
        self.assertEqual(len(meta["languages"]), 6)
        self.assertEqual(meta["stats"]["products"], 357)
        r = c.get("/api/products/?category=mebel&facets=1").json()
        self.assertGreater(r["count"], 50)
        self.assertIn("facets", r)
        r = c.get("/api/products/?q=парта").json()  # ruscha qidiruv
        self.assertGreater(r["count"], 0)
        r = c.get("/api/products/?q=гишт").json()  # o'zbek kirill
        self.assertGreater(r["count"], 0)
        r = c.get("/api/products/?region=Navoiy viloyati&ordering=price&in_stock=1").json()
        prices = [Decimal(p["price"]) for p in r["results"] if p["price"]]
        self.assertEqual(prices, sorted(prices))

    def test_b2c_online_and_b2b_bank(self):
        c = APIClient()
        p1 = Product.objects.get(sku="MK-49-001")  # choyshab to'plami
        p2 = Product.objects.get(sku="MK-44-005")  # divan
        stock_before = p1.available
        body = {
            "buyer_type": "b2c", "buyer_name": "Aliyev Vali", "buyer_pinfl": "31234567890123",
            "buyer_passport": "AD1234567", "buyer_phone": "+998901234567", "payment_method": "payme",
            "delivery_required": True, "delivery_address": "Toshkent, Chilonzor 5", "lang": "ru",
            "items": [{"product": p1.id, "qty": 2}, {"product": p2.id, "qty": 1}],
        }
        r = c.post("/api/applications/", body, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(len(r.data), 2)  # 2 ta sotuvchi -> 2 ta ariza
        token = next(a["token"] for a in r.data if a["seller"]["uz"] == "49-son MK")

        seller = self.login("mk49")
        apps = seller.get("/api/seller/applications/").json()["results"]
        app = next(a for a in apps if a["token"] == token)
        r = seller.post(f"/api/seller/applications/{app['id']}/confirm/", {"delivery_cost": 50000}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.data["status"], "contract")
        p1.refresh_from_db()
        self.assertEqual(p1.available, stock_before - 2)

        order = c.get(f"/api/orders/{token}/").json()
        self.assertEqual(Decimal(order["contract"]["grand_total"]), Decimal("320000"))
        pay = c.post(f"/api/orders/{token}/pay/", {"method": "payme"}, format="json").json()
        self.assertTrue(pay["demo"])
        ctok = order["contract"]["token"]
        r = c.post(f"/api/pay/demo/{pay['payment_id']}/confirm/", {"c": ctok}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        order = c.get(f"/api/orders/{token}/").json()
        self.assertEqual(order["contract"]["status"], "paid")
        r = c.get(f"/api/contracts/{ctok}/pdf/")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(b"".join(r.streaming_content).startswith(b"%PDF"))

        cid = order["contract"]["id"]
        r = seller.post(f"/api/seller/contracts/{cid}/ship/")
        self.assertEqual(r.data["status"], "shipped")
        p1.refresh_from_db()
        self.assertEqual(p1.reserved, 0)
        self.assertEqual(p1.sold, 2)

        # B2B, bank o'tkazmasi
        body2 = {
            "buyer_type": "b2b", "buyer_name": "\"Qurilish Invest\" MChJ", "buyer_inn": "301234567",
            "buyer_director": "Karimov A.", "buyer_phone": "+998711234567", "buyer_bank_name": "Xalq banki",
            "buyer_bank_account": "20208000900123456001", "buyer_bank_mfo": "00873", "payment_method": "bank",
            "items": [{"product": Product.objects.get(sku="JIEK-14-001").id, "qty": 5000}],
        }
        r = c.post("/api/applications/", body2, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        s14 = self.login("jiek14")
        app = s14.get("/api/seller/applications/?status=new").json()["results"][0]
        r = s14.post(f"/api/seller/applications/{app['id']}/confirm/", {"prepayment_percent": 50, "lang": "uz_cyrl"}, format="json")
        cid = r.data["contract"]["id"]
        r = s14.post(f"/api/seller/contracts/{cid}/payment/", {"amount": "2375000", "document_no": "PP-15"}, format="json")
        self.assertEqual(r.data["status"], "paid")  # 50% oldindan to'lov bajarildi

    def test_agent_contract_on_behalf_of_owner(self):
        """14-son JIEK 44-son MK mahsuloti uchun shartnoma chiqaradi — shartnoma 44-son nomidan."""
        agent = self.login("jiek14")
        cat = agent.get("/api/seller/catalog/?seller=mk-44&q=shkaf").json()
        item = cat["results"][0]
        self.assertIn("stock", item)
        body = {
            "buyer_type": "b2b", "buyer_name": "5-maktab", "buyer_inn": "200111222", "buyer_phone": "+998901112233",
            "payment_method": "bank", "items": [{"product": item["id"], "qty": 2}],
        }
        r = agent.post("/api/seller/agent-order/", body, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.data[0]["seller"]["code"], "mk-44")
        self.assertEqual(r.data[0]["agent"]["code"], "jiek-14")
        self.assertEqual(r.data[0]["status"], "contract")
        c = Contract.objects.get(number=r.data[0]["contract"]["number"])
        self.assertTrue(c.number.startswith("MK-44/"))
        owner = self.login("mk44")
        self.assertEqual(owner.get("/api/seller/contracts/").json()["count"], 1)
        self.assertEqual(agent.get("/api/seller/contracts/").json()["count"], 1)
        # Qoldiqdan ortiq buyurtma rad etiladi
        body["items"][0]["qty"] = 10_000
        r = agent.post("/api/seller/agent-order/", body, format="json")
        self.assertEqual(r.status_code, 400)

    def test_pdf_all_languages(self):
        from .contract_pdf import build_pdf
        c = APIClient()
        p = Product.objects.get(sku="JIEK-05-001")
        r = c.post("/api/applications/", {
            "buyer_type": "b2b", "buyer_name": "Test MChJ", "buyer_inn": "123456789", "buyer_phone": "901234567",
            "payment_method": "click", "items": [{"product": p.id, "qty": 100}],
        }, format="json")
        s = self.login("jiek05")
        app = s.get("/api/seller/applications/").json()["results"][0]
        s.post(f"/api/seller/applications/{app['id']}/confirm/", {}, format="json")
        contract = Contract.objects.latest("id")
        for lang in LANGS:
            contract.lang = lang
            self.assertTrue(build_pdf(contract).startswith(b"%PDF"))

    @override_settings(PAYME_MERCHANT_ID="m1", PAYME_KEY="secret")
    def test_payme_rpc(self):
        c = APIClient()
        p = Product.objects.get(sku="MK-49-003")
        r = c.post("/api/applications/", {
            "buyer_type": "b2c", "buyer_name": "Test", "buyer_pinfl": "1", "buyer_phone": "901234567",
            "payment_method": "payme", "items": [{"product": p.id, "qty": 1}],
        }, format="json")
        s = self.login("mk49")
        app = s.get("/api/seller/applications/").json()["results"][0]
        s.post(f"/api/seller/applications/{app['id']}/confirm/", {}, format="json")
        contract = Contract.objects.latest("id")
        auth = "Basic " + base64.b64encode(b"Paycom:secret").decode()
        amount = int(contract.due_amount * 100)

        def rpc(method, params):
            return c.post("/api/payments/payme/", {"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
                          format="json", HTTP_AUTHORIZATION=auth).json()

        self.assertTrue(rpc("CheckPerformTransaction", {"amount": amount, "account": {"contract_id": contract.id}})["result"]["allow"])
        self.assertEqual(rpc("CheckPerformTransaction", {"amount": 1, "account": {"contract_id": contract.id}})["error"]["code"], -31001)
        import time
        t = int(time.time() * 1000)
        self.assertEqual(rpc("CreateTransaction", {"id": "abc", "time": t, "amount": amount, "account": {"contract_id": contract.id}})["result"]["state"], 1)
        self.assertEqual(rpc("PerformTransaction", {"id": "abc"})["result"]["state"], 2)
        contract.refresh_from_db()
        self.assertEqual(contract.status, "paid")
        self.assertEqual(rpc("CheckTransaction", {"id": "abc"})["result"]["state"], 2)

    # ---- Namunaviy (AI) rasmlar va ommaviy yuklash

    def _png(self, color="red"):
        import io

        from PIL import Image
        b = io.BytesIO()
        Image.new("RGB", (40, 30), color).save(b, "PNG")
        return b.getvalue()

    def test_samples_bulk_upload_and_badge(self):
        import io
        import json
        import tempfile
        import zipfile
        from pathlib import Path
        from unittest import mock

        from django.core.files.uploadedfile import SimpleUploadedFile

        from market import images
        tmp = Path(tempfile.mkdtemp())
        (tmp / "manifest.json").write_text(json.dumps({"items": [{"key": "choyshab", "skus": ["MK-49-001", "MK-49-005"]}]}))
        (tmp / "choyshab.png").write_bytes(self._png())
        with mock.patch.object(images, "SEED_DIR", tmp):
            self.assertEqual(images.load_samples(), 2)
            self.assertEqual(images.load_samples(), 0)  # qayta ishga tushirilsa tegmaydi
        p = Product.objects.get(sku="MK-49-001")
        self.assertTrue(p.image_is_sample and p.image.name.endswith(".webp"))
        r = APIClient().get(f"/api/products/{p.id}/").json()
        self.assertTrue(r["image_is_sample"])
        # muassasa haqiqiy suratlarni ommaviy yuklaydi (ZIP + oddiy fayl); boshqa muassasa SKU'si — bog'lanmaydi
        z = io.BytesIO()
        with zipfile.ZipFile(z, "w") as zf:
            zf.writestr("photos/MK-49-005.jpg", self._png("blue"))
            zf.writestr("__MACOSX/._x.jpg", b"x")
        c = self.login("mk49")
        r = c.post("/api/seller/products/bulk-images/", {"files": [
            SimpleUploadedFile("mk-49-001 (2).PNG", self._png("green")),
            SimpleUploadedFile("arxiv.zip", z.getvalue()),
            SimpleUploadedFile("MK-44-005.jpg", self._png()),
        ]}, format="multipart")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(sorted(m["sku"] for m in r.json()["matched"]), ["MK-49-001", "MK-49-005"])
        self.assertEqual(r.json()["unmatched"], ["MK-44-005.jpg"])
        p.refresh_from_db()
        self.assertFalse(p.image_is_sample)
        self.assertEqual(c.get("/api/seller/products/?image=sample").json()["count"], 0)
        self.assertGreater(c.get("/api/seller/products/?image=none").json()["count"], 0)
