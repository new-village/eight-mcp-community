from __future__ import annotations

import re
from html.parser import HTMLParser


class TokenParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.authenticity_token: str | None = None
        self.csrf_token: str | None = None
        self.inputs: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        data = {key: (value or "") for key, value in attrs}
        if tag == "input":
            name = data.get("name")
            if name:
                self.inputs[name] = data.get("value", "")
            if name == "authenticity_token":
                self.authenticity_token = data.get("value")
        if tag == "meta" and data.get("name") == "csrf-token":
            self.csrf_token = data.get("content")


def parse_tokens(html: str) -> TokenParser:
    parser = TokenParser()
    parser.feed(html)
    if not parser.authenticity_token:
        match = re.search(r"name=[\"']authenticity_token[\"'][^>]*value=[\"']([^\"']+)", html)
        if match:
            parser.authenticity_token = match.group(1)
    if not parser.csrf_token:
        match = re.search(r"name=[\"']csrf-token[\"'][^>]*content=[\"']([^\"']+)", html)
        if match:
            parser.csrf_token = match.group(1)
    return parser
