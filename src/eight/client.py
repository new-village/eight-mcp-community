from __future__ import annotations

from typing import Any

import requests

from . import auth
from .errors import AuthRequiredError, EightApiError
from .extract import extract_network_people, extract_personal_cards
from .html import parse_tokens
from .http import create_http_session
from .models import CardResult, SearchResult

MYHOME_URL = "https://8card.net/myhome"
SEARCH_PERSONAL_CARDS_URL = "https://8card.net/search_contacts/search_personal_cards"
SEARCH_EIGHT_NETWORKS_URL = "https://8card.net/search_contacts/search_eight_networks"


def forbidden_guidance() -> str:
    return (
        "Eight /myhome returned HTTP 403. Authentication may be missing or expired, "
        "or Eight/Cloudflare may be blocking the plain requests transport. "
        "Run eight_auth_login to refresh cookies, or eight_set_cookie with a valid Cookie header. "
        "If the cookie is valid but 403 persists, install/use eight-mcp-community[cloudflare] "
        "and restart the MCP client."
    )


class EightClient:
    def __init__(self, session: requests.Session | None = None, *, timeout: float = 30) -> None:
        self.session = session or self._make_session()
        self.timeout = timeout

    @classmethod
    def from_default_config(cls, *, timeout: float = 30) -> EightClient:
        client = cls(timeout=timeout)
        client.configure_auth()
        return client

    def configure_auth(self) -> auth.CredentialSource:
        creds = auth.read_credentials()
        if creds.cookie:
            self.session.headers["Cookie"] = creds.cookie
        return creds

    def auth_status_for_cookie(self, cookie: str) -> dict[str, Any]:
        self.session.headers["Cookie"] = cookie
        csrf = self.ensure_auth()
        return {"authenticated": True, "csrfAvailable": bool(csrf)}

    def ensure_auth(self) -> str:
        csrf = self.get_csrf()
        if csrf:
            return csrf
        raise AuthRequiredError(
            "Eight authentication is not configured or has expired. "
            "Run eight_auth_login to log in with Playwright, or eight_set_cookie with a "
            "valid Cookie header."
        )

    def get_csrf(self) -> str | None:
        response = self.session.get(MYHOME_URL, timeout=self.timeout, allow_redirects=True)
        if response.status_code == 403:
            raise AuthRequiredError(forbidden_guidance())
        response.raise_for_status()
        if "/login" in response.url or "ログイン" in response.text[:5000]:
            return None
        tokens = parse_tokens(response.text)
        return tokens.csrf_token or tokens.authenticity_token

    def search_person(
        self,
        keyword: str,
        *,
        per_page: int = 100,
        network_limit: int = 20,
        always_network: bool = False,
    ) -> SearchResult:
        personal = self.search_registered_cards(keyword, per_page=per_page)
        network: list[CardResult] = []
        should_search_network = always_network or not personal
        if should_search_network:
            network = self.search_network_people(keyword, limit=network_limit)
        return SearchResult(
            status="ok",
            query=keyword,
            searched={"personal_cards": True, "eight_networks": should_search_network},
            personal=personal,
            network=network,
        )

    def search_registered_cards(self, keyword: str, *, per_page: int = 100) -> list[CardResult]:
        csrf = self.ensure_auth()
        data = self._post_json(
            SEARCH_PERSONAL_CARDS_URL,
            {"keyword": keyword, "page": 1, "sort": 5, "per_page": per_page},
            csrf,
        )
        return extract_personal_cards(data, query=keyword)

    def search_network_people(self, keyword: str, *, limit: int = 20) -> list[CardResult]:
        csrf = self.ensure_auth()
        data = self._post_json(SEARCH_EIGHT_NETWORKS_URL, {"keyword": keyword}, csrf)
        return extract_network_people(data, limit, query=keyword)

    def _post_json(self, url: str, payload: dict[str, Any], csrf: str) -> dict[str, Any]:
        response = self.session.post(
            url,
            json=payload,
            headers={
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Content-Type": "application/json",
                "X-CSRF-Token": csrf,
                "X-Requested-With": "XMLHttpRequest",
                "Referer": "https://8card.net/search_contacts",
            },
            timeout=self.timeout,
            allow_redirects=True,
        )
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        if "application/json" not in content_type:
            raise EightApiError(
                "Eight API returned non-JSON response: "
                f"status={response.status_code} url={response.url}"
            )
        data = response.json()
        if not isinstance(data, dict):
            raise EightApiError("Eight API returned a JSON value that was not an object.")
        return data

    @staticmethod
    def _make_session() -> requests.Session:
        session = create_http_session()
        session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                "Accept-Language": "ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7",
                "Sec-Ch-Ua": '"Google Chrome";v="125", "Chromium";v="125", "Not.A/Brand";v="24"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"macOS"',
            }
        )
        return session
