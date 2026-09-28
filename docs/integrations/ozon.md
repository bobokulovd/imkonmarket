# Ozon Seller API — integratsiya konspekti

> Holat sanasi: 2026-09-28. Faqat o'qilgan rasmiy manbalardagi faktlar. Tasdiqlanmagan joylar: **hujjatda topilmadi / tekshirilmadi**.

## 1. Manbalar (o'qilgan, 2026-09-28)

- `https://docs.ozon.ru/api/seller/` — WebFetch eski (taxminan 2020-yilgi) keshlangan SSR sahifani qaytardi (`/v1/product/import`, `/v2/posting/fbs/list` va h.k.). **Bu ma'lumot eskirgan, ishlatilmadi.**
- `https://docs.ozon.com/api/seller/en/`, `https://api-seller.ozon.ru`, `dev.ozon.ru/news/...` — bizning muhitdan yopiq (proxy 403 / robots). **O'qilmadi.**
- **Asosiy manba:** `https://docs.ozon.ru/api/seller/en?__rr=1` rasmiy hujjatining so'zma-so'z Markdown nusxasi — github.com/DragonSigh/ozon-seller-api-docs (commit 2025-10-02). Rasmiy matn, lekin rasmiy bo'lmagan ko'zgu, holati **2025-oktabr**.
- **Yangilanishlar (2025-10 → 2026-09):** Ozonning rasmiy Telegram kanali `https://t.me/s/OzonSellerAPI` (Seller API changelog: postlar 685, 691, 693, 700, 702 va qidiruv natijalari).
- UZ konteksti (rasmiy emas, faqat kontekst uchun): spot.uz, 2026-07-15.

## 2. Autentifikatsiya

- Host: `https://api-seller.ozon.ru`. Har bir so'rovda headerlar: `Client-Id: <id>`, `Api-Key: <key>`, `Content-Type: application/json`. Deyarli barcha metodlar `POST`, JSON body bilan.
- Kalit: kabinet → **Settings → Seller API** → *Generate key*, nom + **access level (rol)** tanlanadi. Bir nechta kalit yaratsa bo'ladi; kalitga ruxsat etilgan IP/tarmoqlar belgilanishi mumkin.
- **Kredensialni arzon tekshirish:** `POST /v1/roles` (body `{}`) → `roles[].name`, `roles[].methods[]`; 2026-02-20 dan javobda `expires_at` bor. Kalit faqat o'qish uchun ishlatiladi, hech narsani o'zgartirmaydi, va qaysi metodlarga ruxsat borligini ko'rsatadi.
- **Kalit muddati:** 2026-02-13 dan har bir kalitning muddati bor (yaratilgandan 6 oy). 2026-09-03 dan **yangi kalitlar 3 oy** amal qiladi (post 685). → Platformada `expires_at` ni saqlash va muddati tugashidan oldin sotuvchini ogohlantirish kerak.
- Auth xatolari: `Invalid Api-Key, please check the key and try again`, `Api-key is deactivated, use another one or generate a new one`, `Api-Key is missing a required role for a method`, `Api-Key is restricted to specific IP addresses`.
- Rollar nomlari (namunada): `Admin`, `Posting FBS`. To'liq ro'yxat: **hujjatda topilmadi / tekshirilmadi**.

## 3. Kategoriyalar va atributlar

