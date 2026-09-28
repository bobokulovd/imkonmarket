"""Excel'dan tozalangan products.txt + sellers.tsv + names_i18n.tsv -> catalog.json (6 til).

Ishga tushirish:  python data/build_catalog.py
"""
import csv
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "backend"))
from market.translit import to_cyrl, to_new  # noqa: E402

LANGS = ["uz", "uz_cyrl", "uz_new", "ru", "kaa", "en"]


def tri(uz, ru, kaa, en, cyrl=None):
    return {"uz": uz, "uz_cyrl": cyrl or to_cyrl(uz), "uz_new": to_new(uz), "ru": ru, "kaa": kaa, "en": en}


CATEGORIES = [
    # slug, icon, uz, ru, kaa, en
    ("qurilish", "brick", "Qurilish materiallari", "Строительные материалы", "Qurılıs materialları", "Building materials"),
    ("temir-beton", "blocks", "Temir-beton va granit buyumlar", "ЖБИ и гранитные изделия", "Temir-beton hám granit buyımlar", "Precast concrete & granite"),
    ("mebel", "sofa", "Uy va ofis mebeli", "Мебель для дома и офиса", "Úy hám ofis mebeli", "Home & office furniture"),
    ("talim-mebeli", "school", "Ta'lim muassasalari uchun mebel", "Мебель для учебных заведений", "Bilimlendiriw mekemeleri ushın mebel", "Furniture for schools"),
    ("rom-eshik", "door", "Eshik, rom va vitrajlar", "Двери, окна и витражи", "Esik, rama hám vitrajlar", "Doors, windows & glazing"),
    ("metall", "wrench", "Metall buyumlar va konstruksiyalar", "Металлоизделия и конструкции", "Metall buyımlar hám konstrukciyalar", "Metal products & structures"),
    ("toqimachilik", "bed", "Ko'rpa-to'shak va to'qimachilik", "Постельные принадлежности и текстиль", "Tósek-orın hám toqımashılıq", "Bedding & textiles"),
    ("kiyim", "shirt", "Maxsus kiyim va poyabzal", "Спецодежда и обувь", "Arnawlı kiyim hám ayaq kiyim", "Workwear & footwear"),
    ("suvenir", "gift", "Suvenir va yog'och o'ymakorligi", "Сувениры и резьба по дереву", "Suvenir hám aǵash oymakerligi", "Souvenirs & wood carving"),
    ("obodonlashtirish", "tree", "Obodonlashtirish va sport jihozlari", "Благоустройство и спортинвентарь", "Abadanlastırıw hám sport úskeneleri", "Landscaping & sports equipment"),
    ("oquv-jihozlar", "target", "Harbiy-vatanparvarlik o'quv jihozlari", "Учебное оборудование для НВП", "Áskeriy-watanparwarlıq oqıw úskeneleri", "Military-patriotic training aids"),
    ("xavfsizlik", "shield", "Xavfsizlik va qo'riqlash jihozlari", "Средства безопасности и ограждения", "Qáwipsizlik hám qorǵaw úskeneleri", "Security & fencing"),
    ("xojalik", "basket", "Oziq-ovqat va xo'jalik mollari", "Продукты и хозтовары", "Azıq-awqat hám xojalıq zatları", "Food & household goods"),
    ("xizmatlar", "tools", "Buyurtma asosidagi xizmatlar", "Услуги на заказ", "Buyırtpa tiykarındaǵı xızmetler", "Made-to-order services"),
]

UNITS = {
    "dona": tri("dona", "шт", "dana", "pcs"),
    "juft": tri("juft", "пара", "jup", "pair"),
    "kg": tri("kg", "кг", "kg", "kg", cyrl="кг"),
    "m²": tri("m²", "м²", "m²", "m²", cyrl="м²"),
    "m³": tri("m³", "м³", "m³", "m³", cyrl="м³"),
    "p/m": tri("p/m", "пог. м", "uzın. m", "lin. m", cyrl="п/м"),
    "to'plam": tri("to'plam", "компл.", "komplekt", "set"),
    "tonna": tri("tonna", "т", "tonna", "t"),
    "xizmat": tri("xizmat", "услуга", "xızmet", "service"),
}

