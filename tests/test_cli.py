from __future__ import annotations

import json

from eight import cli


def test_auth_setup_command_prints_guided_setup(capsys) -> None:
    cli.main(["auth-setup"])

    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "setup_required"
    assert payload["recommendedFirst"] == "set_cookie"
    assert "set-cookie" in payload["commands"]["setCookie"]


def test_auth_login_without_browser_extra_prints_guided_setup(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli, "is_browser_login_available", lambda: False)

    cli.main(["auth-login"])

    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "setup_required"
    assert payload["browserLoginAvailable"] is False
    assert payload["recommendedFirst"] == "set_cookie"
    assert "eight-mcp-community[browser]" in payload["commands"]["installBrowserExtra"]
