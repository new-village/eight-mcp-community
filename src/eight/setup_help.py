from __future__ import annotations

from importlib import import_module
from typing import Any

from . import auth

DEFAULT_COMMAND = "eight-mcp-community"


def is_browser_login_available() -> bool:
    try:
        import_module("playwright.sync_api")
    except ImportError:
        return False
    return True


def auth_setup_help(*, command: str = DEFAULT_COMMAND) -> dict[str, Any]:
    return {
        "status": "setup_required",
        "authenticated": False,
        "recommendedFirst": "set_cookie",
        "summary": (
            "Base installs do not include Playwright. Configure a Cookie header first; "
            "use browser login only after installing the optional [browser] extra."
        ),
        "commands": {
            "setCookie": f"{command} set-cookie 'your 8card.net Cookie header'",
            "passwordLogin": f"{command} set-cookie --email you@example.com --password '...'",
            "authCheck": f"{command} auth-check",
            "installBrowserExtra": "python -m pip install --user 'eight-mcp-community[browser]'",
            "installChromium": "python -m playwright install chromium",
            "browserLoginAfterExtra": f"{command} auth-login",
            "installCloudflareExtra": (
                "python -m pip install --user 'eight-mcp-community[cloudflare]'"
            ),
        },
        "notes": [
            "Do not paste cookies, passwords, or raw contact data into prompts or logs.",
            "The --email/--password flow uses credentials only for login and stores only cookies.",
            "If valid cookies still get 403, install/use the [cloudflare] extra.",
            "Restart Codex or the MCP client after package, dependency, auth, "
            "or MCP config changes.",
        ],
        "configFile": str(auth.config_path()),
    }


def browser_login_unavailable_response(*, command: str = DEFAULT_COMMAND) -> dict[str, Any]:
    payload = auth_setup_help(command=command)
    payload.update(
        {
            "browserLoginAvailable": False,
            "message": (
                "auth-login requires the optional Playwright browser dependency. "
                "This is not installed in the base package. Use set-cookie first, "
                "or install the [browser] extra before running auth-login."
            ),
        }
    )
    return payload
