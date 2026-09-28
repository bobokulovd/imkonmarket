"""Marketplace integratsiyasi API (/api/mp/...).

HTTP so'rov tashqi API'ga murojaat QILMAYDI — faqat vazifa (Job) yaratadi va 202 + job id qaytaradi.
Muassasa faqat o'z kabinetlarini ko'radi; operator (JIED) — hammasini, kategoriya moslashni ham u boshqaradi.
"""
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from market.models import Category, Product, Seller
from market.pagination import Pagination
from market.views import IsSellerUser, seller_of

from . import crypto, services
from .clients import client_class
from .clients.base import CAP_CATEGORIES, CAP_LINK, CAP_ORDER_ACTIONS
from .jobs import enqueue
from .models import (CREDENTIAL_FIELDS, MARKETPLACES, AttributeMapping, AttributeValueMap, CategoryMapping,
                     ExchangeRate, ExternalCategory, Job, MarketplaceAccount, MarketplaceListing, MarketplaceOrder,
                     ProductMarketInfo, SyncLog)
from .serializers import (AccountSerializer, AttributeSerializer, ExternalCategorySerializer, JobSerializer,
                          ListingSerializer, LogSerializer, MappingSerializer, OrderSerializer, ProductInfoSerializer,
                          ValueMapSerializer)


def is_op(request):
    return seller_of(request.user).role == Seller.ROLE_OPERATOR


def require_op(request):
    if not is_op(request):
        raise PermissionDenied("Faqat operator (JIED)")


def accounts_for(request):
    qs = MarketplaceAccount.objects.select_related("seller")
    return qs if is_op(request) else qs.filter(seller=seller_of(request.user))


def job_response(job, code=status.HTTP_202_ACCEPTED):
    return Response({"job": JobSerializer(job).data}, status=code)


@api_view(["GET"])
@permission_classes([IsSellerUser])
def meta(request):
    rates = {}
    for er in ExchangeRate.objects.order_by("ccy", "-date"):
        rates.setdefault(er.ccy, {"rate": er.rate, "nominal": er.nominal, "date": er.date})
    return Response({
        "marketplaces": [{"code": c, "name": n, "capabilities": sorted(client_class(c).capabilities),
                          "credential_fields": CREDENTIAL_FIELDS[c]} for c, n in MARKETPLACES],
        "encryption_ready": crypto.configured(),
        "rates": rates,
        "is_operator": is_op(request),
        "attribute_fields": AttributeMapping.FIELDS,
    })


class AccountViewSet(viewsets.ModelViewSet):
    permission_classes = [IsSellerUser]
    serializer_class = AccountSerializer
    pagination_class = None

    def get_queryset(self):
        qs = accounts_for(self.request).prefetch_related("listings")
        if self.request.query_params.get("seller"):
            qs = qs.filter(seller__code=self.request.query_params["seller"])
        if self.request.query_params.get("marketplace"):
            qs = qs.filter(marketplace=self.request.query_params["marketplace"])
        return qs

    def _ensure_crypto(self):
        if not crypto.configured():
            raise ValidationError({"detail": "Serverda MARKETPLACE_ENC_KEYS sozlanmagan — kalitni saqlab bo'lmaydi"})

    def perform_create(self, ser):
        self._ensure_crypto()
        s = seller_of(self.request.user)
        if s.role == Seller.ROLE_OPERATOR and self.request.data.get("seller"):
            s = get_object_or_404(Seller, code=self.request.data["seller"])
        acc = ser.save(seller=s)
        enqueue("check_account", account=acc, dedupe=f"check:{acc.pk}", max_attempts=3)

    def perform_update(self, ser):
        if ser.validated_data.get("api_key"):
            self._ensure_crypto()
        acc = ser.save()
        if acc.status == MarketplaceAccount.ST_NEW or {"cabinet_id", "campaign_id"} & set(ser.validated_data):
            enqueue("check_account", account=acc, dedupe=f"check:{acc.pk}", max_attempts=3)

    @action(detail=True, methods=["post"])
    def check(self, request, pk=None):
        acc = self.get_object()
        return job_response(enqueue("check_account", account=acc, dedupe=f"check:{acc.pk}", max_attempts=3))

    @action(detail=True, methods=["post"])
    def sync(self, request, pk=None):
        acc = self.get_object()
        return job_response(enqueue("sync_listings", account=acc, payload={"force": True}, dedupe=f"sync:{acc.pk}"))

    @action(detail=True, methods=["post"], url_path="fetch-orders")
    def fetch_orders(self, request, pk=None):
        acc = self.get_object()
        return job_response(enqueue("fetch_orders", account=acc, dedupe=f"orders:{acc.pk}"))

    @action(detail=True, methods=["post"], url_path="fetch-remote")
    def fetch_remote(self, request, pk=None):
        acc = self.get_object()
        if CAP_LINK not in client_class(acc.marketplace).capabilities:
            raise ValidationError({"detail": "not supported"})
        return job_response(enqueue("fetch_remote", account=acc, dedupe=f"remote:{acc.pk}"))

    @action(detail=True, methods=["get"])
    def remote(self, request, pk=None):
        """Kabinetdagi mavjud SKU'lar (bog'lash uchun). Qaysi biri bizdagi mahsulotga bog'langani ham ko'rsatiladi."""
        acc = self.get_object()
        linked = dict(MarketplaceListing.objects.filter(account=acc).exclude(external_sku="")
                      .values_list("external_sku", "product_id"))
        items = [{**r, "product_id": linked.get(r.get("external_sku"))} for r in (acc.meta or {}).get("remote_products") or []]
        q = (request.query_params.get("q") or "").lower()
        if q:
            items = [r for r in items if q in (r.get("title") or "").lower() or q in (r.get("offer_id") or "").lower()
                     or q in (r.get("barcode") or "")]
        return Response({"fetched_at": (acc.meta or {}).get("remote_fetched_at"), "items": items[:500]})


class ListingViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsSellerUser]
    serializer_class = ListingSerializer
    pagination_class = Pagination

    def get_queryset(self):
        qs = MarketplaceListing.objects.filter(account__in=accounts_for(self.request)).select_related(
            "product__category", "account__seller")
        p = self.request.query_params
        if p.get("account"):
            qs = qs.filter(account_id=p["account"])
        if p.get("status"):
            qs = qs.filter(status=p["status"])
        if p.get("product"):
            qs = qs.filter(product_id=p["product"])
        if p.get("q"):
            q = p["q"].lower()
            qs = qs.filter(Q(product__search__contains=q) | Q(offer_id__icontains=q) | Q(external_id=p["q"]))
        return qs.order_by("-updated_at")

    def create(self, request):
        """Mahsulotlarni kabinetga qo'shish va joylash: {account, product_ids: [..], publish: true}"""
        acc = get_object_or_404(accounts_for(request), pk=request.data.get("account"))
        ids = request.data.get("product_ids") or []
        if not isinstance(ids, list) or not ids or not all(str(i).isdigit() for i in ids):
            raise ValidationError({"product_ids": "list of ids required"})
        products = Product.objects.filter(pk__in=ids, seller=acc.seller)
        created = []
        with transaction.atomic():
            for p in products:
                li, _ = MarketplaceListing.objects.get_or_create(product=p, account=acc, defaults={"offer_id": p.sku})
                created.append(li)
        jobs = []
        if request.data.get("publish", True):
            jobs = services.request_publish([li for li in created if li.status != MarketplaceListing.ST_ACTIVE
                                             or not li.external_sku] or created)
        return Response({"listings": ListingSerializer(created, many=True, context={"request": request}).data,
                         "jobs": JobSerializer(jobs, many=True).data}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"])
    def publish(self, request):
        ids = request.data.get("ids") or []
        listings = list(self.get_queryset().filter(pk__in=ids))
        if not listings:
            raise ValidationError({"ids": "required"})
        return Response({"jobs": JobSerializer(services.request_publish(listings), many=True).data},
                        status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=["post"])
    def link(self, request, pk=None):
        """Kabinetdagi mavjud kartochkaga qo'lda bog'lash (Uzum): {external_sku} — ro'yxat /accounts/<id>/remote/ dan."""
        li = self.get_object()
        sku = str(request.data.get("external_sku") or "")
        item = next((r for r in (li.account.meta or {}).get("remote_products") or [] if r.get("external_sku") == sku), None)
        if not item:
            raise ValidationError({"external_sku": "Kabinet ro'yxatida topilmadi — avval ro'yxatni yangilang"})
        if MarketplaceListing.objects.filter(account=li.account, external_sku=sku).exclude(pk=li.pk).exists():
            raise ValidationError({"external_sku": "Bu SKU boshqa mahsulotga bog'langan"})
        services.link_listing(li, item)
        return Response(ListingSerializer(li, context={"request": request}).data)

    @action(detail=True, methods=["get"])
    def check(self, request, pk=None):
        """Joylashdan oldin tekshiruv (tashqi so'rovsiz): nima yetishmaydi."""
        li = self.get_object()
        if CAP_LINK in client_class(li.account.marketplace).capabilities and \
                "create_cards" not in client_class(li.account.marketplace).capabilities:
            return Response({"ok": bool(li.external_sku), "errors": [] if li.external_sku else ["Kabinetdagi SKU'ga bog'lanmagan"]})
        payload, errors = services.build_payload(li)
        return Response({"ok": not errors, "errors": errors,
                         "preview": None if not payload else {"name": payload.name, "price": payload.price,
                                                              "currency": payload.currency,
                                                              "stock": services.stock_for(li.account, li.product),
                                                              "attributes": len(payload.attributes)}})

    def perform_destroy(self, li):
        """ImkonMarket'dan uzish: marketplace'dagi qoldiq 0 qilinadi (kartochka marketplace'da qoladi)."""
        if li.status == MarketplaceListing.ST_ACTIVE and li.account.is_usable:
            enqueue("zero_stock", account=li.account, payload={"refs": [{
                "offer_id": li.offer_id, "external_id": li.external_id, "external_sku": li.external_sku,
                "external_meta": li.external_meta}]})
        li.delete()

    @action(detail=True, methods=["post"])
    def refresh(self, request, pk=None):
        li = self.get_object()
        return job_response(enqueue("poll_status", account=li.account, payload={"ids": [li.pk]}))


class OrderViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsSellerUser]
    serializer_class = OrderSerializer
    pagination_class = Pagination

    def get_queryset(self):
        qs = MarketplaceOrder.objects.filter(account__in=accounts_for(self.request)).select_related("account__seller")
        p = self.request.query_params
        if p.get("account"):
            qs = qs.filter(account_id=p["account"])
        if p.get("state"):
            qs = qs.filter(state__in=p["state"].split(","))
        if p.get("marketplace"):
            qs = qs.filter(account__marketplace=p["marketplace"])
        if p.get("q"):
            qs = qs.filter(external_id__icontains=p["q"])
        return qs

    @action(detail=True, methods=["post"], url_path="action")
    def do_action(self, request, pk=None):
        order = self.get_object()
        act = request.data.get("action")
        cls = client_class(order.account.marketplace)
        if CAP_ORDER_ACTIONS not in cls.capabilities or act not in cls.order_actions(order):
            raise ValidationError({"action": f"Hozir mumkin: {', '.join(cls.order_actions(order)) or '—'}"})
        kw = {k: request.data[k] for k in ("reason", "reason_id", "comment", "issue_code") if request.data.get(k)}
        return job_response(enqueue("order_action", account=order.account,
                                    payload={"order_id": order.pk, "action": act, "kw": kw}, max_attempts=3))


class LogViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsSellerUser]
    serializer_class = LogSerializer
    pagination_class = Pagination

    def get_queryset(self):
        qs = SyncLog.objects.filter(account__in=accounts_for(self.request))
        p = self.request.query_params
        if p.get("account"):
            qs = qs.filter(account_id=p["account"])
        if p.get("errors") == "1":
            qs = qs.filter(ok=False)
        return qs


class JobViewSet(mixins.RetrieveModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsSellerUser]
    serializer_class = JobSerializer
    pagination_class = Pagination

    def get_queryset(self):
        qs = Job.objects.filter(Q(account__in=accounts_for(self.request)) | (Q(account__isnull=True) if is_op(self.request)
                                                                              else Q(pk__in=[])))
        if self.request.query_params.get("account"):
            qs = qs.filter(account_id=self.request.query_params["account"])
        return qs


class ProductInfoView(viewsets.ViewSet):
    """GET/PUT /api/mp/product-info/<product_id>/ — og'irlik, o'lcham, brend, shtrix-kod, xususiyatlar."""

    permission_classes = [IsSellerUser]

    def _product(self, request, pk):
        s = seller_of(request.user)
        qs = Product.objects.all() if s.role == Seller.ROLE_OPERATOR else Product.objects.filter(seller=s)
        return get_object_or_404(qs, pk=pk)

    def retrieve(self, request, pk=None):
        p = self._product(request, pk)
        info = ProductMarketInfo.objects.filter(product=p).first() or ProductMarketInfo(product=p)
        mappings = CategoryMapping.objects.filter(category=p.category).prefetch_related("attributes")
        need = [{"marketplace": m.marketplace, "key": f"{m.marketplace}:{a.external_id}", "name": a.name,
                 "required": a.required, "values": a.values[:200] if a.values else []}
                for m in mappings for a in m.attributes.all() if a.source == AttributeMapping.SRC_PRODUCT]
        return Response({**ProductInfoSerializer(info).data, "product_attributes": need,
                         "listings": ListingSerializer(p.mp_listings.select_related("account__seller", "product__category"),
                                                       many=True, context={"request": request}).data})

    def update(self, request, pk=None):
        p = self._product(request, pk)
        info, _ = ProductMarketInfo.objects.get_or_create(product=p)
        ser = ProductInfoSerializer(info, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)


