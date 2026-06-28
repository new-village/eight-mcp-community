from __future__ import annotations

import requests

from eight.client import EightClient
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


def test_auth_check_403_raises_actionable_auth_required_error() -> None:
    client = EightClient(session=ForbiddenSession())  # type: ignore[arg-type]

    try:
        client.auth_check()
    except AuthRequiredError as error:
        message = str(error)
    else:  # pragma: no cover
        raise AssertionError("Expected AuthRequiredError")

    assert "403" in message
    assert "auth-setup" in message
    assert "set-cookie" in message
    assert "eight-mcp-community[cloudflare]" in message
