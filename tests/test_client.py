from __future__ import annotations

import json
import re

import requests

from eight.client import EightClient, safe_current_jobs
from eight.errors import AuthRequiredError


class ForbiddenSession:
    def __init__(self) -> None:
        self.headers: dict[str, str] = {}

    def get(self, *_args, **_kwargs) -> requests.Response:
        response = requests.Response()
        response.status_code = 403
        response.url = "https://8card.net/myhome"
        response._content = b"Forbidden"
        return response


class JsonSession:
    def __init__(self) -> None:
        self.headers: dict[str, str] = {}
        self.requests: list[dict[str, object]] = []

    def get(self, *_args, **_kwargs) -> requests.Response:
        response = requests.Response()
        response.status_code = 200
        response.url = "https://8card.net/myhome"
        response._content = b'<meta name="csrf-token" content="token">'
        return response

    def request(self, method: str, url: str, **kwargs) -> requests.Response:  # noqa: ANN003
        self.requests.append({"method": method, "url": url, **kwargs})
        response = requests.Response()
        response.status_code = 200
        response.url = url
        response.headers["content-type"] = "application/json; charset=utf-8"
        if "search_personal_cards" in url:
            payload = {"personal_cards": []}
        elif "search_eight_networks" in url:
            payload = {
                "companies": [{"company_id": 1, "company_name": "Example Inc"}],
                "eight_users": [
                    {"person_id": 2, "name": "Alice Example", "company": "Example Inc"}
                ],
            }
        elif "/p/" in url:
            payload = {"profile": {"full_name": "Alice Example", "company_name": "Example Inc"}}
        else:
            payload = {"friend_card": {"front_full_name": "Alice Example"}}
        response._content = json.dumps(payload).encode()
        return response


def test_auth_status_for_cookie_403_raises_actionable_auth_required_error() -> None:
    client = EightClient(session=ForbiddenSession())  # type: ignore[arg-type]

    try:
        client.auth_status_for_cookie("session=abc")
    except AuthRequiredError as error:
        message = str(error)
    else:  # pragma: no cover
        raise AssertionError("Expected AuthRequiredError")

    assert "403" in message
    assert "eight_auth_login" in message
    assert "eight_set_cookie" in message
    assert "eight-mcp-community[cloudflare]" in message


def test_search_person_defaults_to_registered_cards_only() -> None:
    session = JsonSession()
    client = EightClient(session=session)  # type: ignore[arg-type]

    result = client.search_person(" 鈴木 ")

    assert result.to_safe_dict()["searched"] == {
        "personal_cards": True,
        "eight_networks": False,
    }
    assert [call["url"] for call in session.requests] == [
        "https://8card.net/search_contacts/search_personal_cards"
    ]


def test_search_person_all_keeps_public_people_and_companies_separate() -> None:
    session = JsonSession()
    client = EightClient(session=session)  # type: ignore[arg-type]

    result = client.search_person("鈴木", source="all").to_safe_dict()

    assert result["searched"] == {"personal_cards": True, "eight_networks": True}
    network = result["network"][0]
    assert re.fullmatch(r"network:2:[0-9a-f]{16}", network.pop("id"))
    assert network == {
        "source": "Eight: 公開ネットワーク",
        "name": "Alice Example",
        "company": "Example Inc",
        "confidence": "public_network_match",
    }
    assert result["network_companies"] == [
        {
            "source": "Eight: 公開ネットワーク法人",
            "id": "company:1",
            "name": "Example Inc",
            "confidence": "public_network_company_match",
        }
    ]


def test_search_person_validates_inputs() -> None:
    client = EightClient(session=JsonSession())  # type: ignore[arg-type]

    for kwargs in [{"source": "network"}, {"per_page": 0}, {"network_limit": -1}]:
        try:
            client.search_person("鈴木", **kwargs)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            pass
        else:  # pragma: no cover
            raise AssertionError(f"Expected validation failure for {kwargs}")


def test_source_all_with_zero_network_limit_does_not_call_network() -> None:
    session = JsonSession()
    client = EightClient(session=session)  # type: ignore[arg-type]

    result = client.search_person("鈴木", source="all", network_limit=0).to_safe_dict()

    assert result["searched"] == {"personal_cards": True, "eight_networks": False}
    assert result["network"] == []
    assert result["network_companies"] == []
    assert [call["url"] for call in session.requests] == [
        "https://8card.net/search_contacts/search_personal_cards"
    ]


def test_fetch_person_rejects_unsigned_malformed_or_tampered_ids_before_auth() -> None:
    session = JsonSession()
    client = EightClient(session=session)  # type: ignore[arg-type]

    for person_id in [
        "registered:123",
        "company:1",
        "registered:../../myhome",
        "registered:123:0000000000000000",
    ]:
        try:
            client.fetch_person(person_id)
        except ValueError:
            pass
        else:  # pragma: no cover
            raise AssertionError(f"Expected validation failure for {person_id}")

    assert session.requests == []


def test_fetch_person_accepts_signed_search_id() -> None:
    session = JsonSession()
    client = EightClient(session=session)  # type: ignore[arg-type]
    search = client.search_person("鈴木", source="all").to_safe_dict()
    signed_id = search["network"][0]["id"]

    detail = client.fetch_person(signed_id).to_safe_dict()

    assert detail["id"] == signed_id
    assert detail["source"] == "Eight: 公開ネットワーク"


def test_safe_current_jobs_keeps_only_compact_public_fields() -> None:
    assert safe_current_jobs(
        [
            {
                "company_name": "Example Inc",
                "title": "Manager",
                "secretish_internal_key": "ignored",
            }
        ]
    ) == [{"company_name": "Example Inc", "title": "Manager"}]