# ------------------------------------------------------------ operator only
class ExternalCategoryViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsSellerUser]
    serializer_class = ExternalCategorySerializer
    pagination_class = Pagination

    def get_queryset(self):
        p = self.request.query_params
        qs = ExternalCategory.objects.filter(marketplace=p.get("marketplace", ""))
        for word in (p.get("q") or "").lower().split():
            qs = qs.filter(search__contains=word)
        return qs

    @action(detail=False, methods=["post"])
    def refresh(self, request):
        require_op(request)
        mp = request.data.get("marketplace")
        if mp not in dict(MARKETPLACES) or CAP_CATEGORIES not in client_class(mp).capabilities:
            raise ValidationError({"marketplace": "Bu marketplace kategoriyalarni API orqali bermaydi"})
        acc = MarketplaceAccount.objects.filter(marketplace=mp, status=MarketplaceAccount.ST_ACTIVE, is_enabled=True).first()
        if not acc:
            raise ValidationError({"detail": "Kategoriyalarni olish uchun kamida bitta faol kabinet kerak"})
        return job_response(enqueue("fetch_categories", account=acc, dedupe=f"cats:{mp}"))


class MappingViewSet(viewsets.ModelViewSet):
    permission_classes = [IsSellerUser]
    serializer_class = MappingSerializer
    pagination_class = None

    def get_queryset(self):
        qs = CategoryMapping.objects.select_related("category").prefetch_related("attributes__value_map")
        if self.request.query_params.get("marketplace"):
            qs = qs.filter(marketplace=self.request.query_params["marketplace"])
        return qs.order_by("category__order", "marketplace")

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            require_op(request)

    def perform_create(self, ser):
        m = ser.save()
        self._fetch_attrs(m)

    def perform_update(self, ser):
        old = self.get_object()
        changed = old.external_id != ser.validated_data.get("external_id", old.external_id) or \
            old.external_type_id != ser.validated_data.get("external_type_id", old.external_type_id)
        m = ser.save()
        if changed:
            m.attributes.all().delete()
            self._fetch_attrs(m)

    def _fetch_attrs(self, m):
        if CAP_CATEGORIES not in client_class(m.marketplace).capabilities:
            return None
        acc = MarketplaceAccount.objects.filter(marketplace=m.marketplace, status=MarketplaceAccount.ST_ACTIVE,
                                                is_enabled=True).first()
        if acc:
            return enqueue("fetch_attributes", account=acc, payload={"mapping_id": m.pk}, dedupe=f"attrs:{m.pk}")
        return None

    @action(detail=True, methods=["post"], url_path="fetch-attributes")
    def fetch_attributes(self, request, pk=None):
        job = self._fetch_attrs(self.get_object())
        if not job:
            raise ValidationError({"detail": "Faol kabinet yo'q yoki marketplace atributlarni bermaydi"})
        return job_response(job)


class AttributeViewSet(mixins.UpdateModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsSellerUser]
    serializer_class = AttributeSerializer
    queryset = AttributeMapping.objects.select_related("mapping")

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            require_op(request)

    @action(detail=True, methods=["post"], url_path="value-map")
    def value_map(self, request, pk=None):
        am = self.get_object()
        our = (request.data.get("our_value") or "").strip()
        if not our:
            raise ValidationError({"our_value": "required"})
        if request.data.get("delete"):
            AttributeValueMap.objects.filter(attribute=am, our_value=our).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        vm, _ = AttributeValueMap.objects.update_or_create(attribute=am, our_value=our, defaults={
            "external_value_id": str(request.data.get("external_value_id") or ""),
            "external_value": str(request.data.get("external_value") or "")})
        return Response(ValueMapSerializer(vm).data)

    @action(detail=True, methods=["post"])
    def search(self, request, pk=None):
        """Lug'at qiymatlarini qidirish (Ozon) — fon vazifasi; natija GET /api/mp/jobs/<id>/ → result.values"""
        am = self.get_object()
        acc = MarketplaceAccount.objects.filter(marketplace=am.mapping.marketplace, is_enabled=True,
                                                status=MarketplaceAccount.ST_ACTIVE).first()
        if not acc:
            raise ValidationError({"detail": "Faol kabinet yo'q"})
        return job_response(enqueue("search_values", account=acc, max_attempts=2, payload={
            "mapping_id": am.mapping_id, "attribute_id": am.external_id, "query": request.data.get("query", "")}))


@api_view(["GET"])
@permission_classes([IsSellerUser])
def categories_overview(request):
    """Bizning kategoriyalar × marketplace moslash holati (operator ekrani uchun)."""
    maps = {(m.category_id, m.marketplace): m for m in CategoryMapping.objects.prefetch_related("attributes")}
    rows = []
    for c in Category.objects.order_by("order"):
        row = {"slug": c.slug, "name": c.name, "icon": c.icon, "maps": {}}
        for mp, _ in MARKETPLACES:
            m = maps.get((c.id, mp))
            row["maps"][mp] = None if not m else {"id": m.id, "external_name": m.external_name,
                                                  "missing": MappingSerializer().get_required_missing(m)}
        rows.append(row)
    return Response(rows)
