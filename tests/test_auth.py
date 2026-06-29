from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

from eight import auth


class FakeStatusClient:
    def __init__(self, *, authenticated: bool = True) -> None:
        self.authenticated = authenticated
        self.cookies_checked: list[str] = []

    def auth_status_for_cookie(self, cookie: str) -> dict[str, Any]:
        self.cookies_checked.append(cookie)
        return {"authenticated": self.authenticated, "csrfAvailable": self.authenticated}


def _only_test_config(monkeypatch, path) -> None:
    monkeypatch.setenv("EIGHT_MCP_COMMUNITY_CONFIG", str(path))
    monkeypatch.delenv("EIGHT_COOKIE", raising=False)


def test_auth_status_reports_setup_required_when_config_cookie_is_missing(
    tmp_path, monkeypatch
) -> None:
    path = tmp_path / "config.json"
    _only_test_config(monkeypatch, path)
    client = FakeStatusClient()

    status = auth.auth_status(client_factory=lambda: client)

    assert status == {
        "configured": False,
        "authenticated": False,
        "status": "setup_required",
        "source": "none",
        "configPath": str(path),
        "nextAction": "Run eight_auth_login or eight_set_cookie.",
    }
    assert client.cookies_checked == []


def test_auth_status_checks_config_cookie_against_eight(tmp_path, monkeypatch) -> None:
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"cookie": "foo=bar; session=longvalue"}), encoding="utf-8")
    _only_test_config(monkeypatch, path)
    client = FakeStatusClient(authenticated=True)

    status = auth.auth_status(client_factory=lambda: client)

    assert status["configured"] is True
    assert status["authenticated"] is True
    assert status["status"] == "ok"
    assert status["source"] == "config"
    assert status["configPath"] == str(path)
    assert status["cookiePreview"] == "foo=ba…gvalue"
    assert client.cookies_checked == ["foo=bar; session=longvalue"]


def test_auth_status_reports_expired_cookie_without_leaking_cookie(tmp_path, monkeypatch) -> None:
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"cookie": "foo=bar; session=expiredvalue"}), encoding="utf-8")
    _only_test_config(monkeypatch, path)

    def failing_factory() -> Any:
        return SimpleNamespace(
            auth_status_for_cookie=lambda _cookie: (_ for _ in ()).throw(
                RuntimeError("login failed")
            )
        )

    status = auth.auth_status(client_factory=failing_factory)

    assert status["configured"] is True
    assert status["authenticated"] is False
    assert status["status"] == "auth_failed"
    assert status["nextAction"] == "Run eight_auth_login or eight_set_cookie with a fresh cookie."
    assert "expiredvalue" not in str(status)


def test_save_cookie_overwrites_config_cookie(tmp_path, monkeypatch) -> None:
    path = tmp_path / "config.json"
    _only_test_config(monkeypatch, path)

    saved = auth.save_cookie("foo=bar; baz=qux")
    auth.save_cookie("new=session")

    assert saved["saved"] is True
    assert json.loads(path.read_text(encoding="utf-8"))["cookie"] == "new=session"
