# Marketplace integratsiyasi — reja (tasdiqlash uchun)

Holat: **amalga oshirildi (2026-09-28).** Quyida — tasdiqlangan reja va qabul qilingan qarorlar. Konspektlar: [uzum](uzum.md), [ozon](ozon.md), [yandex](yandex.md), [wb](wb.md).

## Tamoyil
Har bir muassasa marketplace'da o'z STIR'i bilan, o'z kabineti orqali sotadi va pul to'g'ridan-to'g'ri muassasaga tushadi.
ImkonMarket faqat texnik vositachi:
- muassasaning kalitini saqlaydi;
- kartochkani joylaydi;
- narx va qoldiqni sinxronlaydi;
- buyurtmalarni tortib oladi.

To'lov oqimiga tegmaydi.

## API imkoniyatlari (konspektlardan)
| | Uzum | Ozon | Yandex Market | Wildberries |
|---|---|---|---|---|
| Kalitni tekshirish | `GET /v1/shops` | `POST /v1/roles` (+`expires_at`) | `POST /v2/auth/token`, `GET /v2/campaigns` | `GET /ping` (har kategoriya) |
| Kategoriya/atribut | **yo'q** | tree/attribute/values | categories + parameters | subjects + charcs + directories |
| Kartochka yaratish | **yo'q** (faqat kabinetda) | async `task_id` | sinxron, statusi keyinroq | async, xato ro'yxati |
| Narx | bor | bor | bor (business) | async task |
| Qoldiq | FBS/DBS | FBS (ombor ID) | FBS/DBS (FBY — yo'q) | FBS (ombor ID, chrtId) |
| Buyurtmalar | FBS/DBS ro'yxat + confirm/cancel | FBS v4 + FBO v3 | `POST /v1/businesses/{id}/orders` | FBS + FBW (faqat o'qish) |
| O'zbekiston/UZS | ha | noaniq (RUB standart) | ha (Market Yandex Go, `.net` host, UZS) | topilmadi (RUB) |

Asosiy cheklovlar:
- **Uzum.** Kartochka API orqali yaratilmaydi. Sotuvchi uni kabinetda yaratadi, biz SKU'ni bog'laymiz ("bog'lash rejimi") va shundan keyin narx, qoldiq va buyurtmalarni yuritamiz.
- **Wildberries.** Shaxsiy token bulut xizmatlarida ishlatilmasligi kerak. Bizga "Servis tokeni" kerak, u WB biznes yechimlar katalogida ro'yxatdan o'tishni talab qiladi.
- **Ozon.** Kalit 3–6 oyda eskiradi, `expires_at` kuzatiladi va muddatidan oldin ogohlantiriladi.

## Arxitektura (mavjud stekka mos: Django + DRF, yangi framework yo'q)
Yangi Django ilova: `backend/integrations/`.

**Fon vazifalari.** Loyihada Celery/RQ yo'q, shuning uchun navbat bazada saqlanadi:
- `Job` modeli: operation, account, payload, status, attempts, run_after, locked_until.
- Worker: `python manage.py run_worker` (Postgres `SELECT … FOR UPDATE SKIP LOCKED`).
- docker-compose'ga backend image'dan `worker` servisi qo'shiladi. HTTP so'rov faqat Job yaratadi va 202 qaytaradi.
- Davriy ishlar (buyurtmalarni tortish, kartochka statusi, kalit tekshiruvi) ham shu worker ichida bajariladi, cron yo'q.
- Bitta account'ning ishlari ketma-ket bajariladi (account bo'yicha lock). Bu marketplace'larning "parallel so'rovlar" cheklovini buzmaydi.

**Retry.**
- Qachon qayta uriniladi: 429, 420 (Yandex), 5xx va timeout bo'lsa.
- Kutish: eksponensial backoff + jitter (2, 4, 8 … 300 s, 6 urinish).
- Server `Retry-After` yoki `X-Ratelimit-Retry` qaytarsa, o'sha qiymat ustun.
- 4xx xatolar qayta urinilmaydi, xato matni listing/logga yoziladi.

**Adapterlar.** `integrations/clients/`:
- `base.py`: `MarketplaceClient`, uning metodlari `check_credentials`, `fetch_categories`, `fetch_category_attributes`, `upsert_products`, `get_product_status`, `update_prices`, `update_stocks`, `fetch_orders`, `update_order_status`, hamda `capabilities` to'plami.
- `uzum.py`, `ozon.py`, `yandex.py`, `wb.py`.

Qo'llanmaydigan metod `NotSupported` tashlaydi, UI esa `capabilities`ga qarab tugmani yashiradi. HTTP uchun `requests` ishlatiladi.

**Shifrlash.**
- `cryptography.Fernet`, `MultiFernet` orqali kalitni almashtirish imkoni bilan. Kalit env'dan olinadi: `MARKETPLACE_ENC_KEYS`.
- DB'da `credentials_enc` (shifrlangan JSON) va `secret_last4` saqlanadi.
- Serializer kalitni faqat qabul qiladi (write-only). Javobda `••••1234` ko'rinadi.
- Admin'da ham faqat mask ko'rinadi, maydon tahrirlanmaydi.
- Log filtri `Authorization`, `Api-Key` va `Client-Id` sarlavhalarini va kalitga o'xshash satrlarni yashiradi.
- SyncLog'da sarlavha va so'rov tanasi saqlanmaydi.

