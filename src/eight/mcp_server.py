from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from . import auth
from .browser_login import run_browser_login
from .client import EightClient
from .errors import error_detail

mcp = FastMCP("eight-mcp-community")


def _client() -> EightClient:
    return EightClient.from_default_config()


def _set_cookie(cookie: str, verify: bool = True) -> dict[str, Any]:
    return auth.set_cookie(cookie, verify=verify)


@mcp.tool()
def eight_auth_status() -> dict[str, Any]:
    """Check whether Eight authentication is configured and currently usable."""
    return auth.auth_status()


@mcp.tool()
def eight_auth_login(headless: bool = False, timeoutSeconds: int = 180) -> dict[str, Any]:
    """Open a Playwright browser login flow, capture Eight cookies, and save them."""
    try:
        cookie = run_browser_login(headless=headless, timeout_seconds=timeoutSeconds)
        return _set_cookie(cookie, verify=True)
    except Exception as exc:  # noqa: BLE001
        return error_detail(exc)


@mcp.tool()
def eight_set_cookie(cookie: str, verify: bool = True) -> dict[str, Any]:
    """Store a Cookie header in the local MCP config file."""
    try:
        return _set_cookie(cookie, verify=verify)
    except Exception as exc:  # noqa: BLE001
        return error_detail(exc)


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
