from __future__ import annotations

from typing import Any

from eight import auth
from eight.login_setup import save_cookie_from_password_login


class FakeLoginClient:
    def __init__(self) -> None:
        self.login_calls: list[tuple[str, str]] = []
        self.auth_checked = False

    def login(self, email: str, password: str) -> str:
        self.login_calls.append((email, password))
        return "session_cookie=COOKIE_VALUE"

    def auth_check(self) -> dict[str, Any]:
        self.auth_checked = True
        return {"authenticated": True}


def test_password_login_saves_only_returned_cookie(monkeypatch) -> None:
    saved_values: list[str] = []

    def fake_save_cookie(cookie: str) -> dict[str, Any]:
        saved_values.append(cookie)
        return {"saved": True, "configPath": "/tmp/config.json", "cookiePreview": "session…VALUE"}

    monkeypatch.setattr(auth, "save_cookie", fake_save_cookie)
    client = FakeLoginClient()

    result = save_cookie_from_password_login(
        "person@example.com",
        "super-secret-password",
        client=client,
    )

    assert client.login_calls == [("person@example.com", "super-secret-password")]
    assert client.auth_checked is True
    assert saved_values == ["session_cookie=COOKIE_VALUE"]
    assert "person@example.com" not in str(result)
    assert "super-secret-password" not in str(result)
    assert result["saved"] is True


def test_password_login_requires_both_email_and_password() -> None:
    try:
        save_cookie_from_password_login("person@example.com", "")
    except ValueError as error:
        assert "Both email and password" in str(error)
    else:  # pragma: no cover
        raise AssertionError("Expected ValueError")
