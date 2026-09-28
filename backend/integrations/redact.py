"""Kalitlarni log va xato matnlaridan tozalash.

Qoida: API kalit hech qayerda (log, SyncLog, API javobi, admin) to'liq ko'rinmaydi.
"""
import logging
import re

# Sarlavha ko'rinishidagi kalitlar: "Api-Key: xxx", "Authorization: xxx", "Client-Id: xxx"
_HEADER_RE = re.compile(r"(?i)\b(api[-_ ]?key|authorization|client[-_ ]?id|token|bearer)(\"?\s*[:=]\s*\"?|\s+)([^\s\"',;}]+)")
# Uzun tasodifiy satrlar (JWT, hex, base64) — 24+ belgi
_LONG_RE = re.compile(r"\b[A-Za-z0-9_\-]{24,}(?:\.[A-Za-z0-9_\-]{8,}){0,2}\b")

_known: set[str] = set()


def register_secret(value: str):
    """Worker ichida ishlatilayotgan kalitni ro'yxatga oladi — u har qanday matndan o'chiriladi."""
    if value and len(value) >= 6:
        _known.add(value)


def mask(value: str | None) -> str:
    if not value:
        return ""
    return "••••" + value[-4:]


def redact(text) -> str:
    if text is None:
        return ""
    s = str(text)
    for k in list(_known):
        if k in s:
            s = s.replace(k, mask(k))
    s = _HEADER_RE.sub(lambda m: f"{m.group(1)}{m.group(2)}••••", s)
    s = _LONG_RE.sub(lambda m: "••••" + m.group(0)[-4:], s)
    return s


class RedactFilter(logging.Filter):
    def filter(self, record):
        try:
            msg = record.getMessage()
        except Exception:  # noqa: BLE001
            return True
        clean = redact(msg)
        if clean != msg:
            record.msg, record.args = clean, ()
        return True
