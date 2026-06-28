from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from . import auth
from .browser_login import run_browser_login
from .client import EightClient
from .errors import error_detail
from .login_setup import save_cookie_from_password_login

mcp = FastMCP("eight-mcp-community")


def _client() -> EightClient:
    return EightClient.from_default_config()


@mcp.tool()
def eight_auth_status() -> dict[str, Any]:
    """Check whether Eight authentication is configured."""
    return auth.auth_status()


@mcp.tool()
def eight_auth_check() -> dict[str, Any]:
    """Verifies whether configured Eight authentication can access /myhome."""
    try:
        return _client().auth_check()
    except Exception as exc:  # noqa: BLE001 - MCP should return structured errors.
        return error_detail(exc)


@mcp.tool()
def eight_set_cookie(
    cookie: str | None = None,
    verify: bool = True,
    email: str | None = None,
    password: str | None = None,
) -> dict[str, Any]:
    """Store a Cookie header, or log in with email/password and save cookies."""
    try:
        if cookie:
            if verify:
                client = EightClient()
                client.session.headers["Cookie"] = cookie
                client.auth_check()
            return auth.save_cookie(cookie)

        if email or password:
            return save_cookie_from_password_login(email or "", password or "")

        raise ValueError("Provide cookie, or email and password.")
    except Exception as exc:  # noqa: BLE001
        return error_detail(exc)


@mcp.tool()
def eight_auth_login_browser(headless: bool = False, timeoutSeconds: int = 180) -> dict[str, Any]:
    """Open a Playwright browser login flow and save Eight cookies locally."""
    try:
        return run_browser_login(headless=headless, timeout_seconds=timeoutSeconds)
    except Exception as exc:  # noqa: BLE001
        return error_detail(exc)


@mcp.tool()
def eight_clear_cookie() -> dict[str, Any]:
    """Delete the config-file Eight cookie."""
    try:
        return auth.clear_stored_cookie()
    except Exception as exc:  # noqa: BLE001
        return error_detail(exc)


@mcp.tool()
def eight_login_help() -> dict[str, Any]:
    """Explains supported eight-mcp-community authentication setup paths."""
    return {
        "recommended": (
            "For servers and private agents, provide EIGHT_COOKIE or call "
            "eight_set_cookie with a trusted 8card.net Cookie header."
        ),
        "configFile": str(auth.config_path()),
        "env": [
            "EIGHT_COOKIE",
            "EIGHT_SESSION_COOKIE",
            "EIGHT_MCP_COMMUNITY_CONFIG",
            "EIGHT_COOKIE_FILE",
            "Install/use eight-mcp-community[cloudflare] for curl_cffi "
            "Chrome impersonation when valid cookies hit 403",
            "eight_set_cookie email/password arguments or CLI --email/--password",
            "eight_auth_login_browser / CLI auth-login for Playwright browser login",
        ],
        "cli": [
            "uvx eight-mcp-community auth-status",
            "uvx eight-mcp-community set-cookie 'Cookie header'",
            "uvx eight-mcp-community set-cookie --email you@example.com --password '...'",
            "uvx --from 'eight-mcp-community[cloudflare]' eight-mcp-community serve",
            "uvx --from 'eight-mcp-community[browser]' eight-mcp-community auth-login",
            "uvx eight-mcp-community auth-check",
            "uvx eight-mcp-community clear-cookie",
        ],
        "privacy": (
            "Do not paste cookies into prompts or logs. Use MCP tool arguments, "
            "env, config files, or a secret manager."
        ),
    }


@mcp.tool()
def eight_search_person(
    query: str,
    perPage: int = 100,
    networkLimit: int = 20,
    alwaysNetwork: bool = False,
) -> dict[str, Any]:
    """Search registered cards first, then public network only if needed."""
    try:
        return (
            _client()
            .search_person(
                query,
                per_page=perPage,
                network_limit=networkLimit,
                always_network=alwaysNetwork,
            )
            .to_safe_dict()
        )
    except Exception as exc:  # noqa: BLE001
        return error_detail(exc)


@mcp.tool()
def eight_search_registered_cards(query: str, perPage: int = 100) -> dict[str, Any]:
    """Searches only the authenticated user's registered/exchanged Eight business cards."""
    try:
        rows = _client().search_registered_cards(query, per_page=perPage)
        return {
            "status": "ok",
            "query": query,
            "searched": {"personal_cards": True, "eight_networks": False},
            "personal": [row.to_safe_dict() for row in rows],
            "network": [],
        }
    except Exception as exc:  # noqa: BLE001
        return error_detail(exc)


@mcp.tool()
def eight_search_network_people(query: str, limit: int = 20) -> dict[str, Any]:
    """Search only public Eight network people results."""
    try:
        rows = _client().search_network_people(query, limit=limit)
        return {
            "status": "ok",
            "query": query,
            "searched": {"personal_cards": False, "eight_networks": True},
            "personal": [],
            "network": [row.to_safe_dict() for row in rows],
        }
    except Exception as exc:  # noqa: BLE001
        return error_detail(exc)


def run() -> None:
    mcp.run(transport="stdio")
