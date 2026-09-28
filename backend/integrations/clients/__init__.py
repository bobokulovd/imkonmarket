from .base import MarketplaceClient  # noqa: F401


def client_class(marketplace):
    from .ozon import OzonClient
    from .uzum import UzumClient
    from .wb import WBClient
    from .yandex import YandexClient
    return {"uzum": UzumClient, "ozon": OzonClient, "yandex": YandexClient, "wb": WBClient}[marketplace]


def get_client(account, job=None, session=None):
    return client_class(account.marketplace)(account, job=job, session=session)
