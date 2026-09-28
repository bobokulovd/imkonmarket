# Wildberries (WB) Seller API — konspekt

> Holat: 2026-09-28. Faqat rasmiy dev.wildberries.ru sahifalarida o'qilgan faktlar. Tekshirilmagan narsa — "hujjatda topilmadi / tekshirilmadi".
> Eslatma: sayt ko'p so'rovda HTTP 498 qaytaradi (bot himoyasi); 2026-yil digest/release-notes sahifalarini o'qib bo'lmadi.

## 1. Manbalar (2026-09-28 da o'qilgan)
- https://dev.wildberries.ru/openapi/api-information (RU) va https://dev.wildberries.ru/en/openapi/api-information
- https://dev.wildberries.ru/en/openapi/work-with-products (Content, Prices, Warehouses, Stocks)
- https://dev.wildberries.ru/en/openapi/orders-fbs
- https://dev.wildberries.ru/en/openapi/orders-fbw
- https://dev.wildberries.ru/en/openapi/reports (Statistics)
- O'qib bo'lmadi (498): /news/302, /news/311, /news/317, /news/324 (2026 digestlar), /en/forum/topics/1713 ("RN: Изменения в методах остатков на складах продавцов"), knowledge-base release notes.

## 2. Autentifikatsiya
- Token — JWT (RFC 7519), `Authorization` headeriga qo'yiladi. `Bearer` prefiksi kerakmi — hujjatda aniq yozilmagan (tekshirilmadi; amalda xom token yuboriladi deb faraz qilinadi, testda tekshirish kerak).
- Amal muddati: **180 kun** yaratilgandan keyin. JWT'ni dekod qilib muddat va kategoriyalarni ko'rish mumkin (`s` bitmask; 30-bit = Read Only).
- Kirish darajasi: "Read and Write" yoki "Read Only".
- Token turlari:
  - **Personal** (acc=3): faqat sotuvchining o'z dasturlari (on-premise ham). Hujjat: *"must not be shared with third parties or used in cloud services"*.
  - **Service** (acc=asid:{ServiceID}): WB rasmiy "Catalog of business solutions" dagi aniq bulutli servis uchun; kategoriyalar avtomatik to'ldiriladi.
  - **Base** (acc=1): cheklangan ma'lumotlar to'plami, boshqa tur mos kelmaganda.
  - **Test** (acc=2, t=true): faqat sandbox.
  - **MUHIM:** bizning platforma (bulutli servis, uchinchi tomon) uchun Personal token hujjatga zid. To'g'ri yo'l — WB katalogida servis sifatida ro'yxatdan o'tib Service token olish yoki Base token (qamrovi tekshirilmadi).
- Kategoriyalar (scopes) va hostlar:
  | Kategoriya | Host |
  |---|---|
  | Content | https://content-api.wildberries.ru (+ `-sandbox`) |
  | Prices & Discounts | https://discounts-prices-api.wildberries.ru (+ sandbox) |
  | Marketplace (FBS, warehouses, stocks) | https://marketplace-api.wildberries.ru |
  | Statistics | https://statistics-api.wildberries.ru (+ sandbox) |
  | Analytics | https://seller-analytics-api.wildberries.ru |
  | Supplies (FBW) | https://supplies-api.wildberries.ru |
  | Tariffs/News/Seller info | https://common-api.wildberries.ru |
  | Boshqa | advert-api, feedbacks-api, buyer-chat-api, returns-api, documents-api, finance-api, user-management-api |
- Tekshirish (ping): `GET https://<host>/ping`, masalan `GET https://content-api.wildberries.ru/ping`, `GET https://marketplace-api.wildberries.ru/ping`, `GET https://discounts-prices-api.wildberries.ru/ping`, `GET https://statistics-api.wildberries.ru/ping`. Limit: 1 so'rov/min, burst 10. 401 = token yo'q/muddati o'tgan/kategoriya mos emas.
- O'zbekiston sotuvchilari, UZS valyutasi, rezidentlik — hujjatda topilmadi.

