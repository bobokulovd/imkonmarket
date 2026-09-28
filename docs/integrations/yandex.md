# Yandex Market Partner API — integratsiya konspekti

Holat: 2026-09-28. Faqat rasmiy manbalarda o'qilgan faktlar. Tasdiqlanmagan joylar: "hujjatda topilmadi / tekshirilmadi".

## 1. Manbalar (2026-09-28 da o'qildi)

- Rasmiy OpenAPI spetsifikatsiya: https://github.com/yandex-market/yandex-market-partner-api (commit `7e6862d`, 2026-09-28) — `openapi/openapi.yaml`, `openapi/paths/*.yaml`, `openapi/components/schemas/*.yaml`. Endpointlar, scope'lar, limitlar (`x-resource-limit-config`), deprecation sanalari (`x-deprecation-config`) shu yerdan.
- https://yandex.ru/dev/market/partner-api/doc/ru/ (bosh sahifa, bo'limlar ro'yxati)
- https://yandex.ru/dev/market/partner-api/doc/ru/concepts/authorization
- https://yandex.ru/dev/market/partner-api/doc/ru/concepts/limits
- https://yandex.ru/dev/market/partner-api/doc/ru/concepts/error-codes
- https://yandex.ru/dev/market/partner-api/doc/ru/concepts/dbs-order-status-model
- https://yandex.ru/dev/market/partner-api/doc/ru/market-yandex-go-sellers (O'zbekiston — Market Yandex Go)
- Inglizcha versiya (https://yandex.com/dev/market/partner-api/doc/en/) — alohida o'qilmadi; mazmuni ruscha bilan bir xil deb faraz qilinmadi.

Base URL: `https://api.partner.market.yandex.ru` (openapi.yaml `servers`).
**Market Yandex Go (O'zbekiston) sotuvchilari uchun:** "В запросах вместо `.ru` используйте `.net`" → `https://api.partner.market.yandex.net/...`.

## 2. Autentifikatsiya

- **Api-Key** (tavsiya etiladi): header `Api-Key: <token>`. Token kabinetga (business) bog'langan, muddatsiz, metod guruhlari bo'yicha ruxsat sozlanadi.
- **OAuth** (`Authorization` header, scope `market:partner-api`) — hujjatda "устарел", foydalanuvchiga bog'langan, 1 yil amal qiladi. Ishlatmaymiz.
- Api-Key scope'lari (`ApiKeyScopeType`): `ALL_METHODS`, `ALL_METHODS_READ_ONLY`, `INVENTORY_AND_ORDER_PROCESSING`(+`_READ_ONLY`), `PRICING`(+`_READ_ONLY`), `OFFERS_AND_CARDS_MANAGEMENT`(+`_READ_ONLY`), `PROMOTION`(+`_READ_ONLY`), `FINANCE_AND_ACCOUNTING`, `COMMUNICATION`, `SETTINGS_MANAGEMENT`, `SUPPLIES_MANAGEMENT_READ_ONLY`.
- Bizga minimal kerak: `OFFERS_AND_CARDS_MANAGEMENT` (kartochka + **qoldiq** — stocks metodlari shu scope'da!), `PRICING`, `INVENTORY_AND_ORDER_PROCESSING` (buyurtmalar). Yoki `ALL_METHODS`.
- `businessId` = kabinet (katalog, kartochka, umumiy narx, v3 qoldiq, buyurtmalar ro'yxati). `campaignId` = magazin (bitta model: `placementType` = `FBS`/`FBY`/`DBS`/`LAAS`); buyurtma statusi, magazin narxi, guruhli skladlar qoldig'i.
- Credential tekshirish:
  - `POST /v2/auth/token` — faqat Api-Key uchun; `result.apiKey.name` va `authScopes[]` qaytaradi (limit 100/soat).
  - `GET /v2/campaigns` — Api-Key bo'yicha kabinetdagi magazinlar: `id`, `domain`, `business{id,name}`, `placementType`, `apiAvailability` (`AVAILABLE`, `DISABLED_BY_INACTIVITY` (>90 kun), `DISABLED_BY_NO_ACTIVE_CONTRACT`, `MANUALLY_DISABLED`, `DISABLED_BY_NO_PLACEMENT_TYPE`). `pageSize` ≤ 100. Limit 1000/soat. `clientId` maydoni 2026-10-05 da o'chiriladi.
  - `GET /v2/campaigns/{campaignId}`, `POST /v2/businesses/{businessId}/settings` (ichida `onlyDefaultPrice`).

## 3. Kategoriyalar va atributlar

- `POST /v2/categories/tree` — butun daraxt (`id`, `name`, `children`), body ixtiyoriy `{"language":"RU"|"EN"}`. Limit 50/soat (Medium: 100/soat) → keshlash shart.
- `POST /v2/category/{categoryId}/parameters?businessId=` — faqat **listovoy** kategoriya uchun xarakteristikalar: `id,name,type,unit,required,multivalue,allowCustomValues,values,constraints,valueRestrictions,distinctive`. Limit 100/min.
- Deprecated: `POST /v2/categories/max-sale-quantum` (degradatsiya 2027-01-18, o'chirish 2027-04-05).

## 4. Kartochka yaratish oqimi

1. `POST /v2/businesses/{businessId}/offer-mappings/update` — tovar qo'shish/yangilash (business darajasida). Body: `{"offerMappings":[{"offer":{...},"mapping":{"marketSku":..}}], "onlyPartnerMediaContent":false}`. Schema `maxItems: 500`, lekin hujjat: "Уже сейчас не передавайте больше 100". Yangi tovar uchun majburiy: `offerId`, `name`, `marketCategoryId`, `pictures`, `vendor`, `description`. Xarakteristikalar `parameterValues[{parameterId,valueId|value,unitId}]` (har doim `marketCategoryId` bilan). Narx ham berilishi mumkin: `basicPrice{value,currencyId,discountBase}`. Query `language=RU|UZ` (`CatalogLanguageType`). `offerId` qayta ishlatib bo'lmaydi.
   - Javob sinxron validatsiya: `200` + `status`; agar biror tovarda `results[].errors` bo'lsa `status=ERROR` va **hech bir tovar qo'llanmaydi**; `warnings` bo'lsa qo'llanadi. `400` — butun paket rad. Qo'llanish asinxron: "Это занимает до нескольких минут".
2. `POST /v2/businesses/{businessId}/offer-cards/update` — faqat kategoriya xarakteristikalari (`offersContent` ≤ 100), asinxron (bir necha daqiqa).
3. Status tekshirish:
   - `POST /v2/businesses/{businessId}/offer-cards` (`offerIds` yoki filtrlar `cardStatuses`, `categoryIds`; `limit` ≤ 200, `page_token`) → `cardStatus`: `HAS_CARD_CAN_NOT_UPDATE`, `HAS_CARD_CAN_UPDATE`, `HAS_CARD_CAN_UPDATE_ERRORS`, `HAS_CARD_CAN_UPDATE_PROCESSING`, `NO_CARD_NEED_CONTENT`, `NO_CARD_MARKET_WILL_CREATE`, `NO_CARD_ERRORS`, `NO_CARD_PROCESSING`, `NO_CARD_ADD_TO_CAMPAIGN`; + `errors`, `warnings`, `contentRating`. Limit 100/min (Medium 600).
   - `POST /v2/businesses/{businessId}/offer-mappings` → `offer.cardStatus`, `offer.campaigns[].status` (`PUBLISHED`, `CHECKING`, `DISABLED_BY_PARTNER`, `REJECTED_BY_MARKET`, `DISABLED_AUTOMATICALLY`, `CREATING_CARD`, `NO_CARD`, `NO_STOCKS`, `ARCHIVED`, `READY_FOR_PUBLICATION`).
- Magazindagi sotish shartlari/NDS: `POST /v2/campaigns/{campaignId}/offers/update`; ro'yxat: `POST /v2/campaigns/{campaignId}/offers`.
- Arxiv/o'chirish: `POST /v2/businesses/{businessId}/offer-mappings/archive|unarchive|delete`.
- Webhook (push) orqali kartochka statusi — tekshirilmadi.

## 5. Narx yangilash

- `POST /v2/businesses/{businessId}/offer-prices/updates` — barcha magazinlar uchun umumiy narx. Body: `{"offers":[{"offerId":"..","price":{"value":N,"currencyId":"UZS","discountBase":N,"minimumForBestseller":N}}]}`, `offers` ≤ 500, `offerId` unikal. Limit 10 000 tovar/min. Asinxron (bir necha daqiqa).
- `POST /v2/campaigns/{campaignId}/offer-prices/updates` — faqat `settings.onlyDefaultPrice=false` bo'lsa. Body `offers[{offerId, price{value,currencyId,discountBase,vat}}]` ≤ 2000. Limit 10 000 tovar/min, parallel ≤ 12.
- O'qish: `POST /v2/businesses/{businessId}/offer-prices`, `POST /v2/campaigns/{campaignId}/offer-prices`. Deprecated: `GET /v2/campaigns/{campaignId}/offer-prices` (o'chirish 2027-04-05).
- Valyuta: `CurrencyType` ichida `UZS` ("узбекский сум") va `KZT` bor. Market Yandex Go: "Указывайте цены в национальной валюте ... в `currencyId`", "Передавать НДС не нужно". `VAT_12` — "Используется только в Узбекистане" (`OrderVatType`).

## 6. Qoldiq yangilash

Tanlov kabinetda **sklad guruhlari** bor-yo'qligiga bog'liq:
- Guruhsiz (asosiy holat): `POST /v3/businesses/{businessId}/offers/stocks/update` — body `{"skuItems":[{"sku":"..","partnerWarehouseId":N,"count":N,"updatedAt":"ISO8601"}]}`, ≤ 2000, limit **50 so'rov/min**. Sklad ID: `POST /v3/businesses/{businessId}/warehouses` (har sklad uchun modellar FBS/DBS/Ekspress va API mavjudligi). O'qish: `POST /v3/businesses/{businessId}/offers/stocks`.
- Guruhli: `PUT /v2/campaigns/{campaignId}/offers/stocks` — body `{"skus":[{"sku":"..","items":[{"count":N,"updatedAt":".."}]}]}`, ≤ 2000, limit 100 000 sku/min; guruhdagi bitta skladga yuborish kifoya. Skladlar: `POST /v2/businesses/{businessId}/warehouses` (`GET` varianti deprecated, 2027-04-05).
- Modellar: stocks update faqat **FBS, DBS, Express** (tag). **FBY** — qoldiq Market skladida, API orqali yozilmaydi; faqat o'qish `POST /v2/campaigns/{campaignId}/offers/stocks` (+ `GET /v2/warehouses`).
- SKU aniq katalogdagidek ("557722" ≠ "0557722"). Qo'llanish bir necha daqiqa.

## 7. Buyurtmalar

- **Joriy:** `POST /v1/businesses/{businessId}/orders?page_token=&limit=` (limit ≤ 50) — butun kabinet bo'yicha. Filtrlar: `orderIds`, `externalOrderIds`, `programTypes`, `campaignIds`, `statuses`, `substatuses`, `dates`, `fake`, `waitingForCancellationApprove`, `sourcePlatforms`. Sana oralig'i ≤ 30 kun (default oxirgi 30 kun). Limit 10 000/soat, parallel ≤ 6.
- **Deprecated:** `GET /v2/campaigns/{campaignId}/orders` va `GET /v2/campaigns/{campaignId}/orders/{orderId}` — degradatsiya 2027-01-18, o'chirish 2027-04-12, o'rniga `getBusinessOrders`.
- Statuslar (`OrderStatusType`): `PLACING`, `RESERVED`, `UNPAID`, `PROCESSING`, `DELIVERY`, `PICKUP`, `DELIVERED`, `CANCELLED`, `PENDING`, `PARTIALLY_RETURNED`, `RETURNED`, `UNKNOWN` ("другие значения ... обрабатывать не нужно"). Substatus: `OrderSubstatusType` (ko'p qiymat: `STARTED`, `READY_TO_SHIP`, `SHOP_FAILED`, `USER_CHANGED_MIND`, ...).
- Status o'zgartirish (tag: FBS, DBS, Express, LaaS — **FBY yo'q**):
  - `PUT /v2/campaigns/{campaignId}/orders/{orderId}/status` — body `{"order":{"status":"PROCESSING","substatus":"READY_TO_SHIP"}}`.
  - `POST /v2/campaigns/{campaignId}/orders/status-update` — `orders` ≤ 30.
  - Hujjatdagi o'tishlar: `PROCESSING/STARTED → PROCESSING/READY_TO_SHIP`; `PROCESSING/(STARTED|READY_TO_SHIP) → CANCELLED/SHOP_FAILED`. DBS qo'shimcha (dbs-order-status-model sahifasi): sotuvchi `DELIVERY`, `PICKUP` ga o'tkazadi; `DELIVERED` qisman Market tomonidan.
- FBS: status o'zgartirishdan tashqari qutilar (`PUT /v2/campaigns/{campaignId}/orders/{orderId}/boxes`), yorliqlar, otgruzkalar — bu konspektda chuqur tekshirilmadi.
- Push-notifikatsiyalar mavjud (yangi buyurtma/status) — tafsilot tekshirilmadi.
- Pul: biz ishlatadigan metodlarda to'lov qabul qilish yo'q (moliya — `FINANCE_AND_ACCOUNTING` scope, bizga kerak emas).

## 8. Rate limitlar va xatolar

- Parallel: bitta `campaignId`/`businessId` uchun ≤ 4 bir vaqtdagi so'rov (limits sahifasi); ayrim metodlarda spec'da `parallel-limit-value` (orders 6, campaign prices 12).
- Resurs limitlari metod bo'yicha (yuqorida). Obuna darajasi "Medium" — kengaytirilgan limitlar (spec'da `none` vs `medium`).
- Headerlar: `X-RateLimit-Resource-Limit`, `X-RateLimit-Resource-Until`, `X-RateLimit-Resource-Remaining`.
- Oshsa: **`420 Enhance Your Calm`**. **429 hujjatda yo'q.** Boshqalar: 400, 401, 403, 404, 405, 415, 423 (metod bu magazin uchun mavjud emas), 499, 500, 503.
- So'rov tanasi ≤ 512 KB.

## 9. Integratsiya uchun xulosa

| Funksiya | Endpoint |
|---|---|
| check_credentials | `POST /v2/auth/token` (scope'lar) + `GET /v2/campaigns` (businessId, campaignId, placementType, apiAvailability) |
| fetch_categories | `POST /v2/categories/tree` |
| fetch_category_attributes | `POST /v2/category/{categoryId}/parameters?businessId={businessId}` |
| upsert_products | `POST /v2/businesses/{businessId}/offer-mappings/update` (+ `POST /v2/businesses/{businessId}/offer-cards/update` xarakteristikalar uchun) |
| get_product_status | `POST /v2/businesses/{businessId}/offer-cards` (`cardStatus`, errors) + `POST /v2/businesses/{businessId}/offer-mappings` (magazin statusi) |
| update_prices | `POST /v2/businesses/{businessId}/offer-prices/updates` (yoki `onlyDefaultPrice=false` bo'lsa `POST /v2/campaigns/{campaignId}/offer-prices/updates`) |
| update_stocks | `POST /v3/businesses/{businessId}/offers/stocks/update` (guruhli skladlar: `PUT /v2/campaigns/{campaignId}/offers/stocks`); FBY — yo'q |
| fetch_orders | `POST /v1/businesses/{businessId}/orders` |
| update_order_status | `PUT /v2/campaigns/{campaignId}/orders/{orderId}/status` / `POST /v2/campaigns/{campaignId}/orders/status-update`; FBY — yo'q |

Ochiq savollar: O'zbekiston sotuvchisida FBS/DBS/FBY qaysi biri mavjudligi — hujjatda topilmadi; `.net` domen va `.ru` kalitlari o'zaro ishlashi — tekshirilmadi; Api-Key yaratish UI qadamlari — tekshirilmadi.

## 10. Adapterda ishlatilgan sxemalar (rasmiy OpenAPI'dan tekshirildi, 2026-09-28)

- `GET /v2/campaigns` → `{campaigns: [{id, domain, business{id,name}, placementType, apiAvailability}], pager{pagesCount}}`.
- `POST /v3/businesses/{businessId}/warehouses` → `{result: {warehouses: [{id, name, models, address}]}}`.
- `POST /v3/businesses/{businessId}/offers/stocks/update` body `{skuItems: [{sku, partnerWarehouseId, count, updatedAt}]}` (≤2000).
- `POST /v2/businesses/{businessId}/offer-mappings/update` → `{results: [{offerId, errors[], warnings[]}]}`.
  `UpdateOfferDTO`: `offerId, name, marketCategoryId, pictures, vendor, barcodes, description, manufacturerCountries, weightDimensions{length,width,height,weight}, parameterValues[{parameterId, valueId|value, unitId}], basicPrice{value,currencyId}`.
- `POST /v2/businesses/{businessId}/offer-cards` → `{result: {offerCards: [{offerId, cardStatus, errors, mapping{marketSku}}]}}`.
- `POST /v1/businesses/{businessId}/orders?limit=50&pageToken=` body `{dates: {updateDateFrom (date-time)}, campaignIds?}` →
  `{orders: [{orderId, campaignId, programType, status, substatus, creationDate, fake, items: [{id, offerId, offerName, count, prices{payment, cashback}}], prices{payment}}], paging{nextPageToken}}`.
  Diqqat: `items[].prices.payment` — **barcha birliklar uchun jami** (bitta dona narxi emas).
- `PUT /v2/campaigns/{campaignId}/orders/{orderId}/status` body `{order: {status, substatus}}`.
