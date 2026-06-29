from __future__ import annotations

from types import SimpleNamespace

from eight import browser_login


class FakeSession:
    def __init__(self, response: SimpleNamespace) -> None:
        self.response = response
        self.headers: dict[str, str] = {}

    def get(self, *_args, **_kwargs) -> SimpleNamespace:
        return self.response


def _install_fake_session(monkeypatch, response: SimpleNamespace) -> None:
    monkeypatch.setattr(browser_login, "create_http_session", lambda: FakeSession(response))


def test_cookie_authentication_requires_successful_status(monkeypatch) -> None:
    _install_fake_session(
        monkeypatch,
        SimpleNamespace(status_code=403, url="https://8card.net/myhome", text="Forbidden"),
    )

    assert browser_login.cookie_authenticates("session=abc") is False


def test_cookie_authentication_requires_csrf_token(monkeypatch) -> None:
    _install_fake_session(
        monkeypatch,
        SimpleNamespace(status_code=200, url="https://8card.net/myhome", text="<html>home</html>"),
    )

    assert browser_login.cookie_authenticates("session=abc") is False


def test_cookie_authentication_accepts_myhome_with_csrf_token(monkeypatch) -> None:
    _install_fake_session(
        monkeypatch,
        SimpleNamespace(
            status_code=200,
            url="https://8card.net/myhome",
            text='<html><meta name="csrf-token" content="token123"></html>',
        ),
    )

    assert browser_login.cookie_authenticates("session=abc") is True


def test_cookie_authentication_diagnostics_include_cloudflare_like_failure(monkeypatch) -> None:
    _install_fake_session(
        monkeypatch,
        SimpleNamespace(
            status_code=403,
            url="https://8card.net/myhome",
            text="<html><title>Just a moment...</title>Cloudflare</html>",
        ),
    )

    result = browser_login.check_cookie_authentication("session=abc")

    assert result["authenticated"] is False
    assert result["reason"] == "http_status"
    assert result["statusCode"] == 403
    assert result["finalUrl"] == "https://8card.net/myhome"
    assert result["cloudflareLike"] is True


def test_auth_login_timeout_message_points_to_cloudflare_extra_when_cookie_was_seen() -> None:
    message = browser_login.auth_login_timeout_message(
        180,
        {
            "authenticated": False,
            "reason": "http_status",
            "statusCode": 403,
            "finalUrl": "https://8card.net/myhome",
            "cloudflareLike": True,
        },
    )

    assert "browser cookie was captured" in message
    assert "verification HTTP" in message
    assert "eight-mcp-community[cloudflare]" in message
    assert "status=403" in message
