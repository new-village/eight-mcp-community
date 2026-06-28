from __future__ import annotations


class EightError(Exception):
    """Base error for eight-mcp-community."""


class AuthRequiredError(EightError):
    """Authentication is missing or expired."""


class MfaRequiredError(EightError):
    """Eight requested MFA; user/operator input is required."""


class LoginChallengeError(EightError):
    """Login failed or Eight presented a challenge that cannot be handled automatically."""


class EightApiError(EightError):
    """Eight API returned an unexpected response."""


def error_detail(error: BaseException) -> dict[str, str]:
    if isinstance(error, AuthRequiredError):
        code = "auth_required"
    elif isinstance(error, MfaRequiredError):
        code = "mfa_required"
    elif isinstance(error, LoginChallengeError):
        code = "login_failed_or_challenge"
    elif isinstance(error, EightApiError):
        code = "eight_api_error"
    else:
        code = "error"
    return {"error": code, "type": type(error).__name__, "message": str(error)}
