from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("accounts", views.AccountViewSet, basename="mp-account")
router.register("listings", views.ListingViewSet, basename="mp-listing")
router.register("orders", views.OrderViewSet, basename="mp-order")
router.register("logs", views.LogViewSet, basename="mp-log")
router.register("jobs", views.JobViewSet, basename="mp-job")
router.register("product-info", views.ProductInfoView, basename="mp-product-info")
router.register("categories", views.ExternalCategoryViewSet, basename="mp-category")
router.register("mappings", views.MappingViewSet, basename="mp-mapping")
router.register("attributes", views.AttributeViewSet, basename="mp-attribute")

urlpatterns = [
    path("meta/", views.meta),
    path("overview/", views.categories_overview),
    path("", include(router.urls)),
]
