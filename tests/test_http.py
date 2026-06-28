from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace

from eight.http import create_http_session


def test_create_http_session_prefers_curl_cffi_when_available(monkeypatch) -> None:
    calls: list[str | None] = []

    class FakeCurlSession:
        def __init__(self, *, impersonate: str | None = None) -> None:
            calls.append(impersonate)
            self.headers: dict[str, str] = {}

    curl_requests = SimpleNamespace(Session=FakeCurlSession)
    curl_module = ModuleType("curl_cffi")
    curl_module.requests = curl_requests
    monkeypatch.setitem(sys.modules, "curl_cffi", curl_module)

    session = create_http_session()

    assert isinstance(session, FakeCurlSession)
    assert calls == ["chrome"]


def test_create_http_session_falls_back_to_requests(monkeypatch) -> None:
    monkeypatch.setitem(sys.modules, "curl_cffi", None)

    session = create_http_session()

    assert session.__class__.__module__.startswith("requests")
