from __future__ import annotations

from typing import Any

import requests


def create_http_session() -> Any:
    """Create an HTTP session, preferring curl_cffi Chrome impersonation if installed."""
    try:
        from curl_cffi import requests as curl_requests
    except ImportError:
        return requests.Session()
    return curl_requests.Session(impersonate="chrome")
