from __future__ import annotations

from eight import mcp_server


def test_only_three_auth_tools_are_exposed() -> None:
    exposed = {
        name
        for name in dir(mcp_server)
        if name.startswith("eight_auth") or name == "eight_set_cookie"
    }

    assert exposed == {"eight_auth_status", "eight_auth_login", "eight_set_cookie"}
    assert not hasattr(mcp_server, "eight_auth_check")
    assert not hasattr(mcp_server, "eight_auth_setup")
    assert not hasattr(mcp_server, "eight_auth_login_browser")
    assert not hasattr(mcp_server, "eight_clear_cookie")
    assert not hasattr(mcp_server, "eight_login_help")


def test_auth_login_delegates_to_browser_login_and_set_cookie(monkeypatch) -> None:
    calls: list[tuple[str, object]] = []

    def fake_run_browser_login(*, headless: bool, timeout_seconds: int) -> str:
        calls.append(("browser", {"headless": headless, "timeout_seconds": timeout_seconds}))
        return "session=from_browser"

    def fake_set_cookie(cookie: str, verify: bool = True) -> dict[str, object]:
        calls.append(("set_cookie", {"cookie": cookie, "verify": verify}))
        return {"saved": True, "authenticated": True}

    monkeypatch.setattr(mcp_server, "run_browser_login", fake_run_browser_login)
    monkeypatch.setattr(mcp_server, "_set_cookie", fake_set_cookie)

    result = mcp_server.eight_auth_login(headless=True, timeoutSeconds=45)

    assert result == {"saved": True, "authenticated": True}
    assert calls == [
        ("browser", {"headless": True, "timeout_seconds": 45}),
        ("set_cookie", {"cookie": "session=from_browser", "verify": True}),
    ]
