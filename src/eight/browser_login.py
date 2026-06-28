from __future__ import annotations

import time
from typing import Any

from . import auth
from .client import MYHOME_URL
from .errors import AuthRequiredError
from .html import parse_tokens
from .http import create_http_session

LOGIN_URL = "https://8card.net/login"


def run_browser_login(*, headless: bool = False, timeout_seconds: int = 180) -> dict[str, Any]:
    """Open a Playwright browser, let the operator log in, then save 8card cookies."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise AuthRequiredError(
            "Playwright is not installed. Run with an extra dependency, for example: "
            "uvx --from 'eight-mcp-community[browser]' eight-mcp-community auth-login, "
            "or install with: uv tool install 'eight-mcp-community[browser]'."
        ) from exc

    deadline = time.monotonic() + timeout_seconds
    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch(headless=headless)
        except Exception as exc:  # noqa: BLE001
            raise AuthRequiredError(
                "Playwright Chromium is not installed or cannot be launched. Run once on "
                "the same machine: python -m playwright install chromium"
            ) from exc

        context = browser.new_context(locale="ja-JP")
        page = context.new_page()
        page.goto(LOGIN_URL, wait_until="domcontentloaded")

        while time.monotonic() < deadline:
            cookie_header = _cookie_header_from_playwright(context.cookies())
            if cookie_header and _cookie_authenticates(cookie_header):
                browser.close()
                saved = auth.save_cookie(cookie_header)
                return {
                    "authenticated": True,
                    "saved": True,
                    **saved,
                    "message": "Eight authentication configured from browser login.",
                }
            page.wait_for_timeout(1000)

        browser.close()

    raise AuthRequiredError(
        f"Timed out after {timeout_seconds}s waiting for authenticated Eight browser login."
    )


def _cookie_header_from_playwright(cookies: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for cookie in cookies:
        domain = str(cookie.get("domain") or "")
        if "8card.net" not in domain:
            continue
        name = cookie.get("name")
        value = cookie.get("value")
        if name and value:
            parts.append(f"{name}={value}")
    return "; ".join(parts)


def _cookie_authenticates(cookie_header: str) -> bool:
    session = create_http_session()
    session.headers.update(
        {
            "Cookie": cookie_header,
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Accept-Language": "ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7",
        }
    )
    try:
        response = session.get(MYHOME_URL, timeout=15, allow_redirects=True)
    except Exception:
        return False
    if response.status_code != 200:
        return False
    if "/login" in response.url or "ログイン" in response.text[:5000]:
        return False
    tokens = parse_tokens(response.text)
    return bool(tokens.csrf_token or tokens.authenticity_token)
