"""O'zbek lotin yozuvidan kirill va "yangi alifbo" (Ó, Ǵ, Ş, Ç) ga avtomatik o'girish.

Bazada har bir matn 6 tilda saqlanadi: uz (lotin), uz_cyrl, uz_new, ru, kaa, en.
Sotuvchi faqat lotinda yozsa, uz_cyrl va uz_new shu yerdan avtomatik to'ldiriladi.
"""
import re

LANGS = ["uz", "uz_cyrl", "uz_new", "ru", "kaa", "en"]
LANG_LABELS = {
    "uz": "O'zbekcha",
    "uz_cyrl": "Ўзбекча",
    "uz_new": "Ózbekçe",
    "ru": "Русский",
    "kaa": "Qaraqalpaqsha",
    "en": "English",
}

_APOS = re.compile(r"[ʻʼ’‘`´]")
VOWELS_LAT = set("aeiouAEIOU")


def norm(s: str) -> str:
    return _APOS.sub("'", s or "")


# ko'p harfli birikmalar birinchi tekshiriladi
_MULTI = [
    ("o'", "ў"), ("g'", "ғ"), ("sh", "ш"), ("ch", "ч"),
    ("yo", "ё"), ("yu", "ю"), ("ya", "я"), ("ts", "ц"),
]
_SINGLE = {
    "a": "а", "b": "б", "d": "д", "e": "е", "f": "ф", "g": "г", "h": "ҳ", "i": "и",
    "j": "ж", "k": "к", "l": "л", "m": "м", "n": "н", "o": "о", "p": "п", "q": "қ",
    "r": "р", "s": "с", "t": "т", "u": "у", "v": "в", "x": "х", "y": "й", "z": "з",
    "c": "с", "w": "в",
}


def to_cyrl(text: str) -> str:
    """Lotin -> kirill (o'zbek)."""
    s = norm(text)
    out = []
    i = 0
    n = len(s)
    while i < n:
        ch = s[i]
        low2 = s[i:i + 2].lower()
        prev = s[i - 1] if i > 0 else " "
        word_start = not prev.isalpha()
        # ye- so'z boshida -> е
        if low2 == "ye" and word_start:
            out.append("Е" if ch.isupper() else "е")
            i += 2
            continue
        matched = False
        for lat, cyr in _MULTI:
            if low2 == lat:
                out.append(cyr.upper() if ch.isupper() else cyr)
                i += 2
                matched = True
                break
        if matched:
            continue
        low = ch.lower()
        if low == "e":
            cyr = "э" if (word_start or prev in VOWELS_LAT) else "е"
            out.append(cyr.upper() if ch.isupper() else cyr)
        elif ch == "'":
            # tutuq belgisi
            out.append("ъ" if prev.isalpha() else ch)
        elif low in _SINGLE:
            cyr = _SINGLE[low]
            out.append(cyr.upper() if ch.isupper() else cyr)
        else:
            out.append(ch)
        i += 1
    return "".join(out)


def to_new(text: str) -> str:
    """Lotin -> yangi alifbo loyihasi (Ó ó, Ǵ ǵ, Ş ş, Ç ç, tutuq ’)."""
    s = norm(text)
    s = re.sub(r"O'", "Ó", s)
    s = re.sub(r"o'", "ó", s)
    s = re.sub(r"G'", "Ǵ", s)
    s = re.sub(r"g'", "ǵ", s)
    s = re.sub(r"S[hH]", "Ş", s)
    s = re.sub(r"sh", "ş", s)
    s = re.sub(r"C[hH]", "Ç", s)
    s = re.sub(r"ch", "ç", s)
    s = s.replace("'", "’")
    return s


def fill_i18n(d: dict | None, base_lang: str = "uz") -> dict:
    """Bo'sh tillarni to'ldiradi: uz_cyrl/uz_new lotindan, qolganlari uz ga qaytadi."""
    d = {k: (v or "").strip() for k, v in (d or {}).items() if k in LANGS}
    uz = d.get("uz") or ""
    if not uz and d.get(base_lang):
        uz = d[base_lang]
        d["uz"] = uz
    if uz:
        if not d.get("uz_cyrl"):
            d["uz_cyrl"] = to_cyrl(uz)
        if not d.get("uz_new"):
            d["uz_new"] = to_new(uz)
    for lang in LANGS:
        if not d.get(lang):
            d[lang] = uz
    return d


def pick(d: dict | None, lang: str) -> str:
    if not d:
        return ""
    return d.get(lang) or d.get("uz") or next((v for v in d.values() if v), "")
