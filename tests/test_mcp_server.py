from __future__ import annotations

from types import SimpleNamespace

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


def test_search_tool_surface_is_intentionally_small() -> None:
    assert hasattr(mcp_server, "eight_search_person")
    assert hasattr(mcp_server, "eight_fetch_person")
    assert not hasattr(mcp_server, "eight_search_registered_cards")
    assert not hasattr(mcp_server, "eight_search_network_people")


def test_auth_login_runs_cli_in_subprocess_to_avoid_asyncio_playwright_conflict(
    monkeypatch,
) -> None:
    calls: list[dict[str, object]] = []

    def fake_run(command, **kwargs):  # noqa: ANN001
        calls.append({"command": command, **kwargs})
        return SimpleNamespace(
            returncode=0,
            stdout='{"authenticated": true, "saved": true}\n',
            stderr="",
        )

    monkeypatch.setattr(mcp_server.subprocess, "run", fake_run)

    result = mcp_server.eight_auth_login(headless=True, timeoutSeconds=45)

    assert result == {"authenticated": True, "saved": True}
    command = calls[0]["command"]
    assert command[:3] == [mcp_server.sys.executable, "-m", "eight"]
    assert "auth-login" in command
    assert "--headless" in command
    assert "--timeout-seconds" in command
    assert calls[0]["timeout"] == 75


def test_auth_login_subprocess_reports_non_json_failure(monkeypatch) -> None:
    def fake_run(_command, **_kwargs):  # noqa: ANN001
        return SimpleNamespace(returncode=1, stdout="", stderr="boom")

    monkeypatch.setattr(mcp_server.subprocess, "run", fake_run)

    result = mcp_server.eight_auth_login()

    assert result["error"] == "auth_login_failed"
    assert "boom" in result["message"]
