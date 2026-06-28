from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from . import auth
from .browser_login import run_browser_login
from .client import EightClient
from .errors import error_detail
from .mcp_server import run as run_mcp_server


def json_print(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="eight-mcp-community")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("serve", help="Run the stdio MCP server")
    sub.add_parser("auth-status", help="Show authentication status without leaking secrets")
    sub.add_parser("auth-check", help="Verify Eight authentication")
    sub.add_parser("clear-cookie", help="Delete stored config-file cookie")

    set_cookie = sub.add_parser("set-cookie", help="Store a Cookie header in the config file")
    set_cookie.add_argument("cookie", nargs="?", help="8card.net Cookie header")
    set_cookie.add_argument("--email", "-email", help="Eight login email address")
    set_cookie.add_argument("--password", "-password", help="Eight login password")
    set_cookie.add_argument(
        "--browser-login",
        action="store_true",
        help="Open a Playwright browser login flow and save cookies",
    )
    set_cookie.add_argument("--headless", action="store_true", help="Use headless browser login")
    set_cookie.add_argument("--timeout-seconds", type=int, default=180)
    set_cookie.add_argument("--no-verify", action="store_true", help="Save without verifying first")

    auth_login = sub.add_parser("auth-login", help="Open a browser login flow and save cookies")
    auth_login.add_argument("--headless", action="store_true")
    auth_login.add_argument("--timeout-seconds", type=int, default=180)

    search = sub.add_parser("search", help="Search Eight person cards/network")
    search.add_argument("query")
    search.add_argument("--per-page", type=int, default=100)
    search.add_argument("--network-limit", type=int, default=20)
    search.add_argument("--always-network", action="store_true")

    cards = sub.add_parser("search-registered-cards", help="Search only registered/exchanged cards")
    cards.add_argument("query")
    cards.add_argument("--per-page", type=int, default=100)

    network = sub.add_parser(
        "search-network-people", help="Search only public Eight network people"
    )
    network.add_argument("query")
    network.add_argument("--limit", type=int, default=20)

    args = parser.parse_args(argv)
    command = args.command or "serve"

    try:
        if command == "serve":
            run_mcp_server()
        elif command == "auth-status":
            json_print(auth.auth_status())
        elif command == "auth-check":
            json_print(EightClient.from_default_config().auth_check())
        elif command == "set-cookie":
            json_print(_run_set_cookie(args))
        elif command == "auth-login":
            json_print(
                run_browser_login(
                    headless=args.headless,
                    timeout_seconds=args.timeout_seconds,
                )
            )
        elif command == "clear-cookie":
            json_print(auth.clear_stored_cookie())
        elif command == "search":
            result = EightClient.from_default_config().search_person(
                args.query,
                per_page=args.per_page,
                network_limit=args.network_limit,
                always_network=args.always_network,
            )
            json_print(result.to_safe_dict())
        elif command == "search-registered-cards":
            rows = EightClient.from_default_config().search_registered_cards(
                args.query,
                per_page=args.per_page,
            )
            json_print([row.to_safe_dict() for row in rows])
        elif command == "search-network-people":
            rows = EightClient.from_default_config().search_network_people(
                args.query, limit=args.limit
            )
            json_print([row.to_safe_dict() for row in rows])
        else:
            parser.error(f"unknown command: {command}")
    except KeyboardInterrupt:
        raise
    except Exception as exc:  # noqa: BLE001 - CLI should emit JSON failure.
        json_print(error_detail(exc))
        sys.exit(1)


def _run_set_cookie(args: argparse.Namespace) -> dict[str, Any]:
    if args.cookie:
        if not args.no_verify:
            client = EightClient()
            client.session.headers["Cookie"] = args.cookie
            client.auth_check()
        return auth.save_cookie(args.cookie)

    if args.email or args.password:
        if not (args.email and args.password):
            raise ValueError("Both --email and --password are required for password login.")
        client = EightClient()
        cookie = client.login(args.email, args.password)
        client.auth_check()
        saved = auth.save_cookie(cookie)
        return {
            "authenticated": True,
            **saved,
            "message": "Eight authentication configured from email/password login.",
        }

    if args.browser_login:
        return run_browser_login(headless=args.headless, timeout_seconds=args.timeout_seconds)

    raise ValueError(
        "Provide a Cookie header, --email/--password, or --browser-login. "
        "Examples: eight-mcp-community set-cookie 'cookie'; "
        "eight-mcp-community set-cookie --email you@example.com --password '...'; "
        "eight-mcp-community set-cookie --browser-login"
    )


if __name__ == "__main__":
    main()
