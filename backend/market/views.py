from django.conf import settings
from decimal import Decimal

from django.db.models import Count, F, Q, Sum
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

from . import services
from .contract_pdf import render_contract
from .i18n_meta import languages, regions, units
from .models import Application, Category, Contract, Product, Seller
from .payments import checkout_url, click_enabled, payme_enabled
from .serializers import (
    AgentCatalogSerializer, CategorySerializer, ContractSerializer, ProductDetailSerializer, ProductListSerializer,
    PublicOrderSerializer, SellerApplicationSerializer, SellerProductSerializer, SellerProfileSerializer,
    SellerPublicSerializer,
)
from .translit import to_cyrl, to_new


# ---------------------------------------------------------------- helpers
def product_queryset(params, base=None):
    qs = (base if base is not None else Product.objects.filter(is_active=True, seller__is_active=True)).select_related(
        "seller", "category")
    q = (params.get("q") or "").strip().lower()
    if q:
        variants = {q, to_cyrl(q).lower(), to_new(q).lower()}
        cond = Q()
        for v in variants:
            cond |= Q(search__contains=v)
        qs = qs.filter(cond)
    if params.get("category"):
        qs = qs.filter(category__slug__in=params["category"].split(","))
    if params.get("seller"):
        qs = qs.filter(seller__code__in=params["seller"].split(","))
    if params.get("region"):
        qs = qs.filter(seller__region__in=params["region"].split(","))
    if params.get("min_price"):
        qs = qs.filter(price__gte=Decimal(params["min_price"]))
    if params.get("max_price"):
        qs = qs.filter(price__lte=Decimal(params["max_price"]))
    if params.get("in_stock") in ("1", "true"):
        qs = qs.filter(stock__isnull=False, stock__gt=F("reserved"))
    if params.get("made_to_order") in ("1", "true"):
        qs = qs.filter(stock__isnull=True)
    if params.get("delivery") in ("1", "true"):
        qs = qs.filter(delivery=True)
    if params.get("priced") in ("1", "true"):
        qs = qs.filter(price__isnull=False)
    order = params.get("ordering") or "popular"
    if order == "price":
        qs = qs.order_by(F("price").asc(nulls_last=True), "id")
    elif order == "-price":
        qs = qs.order_by(F("price").desc(nulls_last=True), "id")
    elif order == "new":
        qs = qs.order_by("-created_at", "-id")
    elif order == "name":
        qs = qs.order_by("search")
    else:  # popular
        qs = qs.order_by("-sold", "-views", F("image").desc(nulls_last=True), F("price").asc(nulls_last=True), "id")
    return qs


def featured(qs):
    """Bosh sahifa uchun: har kategoriyadan navbatma-navbat (eng ko'p sotilgan/ko'rilgan, keyin qimmatroq)."""
    groups = {}
    for p in qs.order_by("-sold", "-views", F("price").desc(nulls_last=True)):
        groups.setdefault(p.category_id, []).append(p)
    out, lists = [], list(groups.values())
    while any(lists):
        for lst in lists:
            if lst:
                out.append(lst.pop(0))
    return out


def facets(qs):
    return {
        "categories": {r["category__slug"]: r["n"] for r in qs.order_by().values("category__slug").annotate(n=Count("id"))},
        "regions": {r["seller__region"]: r["n"] for r in qs.order_by().values("seller__region").annotate(n=Count("id"))},
        "sellers": {r["seller__code"]: r["n"] for r in qs.order_by().values("seller__code").annotate(n=Count("id"))},
    }


def seller_of(user) -> Seller:
    prof = getattr(user, "profile", None)
    if not prof:
        raise PermissionDenied("seller account required")
    return prof.seller


class IsSellerUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and hasattr(request.user, "profile"))


def is_operator(user):
    return seller_of(user).role == Seller.ROLE_OPERATOR