REGIONS = {
    "Toshkent shahri": ("г. Ташкент", "Tashkent qalası", "Tashkent city"),
    "Toshkent viloyati": ("Ташкентская область", "Tashkent wálayatı", "Tashkent region"),
    "Andijon viloyati": ("Андижанская область", "Ándijan wálayatı", "Andijan region"),
    "Buxoro viloyati": ("Бухарская область", "Buxara wálayatı", "Bukhara region"),
    "Farg'ona viloyati": ("Ферганская область", "Ferǵana wálayatı", "Fergana region"),
    "Jizzax viloyati": ("Джизакская область", "Jizzax wálayatı", "Jizzakh region"),
    "Namangan viloyati": ("Наманганская область", "Namangan wálayatı", "Namangan region"),
    "Navoiy viloyati": ("Навоийская область", "Nawayı wálayatı", "Navoi region"),
    "Qashqadaryo viloyati": ("Кашкадарьинская область", "Qashqadárya wálayatı", "Kashkadarya region"),
    "Qoraqalpog'iston Respublikasi": ("Республика Каракалпакстан", "Qaraqalpaqstan Respublikası", "Republic of Karakalpakstan"),
    "Samarqand viloyati": ("Самаркандская область", "Samarqand wálayatı", "Samarkand region"),
    "Sirdaryo viloyati": ("Сырдарьинская область", "Sırdárya wálayatı", "Syrdarya region"),
    "Surxondaryo viloyati": ("Сурхандарьинская область", "Surxandárya wálayatı", "Surkhandarya region"),
    "Xorazm viloyati": ("Хорезмская область", "Xorezm wálayatı", "Khorezm region"),
}

PLACE_OVR = {  # ru, en, kaa
    "Jizzax": ("Джизак", "Jizzakh", "Jizzax"), "Olmaliq": ("Алмалык", "Almalyk", "Olmalıq"),
    "Qarshi": ("Карши", "Karshi", "Qarshı"), "Zangiota": ("Зангиата", "Zangiata", "Zangiata"),
    "Qiziltepa": ("Кызылтепа", "Kyziltepa", "Qızıltepa"), "Navoiy": ("Навои", "Navoi", "Nawayı"),
    "Karmana": ("Кармана", "Karmana", "Karmana"), "Qamashi": ("Камаши", "Kamashi", "Qamashı"),
    "Kogon": ("Каган", "Kagan", "Kogon"), "Pop": ("Пап", "Pap", "Pap"),
    "Bo'stonliq": ("Бостанлык", "Bostanlyk", "Bóstanlıq"), "Koson": ("Касан", "Kasan", "Kasan"),
    "Zarafshon": ("Зарафшан", "Zarafshan", "Zarafshan"), "Chirchiq": ("Чирчик", "Chirchik", "Shırshıq"),
    "Qorovulbozor": ("Караулбазар", "Karaulbazar", "Qarawılbazar"), "Qo'ng'irot": ("Кунград", "Kungrad", "Qońırat"),
    "Zafarobod": ("Зафарабад", "Zafarabad", "Zafarabad"), "Muborak": ("Мубарек", "Mubarek", "Mubarek"),
    "Pastdarg'om": ("Пастдаргом", "Pastdargom", "Pastdarǵom"), "Samarqand": ("Самарканд", "Samarkand", "Samarqand"),
    "Sardoba": ("Сардоба", "Sardoba", "Sardoba"), "Guliston": ("Гулистан", "Gulistan", "Gúlistan"),
    "Sherobod": ("Шерабад", "Sherabad", "Sherabad"), "Bo'ka": ("Бука", "Buka", "Búka"),
    "Yuqori Chirchiq": ("Юкоричирчик", "Yukorichirchik", "Joqarı Shırshıq"), "Ohangaron": ("Ахангаран", "Akhangaran", "Axangaran"),
    "Piskent": ("Пскент", "Pskent", "Pskent"), "Yashnobod": ("Яшнабад", "Yashnabad", "Yashnabad"),
    "Qarshi shahri, Shayxali": ("Карши, Шайхали", "Karshi, Shaykhali", "Qarshı, Shayxalı"),
}


