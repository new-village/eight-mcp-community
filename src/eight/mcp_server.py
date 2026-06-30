from __future__ import annotations

import json
import subprocess
import sys
from typing import Any, Literal

from mcp.server.fastmcp import FastMCP

from . import auth
from .client import EightClient
from .errors import error_detail

mcp = FastMCP("eight-mcp-community")


def _client() -> EightClient:
    return EightClient.from_default_config()


def _set_cookie(cookie: str, verify: bool = True) -> dict[str, Any]:
    return auth.set_cookie(cookie, verify=verify)


def _run_auth_login_subprocess(
    *, headless: bool = False, timeout_seconds: int = 180
) -> dict[str, Any]:
    command = [
        sys.executable,
        "-m",
        "eight",
        "auth-login",
        "--timeout-seconds",
        str(timeout_seconds),
    ]
    if headless:
        command.append("--headless")
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout_seconds + 30,
        check=False,
    )
    if completed.stdout.strip():
        try:
            return json.loads(completed.stdout)
        except json.JSONDecodeError:
            pass
    if completed.returncode != 0:
        message = (completed.stderr or completed.stdout or "auth-login subprocess failed").strip()
        return {"error": "auth_login_failed", "type": "SubprocessError", "message": message}
    return {
        "error": "auth_login_failed",
        "type": "SubprocessError",
        "message": "auth-login subprocess did not return JSON",
    }


@mcp.tool()
def eight_auth_status() -> dict[str, Any]:
    """Check whether Eight authentication is configured and currently usable."""
    return auth.auth_status()


@mcp.tool()
def eight_auth_login(headless: bool = False, timeoutSeconds: int = 180) -> dict[str, Any]:
    """Run CLI browser login in a subprocess, capture Eight cookies, and save them."""
    try:
        return _run_auth_login_subprocess(headless=headless, timeout_seconds=timeoutSeconds)
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
    source: Literal["registered", "all"] = "registered",
) -> dict[str, Any]:
    """Search registered Eight cards by default; source='all' also includes public network."""
    try:
        return (
            _client()
            .search_person(
                query,
                per_page=perPage,
                network_limit=networkLimit,
                source=source,
            )
            .to_safe_dict()
        )
    except Exception as exc:  # noqa: BLE001
        return error_detail(exc)


@mcp.tool()
def eight_fetch_person(id: str) -> dict[str, Any]:
    """Fetch detailed contact/profile fields for an id returned by eight_search_person."""
    try:
        return {"status": "ok", "person": _client().fetch_person(id).to_safe_dict()}
    except Exception as exc:  # noqa: BLE001
        return error_detail(exc)


def run() -> None:
    mcp.run(transport="stdio")
