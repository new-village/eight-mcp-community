from eight import CardResult, EightClient, SearchResult


def test_public_imports() -> None:
    assert EightClient
    assert CardResult(source="Eight: 登録名刺", name="鈴木").to_safe_dict() == {
        "source": "Eight: 登録名刺",
        "name": "鈴木",
    }
    assert (
        SearchResult(
            status="ok",
            query="鈴木",
            searched={"personal_cards": True, "eight_networks": False},
            personal=[],
            network=[],
        ).to_safe_dict()["query"]
        == "鈴木"
    )