## 3. Kategoriyalar va atributlar (Content, host content-api)
- `GET https://content-api.wildberries.ru/content/v2/object/parent/all` — ota kategoriyalar.
- `GET https://content-api.wildberries.ru/content/v2/object/all` — predmetlar (subjects); query: `name`, `limit` (≤1000), `offset`, `parentID`, `locale` (ru/en/zh).
- `GET https://content-api.wildberries.ru/content/v2/object/charcs/{subjectId}` — xarakteristikalar: `charcID`, `name`, `required`, `unitName`, `maxCount`, `charcType`.
- Spravochniklar (GET, `https://content-api.wildberries.ru/content/v2/directory/...`): `colors`, `kinds`, `countries`, `seasons`, `vat`, `tnved`.
- Brendlar: `GET https://content-api.wildberries.ru/api/content/v1/brands` (1 so'rov/s).
- Limit: 100/min, interval 600 ms, burst 5.

## 4. Kartochka yaratish oqimi
- `POST https://content-api.wildberries.ru/content/v2/cards/upload` — body: `[{subjectID, variants:[{vendorCode, title, description, brand, dimensions, characteristics:[{id,value}], sizes:[{techSize, wbSize, price, skus[]}]}]}]`. Max 100 imtID × 30 nmID, so'rov ≤10 MB. O'lcham sm, og'irlik kg.
- `POST https://content-api.wildberries.ru/content/v2/cards/upload/add` — mavjud imtID'ga yangi nmID qo'shish.
- **Asinxron**: *"Creating a card is asynchronous, after sending the request is put in a queue for processing."*
- Xatolar: `POST https://content-api.wildberries.ru/content/v2/cards/error/list` — body `cursor{limit, updatedAt, batchUUID}`, `order{ascending}`; javob: `batchUUID`, `subjects`, `brands`, `vendorCodes`, `errors`, `cursor.next`. (v3 versiyasi hujjatda topilmadi.)
- Muvaffaqiyatli kartochkalar: `POST https://content-api.wildberries.ru/content/v2/get/cards/list` (vendorCode bo'yicha topib nmID/chrtID olish).
- Tahrirlash: `POST https://content-api.wildberries.ru/content/v2/cards/update`. Limitlar: `GET https://content-api.wildberries.ru/content/v2/cards/limits`. Shtrixkod generatsiya: `POST https://content-api.wildberries.ru/content/v2/barcodes`.
- Savat: `POST .../content/v2/cards/delete/trash`, `POST .../content/v2/cards/recover`, `POST .../content/v2/get/cards/trash`.
- Identifikatorlar: `vendorCode` — sotuvchi artikuli (bizning SKU); `nmID` — WB artikuli (kartochka); `imtID` — birlashtirilgan kartochka; `chrtID` — o'lcham (size) ID; `skus` — o'lcham shtrixkodlari.
- Media: `POST https://content-api.wildberries.ru/content/v3/media/save` (body `nmId`, `data`[URL]); `POST https://content-api.wildberries.ru/content/v3/media/file` (multipart, headerlar `X-Nm-Id`, `X-Photo-Number`). Rasm: ≤30 ta, ≥700×900 px, ≤32 MB, JPG/PNG/BMP/GIF/WebP; video: 1 ta, ≤50 MB, MOV/MP4. Media nmID talab qiladi → avval kartochka yaratilib nmID olinishi kerak.
- Limit: upload/upload-add/update/error-list — 10/min, interval 6 s; qolganlari 100/min.

## 5. Narx yangilash (host discounts-prices-api)
- `POST https://discounts-prices-api.wildberries.ru/api/v2/upload/task` — body `data:[{nmID, price, discount}]`, ≤1000 tovar; javob `id`/`uploadID`, `alreadyExists`. Narx va chegirma ikkalasi bo'sh bo'lmasligi kerak. Narx nmID darajasida.
- O'lcham bo'yicha narx: `POST .../api/v2/upload/task/size`; klub chegirmasi: `POST .../api/v2/upload/task/club-discount`.
- Holat: `GET https://discounts-prices-api.wildberries.ru/api/v2/history/tasks?uploadID=` (qayta ishlangan), `GET .../api/v2/buffer/tasks?uploadID=` (navbatda); tovar kesimida xatolar: `GET .../api/v2/history/goods/task` va `GET .../api/v2/buffer/goods/task` (`errorText`).
- Statuslar: 1 qayta ishlanmoqda, 3 xatosiz, 4 bekor, 5 qisman xato, 6 hammasi xato.
- Karantin: yangi chegirmali narx eskisidan ≥3 marta past bo'lsa → `GET .../api/v2/quarantine/goods`.
- Joriy narxlar: `GET|POST .../api/v2/list/goods/filter`, `GET .../api/v2/list/goods/size/nm`.
- Valyuta: javobda `currencyIsoCode4217` (misol "RUB"); boshqa valyuta (UZS) — hujjatda topilmadi.
- Limit: 10 so'rov / 6 s, interval 600 ms.

## 6. Qoldiq yangilash (host marketplace-api)
- Sotuvchi omborlari: `GET https://marketplace-api.wildberries.ru/api/v3/warehouses` (`id`, `officeId`, `cargoType`, `deliveryType`, `name`, `isDeleting`, `isProcessing`); yaratish `POST .../api/v3/warehouses`, WB ofislari `GET .../api/v3/offices`.
- Yangilash: `PATCH https://marketplace-api.wildberries.ru/api/v3/stocks/{warehouseId}` — body `{"stocks":[{"chrtId":..., "amount":N}]}` (eski `sku` ham ko'rsatilgan), ≤1000 element; hujjat `chrtId` ni afzal ko'radi.
- O'qish: `POST .../api/v3/stocks/{warehouseId}` body `{"chrtIds":[...]}`; o'chirish: `DELETE .../api/v3/stocks/{warehouseId}` (50/min). `skus` parametri: *"deprecated... will be disabled on February 9th"* (yil ko'rsatilmagan; hozir o'chirilgan deb hisoblash kerak — tekshirilmadi).
- Limit: 300/min, interval 200 ms (DELETE — 50/min).
- FBS vs FBW: API orqali faqat sotuvchi omborlari (FBS) qoldig'i yangilanadi. FBW (WB omborlari) qoldig'i sotuvchi tomonidan yangilanmaydi, faqat o'qiladi: `GET https://statistics-api.wildberries.ru/api/v1/supplier/stocks?dateFrom=` (1/min, 30 daqiqada yangilanadi).

## 7. Buyurtmalar
FBS (host marketplace-api):
- Yangi: `GET https://marketplace-api.wildberries.ru/api/v3/orders/new`
- Ro'yxat: `GET https://marketplace-api.wildberries.ru/api/v3/orders?limit=1..1000&next=0&dateFrom=&dateTo=` (unix ts; default 30 kun)
- Statuslar: `POST https://marketplace-api.wildberries.ru/api/v3/orders/status`
  - `supplierStatus`: new, confirm (postavkaga qo'shilganda), complete (postavka yetkazishga berilganda), cancel.
  - `wbStatus`: waiting, sorted, sold, canceled, canceled_by_client, declined_by_client, defect, ready_for_pickup, postponed_delivery, accepted_by_carrier, sent_to_carrier.
- Bekor qilish: `PATCH https://marketplace-api.wildberries.ru/api/v3/orders/{orderId}/cancel` (100/min).
- Postavka (supply): `POST .../api/v3/supplies` (yaratish), `POST .../api/marketplace/v3/supplies/{supplyId}/orders` (≤100 buyurtma qo'shish → confirm), `PATCH .../api/v3/supplies/{supplyId}/deliver` (→ complete), `GET .../api/v3/supplies`, `GET .../api/marketplace/v3/supplies/{supplyId}/order-ids`. `GET .../api/v3/supplies/{supplyId}/orders` — deprecated (sana ko'rsatilmagan).
- Stikerlar: `POST .../api/v3/orders/stickers` (faqat confirm/complete, ≤100). Meta (sgtin/uin/imei/gtin/expiration): `PATCH .../api/v3/orders/{orderId}/meta/...`.
- Narx maydonlari: `price`, `finalPrice`, `convertedPrice`, `convertedFinalPrice`, `currencyCode` (misol 933), `convertedCurrencyCode` (misol 643). Bizga faqat ma'lumot uchun — pul bizdan o'tmaydi.
- Limit: 300/min, interval 200 ms, burst 20.
FBW (WB omboridan sotuvlar) — Statistics:
- `GET https://statistics-api.wildberries.ru/api/v1/supplier/orders?dateFrom=&flag=` va `GET .../api/v1/supplier/sales?dateFrom=&flag=` — 1/min, 30 daqiqada yangilanadi, ~90 kun saqlanadi. Statusni o'zgartirib bo'lmaydi.
- `GET .../api/v1/supplier/incomes` — deprecated, "will be removed on March 11".
- FBW postavkalar (orders-fbw bo'limi): acceptance coefficients supplies-api da "disabled on February 3" → common-api "Tariffs" bo'limiga ko'chgan.

## 8. Rate limitlar va xatolar
- Algoritm: token bucket; limit — asosan har bir sotuvchi akkaunti/metod bo'yicha (aniq qamrov: hujjatda "per method", tekshirilmadi).
- Headerlar: `X-Ratelimit-Remaining` (429 dan boshqa javoblarda), 429 da `X-Ratelimit-Retry` (necha soniyadan keyin qayta), `X-Ratelimit-Limit` (burst), `X-Ratelimit-Reset` (burst tiklanish soniyasi).
- 409 javob limitga 5 so'rov sifatida (ba'zi Marketplace metodlarida 10) hisoblanadi.
- 401 token/kategoriya xato yoki muddati o'tgan; 403 token o'chirilgan foydalanuvchiniki yoki metod bloklangan; 429 limit oshdi. 404/429 javobida `detail` maydoni.
- Umumlashtirilgan limitlar: Content 100/min (upload/update/error-list 10/min), Prices 10/6 s, Marketplace 300/min, Statistics 1/min, ping 1/min.

## 9. Integratsiya uchun xulosa
| Bizning metod | WB endpoint |
|---|---|
| check_credentials | `GET https://content-api.wildberries.ru/ping` (+ kerakli kategoriyalar: discounts-prices-api, marketplace-api, statistics-api `/ping`); qo'shimcha: JWT'dan `exp` va scope bitlarini o'qish |
| fetch_categories | `GET https://content-api.wildberries.ru/content/v2/object/parent/all` + `GET .../content/v2/object/all` |
| fetch_category_attributes | `GET https://content-api.wildberries.ru/content/v2/object/charcs/{subjectId}` (+ `/content/v2/directory/*`) |
| upsert_products | yaratish `POST .../content/v2/cards/upload`; yangilash `POST .../content/v2/cards/update`; media `POST .../content/v3/media/save` |
| get_product_status | `POST .../content/v2/cards/error/list` (xatolar) + `POST .../content/v2/get/cards/list` (yaratilganlar, nmID/chrtID) — alohida "status" endpoint yo'q |
| update_prices | `POST https://discounts-prices-api.wildberries.ru/api/v2/upload/task` → `GET .../api/v2/history/tasks?uploadID=` / `GET .../api/v2/history/goods/task` |
| update_stocks | `PATCH https://marketplace-api.wildberries.ru/api/v3/stocks/{warehouseId}` (chrtId, amount); omborlar `GET .../api/v3/warehouses`. FBW uchun — yo'q |
| fetch_orders | FBS: `GET https://marketplace-api.wildberries.ru/api/v3/orders/new`, `GET .../api/v3/orders`, `POST .../api/v3/orders/status`; FBW: `GET https://statistics-api.wildberries.ru/api/v1/supplier/orders` |
| update_order_status | To'g'ridan-to'g'ri status o'rnatish yo'q. confirm = supplyga qo'shish (`POST .../api/marketplace/v3/supplies/{supplyId}/orders`), complete = `PATCH .../api/v3/supplies/{supplyId}/deliver`, cancel = `PATCH .../api/v3/orders/{orderId}/cancel`. FBW — yo'q |
