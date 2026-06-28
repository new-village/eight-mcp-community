from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

SourceBucket = Literal["Eight: 登録名刺", "Eight: 公開ネットワーク"]


@dataclass(frozen=True)
class CardResult:
    source: SourceBucket
    name: str | None = None
    company: str | None = None
    department: str | None = None
    title: str | None = None
    updated: str | None = None
    confidence: str | None = None

    def to_safe_dict(self) -> dict[str, Any]:
        """Return only LLM-safe, minimal fields."""
        return {key: value for key, value in asdict(self).items() if value not in (None, "")}


@dataclass(frozen=True)
class SearchResult:
    status: str
    query: str
    searched: dict[str, bool]
    personal: list[CardResult]
    network: list[CardResult]
    message: str | None = None

    def to_safe_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "status": self.status,
            "query": self.query,
            "searched": self.searched,
            "personal": [item.to_safe_dict() for item in self.personal],
            "network": [item.to_safe_dict() for item in self.network],
        }
        if self.message:
            data["message"] = self.message
        return data
