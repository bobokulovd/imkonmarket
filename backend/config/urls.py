from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

admin.site.site_header = f"{settings.BRAND_NAME} — boshqaruv paneli"
admin.site.site_title = settings.BRAND_NAME

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("market.urls")),
    # Mahsulot rasmlari (kichik hajm uchun; katta yuklamada nginx orqali bering)
    re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
]
