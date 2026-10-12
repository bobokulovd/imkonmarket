"""Marketplace xususiyatlarini ImkonMarket lug'atiga avtomatik moslash.

Operator kategoriyani moslaganda (fetch_attributes) marketplace xususiyatlari nomi bo'yicha bizning
AttributeDef'larga (ruscha nomi orqali) yoki standart maydonlarga (brend, mamlakat...) bog'lanadi,
lug'at qiymatlari esa variantlarimiz nomi bo'yicha moslanadi. Operator qo'lda o'zgartirgan moslamalar buzilmaydi —
faqat hali sozlanmagan (doimiy qiymati bo'sh) xususiyatlar to'ldiriladi.
"""
import re

from market.models import AttributeDef

from .models import AttributeMapping, AttributeValueMap

FIELD_SYNONYMS = {
    "brand": ["бренд", "торговая марка", "марка", "brand", "brend"],
    "country": ["страна-изготовитель", "страна изготовитель", "страна производства", "страна изготовления",
                "страна происхождения", "ishlab chiqarilgan mamlakat"],
    "group": ["название модели", "объединить на одной карточке", "модель для объединения"],
    "ikpu": ["икпу", "код икпу", "мхик", "ikpu", "mxik"],
    "barcode": ["штрихкод", "штрих-код", "barcode"],
    "name": ["наименование", "название товара"],
    "description": ["описание", "аннотация"],
}
YES = {"да", "есть", "ha", "yes", "true"}
NO = {"нет", "yo'q", "no", "false", "отсутствует"}


def norm(s: str) -> str:
    s = (s or "").lower().replace("ё", "е").replace("ʻ", "'").replace("‘", "'")
    s = re.sub(r"\(.*?\)", " ", s)
    s = re.sub(r"\b(товара|изделия|продукта|основной|основного)\b", " ", s)
    s = re.sub(r"[,:;.]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _match_field(name):
    n = norm(name)
    for field, words in FIELD_SYNONYMS.items():
        if any(n == norm(w) or n.startswith(norm(w) + " ") for w in words):
            return field
    return None


def _match_def(name, defs):
    n = norm(name)
    if not n:
        return None
    for d in defs:
        for lang in ("ru", "uz", "en"):
            if norm((d.name or {}).get(lang, "")) == n:
                return d
    # "цвет" ~ "основной цвет", "материал" ~ "материал корпуса" — bitta so'zli nom boshqa nomning boshida
    for d in defs:
        dn = norm((d.name or {}).get("ru", ""))
        if len(dn) >= 4 and (n.startswith(dn + " ") or dn.startswith(n + " ")):
            return d
    return None


def suggest_values(am: AttributeMapping, d: AttributeDef) -> int:
    """Lug'atli xususiyat: variant nomlari (ru/uz/en) ↔ marketplace qiymatlari. Mavjud moslamalarga tegmaydi."""
    if not am.is_dictionary or not am.values:
        return 0
    by_name = {}
    for v in am.values:
        by_name.setdefault(norm(str(v.get("value") or "")), v)
    existing = set(am.value_map.values_list("our_value", flat=True))
    n = 0
    pairs = []
    if d.type == AttributeDef.T_ENUM:
        for o in d.options or []:
            names = [norm((o.get("name") or {}).get(lang, "")) for lang in ("ru", "uz", "en")] + [norm(o.get("v", ""))]
            hit = next((by_name[x] for x in names if x and x in by_name), None)
            if hit is None:  # "Керамика (обожжённая глина)" → "керамика"
                hit = next((v for k, v in by_name.items() for x in names if x and k and (x.startswith(k + " ") or k.startswith(x + " "))), None)
            if hit is not None:
                pairs.append((o["v"], hit))
    elif d.type == AttributeDef.T_BOOL:
        yes = next((v for k, v in by_name.items() if k in YES), None)
        no = next((v for k, v in by_name.items() if k in NO), None)
        pairs = [(code, v) for code, v in (("true", yes), ("false", no)) if v is not None]
    for code, hit in pairs:
        if code in existing:
            continue
        AttributeValueMap.objects.create(attribute=am, our_value=code, external_value_id=str(hit.get("id") or ""),
                                         external_value=str(hit.get("value") or "")[:255])
        n += 1
    return n


def auto_map(mapping) -> dict:
    defs = list(AttributeDef.objects.filter(category_id=mapping.category_id))
    by_code = {d.code: d for d in defs}
    fields = attrs = values = 0
    for am in mapping.attributes.prefetch_related("value_map"):
        untouched = am.source == AttributeMapping.SRC_CONST and not (am.value or am.value_id)
        if untouched:
            f = _match_field(am.name)
            if f:
                am.source, am.field = AttributeMapping.SRC_FIELD, f
                am.save(update_fields=["source", "field"])
                fields += 1
                continue
            d = _match_def(am.name, defs)
            if d:
                am.source, am.field = AttributeMapping.SRC_ATTR, d.code
                am.save(update_fields=["source", "field"])
                attrs += 1
        if am.source == AttributeMapping.SRC_ATTR and am.field in by_code:
            values += suggest_values(am, by_code[am.field])
    return {"fields": fields, "attrs": attrs, "values": values}
