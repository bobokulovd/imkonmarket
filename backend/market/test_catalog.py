"""Marketplace standartidagi kartochka: xususiyatlar, galereya, variantlar, IKPU, tayyorlik."""
import io
import tempfile
from decimal import Decimal
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from PIL import Image
from rest_framework.test import APIClient

from .catalog import ean_ok
from .ikpu import score, suggest
from .models import AttributeDef, Product, ProductVariant

MEDIA = tempfile.mkdtemp()


def png(color=(200, 50, 50), size=(800, 900)):
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, "PNG")
    return buf.getvalue()


@override_settings(MEDIA_ROOT=MEDIA, PAYME_MERCHANT_ID="", PAYME_KEY="", CLICK_SERVICE_ID="")
class CatalogTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed", credentials=f"{tempfile.mkdtemp()}/c.xlsx", verbosity=0)
        call_command("load_attributes", verbosity=0)

    def login(self, username):
        u = get_user_model().objects.get(username=username)
        u.set_password("test-pass-123")
        u.save()
        c = APIClient()
        r = c.post("/api/auth/login/", {"username": username, "password": "test-pass-123"}, format="json")
        c.credentials(HTTP_AUTHORIZATION="Bearer " + r.data["access"])
        return c

    def mebel(self):
        p = Product.objects.filter(category__slug="mebel", seller__code="mk-44").order_by("id").first()
        return p, self.login(p.seller.code.replace("-", ""))

    def test_dictionary_loaded_and_idempotent(self):
        n = AttributeDef.objects.count()
        self.assertGreater(n, 100)
        d = AttributeDef.objects.get(category__slug="mebel", code="rang")
        d.name = {**d.name, "uz": "Rangi (operator)"}
        d.save()
        call_command("load_attributes", verbosity=0)
        self.assertEqual(AttributeDef.objects.count(), n)
        self.assertEqual(AttributeDef.objects.get(pk=d.pk).name["uz"], "Rangi (operator)")
        # spec matnidan taxminiy to'ldirilgan
        p = Product.objects.filter(category__slug="qurilish", spec__uz="250×120×65 mm").first()
        self.assertEqual(p.attributes.get("olcham"), "250×120×65 mm")
        r = APIClient().get("/api/attributes/?category=mebel").json()
        self.assertTrue(any(a["code"] == "rang" and a["variant"] for a in r))

    def test_attributes_validated(self):
        p, c = self.mebel()
        r = c.patch(f"/api/seller/products/{p.id}/", {"attributes": {"uzunlik": "120,5", "yigilgan": "ha",
                                                                      "material": "LDSP", "nomalum": "x"}}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()["attributes"]["uzunlik"], 120.5)
        self.assertIs(r.json()["attributes"]["yigilgan"], True)
        self.assertNotIn("nomalum", r.json()["attributes"])
        mat = AttributeDef.objects.get(category__slug="mebel", code="material")
        self.assertTrue(set(r.json()["attributes"]["material"]) <= {o["v"] for o in mat.options})
        r = c.patch(f"/api/seller/products/{p.id}/", {"attributes": {"material": "temir-beton-xyz"}}, format="json")
        self.assertEqual(r.status_code, 400)
        r = c.patch(f"/api/seller/products/{p.id}/", {"barcode": "4780000000001"}, format="json")
        self.assertEqual(r.status_code, 400)  # nazorat raqami noto'g'ri
        r = c.patch(f"/api/seller/products/{p.id}/", {"barcode": "4780000000007", "ikpu": "09401001001000000",
                                                        "brand": "MK-44", "weight_kg": "12.5"}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertTrue(r.json()["ikpu_confirmed"])
        public = APIClient().get(f"/api/products/{p.id}/").json()
        self.assertTrue(any(x["code"] == "uzunlik" and x["value"]["uz"] == "120.5 sm" for x in public["characteristics"]))

    def test_gallery(self):
        p, c = self.mebel()
        from .images import add_image
        Product.objects.filter(pk=p.pk).update(image="", image_is_sample=False)
        p.images.all().delete()
        # namunaviy rasm
        add_image(p, png((1, 1, 1)), sample=True)
        p.refresh_from_db()
        self.assertTrue(p.image_is_sample)
        r = c.post(f"/api/seller/products/{p.id}/images/", {"files": [
            SimpleUploadedFile("a.png", png((10, 200, 10))), SimpleUploadedFile("b.png", png((10, 10, 200)))]},
            format="multipart")
        self.assertEqual(r.status_code, 200, r.content)
        imgs = r.json()
        self.assertEqual(len(imgs), 2)  # namunaviy o'chdi
        # cheklovlar: kichik, cho'zinchoq, rasm emas
        for bad, word in ((png(size=(500, 500)), "kichik"), (png(size=(800, 3000)), "cho'zinchoq"), (b"not an image", "ochilmadi")):
            r = c.post(f"/api/seller/products/{p.id}/images/", {"files": [SimpleUploadedFile("x.png", bad)]}, format="multipart")
            self.assertEqual(r.status_code, 400)
            self.assertIn(word, str(r.json()))
        self.assertEqual(p.images.count(), 2)
        self.assertFalse(any(i["is_sample"] for i in imgs))
        self.assertIs(imgs[0]["bg_ok"], False)  # bir xil, lekin oq emas (yashil) fon
        self.assertTrue(imgs[0]["quality"]["warnings"])
        ready = c.get(f"/api/mp/product-info/{p.id}/readiness/").json()
        self.assertFalse(next(x for x in ready["checks"] if x["key"] == "cover_bg")["ok"])
        p.refresh_from_db()
        self.assertFalse(p.image_is_sample)
        first = p.images.first()
        self.assertEqual(p.image.name, first.image.name)
        r = c.post(f"/api/seller/products/{p.id}/images/reorder/", {"ids": [imgs[1]["id"], imgs[0]["id"]]}, format="json")
        self.assertEqual(r.json()[0]["id"], imgs[1]["id"])
        p.refresh_from_db()
        self.assertEqual(p.image.name, p.images.get(pk=imgs[1]["id"]).image.name)
        r = c.delete(f"/api/seller/products/{p.id}/images/{imgs[1]['id']}/")
        self.assertEqual([i["id"] for i in r.json()], [imgs[0]["id"]])
        detail = APIClient().get(f"/api/products/{p.id}/").json()
        self.assertEqual(len(detail["images"]), 1)

    def test_variants_stock_order_flow(self):
        p, c = self.mebel()
        Product.objects.filter(pk=p.pk).update(price=Decimal("1000000"), stock=None, reserved=0)
        r = c.put(f"/api/seller/products/{p.id}/variants/", [
            {"attributes": {"rang": "qora"}, "price": "1200000", "stock": 5, "barcode": "4780000000007"},
            {"attributes": {"rang": "oq"}, "stock": 2},
        ], format="json")
        self.assertEqual(r.status_code, 200, r.content)
        vs = r.json()["variants"]
        self.assertEqual(len(vs), 2)
        self.assertTrue(vs[0]["sku"].startswith(p.sku + "-QORA"))
        self.assertEqual(vs[1]["price"], "1000000.00")  # o'z narxi yo'q — mahsulot narxi
        p.refresh_from_db()
        self.assertTrue(p.has_variants)
        self.assertEqual((p.stock, p.price), (7, Decimal("1000000")))
        # takror variant / noto'g'ri qiymat
        self.assertEqual(c.put(f"/api/seller/products/{p.id}/variants/", [
            {"attributes": {"rang": "qora"}}, {"attributes": {"rang": "qora"}}], format="json").status_code, 400)
        # vitrina
        d = APIClient().get(f"/api/products/{p.id}/").json()
        self.assertEqual(len(d["variants"]), 2)
        self.assertEqual({o["v"] for o in d["variant_axes"][0]["options"]}, {"qora", "oq"})
        self.assertEqual(d["variants"][0]["label"]["uz"], "Qora")
        # buyurtma: variant majburiy
        body = {"buyer_type": "b2c", "buyer_name": "Ali", "buyer_pinfl": "31234567890123", "buyer_phone": "+998901112233",
                "payment_method": "bank", "items": [{"product": p.id, "qty": 1}]}
        r = APIClient().post("/api/applications/", body, format="json")
        self.assertEqual(r.status_code, 400)
        qora = ProductVariant.objects.get(pk=vs[0]["id"])
        body["items"] = [{"product": p.id, "variant": qora.id, "qty": 6}]
        self.assertEqual(APIClient().post("/api/applications/", body, format="json").status_code, 400)  # 5 ta bor
        body["items"] = [{"product": p.id, "variant": qora.id, "qty": 3}]
        r = APIClient().post("/api/applications/", body, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        item = APIClient().get(f"/api/orders/{r.json()[0]['token']}/").json()["items"][0]
        self.assertEqual(item["sku"], qora.sku)
        self.assertEqual(Decimal(item["price"]), Decimal("1200000"))
        self.assertIn("Qora", item["name"]["uz"])
        app_id = c.get("/api/seller/applications/").json()["results"][0]["id"]
        r = c.post(f"/api/seller/applications/{app_id}/confirm/", {}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        qora.refresh_from_db()
        p.refresh_from_db()
        self.assertEqual((qora.reserved, qora.available, p.reserved, p.available), (3, 2, 3, 4))
        contract_id = r.json()["contract"]["id"]
        c.post(f"/api/seller/contracts/{contract_id}/payment/", {"amount": "3600000", "method": "bank"}, format="json")
        r = c.post(f"/api/seller/contracts/{contract_id}/ship/", {}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        qora.refresh_from_db()
        p.refresh_from_db()
        self.assertEqual((qora.stock, qora.reserved, qora.sold), (2, 0, 3))
        self.assertEqual((p.stock, p.reserved), (4, 0))
        # variantli mahsulotda umumiy qoldiqni qo'lda o'zgartirib bo'lmaydi
        self.assertEqual(c.post(f"/api/seller/products/{p.id}/stock/", {"stock": 10}, format="json").status_code, 400)
        # variantni ro'yxatdan olib tashlash: buyurtmada ishlatilgani — nofaol bo'ladi
        r = c.put(f"/api/seller/products/{p.id}/variants/", [{"id": vs[1]["id"], "attributes": {"rang": "oq"}, "stock": 2}],
                  format="json")
        qora.refresh_from_db()
        self.assertFalse(qora.is_active)
        p.refresh_from_db()
        self.assertEqual(p.stock, 2)

    def test_readiness(self):
        p, c = self.mebel()
        r = c.get(f"/api/mp/product-info/{p.id}/readiness/")
        self.assertEqual(r.status_code, 200, r.content)
        data = r.json()
        self.assertLess(data["score"], 100)
        keys = {x["key"] for x in data["checks"]}
        self.assertTrue({"images", "ikpu", "barcode", "dims", "attributes"} <= keys)
        self.assertEqual(data["marketplaces"], [])

    def test_ikpu_browser_assisted(self):
        p, c = self.mebel()
        Product.objects.filter(pk=p.pk).update(ikpu="")
        miss = c.get("/api/seller/ikpu/missing/").json()
        g = next(x for x in miss["groups"] if p.id in x["ids"])
        items = [{"code": "09403001001000000", "name": g["name_ru"]}, {"code": "123", "name": "bad"}]
        r = c.post("/api/seller/ikpu/apply/", {"ids": g["ids"], "query": g["name_ru"], "items": items}, format="json").json()
        self.assertEqual(r["picked"]["code"], "09403001001000000")
        p.refresh_from_db()
        self.assertEqual((p.ikpu, p.ikpu_confirmed), ("09403001001000000", False))
        other = Product.objects.exclude(seller=p.seller).first()
        r = c.post("/api/seller/ikpu/apply/", {"ids": [other.id], "query": g["name_ru"], "items": items}, format="json").json()
        self.assertEqual(r["updated"], 0)  # boshqa muassasa mahsuloti

    def test_ikpu_scoring_and_suggest(self):
        self.assertTrue(ean_ok("4780000000007"))
        self.assertFalse(ean_ok("4780000000001"))
        items = [
            {"code": "08415001001000000", "name": "Пахта толаси", "subposition": "", "position": "", "class": "", "brand": ""},
            {"code": "09403001001000000", "name": "Парта школьная деревянная", "subposition": "Парты", "position": "",
             "class": "Мебель", "brand": ""},
        ]
        self.assertGreater(score("Парта школьная", items[1]), score("Парта школьная", items[0]))
        with mock.patch("market.ikpu.search", return_value=items):
            s = suggest("Парта школьная (2 местная)", "")
        self.assertEqual(s["code"], "09403001001000000")
        with mock.patch("market.ikpu.search", return_value=items[:1]):
            self.assertIsNone(suggest("Шкаф для одежды", ""))
        op = self.login("jied")
        r = op.patch("/api/seller/categories/mebel/ikpu/", {"ikpu_default": "09403001001000000", "ikpu_name": "Mebel"},
                     format="json")
        self.assertEqual(r.status_code, 200, r.content)
        p = Product.objects.filter(category__slug="mebel").first()
        Product.objects.filter(category__slug="mebel").update(ikpu="")
        with mock.patch("market.management.commands.suggest_ikpu.suggest", return_value=None):
            call_command("suggest_ikpu", verbosity=0, stdout=io.StringIO())
        p.refresh_from_db()
        self.assertEqual((p.ikpu, p.ikpu_confirmed), ("09403001001000000", False))


@override_settings(MEDIA_ROOT=MEDIA)
class DeleteTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed", credentials=f"{tempfile.mkdtemp()}/c.xlsx", verbosity=0)

    def test_delete_and_archive(self):
        u = get_user_model().objects.get(username="mk49")
        u.set_password("test-pass-123")
        u.save()
        c = APIClient()
        tok = c.post("/api/auth/login/", {"username": "mk49", "password": "test-pass-123"}, format="json").data["access"]
        c.credentials(HTTP_AUTHORIZATION="Bearer " + tok)
        mine = list(Product.objects.filter(seller__code="mk-49").order_by("id")[:3])
        other = Product.objects.exclude(seller__code="mk-49").first()
        # birinchisiga ariza tushgan — arxivlanadi
        body = {"buyer_type": "b2c", "buyer_name": "Ali", "buyer_pinfl": "31234567890123", "buyer_phone": "+998901112233",
                "payment_method": "bank", "items": [{"product": mine[0].id, "qty": max(mine[0].min_order, 1)}]}
        if mine[0].price is None:
            Product.objects.filter(pk=mine[0].pk).update(price=1000)
        self.assertEqual(APIClient().post("/api/applications/", body, format="json").status_code, 201)
        r = c.post("/api/seller/products/bulk-delete/", {"ids": [p.id for p in mine] + [other.id]}, format="json").json()
        self.assertEqual([x["id"] for x in r["archived"]], [mine[0].id])
        self.assertEqual(sorted(x["id"] for x in r["deleted"]), sorted([mine[1].id, mine[2].id]))
        self.assertTrue(Product.objects.filter(pk=other.id).exists())  # boshqa muassasaniki — tegilmaydi
        self.assertFalse(Product.objects.filter(pk=mine[1].id).exists())
        a = Product.objects.get(pk=mine[0].id)
        self.assertTrue(a.deleted_at and not a.is_active)
        ids = [x["id"] for x in c.get("/api/seller/products/?page_size=500").json()["results"]]
        self.assertNotIn(a.id, ids)
        self.assertEqual(APIClient().get(f"/api/products/{a.id}/").status_code, 404)
        # band qilingan qoldiq — o'chirilmaydi
        p = Product.objects.filter(seller__code="mk-49", deleted_at__isnull=True).first()
        Product.objects.filter(pk=p.pk).update(stock=10, reserved=2)
        self.assertEqual(c.delete(f"/api/seller/products/{p.id}/").status_code, 400)
