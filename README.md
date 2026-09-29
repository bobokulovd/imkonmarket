# ImkonMarket — muassasalar mahsulotlari savdo platformasi

Sayt (Next.js), mobil ilova (Flutter) va backend (Django REST). 6 tilda ishlaydi: o'zbek (lotin), o'zbek (kirill), o'zbek (yangi alifbo: Ó, Ǵ, Ş, Ç), rus, qoraqalpoq, ingliz.
Nom (`BRAND_NAME`) vaqtinchalik, `.env` orqali o'zgartiriladi.

## Konsepsiya

```
Xaridor (jismoniy / yuridik)            Muassasa (sotuvchi, alohida login)
   │ katalog → savat → ariza               │ mahsulot va qoldiqni yuritadi
   ▼                                       ▼
 Ariza (har bir muassasa uchun alohida) ──► ko'rib chiqish → narx/miqdorni aniqlashtirish
                                           │
                                           ▼
                             Shartnoma (PDF, QR-kod, 6 tildan birida)
                             B2C: Click / Payme (100% oldindan)
                             B2B: bank o'tkazmasi (perechisleniye), oldindan to'lov % belgilanadi
                                           │
                                   To'lov → Jo'natish → Yakunlash
```

- **Sotuvchilar** — 39 muassasa (JIEK / MK). Har biriga alohida login va parol. **IIV JIED** — operator: barcha muassasalar bo'yicha arizalar, shartnomalar va mahsulotlarni ko'radi, Django admin paneliga kiradi.
- **Mahsulotlar** Excel ro'yxatlaridan olingan: 357 ta mahsulot, 12 muassasa, 14 ta kategoriya. Ular tozalangan, lotinchaga o'girilgan va 6 tilga tarjima qilingan.
- **Ariza.** Savatda bir nechta muassasa mahsuloti bo'lsa, ariza muassasalar bo'yicha bo'linadi va har biri bilan alohida shartnoma tuziladi.
- **Vositachi rejimi** («Umumiy katalog»). Muassasa barcha muassasalar mahsulotlarini va ularning qoldig'ini (omborda / band / mavjud) ko'radi. Xaridorga boshqa muassasa mahsulotini taklif qilib, darhol shartnoma chiqaradi. Shartnoma **mahsulot egasi nomidan** tuziladi, rasmiylashtirgan muassasa esa «vositachi» sifatida yoziladi. Shartnoma ikkala muassasa kabinetida ham ko'rinadi.
- **Qoldiq.** Shartnoma tuzilganda mahsulot band qilinadi, jo'natilganda ombordan yechiladi, bekor qilinganda qaytariladi. Qoldiqdan ortiq buyurtma qabul qilinmaydi. Qoldiq bo'sh bo'lsa, mahsulot «buyurtma asosida» sotiladi.
- **To'lov.** Payme Merchant API va Click SHOP API tayyor. Kalitlar kiritilmaguncha to'lov **Demo** rejimida ishlaydi va saytda hamda ilovada «Demo» belgisi ko'rinadi. Bank o'tkazmasini muassasa kabinetda qayd etadi.
- **Shartnoma** PDF ko'rinishida chiqadi. Unda spetsifikatsiya, ikkala tomon rekvizitlari va QR-kod bor. QR-kod `/verify/<token>` sahifasiga olib boradi va shartnoma haqiqiyligini tekshirishga imkon beradi. Shartnoma matni ishchi shablon (`backend/market/contract_texts.py`), uni yuristlar ko'rib chiqishi kerak.

## Marketplace integratsiyasi (Uzum, Ozon, Yandex Market, Wildberries)

Har bir muassasa marketplace'da **o'z STIR'i bilan, o'z kabinetida** sotadi va pul to'g'ridan-to'g'ri muassasaga tushadi. ImkonMarket faqat texnik platforma: kalitni saqlaydi, kartochkani joylaydi, narx va qoldiqni sinxronlaydi, buyurtmalarni tortadi. Konspektlar va reja: `docs/integrations/`.

