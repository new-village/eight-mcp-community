from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .models import CardResult


def first_value(item: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = item.get(key)
        if value:
            return value
    return None


def extract_personal_cards(data: dict[str, Any]) -> list[CardResult]:
    rows: list[CardResult] = []
    for personal_card in data.get("personal_cards", []) or []:
        person = personal_card.get("person") or {}
        cards = person.get("personal_cards") or [personal_card]
        for card in cards:
            friend_card = card.get("friend_card") or card
            name = first_value(friend_card, "front_full_name", "full_name", "name") or first_value(
                person, "full_name", "name"
            )
            company = first_value(friend_card, "front_company_name", "company_name", "company")
            department = first_value(friend_card, "front_department", "department")
            title = first_value(friend_card, "front_title", "title")
            updated = first_value(card, "personal_card_updated_at", "updated_at") or first_value(
                friend_card, "updated_at"
            )
            if name or company or department or title:
                rows.append(
                    CardResult(
                        source="Eight: 登録名刺",
                        name=name,
                        company=company,
                        department=department,
                        title=title,
                        updated=updated,
                        confidence="registered_card_match",
                    )
                )
    return rows


def walk(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def extract_network_people(data: dict[str, Any], limit: int) -> list[CardResult]:
    rows: list[CardResult] = []
    seen: set[str] = set()
    for item in walk(data):
        name = first_value(item, "name", "full_name", "display_name")
        company = first_value(
            item, "company", "company_name", "organization_name", "corporation_name"
        )
        department = first_value(item, "department", "front_department")
        title = first_value(item, "title", "position", "job_title")
        if not (name and (company or department or title)):
            continue
        row = CardResult(
            source="Eight: 公開ネットワーク",
            name=name,
            company=company,
            department=department,
            title=title,
            confidence="public_network_match",
        )
        key = repr(row.to_safe_dict())
        if key in seen:
            continue
        seen.add(key)
        rows.append(row)
        if len(rows) >= limit:
            break
    return rows
