from django.core.checks import Warning, register

from .crypto import EncryptionNotConfigured, configured, fernet


@register()
def enc_key_check(app_configs, **kwargs):
    if not configured():
        return [Warning("MARKETPLACE_ENC_KEYS bo'sh: marketplace kabinetlarini ulab bo'lmaydi",
                        hint="Fernet kalit yarating va env'ga qo'ying", id="integrations.W001")]
    try:
        fernet()
    except EncryptionNotConfigured as e:
        return [Warning(str(e), id="integrations.W002")]
    return []