| Maqsad | Endpoint | Izoh |
|---|---|---|
| Kategoriya/tip daraxti | `POST /v1/description-category/tree` | body `{"language":"DEFAULT"\|"RU"\|"EN"\|"TR"\|"ZH_HANS"}`; javobda `description_category_id`, `category_name`, `children`, `disabled`, `type_id`, `type_name`. Mahsulot faqat oxirgi daraja (type) ga yaratiladi. |
| Atributlar | `POST /v1/description-category/attribute` | `description_category_id`, `type_id` (majburiy), `language`; javobda `id`, `is_required`, `is_collection`, `dictionary_id` (0 = spravochnik yo'q), `attribute_complex_id`, `max_value_count` |
| Spravochnik qiymatlari | `POST /v1/description-category/attribute/values` | `attribute_id`, `description_category_id`, `type_id`, `limit` (1–2000), `last_value_id` (pagination), `has_next` |
| Qiymat qidirish | `POST /v1/description-category/attribute/values/search` | `value` (≥2 belgi), `limit` 1–100 |

Eskirgan (2024-03 da hujjatdan olib tashlangan): `/v2/category/tree`, `/v3/category/attribute`, `/v2/category/attribute/values`.

## 4. Kartochka yaratish oqimi

1. `POST /v3/product/import` — yaratish **va** yangilash (upsert, `offer_id` bo'yicha). Bir so'rovda ≤100 ta `items`. Javob: `result.task_id` (async).
   - Majburiy: kategoriyaning majburiy atributlari, haqiqiy o'lcham/vazn (`depth`, `width`, `height`, `dimension_unit`, `weight`, `weight_unit`; 0 bo'lmasin). 2026-07-10 dan `items.offer_id` majburiy, `items.images360` olib tashlangan.
   - Maydonlar (namunadan): `offer_id`, `name`, `description_category_id`, `type_id`, `attributes[]{complex_id,id,values[]{dictionary_value_id,value}}`, `complex_attributes`, `barcode`, `price`, `old_price`, `currency_code`, `vat`, `images`, `primary_image`, `color_image`, `pdf_list`.
   - Yangilashda mahsulot haqidagi **barcha** ma'lumot qayta yuboriladi.
   - Kunlik limit: `POST /v4/product/info/limit`; oshsa `item_limit_exceeded`.
2. `POST /v1/product/import/info` body `{"task_id": ...}` → `result.items[]{offer_id, product_id, status, errors[]}`. Hujjatda ko'rilgan `status` qiymatlari: `imported`, `skipped` (2025-03), `moderating` tilga olingan. To'liq enum: **tekshirilmadi**.
3. Moderatsiya odatda <1 kun. Keyin holat: `POST /v3/product/info/list` (≤1000 id, `offer_id`/`product_id`/`sku`) → `statuses{status, status_name, moderate_status, validation_status, status_failed, status_description, status_updated_at}`, `errors[]`, `visibility_details{has_price, has_stock}`. Enum qiymatlari: **tekshirilmadi**.
4. Ro'yxat: `POST /v3/product/list` (`filter.visibility`, 2026-07 dan `filter.skus`; `limit` ≤1000, `last_id` pagination) → `offer_id` + `product_id` (+ `sku`).
- **Identifikatorlar:** `offer_id` — sotuvchi tizimidagi artikul (bizning ID; ≤50 belgi — faqat Help sahifasida, eskirgan bo'lishi mumkin); `product_id` — Ozon mahsulot ID; `sku` — Ozon vitrina SKU (sayt: `ozon.ru/context/detail/id/{SKU}`). O'zgartirish: `POST /v1/product/update/offer-id`.
- **Rasmlar:** ommaviy bulutdagi to'g'ridan-to'g'ri URL, JPG/PNG, ≤15 ta (`primary_image` bilan `images` ≤14). Alohida yangilash: `POST /v1/product/pictures/import`, holat: `POST /v2/product/pictures/info`.
- Faqat atributlar: `POST /v1/product/attributes/update`. Arxiv: `POST /v1/product/archive` / `POST /v1/product/unarchive`; SKU'siz xato kartani o'chirish: `POST /v2/products/delete`.

## 5. Narx yangilash

- `POST /v1/product/import/prices`, body `prices[]` (≤1000): `offer_id` yoki `product_id` (ikkalasi bo'lsa `offer_id` ustun), `price`, `old_price` (`0` = reset), `min_price`, `currency_code`, `vat`, `net_price`, … Javob: `result[]{offer_id, product_id, updated, errors[]}`.
- Limit: bitta mahsulot narxi soatiga ≤10 marta.
- 2026-09-11: `prices.auto_action_enabled` va `prices.manage_elastic_boosting_through_price` eskirgan (yubormang).
- **Valyuta:** `currency_code` kabinet sozlamasidagi valyutaga teng bo'lishi shart, default `RUB`; masalan yuan bo'lsa `CNY`, aks holda xato. `currency_code` ning ruxsat etilgan qiymatlari ro'yxati va **`UZS`** qo'llab-quvvatlanishi: **hujjatda topilmadi / tekshirilmadi**. (Rasmiy bo'lmagan xabar, spot.uz 2026-07-15: Ozon O'zbekiston sotuvchilariga FBS modelida narxni so'mda qo'yish va hisob-kitobni so'mda qilishni joriy qilgan — API'da `UZS` ni real kabinetda sinab ko'rish kerak.) 2026-01-26 dan posting javoblarida `financial_data.products.customer_currency_code` bor.
- O'qish: `POST /v5/product/info/prices` (`/v4` o'chirilgan).

## 6. Qoldiq yangilash (FBS/rFBS)

- `POST /v2/products/stocks`, body `stocks[]{offer_id|product_id, stock, warehouse_id}`; ≤100 juft (mahsulot–ombor) har so'rovda, akkaunt bo'yicha ≤80 so'rov/daqiqa; bir mahsulot qoldig'i 30 soniyada ≤1 marta (`TOO_MANY_REQUESTS` / `Stock is updated too frequently`). Qoldiqni faqat mahsulot `price_sent` holatiga o'tgandan keyin qo'yish mumkin (`product_is_not_created`, `PRICE_IS_NOT_SENT`). `stock` < 1 000 000. `/v1/product/import/stocks` o'chirilgan (2025-05-27).
- Omborlar: **`POST /v2/warehouse/list`** (pagination `limit` + `cursor`, `has_next`). `/v1/warehouse/list` 2026-04-07 da o'chirilgan. v1 hujjatiga ko'ra metodni daqiqada 1 marta chaqirish mumkin; v2 limiti: **tekshirilmadi**. v2 body/javobning to'liq sxemasi: **tekshirilmadi** (faqat changelogdagi maydonlar: `cursor`, `has_next`, `warehouse_type`, `pause_at`, …).
- O'qish: `POST /v4/product/info/stocks`; ombor kesimida `POST /v2/product/info/stocks-by-warehouse/fbs` (beta, v1 eskirgan).
- FBO omborlari ro'yxati: `POST /v1/cluster/list` (FBO qoldig'ini API orqali "qo'yib" bo'lmaydi — u ta'minot/supply orqali).

## 7. Buyurtmalar (postings)

- **FBS ro'yxati:** `POST /v4/posting/fbs/list` va `POST /v4/posting/fbs/unfulfilled/list`. `/v3/posting/fbs/list` va `/v3/posting/fbs/unfulfilled/list` 2026-08-31 da o'chirilgan (post 2026-07-10). v4 so'rov/javob sxemasi va pagination: **tekshirilmadi** (v3 da: `filter` majburiy, davr ≤1 yil, `limit`/`offset`, `has_next`; `/list` da limit ≤50).
- **FBO ro'yxati:** `POST /v3/posting/fbo/list`; `/v2/posting/fbo/list` 2026-08-31 da o'chirilgan. v3 sxemasi: **tekshirilmadi**.
- Bitta posting: `POST /v3/posting/fbs/get`, `POST /v2/posting/fbo/get`.
- FBS statuslari (unfulfilled): `awaiting_registration`, `acceptance_in_progress`, `awaiting_approve`, `awaiting_packaging`, `awaiting_deliver`, `arbitration`, `client_arbitration`, `delivering`, `driver_pickup`, `cancelled`, `not_accepted`. FBO: `awaiting_packaging`, `awaiting_deliver`, `delivering`, `delivered`, `cancelled`.
- **Yig'ish (ship):** `POST /v4/posting/fbs/ship` body `{posting_number, packages[]{products[]{product_id, quantity}}}` → `awaiting_deliver`. Qisman: `POST /v4/posting/fbs/ship/package`. Markirovka talab qilinadigan tovarlar uchun avval `.../product/exemplar/*` (`/v6/.../set`, `/v5/.../validate`).
- **Bekor qilish:** `POST /v2/posting/fbs/cancel` (`posting_number`, `cancel_reason_id` majburiy; `402` bo'lsa `cancel_reason_message`). Sabablar: `POST /v2/posting/fbs/cancel-reason/list`. Bitta tovarni bekor qilish: `POST /v2/posting/fbs/product/cancel`.
- Yorliq: `POST /v2/posting/fbs/package-label` (faqat `awaiting_deliver`). 2026-10-05 dan yangi scanit yorliq formatiga o'tish (post 701) — **tafsilot tekshirilmadi**.
- rFBS (o'z yetkazib berish) statuslari: `POST /v2/fbs/posting/delivering`, `POST /v2/fbs/posting/last-mile`, `POST /v2/fbs/posting/delivered`, `POST /v2/fbs/posting/tracking-number/set`. (`sent-by-seller` 2026-01-20 da eskirgan.) `/v2/posting/fbs/act/create` o'chirilgan (post 691).

## 8. Rate limitlar va xatolar

- Umumiy: **Client-Id bo'yicha ≤50 so'rov/soniya** (`You have reached request rate limit per second`); ustiga metodga xos limitlar. Ko'p so'rovda metod vaqtincha bloklanadi: `Circle is open` (bir necha daqiqadan keyin tiklanadi).
- Metod limitlari: stocks 80/daq va 30 s/mahsulot; prices 10/soat/mahsulot; warehouse/list (v1) 1/daq; import — kunlik kvota (`/v4/product/info/limit`).
- 2026-09-25 dan javoblarda rate-limit headerlari bor (post 702). Header nomlari: **tekshirilmadi** (dev.ozon.ru/news/802 yopiq).
- HTTP kodlar: 400, 403, 404, 409, 500; xato javob sxemasi `default Error` (maydonlari tekshirilmadi). `/v1/product/import/info` da `result: items: 0` → kategoriya va VAT ni tekshiring.
- 2026: bir nechta metodlarda javobdagi `total` → `total_items` ga almashmoqda (post 700).

## 9. Integratsiya uchun xulosa (adapter mapping)

| Adapter metodi | Ozon endpoint |
|---|---|
| `check_credentials` | `POST /v1/roles` (rollar + `expires_at`) |
| `fetch_categories` | `POST /v1/description-category/tree` |
| `fetch_category_attributes` | `POST /v1/description-category/attribute` + qiymatlar `POST /v1/description-category/attribute/values` (`/values/search`) |
| `upsert_products` | `POST /v3/product/import` (async → `task_id`) |
| `get_product_status` | `POST /v1/product/import/info` (task bo'yicha) + `POST /v3/product/info/list` (moderatsiya `statuses`) |
| `update_prices` | `POST /v1/product/import/prices` |
| `update_stocks` | `POST /v2/products/stocks` (+ `POST /v2/warehouse/list` dan `warehouse_id`) |
| `fetch_orders` | FBS: `POST /v4/posting/fbs/list` / `POST /v4/posting/fbs/unfulfilled/list`; FBO: `POST /v3/posting/fbo/list` |
| `update_order_status` | FBS: `POST /v4/posting/fbs/ship`, `POST /v2/posting/fbs/cancel`; rFBS: `POST /v2/fbs/posting/{delivering,last-mile,delivered}`; FBO: **yo'q** (Ozon boshqaradi) |

Amaliy eslatmalar:
- Har sotuvchi uchun `Client-Id` + `Api-Key` alohida shifrlangan saqlansin; `expires_at` monitoringi (3 oylik kalitlar).
- `offer_id` = bizning mahsulot ID (barqaror); `product_id`/`sku` import/info va product/list dan olinib saqlansin.
- Rasm URL'lari ommaviy, to'g'ridan-to'g'ri (CDN) bo'lishi kerak.
- Pul oqimi Ozon ↔ sotuvchi o'rtasida; bizga moliya metodlari kerak emas.
- Davlat muassasasi (UZ) sotuvchi sifatida ro'yxatdan o'ta olishi va valyuta (`UZS`/`RUB`) — **hujjatda topilmadi / tekshirilmadi**; birinchi real kabinetda `currency_code` ni sinash kerak.
