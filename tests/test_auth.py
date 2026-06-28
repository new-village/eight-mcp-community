import json

from eight import auth


def test_auth_status_uses_config_cookie(tmp_path, monkeypatch) -> None:
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"cookie": "foo=bar; baz=qux; session=longvalue"}), encoding="utf-8")
    monkeypatch.setenv("EIGHT_MCP_COMMUNITY_CONFIG", str(path))
    monkeypatch.delenv("EIGHT_COOKIE", raising=False)
    monkeypatch.delenv("EIGHT_SESSION_COOKIE", raising=False)
    monkeypatch.delenv("EIGHT_COOKIE_FILE", raising=False)
    monkeypatch.delenv("EIGHT_EMAIL", raising=False)
    monkeypatch.delenv("EIGHT_PASSWORD", raising=False)

    status = auth.auth_status()

    assert status["configured"] is True
    assert status["source"] == "config"
    assert status["configPath"] == str(path)
    assert "foo=ba" in status["cookiePreview"]


def test_save_and_clear_cookie(tmp_path, monkeypatch) -> None:
    path = tmp_path / "config.json"
    monkeypatch.setenv("EIGHT_MCP_COMMUNITY_CONFIG", str(path))

    saved = auth.save_cookie("foo=bar; baz=qux")
    assert saved["saved"] is True
    assert json.loads(path.read_text(encoding="utf-8"))["cookie"] == "foo=bar; baz=qux"

    cleared = auth.clear_stored_cookie()
    assert cleared["cleared"] is True
    assert not path.exists()
