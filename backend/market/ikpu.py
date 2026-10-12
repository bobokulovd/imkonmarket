"""IKPU (MXIK) — tasnif.soliq.uz milliy klassifikatori bilan ishlash.

Qidiruv faqat serverda (brauzerdan to'g'ridan-to'g'ri CORS yo'q). Natija 1 soatga keshlanadi.
Tavsiya: mahsulot nomi bo'yicha qidirib, so'zlari eng ko'p mos kelgan kod tanlanadi va
ikpu_confirmed=False bilan saqlanadi — muassasa kartochkada tasdiqlaydi yoki boshqasini tanlaydi.
"""
import re
import time

import requests
from django.core.cache import cache

API = "https://tasnif.soliq.uz/api/cls-api/elasticsearch/search"
TIMEOUT = 15
STOP = {"и", "для", "из", "с", "в", "на", "по", "до", "от", "мм", "см", "м", "кг", "шт", "x", "х", "uchun", "va"}


def _tokens(s: str) -> set:
    words = re.findall(r"[a-zа-яёўқғҳʻ']+", (s or "").lower())
    return {w[:6] for w in words if len(w) > 2 and w not in STOP}  # o'zak (kelishik qo'shimchalari farq qilmasin)


def search(q: str, lang="ru", size=20) -> list:
    key = f"ikpu:{lang}:{size}:{q.lower()}"
    hit = cache.get(key)
    if hit is not None:
        return hit
    r = requests.get(API, params={"search": q, "page": 0, "size": size, "lang": lang}, timeout=TIMEOUT,
                     headers={"Accept": "application/json", "User-Agent": "ImkonMarket/1.0"})
    r.raise_for_status()
    data = r.json()
    time.sleep(0.2)  # tasnif.soliq.uz ni ortiqcha yuklamaslik
    items = []
    for it in data.get("data") or []:
        code = str(it.get("mxikCode") or "")
        if len(code) != 17:
            continue
        items.append({
            "code": code,
            "name": it.get("name") or "",
            "group": it.get("groupName") or "",
            "class": it.get("className") or "",
            "position": it.get("positionName") or "",
            "subposition": it.get("subPositionName") or "",
            "brand": it.get("brandName") or "",
        })
    cache.set(key, items, 3600)
    return items


def score(query: str, item: dict) -> float:
    q = _tokens(query)
    if not q:
        return 0.0
    name = _tokens(item.get("name", ""))
    ctx = _tokens(" ".join(item.get(k, "") for k in ("subposition", "position", "class")))
    s = len(q & name) * 2 + len(q & ctx) * 0.5
    if item.get("brand"):  # brendli (aniq bir firma) kodlar emas, umumiy kodlar afzal
        s -= 1
    if item["code"].endswith("000000"):  # subpozitsiya darajasidagi umumiy kod
        s += 0.5
    return s / (len(q) * 2)


def suggest(name_ru: str, name_uz: str = "") -> dict | None:
    """Eng mos kod: {"code", "name", "score"} yoki None (ishonchsiz bo'lsa)."""
    best = None
    for q, lang in ((name_ru, "ru"), (name_uz, "uz")):
        if not q:
            continue
        # avval to'liq nom, keyin birinchi 2 so'z (o'lcham/markasiz)
        short = " ".join(re.findall(r"[^\W\d_]{3,}", q)[:2])
        for query in dict.fromkeys([q, short]):
            if not query:
                continue
            try:
                items = search(query, lang=lang)
            except requests.RequestException:
                continue
            for it in items:
                sc = score(q, it)
                if best is None or sc > best["score"]:
                    best = {"code": it["code"], "name": it["name"], "score": round(sc, 3)}
        if best and best["score"] >= 0.5:
            break
    return best if best and best["score"] >= 0.34 else None
