import os
from typing import Dict, Tuple

from .http_client import HttpxClient


_clients: Dict[tuple, HttpxClient] = {}


def _proxies_key(proxies: Dict[str, str]) -> Tuple[Tuple[str, str], ...]:
    if not proxies:
        return ()
    items = sorted((proxies or {}).items())
    return tuple(items)


def _http2_available() -> bool:
    try:
        import h2  # noqa: F401
        return True
    except ImportError:
        return False


def get_http_client(proxies: Dict[str, str]) -> HttpxClient:
    http2_env = os.environ.get('WHOOGLE_HTTP2', '1').lower()
    http2_enabled = http2_env in ('1', 'true', 't', 'yes', 'y') and _http2_available()

    key = (_proxies_key(proxies or {}), http2_enabled)
    client = _clients.get(key)
    if client is not None:
        return client
    client = HttpxClient(proxies=proxies or None, http2=http2_enabled)
    _clients[key] = client
    return client


def close_all_clients() -> None:
    for client in list(_clients.values()):
        try:
            client.close()
        except Exception:
            pass
    _clients.clear()
