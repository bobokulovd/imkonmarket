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

## Tuzilma

```
backend/   Django 5 + DRF + JWT, reportlab (PDF), Payme/Click
web/       Next.js 14 (App Router) + Tailwind — vitrina + /cabinet
mobile/    Flutter (xaridor + sotuvchi kabineti)
data/      Excel'dan tozalangan manba (products.txt, sellers.tsv, names_i18n.tsv) + build_catalog.py
```

## Ishga tushirish (lokal)

```bash
# Backend
cd backend
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed --passwords-from ../data/loginlar.xlsx   # katalog + 40 ta login (parollar shu fayldan)
python manage.py runserver 0.0.0.0:8000
python manage.py test market                                   # 5 ta test: katalog, B2C/B2B, vositachi, PDF 6 tilda, Payme

# Sayt
cd web
cp .env.example .env.local          # NEXT_PUBLIC_API_URL=http://localhost:8000
npm install && npm run dev          # http://localhost:3000 , kabinet: /cabinet

# Mobil ilova
cd mobile
bash setup.sh                       # flutter create + ruxsatlar + pub get
flutter run --dart-define=API_URL=http://10.0.2.2:8000
```

Docker bilan: `cp .env.example .env && docker compose up -d --build`, so'ng
`docker compose exec backend python manage.py seed --passwords-from /data/loginlar.xlsx`.

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
