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
    verify_command = f"{command} auth-check"
    set_cookie_command = f"{command} set-cookie 'your 8card.net Cookie header'"
    password_login_command = f"{command} set-cookie --email you@example.com --password '...'"
    return {
        "status": "setup_required",
        "authenticated": False,
        "recommendedFirst": "set_cookie",
        "summary": (
            "Base installs do not include Playwright. Configure a Cookie header first; "
            "use browser login only after installing the optional [browser] extra."
        ),
        "commands": {
            "setCookie": set_cookie_command,
            "passwordLogin": password_login_command,
            "verifyAfterSetup": f"Run after set-cookie/password login succeeds: {verify_command}",
            "installBrowserExtra": "python -m pip install --user 'eight-mcp-community[browser]'",
            "installChromium": "python -m playwright install chromium",
            "browserLoginAfterExtra": f"{command} auth-login",
            "installCloudflareExtra": (
                "python -m pip install --user 'eight-mcp-community[cloudflare]'"
            ),
        },
        "notes": [
            "Do not paste cookies, passwords, or raw contact data into prompts or logs.",
            "auth-check verifies an already-configured cookie; it does not configure auth.",
            "The --email/--password flow uses credentials only for login and stores only cookies.",
            "If valid cookies still get 403, install/use the [cloudflare] extra.",
            "Restart Codex or the MCP client after package, dependency, auth, "
            "or MCP config changes.",
        ],
        "agentPostInstallMessage": agent_post_install_message(
            command=command,
            set_cookie_command=set_cookie_command,
            password_login_command=password_login_command,
            verify_command=verify_command,
        ),
        "configFile": str(auth.config_path()),
    }


def agent_post_install_message(
    *,
    command: str,
    set_cookie_command: str,
    password_login_command: str,
    verify_command: str,
) -> str:
    return (
        "Eight MCP registration is installed, but Eight authentication is not configured yet.\n"
        f"First run setup guidance: {command} auth-setup\n"
        "To configure auth, choose one setup path:\n"
        f"1. Cookie header: {set_cookie_command}\n"
        f"2. Password login: {password_login_command}\n"
        f"auth-check は設定後の確認用です: {verify_command}\n"
        "If auth-check returns 403 even with a valid cookie, use/install "
        "eight-mcp-community[cloudflare]. Restart Codex or the MCP client after changes."
    )


def forbidden_guidance(*, command: str = DEFAULT_COMMAND) -> str:
    setup = auth_setup_help(command=command)
    return (
        "Eight /myhome returned HTTP 403. Authentication may be missing/expired, "
        "or Eight/Cloudflare may be blocking the plain requests transport. "
        f"Run setup guidance: {command} auth-setup. "
        f"Configure auth with: {setup['commands']['setCookie']} or "
        f"{setup['commands']['passwordLogin']}. "
        "If the cookie is valid but 403 persists, install/use "
        "eight-mcp-community[cloudflare] and restart Codex/the MCP client."
    )


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