# Rus/ingliz/qoraqalpoq: tuman/shahar so'zlari
def place_tr(place: str) -> dict:
    """'Qarshi shahri' / 'Zangiota tumani' kabi joy nomlari."""
    m = re.match(r"(.+?) (shahri|tumani|qo'rg'oni)$", place)
    base, kind = (m.group(1), m.group(2)) if m else (place, "")
    ru_k = {"shahri": "г. ", "tumani": " район", "qo'rg'oni": " (посёлок)"}.get(kind, "")
    en_k = {"shahri": " city", "tumani": " district", "qo'rg'oni": " settlement"}.get(kind, "")
    kaa_k = {"shahri": " qalası", "tumani": " rayonı", "qo'rg'oni": " qorǵanı"}.get(kind, "")
    ovr = PLACE_OVR.get(base)
    base_ru = ovr[0] if ovr else to_cyrl(base).replace("ў", "у").replace("ғ", "г").replace("қ", "к").replace("ҳ", "х").replace("ъ", "")
    ru = f"г. {base_ru}" if kind == "shahri" else f"{base_ru}{ru_k}"
    base_en = ovr[1] if ovr else base.replace("'", "")
    base_kaa = ovr[2] if ovr and len(ovr) > 2 else base
    return tri(place, ru, base_kaa + kaa_k, base_en + en_k)


def address_tr(addr: str) -> dict:
    parts = [p.strip() for p in addr.split(",")]
    out = {k: [] for k in LANGS}
    for p in parts:
        if p in REGIONS:
            ru, kaa, en = REGIONS[p]
            d = tri(p, ru, kaa, en)
        else:
            d = place_tr(p)
        for k in LANGS:
            out[k].append(d[k])
    return {k: ", ".join(v) for k, v in out.items()}


def seller_name(short: str) -> dict:
    m = re.match(r"(\d+)-son (JIEK|MK)", short)
    if not m:  # IIV JIED
        return tri(short, "ДИН МВД", "IIV JIED", "MIA Penitentiary Department", cyrl="ИИВ ЖИЭД")
    n, t = m.groups()
    cyr_t = {"JIEK": "ЖИЭК", "MK": "МК"}[t]
    return {
        "uz": f"{n}-son {t}",
        "uz_cyrl": f"{n}-сон {cyr_t}",
        "uz_new": f"{n}-son {t}",
        "ru": f"{cyr_t} №{n}",
        "kaa": f"{n}-san {t}",
        "en": f"{t} No.{n}",
    }


