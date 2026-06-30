from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .models import CardResult, CompanyResult

DISPLAY_FIELDS = {
    "name": ("front_full_name", "full_name", "name", "display_name"),
    "company": (
        "front_company_name",
        "company_name",
        "company",
        "organization_name",
        "corporation_name",
    ),
    "department": ("front_department", "department"),
    "title": ("front_title", "title", "position", "job_title"),
}
MATCH_ONLY_FIELDS = {
    "memo": ("memo", "note", "notes", "front_memo", "front_note", "description"),
}


def first_value(item: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = item.get(key)
        if value:
            return value
    return None


def extract_personal_cards(data: dict[str, Any], *, query: str | None = None) -> list[CardResult]:
    """Extract minimal registered-card hits from Eight's private search response."""
    rows: list[CardResult] = []
    for personal_card in data.get("personal_cards", []) or []:
        if not isinstance(personal_card, dict):
            continue
        person = personal_card.get("person") or {}
        if not isinstance(person, dict):
            continue
        person_id = first_value(person, "id")
        cards = person.get("personal_cards") or [personal_card]
        for card in cards:
            if not isinstance(card, dict):
                continue
            friend_card = card.get("friend_card") or card
            if not isinstance(friend_card, dict):
                continue
            name = first_value(friend_card, "front_full_name", "full_name", "name") or first_value(
                person, "full_name", "name"
            )
            company = first_value(friend_card, "front_company_name", "company_name", "company")
            department = first_value(friend_card, "front_department", "department")
            title = first_value(friend_card, "front_title", "title")
            updated = first_value(card, "personal_card_updated_at", "updated_at") or first_value(
                friend_card, "updated_at"
            )
            if not (name or company or department or title):
                continue
            rows.append(
                CardResult(
                    id=format_scoped_id("registered", person_id),
                    source="Eight: 登録名刺",
                    name=name,
                    company=company,
                    department=department,
                    title=title,
                    updated=updated,
                    confidence="registered_card_match",
                    **match_context(query, friend_card, person, card),
                )
            )
    return rows


def _network_people_items(data: dict[str, Any]) -> Iterable[dict[str, Any]]:
    """Yield only people-like buckets so companies never leak into person hits."""
    for bucket in ("eight_users", "people", "users"):
        items = data.get(bucket)
        if not isinstance(items, list):
            continue
        for item in items:
            if isinstance(item, dict):
                yield item
        return


def extract_network_people(
    data: dict[str, Any], limit: int, *, query: str | None = None
) -> list[CardResult]:
    """Extract public-network people without mixing company hits into the same list."""
    rows: list[CardResult] = []
    seen: set[str] = set()
    for item in _network_people_items(data):
        name = first_value(item, "name", "full_name", "display_name")
        person_id = first_value(item, "person_id")
        company = first_value(
            item, "company", "company_name", "organization_name", "corporation_name"
        )
        department = first_value(item, "department", "front_department")
        title = first_value(item, "title", "position", "job_title")
        if not (name and (company or department or title)):
            continue
        row = CardResult(
            id=format_scoped_id("network", person_id),
            source="Eight: 公開ネットワーク",
            name=name,
            company=company,
            department=department,
            title=title,
            confidence="public_network_match",
            **match_context(query, item),
        )
        key = repr(row.to_safe_dict())
        if key in seen:
            continue
        seen.add(key)
        rows.append(row)
        if len(rows) >= limit:
            break
    return rows


def extract_network_companies(
    data: dict[str, Any], limit: int, *, query: str | None = None
) -> list[CompanyResult]:
    """Extract public-network company hits into their own bucket."""
    rows: list[CompanyResult] = []
    seen: set[str] = set()
    for item in data.get("companies", []) or []:
        if not isinstance(item, dict):
            continue
        name = first_value(item, "company_name", "corporation_name", "name")
        company_id = first_value(item, "company_id", "id")
        address = first_value(item, "address")
        if not name:
            continue
        row = CompanyResult(
            id=format_scoped_id("company", company_id),
            source="Eight: 公開ネットワーク法人",
            name=name,
            address=address,
            confidence="public_network_company_match",
            **match_context(query, item),
        )
        key = repr(row.to_safe_dict())
        if key in seen:
            continue
        seen.add(key)
        rows.append(row)
        if len(rows) >= limit:
            break
    return rows


def format_scoped_id(source: str, native_id: Any) -> str | None:
    """Namespace Eight ids so callers know which fetch endpoint can handle them."""
    return f"{source}:{native_id}" if native_id is not None else None


def match_context(query: str | None, *items: dict[str, Any]) -> dict[str, Any]:
    if not query:
        return {}
    needle = normalize_text(query)
    if not needle:
        return {}

    matched_fields: list[str] = []
    excerpt: str | None = None
    for field, keys in {**DISPLAY_FIELDS, **MATCH_ONLY_FIELDS}.items():
        for item in items:
            value = first_value(item, *keys)
            if not isinstance(value, str):
                continue
            if needle in normalize_text(value):
                if field not in matched_fields:
                    matched_fields.append(field)
                excerpt = excerpt or make_excerpt(value, query)
                break

    if not matched_fields:
        return {}
    data: dict[str, Any] = {"matched_fields": matched_fields}
    if excerpt:
        data["match_excerpt"] = excerpt
    return data


def normalize_text(value: str) -> str:
    return "".join(value.casefold().split())


def make_excerpt(value: str, query: str, *, radius: int = 40) -> str:
    index = value.find(query)
    if index < 0:
        return value[: radius * 2]
    start = max(0, index - radius)
    end = min(len(value), index + len(query) + radius)
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(value) else ""
    return f"{prefix}{value[start:end]}{suffix}"
