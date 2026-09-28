from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from . import payments, views

router = DefaultRouter()
router.register("products", views.ProductViewSet, basename="product")
router.register("sellers", views.SellerViewSet, basename="seller")
router.register("seller/products", views.SellerProductViewSet, basename="seller-product")
router.register("seller/applications", views.SellerApplicationViewSet, basename="seller-application")
router.register("seller/contracts", views.SellerContractViewSet, basename="seller-contract")

urlpatterns = [
    path("meta/", views.meta),
    path("applications/", views.ApplicationCreateView.as_view()),
    path("orders/track/", views.order_track),
    path("orders/<str:token>/", views.order_detail),
    path("orders/<str:token>/pay/", views.order_pay),
    path("orders/<str:token>/cancel/", views.order_cancel),
    path("contracts/verify/<str:token>/", views.contract_verify),
    path("contracts/<str:token>/pdf/", views.contract_pdf),
    path("auth/login/", views.LoginView.as_view()),
    path("auth/refresh/", TokenRefreshView.as_view()),
    path("auth/me/", views.MeView.as_view()),
    path("auth/change-password/", views.ChangePasswordView.as_view()),
    path("seller/dashboard/", views.DashboardView.as_view()),
    path("seller/catalog/", views.AgentCatalogView.as_view()),
    path("seller/agent-order/", views.AgentOrderView.as_view()),
    path("pay/demo/<int:payment_id>/", payments.demo_info),
    path("pay/demo/<int:payment_id>/confirm/", payments.demo_confirm),
    path("payments/payme/", payments.payme_endpoint),
    path("payments/click/prepare/", payments.click_prepare),
    path("payments/click/complete/", payments.click_complete),
    path("", include(router.urls)),
]
