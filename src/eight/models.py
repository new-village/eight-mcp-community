from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

SourceBucket = Literal["Eight: 登録名刺", "Eight: 公開ネットワーク"]
CompanySourceBucket = Literal["Eight: 公開ネットワーク法人"]
SearchSource = Literal["registered", "all"]


def compact_dict(value: Any) -> dict[str, Any]:
    """Serialize dataclasses without empty fields.

    The MCP tools deliberately return compact dictionaries because these payloads are
    consumed by LLM agents. Empty keys add context noise and make privacy review harder.
    """
    return {key: item for key, item in asdict(value).items() if item not in (None, "", [])}


@dataclass(frozen=True)
class CardResult:
    """Minimal person search hit.

    Search is a discovery operation: it returns enough to identify a likely person
    and a stable fetch id, but excludes contact fields such as email or phone.
    """

    source: SourceBucket
    id: str | None = None
    name: str | None = None
    company: str | None = None
    department: str | None = None
    title: str | None = None
    updated: str | None = None
    confidence: str | None = None
    matched_fields: list[str] | None = None
    match_excerpt: str | None = None

    def to_safe_dict(self) -> dict[str, Any]:
        return compact_dict(self)


@dataclass(frozen=True)
class CompanyResult:
    """Minimal public-network company hit returned separately from people."""

    source: CompanySourceBucket
    id: str | None = None
    name: str | None = None
    address: str | None = None
    confidence: str | None = None
    matched_fields: list[str] | None = None
    match_excerpt: str | None = None

    def to_safe_dict(self) -> dict[str, Any]:
        return compact_dict(self)


@dataclass(frozen=True)
class SearchResult:
    status: str
    query: str
    searched: dict[str, bool]
    personal: list[CardResult]
    network: list[CardResult]
    network_companies: list[CompanyResult] | None = None
    message: str | None = None

    def to_safe_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "status": self.status,
            "query": self.query,
            "searched": self.searched,
            "personal": [item.to_safe_dict() for item in self.personal],
            "network": [item.to_safe_dict() for item in self.network],
            "network_companies": [item.to_safe_dict() for item in (self.network_companies or [])],
        }
        if self.message:
            data["message"] = self.message
        return data


@dataclass(frozen=True)
class PersonDetail:
    """Detailed person payload returned only after the caller opts in with an id."""

    id: str
    source: SourceBucket
    name: str | None = None
    company: str | None = None
    department: str | None = None
    title: str | None = None
    email: str | None = None
    company_phone_number: str | None = None
    department_number: str | None = None
    direct_line_number: str | None = None
    mobile_phone_number: str | None = None
    company_fax_number: str | None = None
    postal_code: str | None = None
    address: str | None = None
    url: str | None = None
    updated: str | None = None
    career_summary: str | None = None
    current_jobs: list[dict[str, Any]] | None = None

    def to_safe_dict(self) -> dict[str, Any]:
        return compact_dict(self)
