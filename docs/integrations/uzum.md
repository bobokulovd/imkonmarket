# Uzum Market Seller OpenAPI — konspekt

> Holati: 2026-09-28. Faqat rasmiy manbalarda o'qilgan faktlar yozildi. Tasdiqlanmagan joylar
> "hujjatda topilmadi / tekshirilmadi" deb belgilangan.
> **Muhim cheklov:** swagger JSON (≈65–70 KB) WebFetch orqali qisqartirilib keldi. Paths, parametrlar,
> enum'lar va response kodlari o'qildi, lekin `components/schemas` bo'limi (request/response body
> maydonlari) ko'rinmadi. Body tuzilmalari quyida faqat schema **nomi** bilan berilgan; maydonlarni
> real token bilan swagger UI orqali qo'lda tekshirish kerak.

## 1. Manbalar (2026-09-28 da o'qildi)

- https://api-seller.uzum.uz/api/seller-openapi/swagger/api-docs — OpenAPI 3.0.0 spec, title "Uzum market seller openapi", version 1.0.0 (asosiy manba)
- https://api-seller.uzum.uz/api/seller-openapi/swagger/swagger-ui/index.html — Swagger UI (JS talab qiladi, kontent o'qilmadi)
- https://seller.uzum.uz/manual/ — sotuvchi qo'llanmasi (API bo'limi yo'q)
- https://seller.uzum.uz/manual/5.product-creation/ — kartochka yaratish (faqat UI orqali)
- https://seller.uzum.uz/seller/api-keys — kabinetdagi API kalitlar sahifasi (SPA, login talab qiladi, matn o'qilmadi)
- Ochilmadi: `.../v3/api-docs` (403), `.../swagger/swagger-ui/` (404), `.../swagger/api-docs.yaml` (403)

Base URL (spec `servers`): `https://api-seller.uzum.uz/api/seller-openapi/` — "OpenAPI для продавцов UZUM MARKET".

## 2. Autentifikatsiya

- Security scheme `TokenAuth`: `type: apiKey`, `in: header`, `name: Authorization`, description "Seller token for API access". Barcha endpointlarga qo'llanadi.
- Header formati: `Authorization: <token>`. Spec'da "Bearer" so'zi **uchramaydi** → prefiks yo'q deb taxmin qilinadi; real so'rov bilan tekshirilmadi.
- Token olish: kabinetda `https://seller.uzum.uz/seller/api-keys` sahifasi mavjud (URL qidiruvda topildi). Qadamlar matni — hujjatda topilmadi / tekshirilmadi.
- Scopes / ruxsatlar: hujjatda topilmadi / tekshirilmadi.
- Do'konlar ro'yxati (shopId): `GET /v1/shops` — "Получение списка собственных магазинов", parametrsiz. Response schema nomi `OrganizationDto` massivi deb ko'rsatildi; maydonlari (id, name, ...) tekshirilmadi.
- Bitta token → bir nechta shop bo'lishi mumkin (endpointlar `shopId`/`shopIds` qabul qiladi).

## 3. Kategoriyalar va atributlar

- Spec'da `category`, `characteristic`, `attribute` so'zli path **yo'q**. Kategoriya daraxti va majburiy xarakteristikalar API orqali olinmaydi.

## 4. Kartochka yaratish oqimi

