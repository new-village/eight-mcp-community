from __future__ import annotations

import hashlib
import hmac
import re
from dataclasses import replace
from typing import Any

import requests

from . import auth
from .errors import AuthRequiredError, EightApiError
from .extract import (
    extract_network_companies,
    extract_network_people,
    extract_personal_cards,
    first_value,
)
from .html import parse_tokens
from .http import create_http_session
from .models import CardResult, CompanyResult, PersonDetail, SearchResult, SearchSource

MYHOME_URL = "https://8card.net/myhome"
SEARCH_PERSONAL_CARDS_URL = "https://8card.net/search_contacts/search_personal_cards"
SEARCH_EIGHT_NETWORKS_URL = "https://8card.net/search_contacts/search_eight_networks"
PERSON_FRIEND_CARD_URL = "https://8card.net/people/{person_id}/friend_card.json"
PUBLIC_PROFILE_URL = "https://8card.net/p/{person_id}.json"

DEFAULT_PER_PAGE = 100
MAX_PER_PAGE = 500
DEFAULT_NETWORK_LIMIT = 20
MAX_NETWORK_LIMIT = 100
FETCH_ID_RE = re.compile(r"^(registered|network):(\d+):([0-9a-f]{16})$")
UNSIGNED_PERSON_ID_RE = re.compile(r"^(registered|network):(\d+)$")


def forbidden_guidance() -> str:
    return (
        "Eight /myhome returned HTTP 403. Authentication may be missing or expired, "
        "or Eight/Cloudflare may be blocking the plain requests transport. "
        "Run eight_auth_login to refresh cookies, or eight_set_cookie with a valid Cookie header. "
        "If the cookie is valid but 403 persists, install/use eight-mcp-community[cloudflare] "
        "and restart the MCP client."
    )


class EightClient:
    """Small reusable client for Eight's private web endpoints.

    MCP tools and the CLI both call this class. Keeping endpoint logic here makes
    the public surfaces thin and keeps privacy decisions testable without an LLM.
    """

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
        per_page: int = DEFAULT_PER_PAGE,
        network_limit: int = DEFAULT_NETWORK_LIMIT,
        source: SearchSource = "registered",
    ) -> SearchResult:
        """Search registered cards, optionally including public-network buckets.

        Defaulting to registered cards keeps private/contact searches fast and
        context-light. `source="all"` is an explicit opt-in to public-network
        people and company hits, returned in separate arrays so agents do not
        confuse corporations with individuals.
        """
        keyword = validate_keyword(keyword)
        per_page = validate_int_range("per_page", per_page, minimum=1, maximum=MAX_PER_PAGE)
        network_limit = validate_int_range(
            "network_limit", network_limit, minimum=0, maximum=MAX_NETWORK_LIMIT
        )
        if source not in {"registered", "all"}:
            raise ValueError("source must be one of: registered, all")

        personal = sign_card_ids(
            self.search_registered_cards(keyword, per_page=per_page), secret=self._id_secret()
        )
        network: list[CardResult] = []
        network_companies: list[CompanyResult] = []
        should_search_network = source == "all" and network_limit > 0

        if should_search_network:
            network_data = self.search_network(keyword)
            network = sign_card_ids(
                extract_network_people(network_data, network_limit, query=keyword),
                secret=self._id_secret(),
            )
            network_companies = extract_network_companies(
                network_data, network_limit, query=keyword
            )

        return SearchResult(
            status="ok",
            query=keyword,
            searched={
                "personal_cards": True,
                "eight_networks": should_search_network,
            },
            personal=personal,
            network=network,
            network_companies=network_companies,
        )

    def search_registered_cards(
        self, keyword: str, *, per_page: int = DEFAULT_PER_PAGE
    ) -> list[CardResult]:
        keyword = validate_keyword(keyword)
        per_page = validate_int_range("per_page", per_page, minimum=1, maximum=MAX_PER_PAGE)
        csrf = self.ensure_auth()
        data = self._post_json(
            SEARCH_PERSONAL_CARDS_URL,
            {"keyword": keyword, "page": 1, "sort": 5, "per_page": per_page},
            csrf,
        )
        return sign_card_ids(extract_personal_cards(data, query=keyword), secret=self._id_secret())

    def search_network(self, keyword: str) -> dict[str, Any]:
        keyword = validate_keyword(keyword)
        csrf = self.ensure_auth()
        return self._post_json(SEARCH_EIGHT_NETWORKS_URL, {"keyword": keyword}, csrf)

    def search_network_people(
        self, keyword: str, *, limit: int = DEFAULT_NETWORK_LIMIT
    ) -> list[CardResult]:
        limit = validate_int_range("limit", limit, minimum=0, maximum=MAX_NETWORK_LIMIT)
        if limit == 0:
            return []
        data = self.search_network(keyword)
        return sign_card_ids(
            extract_network_people(data, limit, query=keyword), secret=self._id_secret()
        )

    def fetch_person(self, person_id: str) -> PersonDetail:
        """Fetch detail for a person id returned by search.

        `registered:<id>` can expose private contact fields from the registered
        business card. `network:<id>` uses the public profile JSON endpoint and
        returns only profile fields available there.
        """
        source, native_id = parse_person_id(person_id, secret=self._id_secret())
        csrf = self.ensure_auth()
        if source == "registered":
            data = self._get_json(PERSON_FRIEND_CARD_URL.format(person_id=native_id), csrf)
            card = data.get("friend_card") or {}
            if not isinstance(card, dict):
                raise EightApiError("Eight friend-card response did not contain an object.")
            return PersonDetail(
                id=person_id,
                source="Eight: 登録名刺",
                name=first_value(card, "front_full_name"),
                company=first_value(card, "front_company_name"),
                department=first_value(card, "front_department"),
                title=first_value(card, "front_title"),
                email=first_value(card, "front_email"),
                company_phone_number=first_value(card, "front_company_phone_number"),
                department_number=first_value(card, "front_department_number"),
                direct_line_number=first_value(card, "front_direct_line_number"),
                mobile_phone_number=first_value(card, "front_mobile_phone_number"),
                company_fax_number=first_value(card, "front_company_fax_number"),
                postal_code=first_value(card, "front_postal_code"),
                address=first_value(card, "front_address"),
                url=first_value(card, "front_url1"),
                updated=first_value(card, "updated_at"),
            )
        if source == "network":
            data = self._get_json(PUBLIC_PROFILE_URL.format(person_id=native_id), csrf)
            profile = data.get("profile") or {}
            if not isinstance(profile, dict):
                raise EightApiError("Eight profile response did not contain an object.")
            summary = profile.get("career_summary") or {}
            current_jobs = profile.get("current_jobs")
            career_summary = first_value(summary, "content") if isinstance(summary, dict) else None
            return PersonDetail(
                id=person_id,
                source="Eight: 公開ネットワーク",
                name=first_value(profile, "full_name", "name"),
                company=first_value(profile, "company_name", "company"),
                title=first_value(profile, "title"),
                career_summary=career_summary,
                current_jobs=safe_current_jobs(current_jobs),
            )
        raise ValueError("person id must start with registered: or network:")

    def _post_json(self, url: str, payload: dict[str, Any], csrf: str) -> dict[str, Any]:
        return self._request_json("POST", url, csrf, json=payload)

    def _get_json(self, url: str, csrf: str) -> dict[str, Any]:
        return self._request_json("GET", url, csrf)

    def _request_json(self, method: str, url: str, csrf: str, **kwargs: Any) -> dict[str, Any]:
        headers = {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-CSRF-Token": csrf,
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://8card.net/search_contacts",
        }
        if method == "POST":
            headers["Content-Type"] = "application/json"
        response = self.session.request(
            method,
            url,
            headers=headers,
            timeout=self.timeout,
            allow_redirects=True,
            **kwargs,
        )
        if response.status_code == 403:
            raise AuthRequiredError(forbidden_guidance())
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

    def _id_secret(self) -> str:
        # Search ids are signed with the local auth cookie so a fetch call cannot
        # invent arbitrary ids without first seeing a search result from this client.
        return str(self.session.headers.get("Cookie") or "eight-mcp-community-local")


