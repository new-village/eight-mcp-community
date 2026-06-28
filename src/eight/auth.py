from __future__ import annotations

import json
import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PACKAGE_NAME = "eight-mcp-community"
CONFIG_ENV = "EIGHT_MCP_COMMUNITY_CONFIG"
COOKIE_ENV = "EIGHT_COOKIE"
SESSION_COOKIE_ENV = "EIGHT_SESSION_COOKIE"
COOKIE_FILE_ENV = "EIGHT_COOKIE_FILE"
LEGACY_COOKIE_FILE = Path("/opt/data/private/eight/cookies.txt")


@dataclass(frozen=True)
class CredentialSource:
    source: str
    cookie: str | None = None
    cookie_file: Path | None = None
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
        return CredentialSource(source="env:EIGHT_COOKIE", cookie=cookie)
    if cookie := os.environ.get(SESSION_COOKIE_ENV):
        return CredentialSource(source="env:EIGHT_SESSION_COOKIE", cookie=cookie)

    path = config_path()
    data = _read_config(path)
    if cookie := data.get("cookie"):
        return CredentialSource(source="config", cookie=str(cookie), config_path=path)

    if cookie_file := os.environ.get(COOKIE_FILE_ENV):
        return CredentialSource(source="cookie_file", cookie_file=Path(cookie_file).expanduser())
    if LEGACY_COOKIE_FILE.exists():
        return CredentialSource(source="legacy_cookie_file", cookie_file=LEGACY_COOKIE_FILE)

    if os.environ.get("EIGHT_EMAIL") and os.environ.get("EIGHT_PASSWORD"):
        return CredentialSource(source="env:EIGHT_EMAIL_PASSWORD", config_path=path)

    return CredentialSource(source="none", config_path=path)


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


def clear_stored_cookie(path: Path | None = None) -> dict[str, Any]:
    target = path or config_path()
    if not target.exists():
        return {"cleared": False, "configPath": str(target), "message": "No config file exists."}
    data = _read_config(target)
    if "cookie" not in data:
        return {"cleared": False, "configPath": str(target), "message": "No cookie was stored."}
    data.pop("cookie", None)
    if data:
        target.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    else:
        target.unlink()
    return {"cleared": True, "configPath": str(target)}


def auth_status() -> dict[str, Any]:
    creds = read_credentials()
    data: dict[str, Any] = {
        "configured": creds.source != "none",
        "source": creds.source,
        "configPath": str(config_path()),
    }
    if creds.cookie:
        data["cookiePreview"] = preview_cookie(creds.cookie)
    if creds.cookie_file:
        data["cookieFile"] = str(creds.cookie_file)
        data["cookieFileExists"] = creds.cookie_file.exists()
    return data


def preview_cookie(cookie: str) -> str:
    compact = " ".join(cookie.split())
    if len(compact) <= 16:
        return "<redacted>"
    return f"{compact[:6]}…{compact[-6:]}"