SPEC_DICT = {
    "100% paxta, gulsiz, oqartirilgan, 214×120 sm": ("100% хлопок, без рисунка, отбелённая, 214×120 см", "100% paxta, gúlsiz, aǵartılǵan, 214×120 sm", "100% cotton, plain, bleached, 214×120 cm"),
    "200 g, paxta": ("200 г, хлопок", "200 g, paxta", "200 g, cotton"),
    "50 kg lik": ("на 50 кг", "50 kg lıq", "50 kg capacity"),
    "70%, og'irligi 200 g": ("70%, вес 200 г", "70%, salmaǵı 200 g", "70%, weight 200 g"),
    "8 kishilik": ("на 8 персон", "8 adamlıq", "for 8 people"),
    "PVX profil, 1 m² narxi": ("профиль ПВХ, цена за 1 м²", "PVX profil, 1 m² bahası", "PVC profile, price per 1 m²"),
    "alyumin profil, 1 m² narxi": ("алюминиевый профиль, цена за 1 м²", "alyuminiy profil, 1 m² bahası", "aluminium profile, price per 1 m²"),
    "buyurtmachi materialidan": ("из материала заказчика", "buyırtpashı materialınan", "from customer's material"),
    "buyurtmachi o'lchami va eskizi bo'yicha": ("по размерам и эскизу заказчика", "buyırtpashı ólshemi hám eskizi boyınsha", "to customer's size and sketch"),
    "buyurtmachi talabi bo'yicha": ("по требованию заказчика", "buyırtpashı talabı boyınsha", "per customer's requirements"),
    "choyshab 130×200 sm, ko'rpa jildi 130×200 sm, yostiq jildi 60×60 sm": ("простыня 130×200 см, пододеяльник 130×200 см, наволочка 60×60 см", "shoyshap 130×200 sm, kórpe qabı 130×200 sm, jastıq qabı 60×60 sm", "sheet 130×200 cm, duvet cover 130×200 cm, pillowcase 60×60 cm"),
    "d 110 mm": ("Ø 110 мм", "d 110 mm", "Ø 110 mm"),
    "diametri 50, 60, 90 sm": ("диаметр 50, 60, 90 см", "diametri 50, 60, 90 sm", "diameter 50, 60, 90 cm"),
    "javon, stol, idish yuvish burchagi": ("шкаф, стол, мойка", "shkaf, stol, ıdıs juwıw múyeshi", "cabinet, table, sink unit"),
    "juft": ("пара", "jup", "pair"),
    "kaska, niqob, forma, qo'lqop, etik, bronejilet, himoyalagichlar": ("каска, маска, форма, перчатки, сапоги, бронежилет, защита рук и ног", "kaska, betperde, forma, qolǵap, etik, bronejilet, qorǵaǵıshlar", "helmet, mask, uniform, gloves, boots, body armour, limb protectors"),
    "katta": ("большой", "úlken", "large"),
    "kichik": ("малый", "kishi", "small"),
    "laminat": ("ламинат", "laminat", "laminate"),
    "metall": ("металл", "metall", "metal"),
    "metall konstruksiya": ("металлоконструкция", "metall konstrukciya", "metal structure"),
    "po'lat, 2,8 mm": ("сталь, 2,8 мм", "polat, 2,8 mm", "steel, 2.8 mm"),
    "s/k": ("с/к", "s/k", "s/k"),
    "suvenir": ("сувенир", "suvenir", "souvenir"),
    "taxtadan, 72×38 sm": ("из дерева, 72×38 см", "taxtadan, 72×38 sm", "wooden, 72×38 cm"),
    "to'plam": ("комплект", "komplekt", "set"),
    "turli materialdan, o'lchamga qarab (350 000 – 750 000 so'm)": ("из разных материалов, по размеру (350 000 – 750 000 сум)", "túrli materialdan, ólshemge qarap (350 000 – 750 000 sum)", "various materials, by size (UZS 350,000 – 750,000)"),
    "turli o'lchamda": ("разных размеров", "túrli ólshemde", "various sizes"),
    "turli o'lchamda, buyurtma asosida": ("разных размеров, на заказ", "túrli ólshemde, buyırtpa tiykarında", "various sizes, made to order"),
    "yog'och": ("дерево", "aǵash", "wood"),
    "1,80×0,90×0,50 m, LDSP": ("1,80×0,90×0,50 м, ЛДСП", "1,80×0,90×0,50 m, LDSP", "1.80×0.90×0.50 m, chipboard"),
    "20×40 fraksiya": ("фракция 20×40", "20×40 fraksiya", "20×40 fraction"),
    "3,8–7,2 metr": ("3,8–7,2 м", "3,8–7,2 metr", "3.8–7.2 m"),
    "4,5×3 m (12 m²)": ("4,5×3 м (12 м²)", "4,5×3 m (12 m²)", "4.5×3 m (12 m²)"),
    "14 sm × 1,8 mm": ("14 см × 1,8 мм", "14 sm × 1,8 mm", "14 cm × 1.8 mm"),
}