- **Public API'da mahsulot (kartochka) yaratish/tahrirlash endpointi yo'q.** Mahsulotga tegishli POST faqat narx: `POST /v1/product/{shopId}/sendPriceData`.
- Qo'llanma (5-bo'lim): kartochka kabinet UI orqali yaratiladi ("Товары" → "Создать товар"); nom va foto moderatsiyadan o'tadi; vaqtinchalik IKPU kodi 7 kunlik. Moderatsiya muddati — hujjatda topilmadi.
- API orqali mumkin bo'lgani — faqat o'qish:
  - `GET /v1/product/shop/{shopId}` — "Получение SKU по ID магазина" (tovarlar va qoldiqlar ro'yxati).
    Query: `size` (req), `page` (req, ≥0), `searchQuery`, `sortBy` (DEFAULT, ORDERS, PRICE, ID, ROI, CONVERSION, LEFTOVERS, CREATED_AND_TITLE), `order` (ASC|DESC), `productRank` (A, B, C, N, D), `filter` (ALL, ACTIVE, INACTIVE, WARNING, WITH_SKU, ARCHIVE, DEFECTED, WITHOUT_REQUIRED_FILTERS). Response: `AllProducts` (maydonlari tekshirilmadi).
  - `filter` qiymatlaridan (ACTIVE/INACTIVE/WARNING/ARCHIVE/DEFECTED) kartochka holatini bilvosita kuzatish mumkin.

## 5. Narx yangilash

- `POST /v1/product/{shopId}/sendPriceData` — "Изменение цен SKU". Path: `shopId`.
- Body schema: `SendPriceData` — maydonlari tekshirilmadi (components ko'rinmadi).
- Response kodlari: faqat `200` e'lon qilingan. Batch hajmi / limitlar — hujjatda topilmadi.

## 6. Qoldiq yangilash

- `POST /v2/fbs/sku/stocks` — "Обновление остатков по SKU"; tavsif: FBS **va DBS** qoldiqlarini yangilaydi. Body schema: `SkuStockUpdateApiRequestDto` (maydonlari tekshirilmadi). Response kodlari: 200, 400, 403, 500.
- O'qish: `GET /v3/fbs/sku/stocks` — sahifalangan; query `page` (default 0), `size` (default 50, 1..100), `skuIdFrom` (kursor: skuId dan katta). `GET /v2/fbs/sku/stocks` — eskirgan (устарело).
- **FBO** qoldig'ini API orqali yangilash yo'q (FBO — Uzum ombori; faqat yetkazib berish nakladnoylarini o'qish):
  - `GET /v1/shop/{shopId}/invoice` (`page`, `size`), `GET /v1/shop/{shopId}/invoice/products`, `GET /v1/invoice`
  - Qaytarishlar: `GET /v1/shop/{shopId}/return`, `GET /v1/shop/{shopId}/return/{returnId}`, `GET /v1/return`

## 7. Buyurtmalar

FBS/DBS (tag "Работа с заказами FBS/DBS"):
- `GET /v2/fbs/orders` — query: `shopIds` (req, int64[]), `status` (default CREATED), `scheme` (FBS|DBS), `dateFrom`, `dateTo` (int64), `page` (default 0), `size` (default 20, max 50).
- `GET /v2/fbs/orders/count` — `shopIds`, `status`, `dateFrom`, `dateTo`.
- `GET /v1/fbs/order/{orderId}` — bitta buyurtma.
- `POST /v1/fbs/order/{orderId}/confirm` — tasdiqlash.
- `POST /v1/fbs/order/{orderId}/cancel` — bekor qilish, body `SellerOrderCancelRq` (sabab enum'lari tekshirilmadi).
- `GET /v1/fbs/order/return-reasons` — qaytarish sabablari ro'yxati.
- `POST /v1/fbs/order/{orderId}/identifier` — tovarlarga identifikator (masalan, markirovka) bog'lash.
- `GET /v1/fbs/order/{orderId}/labels/print` — etiketka; query `size` (req, LARGE|BIG, default LARGE).
- DBS: `POST /v1/dbs/order/{orderId}/delivering` (→ DELIVERING), `POST /v1/dbs/order/{orderId}/completed` (→ COMPLETED, query `issueCode`), `POST /v1/dbs/order/{orderId}/refund`.
- FBS nakladnoy: `GET /v1/fbs/invoice`, `POST /v1/fbs/invoice` (body `InvoiceRequest`, header `Accept-Language`), `GET /v1/fbs/invoice/{invoiceId}`.

Status enum: `CREATED, PACKING, PENDING_DELIVERY, DELIVERING, DELIVERED, ACCEPTED_AT_DP, DELIVERED_TO_CUSTOMER_DELIVERY_POINT, COMPLETED, CANCELED, PENDING_CANCELLATION, RETURNED`.

FBO buyurtmalari: alohida FBO order endpointi yo'q. Moliya bo'limida barcha sotuvlar:
- `GET /v1/finance/orders` — `shopIds` (req), `page`, `size`, `group`, `dateFrom`, `dateTo`, `statuses`.
- `GET /v1/finance/expenses` — sotuvchi xarajatlari. (Biz pul bilan ishlamaymiz, faqat buyurtma ma'lumoti uchun.)

## 8. Rate limitlar va xatolar

- Response headerlar (spec'da): `x-ratelimit-remaining`, `x-ratelimit-replenish-rate`, `x-ratelimit-burst-capacity`, `x-ratelimit-requested-tokens`, `x-ratelimit-limit-per-day`, `x-ratelimit-remaining-per-day` → token-bucket + kunlik limit.
- Aniq raqamlar (rps, kunlik limit) — hujjatda topilmadi. `429` javobi spec'da e'lon qilinmagan.
- Tavsiya: headerlarni o'qib throttling qilish; 429/5xx da exponential backoff; `remaining-per-day` 0 ga yaqinlashsa navbatni to'xtatish.
- Xato body formati: javoblar `GenericResponse*` o'ramida (nomidan); maydonlari tekshirilmadi.

## 9. Integratsiya uchun xulosa

| Adapter metodi | Uzum endpoint | Izoh |
|---|---|---|
| check_credentials | `GET /v1/shops` | 200 + shop ro'yxati = token ishlaydi; shopId'larni saqlash |
| fetch_categories | yo'q | kategoriya API yo'q |
| fetch_category_attributes | yo'q | xarakteristika API yo'q |
| upsert_products | yo'q | kartochka faqat kabinet UI'da; API'da faqat `GET /v1/product/shop/{shopId}` bilan SKU'larni o'qib, bizdagi mahsulotga mapping qilish |
| get_product_status | qisman: `GET /v1/product/shop/{shopId}?filter=...` | moderatsiya statusi endpointi yo'q |
| update_prices | `POST /v1/product/{shopId}/sendPriceData` | body maydonlarini tekshirish kerak |
| update_stocks | `POST /v2/fbs/sku/stocks` | faqat FBS/DBS; FBO yo'q |
| fetch_orders | `GET /v2/fbs/orders`, `GET /v1/fbs/order/{orderId}` | FBO uchun faqat `GET /v1/finance/orders` |
| update_order_status | `POST /v1/fbs/order/{orderId}/confirm`, `.../cancel`, `POST /v1/dbs/order/{orderId}/delivering`, `.../completed`; etiketka `GET /v1/fbs/order/{orderId}/labels/print` | |

Oqim oqibati: muassasa kartochkalarni o'zi kabinetda yaratadi (yoki biz operator sifatida qo'lda), platforma esa SKU mapping + narx/qoldiq sinxron + FBS/DBS buyurtmalarni boshqaradi.

Ochiq savollar (real token bilan tekshirish): `SendPriceData`, `SkuStockUpdateApiRequestDto`, `SellerOrderCancelRq`, `AllProducts`, `SellerOrderDto` maydonlari; `Authorization` prefiksi; token ruxsatlari; aniq rate limit raqamlari.