def validate_keyword(keyword: str) -> str:
    value = keyword.strip()
    if not value:
        raise ValueError("query must not be empty")
    return value


def validate_int_range(name: str, value: int, *, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if value < minimum or value > maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return value


def sign_card_ids(rows: list[CardResult], *, secret: str) -> list[CardResult]:
    signed: list[CardResult] = []
    for row in rows:
        if row.id and UNSIGNED_PERSON_ID_RE.match(row.id):
            signed.append(replace(row, id=sign_fetch_id(row.id, secret=secret)))
        else:
            signed.append(row)
    return signed


def sign_fetch_id(scoped_id: str, *, secret: str) -> str:
    source, native_id = parse_unsigned_person_id(scoped_id)
    signature = fetch_id_signature(source, native_id, secret=secret)
    return f"{source}:{native_id}:{signature}"


def parse_person_id(person_id: str, *, secret: str) -> tuple[str, str]:
    match = FETCH_ID_RE.fullmatch(person_id)
    if not match:
        raise ValueError("person id must be a signed id returned by eight_search_person")
    source, native_id, signature = match.groups()
    expected = fetch_id_signature(source, native_id, secret=secret)
    if not hmac.compare_digest(signature, expected):
        raise ValueError("person id signature is invalid for the current Eight cookie")
    return source, native_id


def parse_unsigned_person_id(scoped_id: str) -> tuple[str, str]:
    match = UNSIGNED_PERSON_ID_RE.fullmatch(scoped_id)
    if not match:
        raise ValueError("person id must be formatted as '<source>:<numeric_id>'")
    return match.group(1), match.group(2)


def fetch_id_signature(source: str, native_id: str, *, secret: str) -> str:
    message = f"{source}:{native_id}".encode()
    return hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()[:16]


def safe_current_jobs(value: Any) -> list[dict[str, Any]] | None:
    """Keep public profile career data compact and schema-tolerant."""
    if not isinstance(value, list):
        return None
    safe_jobs: list[dict[str, Any]] = []
    for item in value[:5]:
        if not isinstance(item, dict):
            continue
        safe = {
            key: item[key]
            for key in (
                "company_name",
                "department",
                "title",
                "career_date_from",
                "career_date_to",
            )
            if item.get(key)
        }
        if safe:
            safe_jobs.append(safe)
    return safe_jobs or None
