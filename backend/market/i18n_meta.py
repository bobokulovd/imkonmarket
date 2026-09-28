"""Katalog meta-ma'lumotlari (o'lchov birliklari, viloyatlar) — seed/catalog.json dan."""
import json
from functools import lru_cache
from pathlib import Path

from .translit import LANG_LABELS, LANGS, fill_i18n, pick

SEED = Path(__file__).resolve().parent / "seed" / "catalog.json"


@lru_cache
def catalog():
    return json.loads(SEED.read_text(encoding="utf-8"))


def units():
    return catalog()["units"]


def unit_label(unit, lang):
    d = units().get(unit)
    return pick(d, lang) if d else unit


@lru_cache
def regions():
    seen = {}
    for s in catalog()["sellers"]:
        seen.setdefault(s["region"], s["region_i18n"])
    return [{"key": k, "name": v} for k, v in seen.items()]


def languages():
    return [{"code": c, "label": LANG_LABELS[c]} for c in LANGS]


__all__ = ["catalog", "units", "unit_label", "regions", "languages", "fill_i18n", "pick"]