# ---------------------------------------------------------------- public
@api_view(["GET"])
def meta(request):
    cats = Category.objects.annotate(
        count=Count("products", filter=Q(products__is_active=True, products__seller__is_active=True))).order_by("order", "id")
    sellers = Seller.objects.filter(is_active=True, role=Seller.ROLE_SELLER).annotate(
        product_count=Count("products", filter=Q(products__is_active=True))).order_by("id")
    stats = Product.objects.filter(is_active=True).aggregate(n=Count("id"))
    return Response({
        "brand": settings.BRAND_NAME,
        "languages": languages(),
        "categories": CategorySerializer(cats, many=True).data,
        "regions": regions(),
        "units": units(),
        "sellers": SellerPublicSerializer(sellers, many=True, context={"request": request}).data,
        "stats": {"products": stats["n"], "sellers": sellers.filter(product_count__gt=0).count(),
                  "sellers_total": sellers.count(), "regions": len(regions())},
        "payments": {"click": {"demo": not click_enabled()}, "payme": {"demo": not payme_enabled()},
                     "bank": {"demo": False}},
    })


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ProductListSerializer

    def get_queryset(self):
        return product_queryset(self.request.query_params)

    def get_serializer_class(self):
        return ProductDetailSerializer if self.action == "retrieve" else ProductListSerializer

    def list(self, request, *a, **kw):
        qs = self.filter_queryset(self.get_queryset())
        if request.query_params.get("ordering") == "featured":
            qs = featured(qs)
        page = self.paginate_queryset(qs)
        resp = self.get_paginated_response(self.get_serializer(page, many=True).data)
        if request.query_params.get("facets") in ("1", "true"):
            base = product_queryset({"q": request.query_params.get("q", "")})
            resp.data["facets"] = facets(base)
        return resp

    def retrieve(self, request, *a, **kw):
        obj = get_object_or_404(Product.objects.select_related("seller", "category"), pk=kw["pk"], is_active=True)
        Product.objects.filter(pk=obj.pk).update(views=F("views") + 1)
        data = ProductDetailSerializer(obj, context={"request": request}).data
        similar = Product.objects.filter(is_active=True, category=obj.category).exclude(pk=obj.pk).select_related(
            "seller", "category").order_by(F("price").asc(nulls_last=True))[:8]
        same_seller = Product.objects.filter(is_active=True, seller=obj.seller).exclude(pk=obj.pk).select_related(
            "seller", "category")[:8]
        data["similar"] = ProductListSerializer(similar, many=True, context={"request": request}).data
        data["same_seller"] = ProductListSerializer(same_seller, many=True, context={"request": request}).data
        data["seller_full"] = SellerPublicSerializer(obj.seller, context={"request": request}).data
        return Response(data)


class SellerViewSet(viewsets.ReadOnlyModelViewSet):
    lookup_field = "code"
    serializer_class = SellerPublicSerializer
    pagination_class = None

    def get_queryset(self):
        return Seller.objects.filter(is_active=True, role=Seller.ROLE_SELLER).annotate(
            product_count=Count("products", filter=Q(products__is_active=True))).order_by("id")


class ApplicationCreateView(APIView):
    """Savatdan ariza yuborish. Javob: har bir sotuvchi uchun alohida ariza."""

    def post(self, request):
        apps = services.create_applications(request.data)
        return Response(
            [{"number": a.number, "token": str(a.token), "seller": a.seller.name, "total": str(a.total),
              "has_unpriced": a.has_unpriced} for a in apps],
            status=status.HTTP_201_CREATED,
        )


def _order(token):
    try:
        return Application.objects.select_related("seller", "agent").prefetch_related("items__product", "logs").get(token=token)
    except (Application.DoesNotExist, ValueError, Exception):
        raise Http404


@api_view(["GET"])
def order_detail(request, token):
    return Response(PublicOrderSerializer(_order(token), context={"request": request}).data)


