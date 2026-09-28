"""API kalitlarni shifrlash (Fernet). Kalit env'dan: MARKETPLACE_ENC_KEYS."""
import json

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from django.conf import settings


class EncryptionNotConfigured(Exception):
    pass


def _keys():
    return [k.strip() for k in (settings.MARKETPLACE_ENC_KEYS or "").split(",") if k.strip()]


def configured() -> bool:
    return bool(_keys())


def fernet() -> MultiFernet:
    keys = _keys()
    if not keys:
        raise EncryptionNotConfigured(
            "MARKETPLACE_ENC_KEYS sozlanmagan — marketplace kalitlarini saqlab bo'lmaydi")
    try:
        return MultiFernet([Fernet(k.encode()) for k in keys])
    except (ValueError, TypeError) as e:
        raise EncryptionNotConfigured("MARKETPLACE_ENC_KEYS noto'g'ri formatda (Fernet kalit kerak)") from e


def encrypt(data: dict) -> str:
    return fernet().encrypt(json.dumps(data, separators=(",", ":")).encode()).decode()


def decrypt(token: str) -> dict:
    if not token:
        return {}
    try:
        return json.loads(fernet().decrypt(token.encode()).decode())
    except InvalidToken as e:
        raise EncryptionNotConfigured("Kalitni ochib bo'lmadi: MARKETPLACE_ENC_KEYS o'zgarganmi?") from e


def rotate(token: str) -> str:
    return fernet().rotate(token.encode()).decode()