def spec_tr(spec: str) -> dict:
    if not spec:
        return {k: "" for k in LANGS}
    if spec in SPEC_DICT:
        ru, kaa, en = SPEC_DICT[spec]
        return tri(spec, ru, kaa, en)
    # O'lchamlar va GOST belgilari
    ru = spec
    for a, b in [("KTsD", "КЦД"), ("KTs", "КЦ"), ("PK ", "ПК "), ("M-", "М-"), ("G5", "Г5")]:
        ru = ru.replace(a, b)
    ru = re.sub(r"\bsm\b", "см", ru)
    ru = re.sub(r"\bmm\b", "мм", ru)
    ru = re.sub(r"\bm\b", "м", ru)
    ru = re.sub(r"\bg\b", "г", ru)
    en = re.sub(r"\bsm\b", "cm", spec)
    en = re.sub(r"(\d),(\d)", r"\1.\2", en)
    cyrl = spec
    for a, b in [("KTsD", "КЦД"), ("KTs", "КЦ"), ("PK ", "ПК "), ("M-", "М-"), ("G5", "Г5")]:
        cyrl = cyrl.replace(a, b)
    cyrl = re.sub(r"\bsm\b", "см", cyrl)
    cyrl = re.sub(r"\bmm\b", "мм", cyrl)
    cyrl = re.sub(r"\bm\b", "м", cyrl)
    cyrl = re.sub(r"\bg\b", "г", cyrl)
    return {"uz": spec, "uz_cyrl": cyrl, "uz_new": spec, "ru": ru, "kaa": spec, "en": en}


def slugify(s: str) -> str:
    s = s.lower().replace("'", "").replace("№", "n")
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def main():
    names = {}
    with open(HERE / "names_i18n.tsv", encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            names[row["uz"]] = row

    sellers = []
    with open(HERE / "sellers.tsv", encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            ru, kaa, en = REGIONS[row["region"]]
            sellers.append({
                "code": row["code"],
                "inn": row["inn"],
                "role": row["role"],
                "name": seller_name(row["short"]),
                "region": row["region"],
                "region_i18n": tri(row["region"], ru, kaa, en),
                "district_i18n": place_tr(row["district"]),
            })

    # products.txt ni o'qish
    blocks, cur, shared = {}, None, []
    header = {}
    for raw in open(HERE / "products.txt", encoding="utf-8"):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("@@"):
            blocks[cur].append(("@@", line[2:]))
            continue
        if line.startswith("@"):
            parts = [p.strip() for p in line[1:].split("|")]
            cur = parts[0]
            blocks[cur] = []
            if len(parts) > 1:
                header[cur] = {"address": parts[1], "delivery": parts[2] == "1"}
            continue
        blocks[cur].append(("row", line))

    def expand(code):
        rows = []
        for kind, val in blocks[code]:
            if kind == "@@":
                rows.extend(expand(val))
            else:
                rows.append(val)
        return rows

    products = []
    missing = set()
    quality = []
    for code, h in header.items():
        seen = set()
        for i, line in enumerate(expand(code)):
            p = [x.strip() for x in line.split("|")]
            p += [""] * (7 - len(p))
            name, spec, unit, price, qty, cat, note = p[:7]
            if name not in names:
                missing.add(name)
                continue
            n = names[name]
            key = (name, spec)
            if key in seen:
                continue
            seen.add(key)
            price_v = int(float(price)) if price else None
            qty_v = int(float(qty)) if qty else None
            delivery = h["delivery"] and "Yetkazib berish yo'q" not in note
            sku = f"{code.upper()}-{len(seen):03d}"
            products.append({
                "sku": sku,
                "seller": code,
                "category": cat,
                "name": tri(name, n["ru"], n["kaa"], n["en"]),
                "spec": spec_tr(spec),
                "unit": unit,
                "price": price_v,
                "stock": qty_v,
                "daily_capacity": qty_v,
                "address": address_tr(h["address"]),
                "delivery": delivery,
                "note": note,
            })
            if note:
                quality.append({"sku": sku, "seller": code, "name": name, "spec": spec, "note": note})

    if missing:
        print("TARJIMASI YO'Q:", sorted(missing))
        sys.exit(1)

    catalog = {
        "languages": LANGS,
        "categories": [
            {"slug": s, "icon": ic, "name": tri(uz, ru, kaa, en)} for s, ic, uz, ru, kaa, en in CATEGORIES
        ],
        "units": UNITS,
        "sellers": sellers,
        "products": products,
        "quality_notes": quality,
    }
    out = HERE.parent / "backend" / "market" / "seed" / "catalog.json"
    out.write_text(json.dumps(catalog, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"sellers={len(sellers)} products={len(products)} categories={len(CATEGORIES)} notes={len(quality)} -> {out}")


if __name__ == "__main__":
    main()
