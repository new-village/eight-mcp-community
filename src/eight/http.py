from __future__ import annotations

from typing import Any

import requests


def has_cloudflare_transport() -> bool:
    try:
        import curl_cffi  # noqa: F401
    except ImportError:
        return False
    return True


def create_http_session() -> Any:
    """Create an HTTP session, preferring curl_cffi Chrome impersonation if installed."""
    try:
        from curl_cffi import requests as curl_requests
    except ImportError:
        return requests.Session()
    return curl_requests.Session(impersonate="chrome")
