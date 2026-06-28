from __future__ import annotations

import re

from eight import setup_help
from eight.setup_help import auth_setup_help, browser_login_unavailable_response


def test_auth_setup_help_recommends_cookie_first_and_browser_extra() -> None:
    help_payload = auth_setup_help(command="/Users/new-village/.local/bin/eight-mcp-community")

    assert help_payload["status"] == "setup_required"
    assert help_payload["recommendedFirst"] == "set_cookie"
    assert (
        "/Users/new-village/.local/bin/eight-mcp-community set-cookie"
        in help_payload["commands"]["setCookie"]
    )
    assert "auth-login" not in help_payload["commands"]["setCookie"]
    assert "auth-check" not in help_payload["commands"]
    assert "auth-check" in help_payload["commands"]["verifyAfterSetup"]
    assert "after" in help_payload["commands"]["verifyAfterSetup"].lower()
    assert "eight-mcp-community[browser]" in help_payload["commands"]["installBrowserExtra"]
    assert "python -m playwright install chromium" in help_payload["commands"]["installChromium"]
    assert any("restart" in note.lower() for note in help_payload["notes"])


def test_browser_login_unavailable_response_is_not_a_raw_exception() -> None:
    response = browser_login_unavailable_response(command="eight-mcp-community")

    assert response["status"] == "setup_required"
    assert response["authenticated"] is False
    assert response["browserLoginAvailable"] is False
    assert response["recommendedFirst"] == "set_cookie"
    assert "Traceback" not in str(response)
    assert (
        "pip install --user 'eight-mcp-community[browser]'"
        in response["commands"]["installBrowserExtra"]
    )


def test_browser_login_availability_requires_importable_sync_api(monkeypatch) -> None:
    def fake_import_module(name: str) -> None:
        assert name == "playwright.sync_api"
        raise ImportError("No module named 'playwright'")

    monkeypatch.setattr(setup_help, "import_module", fake_import_module)

    assert setup_help.is_browser_login_available() is False


def test_auth_setup_help_includes_agent_install_message_template() -> None:
    help_payload = auth_setup_help(command="/Users/new-village/.local/bin/eight-mcp-community")

    message = help_payload["agentPostInstallMessage"]
    assert "auth-setup" in message
    assert "auth-check は設定後の確認用" in message
    assert "set-cookie '<COOKIE_HEADER>'" in message
    assert "set-cookie 'your <http" not in message


def test_auth_setup_help_avoids_slack_auto_link_placeholders() -> None:
    help_payload = auth_setup_help(command="/Users/new-village/.local/bin/eight-mcp-community")
    rendered = str(help_payload)

    assert "8card.net" not in rendered
    assert "you@example.com" not in rendered
    assert "<http" not in rendered
    assert "mailto:" not in rendered
    assert re.search(r"[\w.+-]+@[\w.-]+", rendered) is None
