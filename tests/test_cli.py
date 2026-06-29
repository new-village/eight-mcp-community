from __future__ import annotations

import json

import pytest

from eight import cli


def test_auth_status_command_reports_setup_required(monkeypatch, tmp_path, capsys) -> None:
    path = tmp_path / "config.json"
    monkeypatch.setenv("EIGHT_MCP_COMMUNITY_CONFIG", str(path))
    monkeypatch.delenv("EIGHT_COOKIE", raising=False)

    cli.main(["auth-status"])

    payload = json.loads(capsys.readouterr().out)
    assert payload["configured"] is False
    assert payload["authenticated"] is False
    assert payload["status"] == "setup_required"


def test_removed_auth_commands_are_not_available(capsys) -> None:
    with pytest.raises(SystemExit):
        cli.main(["auth-check"])
    with pytest.raises(SystemExit):
        cli.main(["auth-setup"])
    with pytest.raises(SystemExit):
        cli.main(["clear-cookie"])