Yangi kutubxonalar: `cryptography`, `requests`. Ular kutubxona, framework emas.

## Modellar
- **MarketplaceAccount**: seller FK, marketplace (uzum/ozon/yandex/wb), title, external_ids JSON (shopId / Client-Id / businessId+campaignId / —), credentials_enc, secret_last4, status (active/invalid/disabled), last_checked_at, key_expires_at, settings JSON (ombor ID, valyuta, narx koeffitsienti, qoldiq buferi). Bir muassasada bitta marketplace uchun bir nechta kabinet bo'lishi mumkin.
- **CategoryMapping**: bizning Category ↔ (marketplace, tashqi kategoriya/type ID, nomi).
- **AttributeMapping**: CategoryMapping ↔ tashqi atribut (majburiy/yo'q, manba: doimiy qiymat / mahsulot maydoni / lug'at).
- **AttributeValueMap**: bizning qiymat ↔ tashqi dictionary value ID.
- **MarketplaceListing**: product × account; offer_id (= bizning SKU), external_id (product_id/nmID/SKU), status (draft/pending/active/rejected/error), last_error, last_synced_at, pushed_price, pushed_stock.
- **MarketplaceOrder**: external_id, account, scheme (FBS/FBO/DBS), status, items JSON, total, currency, raw JSON, (ixtiyoriy) ichki bog'lanish.
- **SyncLog**: account, operation, http_status, ok, duration_ms, error, job. Kalitlar yozilmaydi.
- **Job**: fon navbati (yuqorida).

## Oqimlar
1. **Kabinet ulash.** Muassasa kalitni kiritadi, `check_credentials` job ishga tushadi. Natija: status `active` yoki `invalid`, do'kon/kampaniya ro'yxati va omborlar.
2. **Kategoriya moslash.** Operator (JIED) kategoriya daraxtini bir marta tortadi va bizning 14 kategoriyani moslaydi (majburiy atributlar va lug'at bilan).
3. **Joylash.** Muassasa mahsulotlarni belgilab «Joylash» tugmasini bosadi. Listing `draft` → `pending` holatiga o'tadi. Keyin `upsert_products` ishlaydi va `get_product_status` so'rovi natijaga ko'ra `active`, `rejected` yoki `error` qo'yadi (xato matni bilan). Uzum'da buning o'rniga SKU bog'lanadi.
4. **Narx va qoldiq.** Mahsulot narxi yoki qoldig'i o'zgarsa (signal orqali), debounce bilan job qo'yiladi. Marketplace'ga yuboriladigan qoldiq: `available − bufer`. Limitlar hisobga olinadi: Ozon mahsulot boshiga 30 soniyada bir marta, WB esa task tarzida.
5. **Buyurtmalar.** Buyurtmalar har 5 daqiqada tortiladi va MarketplaceOrder'ga saqlanadi. Status yangilash (confirm/ship/cancel) kabinetdan, job orqali bajariladi.

## Kabinet UI
Web'da `/cabinet/marketplaces` bo'limi bo'ladi. Tablar: Kabinetlar · Mahsulotlar (listinglar va xatolar) · Buyurtmalar · Loglar.
Operatorda qo'shimcha: kategoriya va atribut moslash hamda barcha muassasalar bo'yicha holat.
6 tilda ishlaydi. Mobil ilovada 1-bosqichda faqat buyurtmalarni ko'rish qo'shiladi.

## Bosqichlar
1. Poydevor: modellar, shifrlash, Job va worker, SyncLog, base adapter, testlar (API mock).
2. Yandex Market (UZS va O'zbekiston rasman bor) va Uzum (bog'lash rejimi).
3. Ozon.
4. Wildberries (servis tokeni masalasi hal bo'lgach).

## Qarorlar (foydalanuvchi bilan kelishildi)
- Har bir muassasa uchun alohida kabinet(lar) va alohida mahsulotlar ulanadi.
- Marketplace buyurtmasi (FBS/DBS) bizdagi qoldiqni band qiladi; jo'natilganda yechiladi; bekor bo'lsa qaytariladi. Qoldiq o'zgarishi boshqa barcha kanallarga ham yuboriladi.
- Valyuta: kabinetda UZS (standart — Ozon/WB O'zbekistonda so'mda sotadi) yoki RUB; RUB bo'lsa kurs manbai tanlanadi: Markaziy bank (cbu.uz) yoki qo'lda.
- «Buyurtma asosida» mahsulot: kabinet sozlamasi `mto_stock` (standart 0 — sotilmaydi).

## Ochiq savollar (avvalgi)
1. Xabar «Har bir account uchun …» joyida uzilgan — davomi kerak.
2. Marketplace buyurtmasi bizning qoldiqni band qilsinmi (ya'ni `reserved`, jo'natilganda yechish)? Taklif: ha, aks holda bir mahsulot ikki joyda sotilib ketadi.
3. Ozon/WB narxi RUB bo'lsa: account bo'yicha qo'lda kurs yoki koeffitsient kiritilsinmi?
4. «Buyurtma asosida» mahsulot (qoldiq yo'q): marketplace'ga qancha qoldiq ko'rsatilsin (masalan, kunlik quvvat × N) yoki joylanmasinmi?
5. WB servis tokeni: katalogda ro'yxatdan o'tishni kim qiladi?
