# eight-mcp-community

Unofficial Python client and stdio MCP server for Eight person-search workflows.

> [!WARNING]
> This project is unofficial and not affiliated with Eight or Sansan. It uses private/internal web endpoints that can change without notice. Keep cookies, passwords, and raw contact data out of GitHub, logs, issues, prompts, and public reports.

## Design

This package follows the same idea as `note-mcp-community`, but the core is Python:

- PyPI/project name: `eight-mcp-community`
- Python import package: `eight`
- CLI commands: `eight-mcp-community` and `eight-mcp`
- MCP server: stdio, suitable for local/private agent use

The core client is reusable without an LLM:

```python
from eight import EightClient

client = EightClient.from_default_config()
result = client.search_person("鈴木太郎 東京商事")
print(result.to_safe_dict())
```

The MCP server is a thin wrapper over the same `EightClient`.

## Install / run

Local development:

```bash
uv sync --dev
uv run eight-mcp-community --help
uv run eight-mcp-community serve
```

Run directly without installing permanently:

```bash
uvx eight-mcp-community serve
```

MCP client configuration:

```json
{
  "mcpServers": {
    "eight": {
      "command": "uvx",
      "args": ["eight-mcp-community", "serve"]
    }
  }
}
```

Local development MCP config:

```json
{
  "mcpServers": {
    "eight": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/eight-mcp-community",
        "run",
        "eight-mcp-community",
        "serve"
      ]
    }
  }
}
```

## Authentication

Supported credential lookup order:

1. `EIGHT_COOKIE` — Cookie header
2. `EIGHT_SESSION_COOKIE` — alternate Cookie header
3. `EIGHT_MCP_COMMUNITY_CONFIG` — path to config JSON with a `cookie` field
4. Default config file: `~/.config/eight-mcp-community/config.json`
5. `EIGHT_COOKIE_FILE` — Mozilla/Netscape cookie jar path
6. Optional env login: `EIGHT_EMAIL` + `EIGHT_PASSWORD`

For remote/server use, prefer a cookie config or env secret. The package does not require browser automation.

Create a config file from a trusted Cookie header:

```bash
eight-mcp-community set-cookie 'your 8card.net Cookie header'
eight-mcp-community auth-status
```

If you do not have a Cookie header, you can ask the CLI to log in and save cookies:

```bash
eight-mcp-community set-cookie --email you@example.com --password 'your password'
```

`--email` and `--password` are used only for the login request. The config file stores the resulting Cookie header, not the email or password.

Eight may require MFA or another browser challenge. In that case, use the browser login flow:

```bash
uvx --from 'eight-mcp-community[browser]' eight-mcp-community auth-login
```

If Playwright's browser binary is missing, install it once on the same machine/user account:

```bash
python -m playwright install chromium
```

Or use env:

```bash
EIGHT_COOKIE='your 8card.net Cookie header' eight-mcp-community auth-check
```

If `EIGHT_EMAIL` and `EIGHT_PASSWORD` are set, the client can perform the same password-login flow used by the existing Hermes skill and save resulting cookies into the default config as a Cookie header. MFA/challenge responses are reported as structured errors and are not bypassed.

## CLI

```bash
eight-mcp-community auth-status
eight-mcp-community auth-check
eight-mcp-community set-cookie 'Cookie header'
eight-mcp-community set-cookie --email you@example.com --password 'your password'
uvx --from 'eight-mcp-community[browser]' eight-mcp-community auth-login
eight-mcp-community clear-cookie
eight-mcp-community search '鈴木'
eight-mcp-community search '鈴木' --always-network
eight-mcp-community serve
```

All command output is JSON except `--help`.

## MCP tools

Authentication/setup tools:

- `eight_auth_status` — report whether auth is configured and from where, without leaking secrets
- `eight_auth_check` — verify access to Eight `/myhome` and CSRF extraction
- `eight_set_cookie` — store a Cookie header in the local config file, or log in with `email`/`password` and save cookies
- `eight_auth_login_browser` — open a Playwright browser login flow and save cookies locally
- `eight_clear_cookie` — delete the stored config-file cookie
- `eight_login_help` — explain supported setup paths

Search tools:

- `eight_search_person` — search registered/exchanged cards first; search public Eight network only if no registered-card hit, unless `alwaysNetwork` is true
- `eight_search_registered_cards` — search only registered/exchanged business cards
- `eight_search_network_people` — search only public Eight network people, keeping public results separate from private cards

Returned data is intentionally minimal and LLM-safe: source, name, company, department, title, updated date, and confidence/source bucket. Raw HTML, raw JSON, cookies, tokens, email addresses, phone numbers, and bulk exports are not returned.

## Privacy and safety

- Do not use this project for bulk contact export or contact-list harvesting.
- Do not commit cookies, config files, raw API dumps, screenshots, or credentials.
- Treat registered business-card results as private context; cite public sources for public-facing reports.
- Eight business-card data can be stale. Corroborate current affiliation/title with public sources when accuracy matters.

## Development

```bash
uv sync --dev
uv run ruff check .
uv run pytest
```

Manual MCP smoke test:

```bash
printf '%s\n' \
'{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"smoke-test","version":"0.0.0"}}}' \
'{"jsonrpc":"2.0","method":"notifications/initialized","params":{}}' \
'{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' \
| timeout 5s uv run eight-mcp-community serve
```
