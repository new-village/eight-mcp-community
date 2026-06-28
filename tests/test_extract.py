from eight.extract import extract_network_people, extract_personal_cards


def test_extract_personal_cards_minimal_fields() -> None:
    data = {
        "personal_cards": [
            {
                "person": {
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
                    ]
                }
            }
        ]
    }

    rows = extract_personal_cards(data)

    assert [row.to_safe_dict() for row in rows] == [
        {
            "source": "Eight: 登録名刺",
            "name": "鈴木 太郎",
            "company": "東京商事",
            "department": "Compliance",
            "title": "Director",
            "updated": "2026-06-01",
            "confidence": "registered_card_match",
        }
    ]


def test_extract_network_people_deduplicates_and_limits() -> None:
    data = {
        "people": [
            {"name": "佐藤 花子", "company_name": "Example Inc", "title": "Manager"},
            {"name": "佐藤 花子", "company_name": "Example Inc", "title": "Manager"},
            {"name": "会社だけ"},
        ]
    }

    rows = extract_network_people(data, limit=10)

    assert [row.to_safe_dict() for row in rows] == [
        {
            "source": "Eight: 公開ネットワーク",
            "name": "佐藤 花子",
            "company": "Example Inc",
            "title": "Manager",
            "confidence": "public_network_match",
        }
    ]
