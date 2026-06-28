from eight import CardResult, EightClient, SearchResult


def test_public_imports() -> None:
    assert EightClient
    assert CardResult(source="Eight: 登録名刺", name="山田").to_safe_dict() == {
        "source": "Eight: 登録名刺",
        "name": "山田",
    }
    assert (
        SearchResult(
            status="ok",
            query="山田",
            searched={"personal_cards": True, "eight_networks": False},
            personal=[],
            network=[],
        ).to_safe_dict()["query"]
        == "山田"
    )
