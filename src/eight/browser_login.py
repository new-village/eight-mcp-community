from __future__ import annotations

import time
from typing import Any

from .client import MYHOME_URL
from .errors import AuthRequiredError
from .html import parse_tokens
from .http import create_http_session, has_cloudflare_transport

LOGIN_URL = "https://8card.net/login"


def run_browser_login(*, headless: bool = False, timeout_seconds: int = 180) -> str:
    """Open Playwright, wait for an authenticated Eight login, and return a Cookie header."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise AuthRequiredError(
            "eight_auth_login requires Playwright. Install the browser extra and Chromium: "
            "python -m pip install --user 'eight-mcp-community[browser]' && "
            "python -m playwright install chromium. Or provide a Cookie header via "
            "eight_set_cookie. If browser login later captures cookies but cannot verify "
            "them, install/use eight-mcp-community[cloudflare]."
        ) from exc

    deadline = time.monotonic() + timeout_seconds
    last_check: dict[str, Any] | None = None
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
            cookie_header = cookie_header_from_playwright(context.cookies())
            if cookie_header:
                last_check = check_cookie_authentication(cookie_header)
            if last_check and last_check["authenticated"]:
                browser.close()
                return cookie_header
            page.wait_for_timeout(1000)

        browser.close()

    raise AuthRequiredError(auth_login_timeout_message(timeout_seconds, last_check))


def cookie_header_from_playwright(cookies: list[dict[str, Any]]) -> str:
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


def cookie_authenticates(cookie_header: str) -> bool:
    return bool(check_cookie_authentication(cookie_header)["authenticated"])


def check_cookie_authentication(cookie_header: str) -> dict[str, Any]:
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
    except Exception as exc:  # noqa: BLE001 - diagnostics only.
        return {
            "authenticated": False,
            "reason": "request_error",
            "errorType": type(exc).__name__,
            "cloudflareTransportAvailable": has_cloudflare_transport(),
        }

    text = response.text or ""
    final_url = str(response.url)
    cloudflare_like = _looks_like_cloudflare(response.status_code, text)
    base = {
        "statusCode": response.status_code,
        "finalUrl": final_url,
        "cloudflareLike": cloudflare_like,
        "cloudflareTransportAvailable": has_cloudflare_transport(),
    }
    if response.status_code != 200:
        return {"authenticated": False, "reason": "http_status", **base}
    if "/login" in final_url or "ログイン" in text[:5000]:
        return {"authenticated": False, "reason": "login_page", **base}
    tokens = parse_tokens(text)
    if not (tokens.csrf_token or tokens.authenticity_token):
        return {"authenticated": False, "reason": "csrf_missing", **base}
    return {"authenticated": True, "reason": "ok", **base}


def auth_login_timeout_message(
    timeout_seconds: int, last_check: dict[str, Any] | None = None
) -> str:
    base = f"Timed out after {timeout_seconds}s waiting for authenticated Eight browser login."
    cloudflare_hint = (
        " If the Playwright browser is already on /myhome, the browser cookie was captured "
        "but verification HTTP likely failed. Install/use eight-mcp-community[cloudflare] "
        "and retry, for example: eight-mcp-community auth-login --timeout-seconds 300."
    )
    if not last_check:
        return base + cloudflare_hint

    bits = [f"reason={last_check.get('reason')}"]
    if last_check.get("statusCode") is not None:
        bits.append(f"status={last_check['statusCode']}")
    if last_check.get("finalUrl"):
        bits.append(f"finalUrl={last_check['finalUrl']}")
    if last_check.get("cloudflareLike") is not None:
        bits.append(f"cloudflareLike={last_check['cloudflareLike']}")
    if last_check.get("cloudflareTransportAvailable") is False:
        bits.append("cloudflareExtraInstalled=False")
    return base + cloudflare_hint + " Last verification: " + ", ".join(bits) + "."


def _looks_like_cloudflare(status_code: int, text: str) -> bool:
    lowered = text[:5000].lower()
    return status_code in {403, 429, 503} or "cloudflare" in lowered or "just a moment" in lowered
