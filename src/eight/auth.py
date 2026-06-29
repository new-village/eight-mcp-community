from __future__ import annotations

import json
import os
import stat
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

PACKAGE_NAME = "eight-mcp-community"
CONFIG_ENV = "EIGHT_MCP_COMMUNITY_CONFIG"
COOKIE_ENV = "EIGHT_COOKIE"


class AuthStatusClient(Protocol):
    def auth_status_for_cookie(self, cookie: str) -> dict[str, Any]: ...


@dataclass(frozen=True)
class CredentialSource:
    source: str
    cookie: str | None = None
    config_path: Path | None = None


def default_config_path() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg).expanduser() if xdg else Path.home() / ".config"
    return base / PACKAGE_NAME / "config.json"


def config_path() -> Path:
    override = os.environ.get(CONFIG_ENV)
    return Path(override).expanduser() if override else default_config_path()


def _read_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def read_credentials() -> CredentialSource:
    if cookie := os.environ.get(COOKIE_ENV):
        return CredentialSource(source="env:EIGHT_COOKIE", cookie=cookie, config_path=config_path())

    path = config_path()
    data = _read_config(path)
    if cookie := data.get("cookie"):
        return CredentialSource(source="config", cookie=str(cookie), config_path=path)

    return CredentialSource(source="none", config_path=path)


def auth_status(*, client_factory: Callable[[], AuthStatusClient] | None = None) -> dict[str, Any]:
    """Return whether Eight auth is configured and currently usable."""
    creds = read_credentials()
    base: dict[str, Any] = {
        "configured": bool(creds.cookie),
        "authenticated": False,
        "source": creds.source,
        "configPath": str(config_path()),
    }
    if not creds.cookie:
        return {
            **base,
            "status": "setup_required",
            "nextAction": "Run eight_auth_login or eight_set_cookie.",
        }

    base["cookiePreview"] = preview_cookie(creds.cookie)
    try:
        client = client_factory() if client_factory else _default_client()
        live = client.auth_status_for_cookie(creds.cookie)
    except Exception as exc:  # noqa: BLE001 - auth status should be diagnostic, not fatal.
        return {
            **base,
            "status": "auth_failed",
            "errorType": type(exc).__name__,
            "message": str(exc),
            "nextAction": "Run eight_auth_login or eight_set_cookie with a fresh cookie.",
        }

    authenticated = bool(live.get("authenticated"))
    return {
        **base,
        **live,
        "authenticated": authenticated,
        "status": "ok" if authenticated else "auth_failed",
    }


def set_cookie(
    cookie: str,
    *,
    verify: bool = True,
    client_factory: Callable[[], AuthStatusClient] | None = None,
) -> dict[str, Any]:
    """Store a Cookie header in the config file, verifying it by default."""
    if not cookie:
        raise ValueError("Cookie header is required.")

    live: dict[str, Any] = {}
    if verify:
        client = client_factory() if client_factory else _default_client()
        live = client.auth_status_for_cookie(cookie)
        if not live.get("authenticated"):
            raise ValueError("Cookie did not authenticate with Eight.")

    saved = save_cookie(cookie)
    return {"authenticated": bool(live.get("authenticated", False)), **live, **saved}


def save_cookie(cookie: str, path: Path | None = None) -> dict[str, Any]:
    target = path or config_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps({"cookie": cookie}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    try:
        target.chmod(stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass
    return {
        "saved": True,
        "configPath": str(target),
        "cookiePreview": preview_cookie(cookie),
    }


def preview_cookie(cookie: str) -> str:
    compact = " ".join(cookie.split())
    if len(compact) <= 16:
        return "<redacted>"
    return f"{compact[:6]}…{compact[-6:]}"


def _default_client() -> AuthStatusClient:
    from .client import EightClient

    return EightClient()