@api_view(["GET"])
def order_track(request):
    number = (request.query_params.get("number") or "").strip().upper()
    phone = "".join(ch for ch in request.query_params.get("phone", "") if ch.isdigit())[-9:]
    app = Application.objects.filter(number=number).first()
    if not app or not phone or "".join(ch for ch in app.buyer_phone if ch.isdigit())[-9:] != phone:
        return Response({"detail": "not found"}, status=404)
    return Response({"token": str(app.token)})


@api_view(["POST"])
def order_pay(request, token):
    app = _order(token)
    c = getattr(app, "contract", None)
    if not c or c.status == Contract.ST_CANCELLED:
        raise ValidationError({"detail": "contract not ready"})
    method = request.data.get("method") or app.payment_method
    if method not in ("click", "payme"):
        raise ValidationError({"method": "click | payme"})
    return Response(checkout_url(c, method, request.data.get("lang") or app.lang))


@api_view(["POST"])
def order_cancel(request, token):
    app = _order(token)
    if app.status not in (Application.ST_NEW, Application.ST_REVIEW):
        raise ValidationError({"status": "cannot cancel"})
    app.status = Application.ST_CANCELLED
    app.save()
    services.log(app, "cancelled", "buyer")
    return Response({"ok": True})


@api_view(["GET"])
def contract_verify(request, token):
    try:
        c = Contract.objects.select_related("seller", "agent", "application").get(token=token)
    except Exception:
        return Response({"valid": False}, status=404)
    a = c.application
    masked = a.buyer_name if a.buyer_type == "b2b" else (a.buyer_name.split(" ")[0] + " ***")
    return Response({
        "valid": True, "number": c.number, "date": c.date, "status": c.status, "seller": c.seller.name,
        "seller_inn": c.seller.inn, "agent": c.agent.name if c.agent else None, "buyer": masked,
        "buyer_type": c.buyer_type, "total": str(c.grand_total), "paid": str(c.paid_amount),
    })


@api_view(["GET"])
def contract_pdf(request, token):
    try:
        c = Contract.objects.get(token=token)
    except Exception:
        raise Http404
    if not c.pdf:
        render_contract(c)
    return FileResponse(c.pdf.open("rb"), content_type="application/pdf",
                        filename=c.number.replace("/", "_") + ".pdf", as_attachment=request.query_params.get("dl") == "1")


# ---------------------------------------------------------------- auth
class LoginSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        prof = getattr(self.user, "profile", None)
        if not prof:
            raise ValidationError({"detail": "not a seller account"})
        data["seller"] = SellerProfileSerializer(prof.seller).data
        data["username"] = self.user.username
        return data


class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer


class MeView(APIView):
    permission_classes = [IsSellerUser]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get(self, request):
        s = seller_of(request.user)
        return Response({"username": request.user.username, "seller": SellerProfileSerializer(s, context={"request": request}).data})

    def patch(self, request):
        s = seller_of(request.user)
        ser = SellerProfileSerializer(s, data=request.data, partial=True, context={"request": request})
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response({"username": request.user.username, "seller": ser.data})


class ChangePasswordView(APIView):
    permission_classes = [IsSellerUser]

    def post(self, request):
        old, new = request.data.get("old_password"), request.data.get("new_password") or ""
        if not request.user.check_password(old):
            raise ValidationError({"old_password": "wrong"})
        if len(new) < 8:
            raise ValidationError({"new_password": "min 8"})
        request.user.set_password(new)
        request.user.save()
        return Response({"ok": True})


