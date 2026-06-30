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
    sub.add_parser("auth-status", help="Check whether Eight authentication is usable")

    auth_login = sub.add_parser("auth-login", help="Log in with Playwright and save cookies")
    auth_login.add_argument("--headless", action="store_true")
    auth_login.add_argument("--timeout-seconds", type=int, default=180)

    set_cookie = sub.add_parser("set-cookie", help="Store a Cookie header in the config file")
    set_cookie.add_argument("cookie", help="8card.net Cookie header")
    set_cookie.add_argument("--no-verify", action="store_true", help="Save without verifying first")

    search = sub.add_parser("search", help="Search Eight registered cards by default")
    search.add_argument("query")
    search.add_argument("--per-page", type=int, default=100)
    search.add_argument("--network-limit", type=int, default=20)
    search.add_argument(
        "--source",
        choices=("registered", "all"),
        default="registered",
        help=(
            "Search source: registered cards only by default; "
            "all also includes public network people and companies"
        ),
    )

    fetch = sub.add_parser("fetch-person", help="Fetch detailed fields for an id from search")
    fetch.add_argument("id")

    args = parser.parse_args(argv)
    command = args.command or "serve"

    try:
        if command == "serve":
            run_mcp_server()
        elif command == "auth-status":
            json_print(auth.auth_status())
        elif command == "auth-login":
            cookie = run_browser_login(
                headless=args.headless,
                timeout_seconds=args.timeout_seconds,
            )
            json_print(auth.set_cookie(cookie, verify=True))
        elif command == "set-cookie":
            json_print(auth.set_cookie(args.cookie, verify=not args.no_verify))
        elif command == "search":
            result = EightClient.from_default_config().search_person(
                args.query,
                per_page=args.per_page,
                network_limit=args.network_limit,
                source=args.source,
            )
            json_print(result.to_safe_dict())
        elif command == "fetch-person":
            person = EightClient.from_default_config().fetch_person(args.id)
            json_print({"status": "ok", "person": person.to_safe_dict()})
        else:
            parser.error(f"unknown command: {command}")
    except KeyboardInterrupt:
        raise
    except Exception as exc:  # noqa: BLE001 - CLI should emit JSON failure.
        json_print(error_detail(exc))
        sys.exit(1)


if __name__ == "__main__":
    main()
