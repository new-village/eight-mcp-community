from eight.extract import (
    extract_network_companies,
    extract_network_people,
    extract_personal_cards,
)


def test_extract_personal_cards_minimal_fields() -> None:
    data = {
        "personal_cards": [
            {
                "person": {
                    "id": 123,
                    "personal_cards": [
                        {
                            "friend_card": {
                                "front_full_name": "鈴木 太郎",
                                "front_company_name": "東京商事",
                                "front_department": "Compliance",
                                "front_title": "Director",
                            },
                            "personal_card_updated_at": "2026-06-01",
                        }
                    ],
                }
            }
        ]
    }

    rows = extract_personal_cards(data)

    assert [row.to_safe_dict() for row in rows] == [
        {
            "source": "Eight: 登録名刺",
            "id": "registered:123",
            "name": "鈴木 太郎",
            "company": "東京商事",
            "department": "Compliance",
            "title": "Director",
            "updated": "2026-06-01",
            "confidence": "registered_card_match",
        }
    ]


def test_extract_personal_cards_includes_match_reason_for_memo_hit() -> None:
    data = {
        "personal_cards": [
            {
                "person": {
                    "personal_cards": [
                        {
                            "friend_card": {
                                "front_full_name": "鈴木 太郎",
                                "front_company_name": "東京商事",
                                "front_title": "Director",
                                "memo": "展示会で高橋さんから紹介。次回相談予定。",
                            }
                        }
                    ]
                }
            }
        ]
    }

    rows = extract_personal_cards(data, query="高橋")

    assert rows[0].to_safe_dict()["matched_fields"] == ["memo"]
    assert rows[0].to_safe_dict()["match_excerpt"] == "展示会で高橋さんから紹介。次回相談予定。"


def test_extract_network_people_uses_explicit_people_bucket() -> None:
    data = {
        "companies": [{"company_id": 1, "company_name": "Example Inc"}],
        "eight_users": [
            {
                "person_id": 10,
                "name": "佐藤 花子",
                "company_name": "Example Inc",
                "title": "Manager",
            },
            {
                "person_id": 10,
                "name": "佐藤 花子",
                "company_name": "Example Inc",
                "title": "Manager",
            },
        ],
    }

    rows = extract_network_people(data, limit=10)

    assert [row.to_safe_dict() for row in rows] == [
        {
            "source": "Eight: 公開ネットワーク",
            "id": "network:10",
            "name": "佐藤 花子",
            "company": "Example Inc",
            "title": "Manager",
            "confidence": "public_network_match",
        }
    ]


def test_extract_network_people_falls_back_for_older_shapes() -> None:
    data = {
        "people": [
            {"name": "佐藤 花子", "company_name": "Example Inc", "title": "Manager"},
            {"name": "会社だけ"},
        ]
    }

    rows = extract_network_people(data, limit=10)

    assert rows[0].to_safe_dict()["name"] == "佐藤 花子"
    assert "id" not in rows[0].to_safe_dict()


def test_extract_network_people_never_reads_company_bucket() -> None:
    data = {"companies": [{"company_id": 1, "name": "Example Inc", "company_name": "Example Inc"}]}

    assert extract_network_people(data, limit=10) == []


def test_extract_network_companies_deduplicates_and_limits() -> None:
    data = {
        "companies": [
            {"company_id": 1, "company_name": "Example Inc", "address": "Tokyo"},
            {"company_id": 1, "company_name": "Example Inc", "address": "Tokyo"},
            {"company_id": 2, "company_name": "Other Inc"},
        ]
    }

    rows = extract_network_companies(data, limit=1)

    assert [row.to_safe_dict() for row in rows] == [
        {
            "source": "Eight: 公開ネットワーク法人",
            "id": "company:1",
            "name": "Example Inc",
            "address": "Tokyo",
            "confidence": "public_network_company_match",
        }
    ]