- **Kabinet ulash** (`/cabinet/marketplaces`). Muassasa API kalitni kiritadi. Kalit bazada **Fernet bilan shifrlangan** holda saqlanadi (`MARKETPLACE_ENC_KEYS`). Javoblarda, admin panelda va loglarda kalitning faqat oxirgi 4 belgisi ko'rinadi. Bir muassasa bitta marketplace'da bir nechta kabinet ulashi mumkin.
- **Imkoniyatlar**:

  | | Kartochka | Narx | Qoldiq | Buyurtmalar |
  |---|---|---|---|---|
  | Yandex Market | API orqali | ✓ | FBS/DBS | ✓ (holat o'zgartirish bilan) |
  | Ozon | API orqali (async) | ✓ | FBS | FBS + FBO (FBO faqat ko'rish) |
  | Wildberries | API orqali (async) | ✓ | FBS | FBS (postavka orqali) |
  | Uzum | **kabinetda yaratiladi**, bu yerda SKU bog'lanadi | ✓ | FBS/DBS | FBS/DBS |

- **Qoldiq bitta.** Marketplace'dagi FBS/DBS buyurtma bizdagi qoldiqni band qiladi. Jo'natilganda qoldiq ombordan yechiladi, bekor qilinsa qaytariladi. Har qanday o'zgarish (sayt shartnomasi yoki boshqa marketplace buyurtmasi) barcha kanallarga yuboriladi.
  - Marketplace'ga yuboriladigan qoldiq: `stock − reserved − zaxira`.
  - «Buyurtma asosida» mahsulot uchun kabinet sozlamasi ishlatiladi (standart 0).
  - FBO/FBY/FBW buyurtmalari marketplace omboridan jo'natiladi va bizdagi qoldiqqa ta'sir qilmaydi.
- **Narx.** Mahsulot narxi so'mda. Kabinet valyutasi UZS bo'lsa (standart), faqat ustama qo'shiladi. RUB bo'lsa, kurs Markaziy bankdan (cbu.uz, kuniga bir marta) yoki qo'lda kiritilgan qiymatdan olinadi.
- **Kategoriya moslash** (operator JIED). Bizning 14 kategoriya har bir marketplace kategoriyasiga bir marta moslanadi. Majburiy xususiyatlar doimiy qiymat, mahsulot maydoni yoki har bir mahsulotda alohida kiritiladi. Lug'at qiymatlari ham moslanadi.
- **Fon vazifalari.** Celery ishlatilmaydi: vazifalar bazadagi navbatda turadi, ularni `worker` servisi (`manage.py run_worker`) bajaradi.
  - HTTP so'rov tashqi API'ga murojaat qilmaydi, faqat vazifa yaratadi.
  - 429/420/5xx xatolarida vazifa eksponensial kechikish bilan qayta uriniladi (`Retry-After` hisobga olinadi).
  - Har bir chaqiruv `SyncLog` jurnaliga yoziladi (kalitsiz).
  - Davriylik: buyurtmalar har 5 daqiqada, narx va qoldiq solishtiruvi har 10 daqiqada.

API: `/api/mp/meta|accounts|listings|orders|logs|jobs|product-info|categories|mappings|attributes|overview/`.

Kalitni almashtirish tartibi: `MARKETPLACE_ENC_KEYS=<yangi>,<eski>` → `python manage.py mp_rotate_keys` → eski kalitni olib tashlang. **Kalit yo'qolsa, barcha muassasalar API kalitlarini qayta kiritishi kerak bo'ladi.**

## Mahsulot rasmlari

- **Namunaviy (AI) rasmlar.** `backend/market/seed/images/manifest.json` da 242 ta noyob mahsulot uchun prompt bor; bir xil nomli mahsulotlar bitta rasmni ulashadi. Rasmlar `data/gen_images.py` (OpenAI API) yoki `data/split_grid.py` bilan yaratiladi (bitta AI rasmda 3×3 to'r → 9 ta rasm) va `<key>.webp` nomi bilan saqlanadi. Konteyner har safar ishga tushganda `load_sample_images` rasmsiz mahsulotlarga shu rasmlarni qo'yadi. Saytda va ilovada bunday rasmda «Namunaviy rasm» belgisi chiqadi. Marketplace'larga namunaviy rasm **yuborilmaydi**.
- **Haqiqiy suratlar.** Muassasa kabinetida «Mahsulotlarim → Rasmlarni ommaviy yuklash» bo'limi bor, u yerga bir nechta fayl yoki ZIP yuklanadi. Fayl nomi mahsulot SKU'si bo'lishi kerak, masalan `MK-49-001.jpg`. Haqiqiy surat namunaviy rasmni almashtiradi va belgi yo'qoladi. Serverdan ham yuklash mumkin: `python manage.py import_images photos.zip`.

## Tuzilma

```
backend/   Django 5 + DRF + JWT, reportlab (PDF), Payme/Click
web/       Next.js 14 (App Router) + Tailwind — vitrina + /cabinet
mobile/    Flutter (xaridor + sotuvchi kabineti)
data/      Excel'dan tozalangan manba (products.txt, sellers.tsv, names_i18n.tsv) + build_catalog.py
```

## Dokploy'ga deploy

1. Dokploy → **Create Service → Compose**. Provider: GitHub, repo `bobokulovd/imkonmarket`, branch `main`, Compose path `./docker-compose.yml`.
2. **Environment** bo'limiga `.env.example` dagi qiymatlarni kiriting. Kamida `SITE_URL`, `POSTGRES_PASSWORD` va `DJANGO_SECRET_KEY` kerak. Marketplace integratsiyasi uchun `MARKETPLACE_ENC_KEYS` ham kerak. Compose'da 4 ta servis ishlaydi: `db`, `backend`, `worker`, `web`. `SEED_PASSWORDS` qatori `loginlar.xlsx` dagi parollarni beradi (u alohida yuboriladi, repoga qo'yilmaydi).
3. **Domains**: service `web`, port `3000`, masalan `imkon-market.uz`, HTTPS (Let's Encrypt). Bitta domen yetadi: `/api`, `/admin`, `/media` va shartnoma PDF'lari Next.js orqali backendga o'tadi.
4. **Deploy.** Birinchi ishga tushishda migratsiya o'tadi, 357 mahsulot va 40 ta muassasa logini yaratiladi. Keyingi deploylarda baza o'zgarmaydi.

Mobil ilova: `flutter run --dart-define=API_URL=https://imkon-market.uz`.
Payme webhook: `https://imkon-market.uz/api/payments/payme/`. Click: `.../api/payments/click/prepare/` va `.../complete/`.

## Ishga tushirish (lokal)

```bash
# Backend
cd backend
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed --passwords-from ../data/loginlar.xlsx   # katalog + 40 ta login (parollar shu fayldan)
python manage.py runserver 0.0.0.0:8000
python manage.py test market integrations                      # katalog, B2C/B2B, vositachi, PDF, Payme + marketplace (soxta HTTP bilan)

# Sayt
cd web
cp .env.example .env.local          # NEXT_PUBLIC_API_URL=http://localhost:8000
npm install && npm run dev          # http://localhost:3000 , kabinet: /cabinet

# Mobil ilova
cd mobile
bash setup.sh                       # flutter create + ruxsatlar + pub get
flutter run --dart-define=API_URL=http://10.0.2.2:8000
```

Docker bilan (lokal): `cp .env.example .env && docker compose -f docker-compose.yml -f docker-compose.local.yml up -d --build`.

`--passwords-from` berilmasa, har bir muassasa uchun yangi parol yaratiladi va `backend/credentials.xlsx` fayliga yoziladi.

## Muhim sozlamalar (.env)

| O'zgaruvchi | Vazifasi |
|---|---|
| `SITE_URL` | Sayt manzili (shartnomadagi QR-kod va to'lovdan qaytish uchun) |
| `PAYME_MERCHANT_ID`, `PAYME_KEY` | Payme kassasi. Webhook: `POST {API}/api/payments/payme/`, hisob parametri `contract_id` |
| `CLICK_SERVICE_ID`, `CLICK_MERCHANT_ID`, `CLICK_SECRET_KEY` | Click. Prepare: `/api/payments/click/prepare/`, Complete: `/api/payments/click/complete/` |

## API qisqacha

Ochiq endpointlar:
- `GET /api/meta/`, `GET /api/products/?q=&category=&region=&seller=&in_stock=1&ordering=featured|price|-price|new`
- `POST /api/applications/`
- `GET /api/orders/<token>/`, `POST /api/orders/<token>/pay/`
- `GET /api/contracts/<token>/pdf/`, `GET /api/contracts/verify/<token>/`

Kabinet endpointlari (JWT bilan):
- `POST /api/auth/login/`
- `/api/seller/dashboard/`, `/api/seller/products/`
- `/api/seller/applications/<id>/confirm|reject|review/`
- `/api/seller/contracts/<id>/payment|ship|complete|cancel|regenerate|pay-link/`
- `GET /api/seller/catalog/`, `POST /api/seller/agent-order/`

## Excel ma'lumotlari bo'yicha aniqlashtirish kerak

`loginlar.xlsx` → «Ma'lumot sifati» varag'ida batafsil yozilgan. Qisqacha:
- **29-son MK:** narx ustunida hamma joyda «5 so'm» turibdi, shuning uchun narx «kelishiladi» deb qo'yildi.
- **11-son JIEK:** narx ustuniga jami summa yozilgan, birlik narx `summa ÷ miqdor` qilib hisoblandi.
- **Qoldiq:** Excelda qoldiq yo'q. Boshlang'ich qoldiq sifatida kunlik ishlab chiqarish quvvati qo'yildi, muassasalar uni kabinetdan yangilaydi.
- **5-son JIEK:** ohak va keramzitning o'lchov birligi aniq emas.
- **14-son JIEK:** 6 500 so'mlik bordyur narxi xato bo'lishi mumkin.
- **«2-JIEK» fayli:** sarlavhada «4-son» deb yozilgan.
