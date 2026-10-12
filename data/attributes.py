"""ImkonMarket yagona xususiyatlar lug'ati (14 kategoriya) -> backend/market/seed/attributes.json

    python data/attributes.py

Tamoyil: muassasa o'zbekcha to'ldiradi, operator har bir xususiyatni marketplace xususiyatiga bir marta bog'laydi.
Marketplace'larda deyarli doim so'raladigan xususiyatlar (rang, material, o'lcham, komplektatsiya) birinchi o'rinda.
`ru` nomlar marketplace xususiyatlariga avtomatik moslash uchun ham ishlatiladi.
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "backend/market/seed/attributes.json"


def n(uz, ru, en, kaa=None):
    return {"uz": uz, "ru": ru, "en": en, "kaa": kaa or uz}


def opt(v, uz, ru, en, kaa=None):
    return {"v": v, "name": n(uz, ru, en, kaa)}


def a(code, name, type="text", unit="", required=False, multi=False, variant=False, options=None, hint=None):
    d = {"code": code, "name": name, "type": type, "unit": unit, "required": required, "multi": multi,
         "variant": variant, "options": options or []}
    if hint:
        d["hint"] = hint
    return d


COLORS = [
    opt("oq", "Oq", "Белый", "White", "Aq"), opt("qora", "Qora", "Чёрный", "Black", "Qara"),
    opt("kulrang", "Kulrang", "Серый", "Grey", "Sur"), opt("jigarrang", "Jigarrang", "Коричневый", "Brown", "Qońır"),
    opt("bej", "Bej", "Бежевый", "Beige"), opt("qizil", "Qizil", "Красный", "Red", "Qızıl"),
    opt("kok", "Ko'k", "Синий", "Blue", "Kók"), opt("havorang", "Havorang", "Голубой", "Light blue", "Aspan reń"),
    opt("yashil", "Yashil", "Зелёный", "Green", "Jasıl"), opt("sariq", "Sariq", "Жёлтый", "Yellow", "Sarı"),
    opt("toq-sariq", "To'q sariq", "Оранжевый", "Orange", "Qızǵılt sarı"),
    opt("binafsha", "Binafsha", "Фиолетовый", "Purple"), opt("pushti", "Pushti", "Розовый", "Pink"),
    opt("haki", "Xaki", "Хаки", "Khaki"), opt("yogoch", "Yog'och rangi", "Цвет дерева", "Wood", "Aǵash reńi"),
    opt("venge", "Venge", "Венге", "Wenge"), opt("yongoq", "Yong'oq", "Орех", "Walnut", "Ǵoz"),
    opt("dub", "Eman (dub)", "Дуб", "Oak"), opt("kumush", "Kumushrang", "Серебристый", "Silver"),
    opt("tilla", "Tillarang", "Золотистый", "Gold"), opt("rangbarang", "Rang-barang", "Разноцветный", "Multicolor"),
    opt("tabiiy", "Tabiiy (bo'yalmagan)", "Натуральный", "Natural"),
]
COLOR = lambda req=True, variant=True: a("rang", n("Rang", "Цвет", "Color", "Reń"), "enum", required=req,
                                         variant=variant, options=COLORS)

FURN_MAT = [
    opt("ldsp", "LDSP", "ЛДСП", "Laminated chipboard"), opt("mdf", "MDF", "МДФ", "MDF"),
    opt("yogoch", "Massiv yog'och", "Массив дерева", "Solid wood", "Massiv aǵash"),
    opt("fanera", "Fanera", "Фанера", "Plywood"), opt("metall", "Metall", "Металл", "Metal"),
    opt("plastik", "Plastik", "Пластик", "Plastic"), opt("rotang", "Rotang", "Ротанг", "Rattan"),
    opt("dsp", "DSP", "ДСП", "Chipboard"), opt("shisha", "Shisha", "Стекло", "Glass", "Áyne"),
]
UPHOLSTERY = [
    opt("gazlama", "Gazlama", "Ткань", "Fabric"), opt("ekokoja", "Eko-charm", "Экокожа", "Eco leather"),
    opt("charm", "Charm", "Кожа", "Leather"), opt("velur", "Velur", "Велюр", "Velour"),
]

DIMS = [
    a("uzunlik", n("Uzunligi", "Длина", "Length", "Uzınlıǵı"), "number", "sm"),
    a("kenglik", n("Kengligi", "Ширина", "Width", "Keńligi"), "number", "sm"),
    a("balandlik", n("Balandligi", "Высота", "Height", "Biyikligi"), "number", "sm"),
]
WEIGHT_NET = a("vazn", n("Mahsulot og'irligi", "Вес товара", "Product weight", "Ónim salmaǵı"), "number", "kg")
COMPLECT = a("komplekt", n("Komplektatsiya", "Комплектация", "Package contents", "Komplektaciya"), "text",
             hint=n("Masalan: 1 stol, 2 stul", "Например: 1 стол, 2 стула", "E.g. 1 table, 2 chairs"))
ASSEMBLY = a("yigilgan", n("Yig'ilgan holda yetkaziladi", "Поставляется в собранном виде", "Delivered assembled",
                           "Jıynalǵan túrde jetkeriledi"), "bool")

SIZES_CLOTH = [opt(s, s, s, s) for s in ["44", "46", "48", "50", "52", "54", "56", "58", "60", "62"]]
SIZES_SHOE = [opt(s, s, s, s) for s in [str(x) for x in range(36, 47)]]
GENDER = a("jins", n("Jinsi", "Пол", "Gender", "Jınısı"), "enum", required=True, options=[
    opt("erkak", "Erkak", "Мужской", "Men", "Er"), opt("ayol", "Ayol", "Женский", "Women", "Hayal"),
    opt("uniseks", "Uniseks", "Унисекс", "Unisex")])
SEASON = a("mavsum", n("Mavsum", "Сезон", "Season", "Máwsim"), "enum", options=[
    opt("yoz", "Yoz", "Лето", "Summer", "Jaz"), opt("qish", "Qish", "Зима", "Winter", "Qıs"),
    opt("demi", "Bahor-kuz", "Демисезон", "Mid-season", "Báhár-gúz"), opt("yil", "Yil bo'yi", "Всесезон", "All season", "Jıl boyı")])

CATS = {
    "qurilish": [
        a("material", n("Material", "Материал", "Material"), "enum", required=True, options=[
            opt("loy", "Pishgan loy", "Керамика (обожжённая глина)", "Fired clay", "Pisken ılay"),
            opt("xom-loy", "Xom loy", "Сырцовая глина", "Raw clay"), opt("shlak", "Shlakobeton", "Шлакобетон", "Slag concrete"),
            opt("beton", "Beton", "Бетон", "Concrete"), opt("gips", "Gips", "Гипс", "Gypsum"),
            opt("ohak", "Ohak", "Известь", "Lime"), opt("tosh", "Tabiiy tosh", "Природный камень", "Natural stone"),
            opt("polietilen", "Polietilen", "Полиэтилен", "Polyethylene"), opt("keramzit", "Keramzit", "Керамзит", "Expanded clay")]),
        a("olcham", n("O'lchami", "Размер", "Size", "Ólshemi"), "text", required=True,
          hint=n("Masalan: 250×120×65 mm", "Например: 250×120×65 мм", "E.g. 250×120×65 mm")),
        a("marka", n("Mustahkamlik markasi", "Марка прочности", "Strength grade", "Bekkemlik markası"), "text",
          hint=n("Masalan: M100, M150", "Например: M100, M150", "E.g. M100")),
        a("fraksiya", n("Fraksiya", "Фракция", "Fraction"), "text", hint=n("Masalan: 5–20 mm", "Например: 5–20 мм", "E.g. 5–20 mm")),
        a("ichi_kovak", n("Ichi kovak", "Пустотелый", "Hollow", "Ishi qawıs"), "bool"),
        COLOR(req=False, variant=False), WEIGHT_NET,
        a("qadoq_soni", n("Qadoqdagi soni", "Количество в упаковке", "Quantity per pack", "Qaptamadaǵı sanı"), "number", "dona"),
    ],
    "temir-beton": [
        a("material", n("Material", "Материал", "Material"), "enum", required=True, options=[
            opt("temir-beton", "Temir-beton", "Железобетон", "Reinforced concrete", "Temir-beton"),
            opt("beton", "Beton", "Бетон", "Concrete"), opt("granit", "Granit", "Гранит", "Granite")]),
        a("marka", n("Marka / seriya", "Марка / серия", "Grade / series"), "text", required=True,
          hint=n("Masalan: PK 23-12-8, KTs 07-9", "Например: ПК 23-12-8, КЦ 07-9", "E.g. PK 23-12-8")),
        *DIMS, WEIGHT_NET,
        a("beton_markasi", n("Beton markasi", "Марка бетона", "Concrete grade"), "text", hint=n("M200, M300", "М200, М300", "M200")),
        COLOR(req=False, variant=True),
    ],
    "mebel": [
        a("material", n("Asosiy material", "Материал корпуса", "Main material", "Tiykarǵı material"), "enum",
          required=True, multi=True, options=FURN_MAT),
        COLOR(), *DIMS,
        a("qoplama", n("Qoplama (yumshoq mebel)", "Материал обивки", "Upholstery"), "enum", options=UPHOLSTERY),
        a("tolgich", n("To'ldirgich", "Наполнитель", "Filling", "Toltırǵısh"), "enum", options=[
            opt("porolon", "Porolon", "Поролон", "Foam"), opt("prujina", "Prujinali blok", "Пружинный блок", "Spring block"),
            opt("paxta", "Paxta", "Хлопок (вата)", "Cotton wool", "Paxta")]),
        a("orinlar", n("O'rinlar soni", "Количество мест", "Seats", "Orınlar sanı"), "number"),
        a("eshiklar", n("Eshiklar soni", "Количество дверей", "Number of doors", "Esikler sanı"), "number"),
        a("tortmalar", n("Tortmalar soni", "Количество ящиков", "Number of drawers", "Tartpalar sanı"), "number"),
        a("max_yuk", n("Maksimal yuklama", "Максимальная нагрузка", "Max load"), "number", "kg"),
        ASSEMBLY, COMPLECT, WEIGHT_NET,
    ],
    "talim-mebeli": [
        a("material", n("Asosiy material", "Материал", "Main material", "Tiykarǵı material"), "enum",
          required=True, multi=True, options=FURN_MAT),
        a("karkas", n("Karkas", "Каркас", "Frame"), "enum", options=[
            opt("metall", "Metall", "Металл", "Metal"), opt("yogoch", "Yog'och", "Дерево", "Wood", "Aǵash"),
            opt("yoq", "Karkassiz", "Без каркаса", "No frame", "Karkassız")]),
        a("guruh", n("Bo'y guruhi (№)", "Ростовая группа (№)", "Height group (No.)", "Boy toparı (№)"), "enum",
          variant=True, options=[opt(str(i), f"№{i}", f"№{i}", f"No.{i}") for i in range(1, 7)]),
        a("orinlar", n("O'rinlar soni", "Количество мест", "Seats", "Orınlar sanı"), "number"),
        COLOR(req=False), *DIMS, COMPLECT, ASSEMBLY, WEIGHT_NET,
    ],
    "rom-eshik": [
        a("profil", n("Profil materiali", "Материал профиля", "Profile material", "Profil materialı"), "enum", required=True, options=[
            opt("pvx", "PVX", "ПВХ", "PVC"), opt("alyumin", "Alyumin", "Алюминий", "Aluminium", "Alyuminiy"),
            opt("mdf", "MDF", "МДФ", "MDF"), opt("yogoch", "Yog'och", "Дерево", "Wood", "Aǵash"),
            opt("metall", "Metall", "Металл", "Metal")]),
        a("profil_brend", n("Profil brendi", "Бренд профиля", "Profile brand"), "text", hint=n("Masalan: Akfa", "Например: Akfa", "E.g. Akfa")),
        a("turi", n("Turi", "Тип изделия", "Type", "Túri"), "enum", required=True, options=[
            opt("rom", "Rom (deraza)", "Окно", "Window", "Ayna"), opt("eshik", "Eshik", "Дверь", "Door", "Esik"),
            opt("fortochka", "Fortochka", "Форточка", "Vent"), opt("vitraj", "Vitraj", "Витраж", "Stained glass / curtain wall"),
            opt("peregorodka", "To'siq devor", "Перегородка", "Partition")]),
        a("kamera", n("Shisha paketi kameralari", "Камер в стеклопакете", "Glazing chambers"), "number"),
        COLOR(req=False), *DIMS[:1], DIMS[2],
        a("narx_m2", n("Narx 1 m² uchun", "Цена за 1 м²", "Price per m²"), "bool"),
    ],
    "metall": [
        a("material", n("Material", "Материал", "Material"), "enum", required=True, options=[
            opt("qora-metall", "Qora metall", "Чёрный металл", "Mild steel", "Qara metall"),
            opt("zanglamas", "Zanglamas po'lat", "Нержавеющая сталь", "Stainless steel"),
            opt("ocinkovka", "Ruxlangan po'lat", "Оцинкованная сталь", "Galvanized steel"),
            opt("alyumin", "Alyumin", "Алюминий", "Aluminium")]),
        a("devor", n("Metall qalinligi", "Толщина металла", "Metal thickness", "Metall qalıńlıǵı"), "number", "mm"),
        a("qoplama", n("Qoplama", "Покрытие", "Coating", "Qaplama"), "enum", options=[
            opt("boyoq", "Bo'yoq", "Краска", "Paint", "Boyaw"), opt("poroshok", "Kukunli bo'yoq", "Порошковая краска", "Powder coat"),
            opt("yoq", "Qoplamasiz", "Без покрытия", "None", "Qaplamasız")]),
        COLOR(req=False), *DIMS, WEIGHT_NET,
        a("qulf", n("Qulf bilan", "С замком", "With lock", "Qulıp penen"), "bool"),
    ],
    "toqimachilik": [
        a("mato", n("Mato tarkibi", "Состав ткани", "Fabric composition", "Mata quramı"), "enum", required=True, options=[
            opt("paxta100", "100% paxta", "100% хлопок", "100% cotton", "100% paxta"), opt("biz", "Bo'z (byaz)", "Бязь", "Calico"),
            opt("satin", "Satin", "Сатин", "Sateen"), opt("poplin", "Poplin", "Поплин", "Poplin"),
            opt("yarimjun", "Yarim jun", "Полушерсть", "Half wool", "Yarım jún"), opt("trikotaj", "Trikotaj", "Трикотаж", "Jersey"),
            opt("aralash", "Aralash (paxta+sintetika)", "Смесовая ткань", "Blend")]),
        a("olcham", n("O'lchami", "Размер", "Size", "Ólshemi"), "enum", required=True, variant=True, options=[
            opt("1", "1 kishilik", "1-спальный", "Single", "1 adamlıq"), opt("1.5", "1,5 kishilik", "1,5-спальный", "1.5 bed"),
            opt("2", "2 kishilik", "2-спальный", "Double", "2 adamlıq"), opt("evro", "Evro", "Евро", "Euro"),
            opt("bolalar", "Bolalar uchun", "Детский", "Kids", "Balalar ushın")]),
        a("olcham_sm", n("Aniq o'lchami", "Размеры, см", "Dimensions, cm", "Anıq ólshemi"), "text",
          hint=n("Masalan: 214×120 sm", "Например: 214×120 см", "E.g. 214×120 cm")),
        a("zichlik", n("Zichlik", "Плотность", "Density"), "number", "g/m²"),
        COLOR(req=False), a("naqsh", n("Naqsh", "Рисунок", "Pattern", "Naǵıs"), "enum", options=[
            opt("gulsiz", "Gulsiz", "Однотонный", "Plain"), opt("gulli", "Gulli", "Цветочный", "Floral"),
            opt("geometrik", "Geometrik", "Геометрический", "Geometric")]),
        COMPLECT,
    ],
    "kiyim": [
        a("turi", n("Turi", "Вид изделия", "Item type", "Túri"), "enum", required=True, options=[
            opt("kostyum", "Kostyum", "Костюм", "Suit"), opt("kombinezon", "Kombinezon", "Комбинезон", "Overalls"),
            opt("kurtka", "Kurtka", "Куртка", "Jacket"), opt("shim", "Shim", "Брюки", "Trousers"),
            opt("mayka", "Mayka / futbolka", "Майка / футболка", "T-shirt / tank top"),
            opt("ichki", "Ichki kiyim", "Нательное бельё", "Underwear"), opt("botinka", "Botinka", "Ботинки", "Boots"),
            opt("polubotinka", "Polubotinka", "Полуботинки", "Low shoes"), opt("tufli", "Tufli", "Туфли", "Shoes"),
            opt("krossovka", "Krossovka", "Кроссовки", "Sneakers"), opt("etik", "Etik", "Сапоги", "High boots")]),
        GENDER, SEASON,
        a("olcham", n("Kiyim o'lchami", "Размер одежды", "Clothing size", "Kiyim ólshemi"), "enum", variant=True,
          options=SIZES_CLOTH, hint=n("Faqat kiyim uchun", "Только для одежды", "Clothing only")),
        a("poyabzal_olcham", n("Poyabzal o'lchami", "Размер обуви", "Shoe size", "Ayaq kiyim ólshemi"), "enum", variant=True,
          options=SIZES_SHOE, hint=n("Faqat poyabzal uchun", "Только для обуви", "Footwear only")),
        a("material", n("Ust materiali", "Материал верха", "Upper / outer material", "Ústingi materialı"), "enum", required=True, options=[
            opt("paxta", "Paxta", "Хлопок", "Cotton", "Paxta"), opt("aralash", "Aralash mato", "Смесовая ткань", "Blend"),
            opt("charm", "Tabiiy charm", "Натуральная кожа", "Genuine leather"),
            opt("suniy-charm", "Sun'iy charm", "Искусственная кожа", "Faux leather"),
            opt("tekstil", "Tekstil", "Текстиль", "Textile"), opt("trikotaj", "Trikotaj", "Трикотаж", "Jersey")]),
        a("taglik", n("Taglik materiali", "Материал подошвы", "Sole material", "Taban materialı"), "enum", options=[
            opt("rezina", "Rezina", "Резина", "Rubber"), opt("pu", "Poliuretan", "Полиуретан", "Polyurethane"),
            opt("eva", "EVA", "ЭВА", "EVA")]),
        COLOR(),
    ],
    "suvenir": [
        a("material", n("Material", "Материал", "Material"), "enum", required=True, multi=True, options=[
            opt("yongoq", "Yong'oq yog'ochi", "Орех", "Walnut", "Ǵoz aǵashı"), opt("sosna", "Qarag'ay (sosna)", "Сосна", "Pine"),
            opt("yogoch", "Yog'och", "Дерево", "Wood", "Aǵash"), opt("laminat", "Laminat", "Ламинат", "Laminate"),
            opt("mdf", "MDF", "МДФ", "MDF"), opt("charm", "Charm", "Кожа", "Leather")]),
        a("ishlov", n("Ishlov berish", "Техника исполнения", "Technique", "Islew beriw"), "enum", options=[
            opt("oyma", "O'yma naqsh", "Резьба по дереву", "Wood carving"), opt("qolda", "Qo'lda yasalgan", "Ручная работа", "Handmade"),
            opt("lak", "Lak bilan qoplangan", "Лакированный", "Lacquered")]),
        *DIMS, COLOR(req=False, variant=False), COMPLECT,
        a("sovga_qadoq", n("Sovg'a qadog'ida", "В подарочной упаковке", "Gift packaging", "Sawǵa qaptamasında"), "bool"),
    ],
    "obodonlashtirish": [
        a("material", n("Material", "Материал", "Material"), "enum", required=True, multi=True, options=[
            opt("metall", "Metall", "Металл", "Metal"), opt("yogoch", "Yog'och", "Дерево", "Wood", "Aǵash"),
            opt("beton", "Beton", "Бетон", "Concrete"), opt("plastik", "Plastik", "Пластик", "Plastic")]),
        a("qoplama", n("Qoplama", "Покрытие", "Coating", "Qaplama"), "enum", options=[
            opt("boyoq", "Bo'yoq", "Краска", "Paint", "Boyaw"), opt("poroshok", "Kukunli bo'yoq", "Порошковая краска", "Powder coat"),
            opt("ocinkovka", "Ruxlangan", "Оцинковка", "Galvanized")]),
        *DIMS, COLOR(req=False), WEIGHT_NET,
        a("max_yuk", n("Maksimal yuklama", "Максимальная нагрузка", "Max load"), "number", "kg"),
        a("yosh", n("Foydalanuvchi yoshi", "Возраст пользователя", "User age", "Paydalanıwshı jası"), "text"),
        ASSEMBLY,
    ],
    "oquv-jihozlar": [
        a("material", n("Material", "Материал", "Material"), "enum", required=True, multi=True, options=[
            opt("plastik", "Plastik", "Пластик", "Plastic"), opt("metall", "Metall", "Металл", "Metal"),
            opt("yogoch", "Yog'och", "Дерево", "Wood", "Aǵash"), opt("mato", "Mato", "Ткань", "Fabric", "Mata"),
            opt("rezina", "Rezina", "Резина", "Rubber")]),
        a("maket", n("O'quv maketi (jangovar emas)", "Учебный макет (небоевой)", "Training mock-up (non-functional)",
                     "Oqıw maketi (urıs ushın emes)"), "bool"),
        a("maqsad", n("Mo'ljal", "Назначение", "Purpose", "Mólsher"), "text",
          hint=n("Masalan: CHQBT darslari, tibbiy tayyorgarlik", "Например: уроки НВП, медподготовка", "E.g. pre-military training")),
        *DIMS, COLOR(req=False, variant=False), COMPLECT, WEIGHT_NET,
    ],
    "xavfsizlik": [
        a("material", n("Material", "Материал", "Material"), "enum", required=True, options=[
            opt("polat", "Po'lat", "Сталь", "Steel"), opt("ocinkovka", "Ruxlangan po'lat", "Оцинкованная сталь", "Galvanized steel"),
            opt("metall", "Metall", "Металл", "Metal")]),
        a("diametr", n("Diametri", "Диаметр", "Diameter", "Diametri"), "number", "sm", variant=True),
        a("sim_qalinligi", n("Sim qalinligi", "Толщина проволоки", "Wire thickness", "Sım qalıńlıǵı"), "number", "mm"),
        *DIMS, WEIGHT_NET, COMPLECT,
    ],
    "xojalik": [
        a("turi", n("Mahsulot turi", "Вид товара", "Product type", "Ónim túri"), "text", required=True),
        a("hajm", n("Og'irligi / hajmi", "Вес / объём", "Weight / volume", "Salmaǵı / kólemi"), "text", required=True,
          hint=n("Masalan: 200 g, 50 kg", "Например: 200 г, 50 кг", "E.g. 200 g")),
        a("tarkib", n("Tarkibi", "Состав", "Composition", "Quramı"), "text"),
        a("yaroqlilik", n("Yaroqlilik muddati", "Срок годности", "Shelf life", "Jaramlılıq múddeti"), "text"),
        a("qadoq_soni", n("Qadoqdagi soni", "Количество в упаковке", "Quantity per pack", "Qaptamadaǵı sanı"), "number", "dona"),
    ],
    "xizmatlar": [
        a("xizmat_turi", n("Xizmat turi", "Вид услуги", "Service type", "Xızmet túri"), "enum", required=True, options=[
            opt("mebel", "Mebel yasash", "Изготовление мебели", "Furniture making", "Mebel jasaw"),
            opt("tikuv", "Tikuvchilik", "Пошив", "Tailoring", "Tigiwshilik"),
            opt("duradgor", "Duradgorlik", "Столярные работы", "Carpentry"),
            opt("metall", "Metallga ishlov berish", "Металлообработка", "Metalwork", "Metallǵa islew beriw"),
            opt("beton", "Beton/granit buyumlar", "Изделия из бетона/гранита", "Concrete / granite products"),
            opt("tamir", "Ta'mirlash", "Ремонт", "Repair", "Remont")]),
        a("xomashyo", n("Xomashyo kimdan", "Чьё сырьё", "Raw material provided by", "Shiyki zat kimnen"), "enum", required=True, options=[
            opt("bizdan", "Ijrochidan (bizdan)", "Сырьё исполнителя", "Contractor's material", "Orınlawshıdan"),
            opt("buyurtmachi", "Buyurtmachidan", "Сырьё заказчика", "Customer's material", "Buyırtpashıdan")]),
        a("muddat", n("Bajarish muddati", "Срок выполнения", "Lead time", "Orınlaw múddeti"), "number", "kun"),
        a("minimal", n("Minimal buyurtma", "Минимальный заказ", "Minimum order"), "text"),
    ],
}

# Kategoriya uchun odatiy tavsif shablon emas — faqat xususiyatlar.
if __name__ == "__main__":
    data = {}
    for cat, attrs in CATS.items():
        seen = set()
        rows = []
        for i, x in enumerate(attrs):
            assert x["code"] not in seen, (cat, x["code"])
            seen.add(x["code"])
            rows.append({**x, "order": i})
        data[cat] = rows
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1))
    print(sum(len(v) for v in data.values()), "xususiyat,", len(data), "kategoriya ->", OUT)
