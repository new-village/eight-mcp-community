# eight-mcp-community

Unofficial Python client and stdio MCP server for Eight person-search workflows.

> [!WARNING]
> This project is unofficial and not affiliated with Eight or Sansan. It uses private/internal web endpoints that can change without notice. Keep cookies, credentials, and raw contact data out of GitHub, logs, issues, prompts, and public reports.

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

If Eight returns Cloudflare-style `403` responses with valid cookies, use the optional `curl_cffi` transport. It impersonates Chrome for the normal CLI/MCP path and does not require Playwright:

```bash
uvx --from 'eight-mcp-community[cloudflare]' eight-mcp-community serve
```

If you install with `python -m pip install --user eight-mcp-community`, the command may be placed under `~/.local/bin`, which is not always on `PATH`. Either add that directory to `PATH`, use the absolute path, or run the module form:

```bash
python -m eight serve
~/.local/bin/eight-mcp-community serve
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

Codex MCP examples:

```bash
# PATH-based
codex mcp add eight -- eight-mcp-community serve

# pip --user / absolute-path style
codex mcp add eight -- /Users/you/.local/bin/eight-mcp-community serve

# module form, useful when the command is not on PATH
codex mcp add eight -- python3 -m eight serve

# Cloudflare-resistant transport via uvx
codex mcp add eight -- uvx --from 'eight-mcp-community[cloudflare]' eight-mcp-community serve
```

After package upgrades, optional dependency changes, authentication changes, or MCP configuration edits, restart Codex / your MCP client or otherwise restart the MCP server process. Already-running MCP servers keep using the old Python process.

Recommended post-install message for agents:

```text
Eight MCP registration is installed. Authentication is intentionally simple:
1. Check current state: /Users/you/.local/bin/eight-mcp-community auth-status
2. If no cookie is configured, log in with Playwright. Recommended install for Eight login reliability: python -m pip install --user 'eight-mcp-community[browser,cloudflare]' && python -m playwright install chromium
3. If you already have a trusted Cookie header, save it directly: /Users/you/.local/bin/eight-mcp-community set-cookie '<COOKIE_HEADER>'
If a known-good cookie returns 403, use/install eight-mcp-community[cloudflare]. Restart Codex or the MCP client after package/auth/config changes.
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

The authentication surface is intentionally small:

1. `auth-status` checks whether a Cookie header is configured and whether it can currently access Eight.
2. `auth-login` uses Playwright for an interactive browser login, captures 8card.net cookies, and saves them.
3. `set-cookie` saves a trusted Cookie header supplied from outside the MCP flow.

Unless you provide a Cookie header via `set-cookie` or `EIGHT_COOKIE`, logging in requires Playwright. For Eight, installing both `browser` and `cloudflare` extras is recommended because the final cookie verification may need Chrome-like HTTP transport:

```bash
python -m pip install --user 'eight-mcp-community[browser,cloudflare]'
python -m playwright install chromium
~/.local/bin/eight-mcp-community auth-login
```

The MCP `eight_auth_login` tool runs the CLI login flow in a subprocess so Playwright does not collide with the MCP server's asyncio loop.

If Playwright's browser binary is missing, install it once on the same machine/user account:

```bash
python -m playwright install chromium
```

Create or overwrite the config file from a trusted Cookie header:

```bash
~/.local/bin/eight-mcp-community set-cookie '<COOKIE_HEADER>'
~/.local/bin/eight-mcp-community auth-status
```

Supported credential lookup order:

1. `EIGHT_COOKIE` — externally supplied Cookie header
2. `EIGHT_MCP_COMMUNITY_CONFIG` — path to config JSON with a `cookie` field
3. Default config file: `~/.config/eight-mcp-community/config.json`

If `auth-login` times out after the browser reached `/myhome`, the cookie was probably captured but the verification HTTP request failed. The timeout message includes the last non-secret diagnostic (`reason`, HTTP status, final URL, and Cloudflare-like signal). Use the `[cloudflare]` extra and restart the MCP client:

```bash
python -m pip install --user 'eight-mcp-community[cloudflare]'
```

## CLI

```bash
eight-mcp-community auth-status
eight-mcp-community auth-login
eight-mcp-community set-cookie 'Cookie header'
eight-mcp-community search '鈴木'
eight-mcp-community search '鈴木' --always-network
eight-mcp-community serve
```

All command output is JSON except `--help`.

## MCP tools

Authentication tools:

- `eight_auth_status` — check whether auth is configured and whether the current Cookie can access Eight
- `eight_auth_login` — open a Playwright browser login flow, capture cookies, and save them through `eight_set_cookie`
- `eight_set_cookie` — store a trusted Cookie header in the local MCP config file

Search tools:

- `eight_search_person` — search registered/exchanged cards first; search public Eight network only if no registered-card hit, unless `alwaysNetwork` is true
- `eight_search_registered_cards` — search only registered/exchanged business cards
- `eight_search_network_people` — search only public Eight network people, keeping public results separate from private cards

Returned data is intentionally minimal and LLM-safe: source, name, company, department, title, updated date, confidence/source bucket, and when available `matched_fields` / `match_excerpt` so users can understand why a result matched. Raw HTML, raw JSON, cookies, tokens, email addresses, phone numbers, and bulk exports are not returned.

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
