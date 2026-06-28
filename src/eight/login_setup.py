from __future__ import annotations

from typing import Any, Protocol

from . import auth
from .client import EightClient


class PasswordLoginClient(Protocol):
    def login(self, email: str, password: str) -> str: ...

    def auth_check(self) -> dict[str, Any]: ...


def save_cookie_from_password_login(
    email: str,
    password: str,
    *,
    client: PasswordLoginClient | None = None,
) -> dict[str, Any]:
    """Authenticate with email/password, then persist only the resulting Cookie header."""
    if not email or not password:
        raise ValueError("Both email and password are required for password login.")

    login_client = client or EightClient()
    cookie = login_client.login(email, password)
    login_client.auth_check()
    saved = auth.save_cookie(cookie)
    return {
        "authenticated": True,
        **saved,
        "message": (
            "Eight authentication configured from email/password login. Only cookies were saved."
        ),
    }