# ---------------------------------------------------------------- seller cabinet
class DashboardView(APIView):
    permission_classes = [IsSellerUser]

    def get(self, request):
        s = seller_of(request.user)
        op = s.role == Seller.ROLE_OPERATOR
        apps = Application.objects.all() if op else Application.objects.filter(Q(seller=s) | Q(agent=s))
        contracts = Contract.objects.all() if op else Contract.objects.filter(Q(seller=s) | Q(agent=s))
        products = Product.objects.all() if op else Product.objects.filter(seller=s)
        month = timezone.localdate().replace(day=1)
        own = contracts if op else contracts.filter(seller=s)
        data = {
            "applications_new": apps.filter(status__in=["new", "review"]).count(),
            "applications_total": apps.count(),
            "contracts_active": contracts.filter(status__in=["active", "paid"]).count(),
            "contracts_total": contracts.count(),
            "revenue_month": str(own.filter(date__gte=month).exclude(status="cancelled").aggregate(v=Sum("total"))["v"] or 0),
            "paid_month": str(own.filter(date__gte=month).aggregate(v=Sum("paid_amount"))["v"] or 0),
            "receivable": str(sum((c.due_amount for c in own.filter(status__in=["active", "paid", "shipped"])), Decimal(0))),
            "products": products.count(),
            "products_out_of_stock": products.filter(stock=0).count() + products.filter(stock__isnull=False, stock__lte=F("reserved")).exclude(stock=0).count(),
            "agent_contracts": Contract.objects.filter(agent=s).count(),
            "recent": SellerApplicationSerializer(apps.select_related("seller", "agent").prefetch_related("items", "logs")[:6], many=True).data,
            "top_products": SellerProductSerializer(products.order_by("-sold", "-views")[:5], many=True, context={"request": request}).data,
        }
        return Response(data)


class SellerProductViewSet(viewsets.ModelViewSet):
    permission_classes = [IsSellerUser]
    serializer_class = SellerProductSerializer
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_queryset(self):
        s = seller_of(self.request.user)
        base = Product.objects.all() if s.role == Seller.ROLE_OPERATOR else Product.objects.filter(seller=s)
        params = self.request.query_params.copy()
        qs = product_queryset(params, base=base)
        if params.get("active") == "0":
            qs = qs.filter(is_active=False)
        return qs if params.get("ordering") else qs.order_by("-updated_at")

    def perform_create(self, ser):
        s = seller_of(self.request.user)
        if s.role == Seller.ROLE_OPERATOR and self.request.data.get("seller"):
            s = get_object_or_404(Seller, code=self.request.data["seller"])
        addr = ser.validated_data.get("address") or s.district_i18n
        ser.save(seller=s, address=addr)

    @action(detail=True, methods=["post"])
    def stock(self, request, pk=None):
        p = self.get_object()
        v = request.data.get("stock")
        p.stock = None if v in (None, "", "null") else max(int(v), 0)
        p.save()
        return Response(SellerProductSerializer(p, context={"request": request}).data)


class AgentCatalogView(APIView):
    """Barcha muassasalar mahsulotlari va qoldig'i — boshqa muassasa nomidan shartnoma tuzish uchun."""

    permission_classes = [IsSellerUser]

    def get(self, request):
        qs = product_queryset(request.query_params)
        from .pagination import Pagination

        pg = Pagination()
        page = pg.paginate_queryset(qs, request, view=self)
        resp = pg.get_paginated_response(AgentCatalogSerializer(page, many=True, context={"request": request}).data)
        if request.query_params.get("facets") in ("1", "true"):
            resp.data["facets"] = facets(product_queryset({"q": request.query_params.get("q", "")}))
        return resp


class AgentOrderView(APIView):
    """Muassasa xaridor uchun (o'zi yoki boshqa muassasa mahsulotidan) shartnoma chiqaradi.
    Mahsulot kimniki bo'lsa, shartnoma o'sha muassasa nomidan tuziladi."""

    permission_classes = [IsSellerUser]

    def post(self, request):
        s = seller_of(request.user)
        apps = services.create_applications(request.data, user=request.user, agent=s)
        out = []
        for a in apps:
            a.refresh_from_db()
            out.append(SellerApplicationSerializer(a, context={"request": request}).data)
        return Response(out, status=201)


class SellerApplicationViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsSellerUser]
    serializer_class = SellerApplicationSerializer

    def get_queryset(self):
        s = seller_of(self.request.user)
        qs = Application.objects.select_related("seller", "agent", "contract").prefetch_related("items__product", "logs")
        if s.role != Seller.ROLE_OPERATOR:
            scope = self.request.query_params.get("scope")
            if scope == "agent":
                qs = qs.filter(agent=s)
            elif scope == "own":
                qs = qs.filter(seller=s)
            else:
                qs = qs.filter(Q(seller=s) | Q(agent=s))
        st = self.request.query_params.get("status")
        if st:
            qs = qs.filter(status__in=st.split(","))
        q = (self.request.query_params.get("q") or "").strip()
        if q:
            qs = qs.filter(Q(number__icontains=q) | Q(buyer_name__icontains=q) | Q(buyer_phone__icontains=q) | Q(buyer_inn__icontains=q))
        return qs

    def _own(self, app):
        s = seller_of(self.request.user)
        if s.role != Seller.ROLE_OPERATOR and app.seller_id != s.id:
            raise PermissionDenied("only product owner can process")

    @action(detail=True, methods=["post"])
    def review(self, request, pk=None):
        app = self.get_object()
        self._own(app)
        if app.status == Application.ST_NEW:
            app.status = Application.ST_REVIEW
            app.save()
            services.log(app, "review", "", request.user)
        return Response(self.get_serializer(app).data)

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        app = self.get_object()
        self._own(app)
        services.confirm_application(app, request.data, user=request.user)
        return Response(self.get_serializer(self.get_queryset().get(pk=app.pk)).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        app = self.get_object()
        self._own(app)
        services.reject_application(app, request.data.get("reason", ""), request.user)
        return Response(self.get_serializer(self.get_queryset().get(pk=app.pk)).data)


class SellerContractViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsSellerUser]
    serializer_class = ContractSerializer

    def get_queryset(self):
        s = seller_of(self.request.user)
        qs = Contract.objects.select_related("seller", "agent", "application").prefetch_related("payments", "application__items__product")
        if s.role != Seller.ROLE_OPERATOR:
            qs = qs.filter(Q(seller=s) | Q(agent=s))
        st = self.request.query_params.get("status")
        if st:
            qs = qs.filter(status__in=st.split(","))
        q = (self.request.query_params.get("q") or "").strip()
        if q:
            qs = qs.filter(Q(number__icontains=q) | Q(application__buyer_name__icontains=q) | Q(application__number__icontains=q))
        return qs

    def _own(self, c):
        s = seller_of(self.request.user)
        if s.role != Seller.ROLE_OPERATOR and c.seller_id != s.id:
            raise PermissionDenied("only contract seller can do this")

    def _out(self, c):
        return Response(self.get_serializer(self.get_queryset().get(pk=c.pk)).data)

    @action(detail=True, methods=["post"])
    def payment(self, request, pk=None):
        """Bank o'tkazmasi (perechisleniye) tushganini qayd etish."""
        c = self.get_object()
        self._own(c)
        services.register_payment(c, request.data.get("amount") or c.due_amount, request.data.get("method") or "bank",
                                  document_no=request.data.get("document_no", ""), note=request.data.get("note", ""),
                                  user=request.user)
        return self._out(c)

    @action(detail=True, methods=["post"])
    def ship(self, request, pk=None):
        c = self.get_object()
        self._own(c)
        services.ship_contract(c, request.user)
        return self._out(c)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        c = self.get_object()
        self._own(c)
        services.complete_contract(c, request.user)
        return self._out(c)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        c = self.get_object()
        self._own(c)
        services.cancel_contract(c, request.data.get("reason", ""), request.user)
        return self._out(c)

    @action(detail=True, methods=["post"])
    def regenerate(self, request, pk=None):
        c = self.get_object()
        if request.data.get("lang"):
            c.lang = request.data["lang"]
            c.save(update_fields=["lang"])
        render_contract(c)
        return self._out(c)

    @action(detail=True, methods=["post"], url_path="pay-link")
    def pay_link(self, request, pk=None):
        c = self.get_object()
        return Response(checkout_url(c, request.data.get("method") or "payme", c.lang))
