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
