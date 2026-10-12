"""Ma'lumotlarni yangi kartochka tuzilmasiga ko'chirish:
- integrations.ProductMarketInfo (brend, shtrix-kod, o'lcham...) -> Product maydonlari
- Product.image -> ProductImage (galereyaning birinchi rasmi)
"""
from django.db import migrations


def forward(apps, schema_editor):
    Product = apps.get_model("market", "Product")
    ProductImage = apps.get_model("market", "ProductImage")
    try:
        Info = apps.get_model("integrations", "ProductMarketInfo")
    except LookupError:
        Info = None
    if Info is not None:
        for i in Info.objects.all():
            Product.objects.filter(pk=i.product_id).update(
                brand=i.brand, barcode=i.barcode, country=i.country or "O'zbekiston", weight_kg=i.weight_kg,
                length_cm=i.length_cm, width_cm=i.width_cm, height_cm=i.height_cm)
    for p in Product.objects.exclude(image="").exclude(image__isnull=True):
        if not ProductImage.objects.filter(product=p).exists():
            ProductImage.objects.create(product=p, image=p.image.name, order=0, is_sample=p.image_is_sample)


class Migration(migrations.Migration):
    dependencies = [
        ("market", "0003_catalog_v2"),
        ("integrations", "0002_marketplaceorder_stock_items"),
    ]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
