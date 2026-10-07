import json
from pathlib import Path

from methods.webhook_event import (
    get_author_ids,
    get_author_types,
    get_data_source_id,
    get_event_id,
    get_event_type,
    get_updated_properties,
    is_authored_by_bot,
    is_authored_by_person,
)


SAMPLE = {
    "record_id": "b10f81f8-ed8f-47d2-889e-04027e9a835d",
    "event_id": "93d6c3c1-deda-445c-addb-a76c9a401cf5",
    "received_at": "2026-10-07T06:12:52.214544+00:00",
    "source": "notion_webhook",
    "event_type": "page.properties_updated",
    "attempt_number": 1,
    "payload": {
        "id": "93d6c3c1-deda-445c-addb-a76c9a401cf5",
        "authors": [
            {
                "id": "3e1d872b-594c-8152-a31f-00026246ba3c",
                "type": "person",
            }
        ],
        "entity": {
            "id": "3eb7613b-20a9-816a-a6e9-e55fcbc05115",
            "type": "page",
        },
        "type": "page.properties_updated",
        "data": {
            "parent": {
                "id": "8581c831-f383-4ff2-bc9d-c276531b1004",
                "type": "database",
                "data_source_id": "9c7afd69-cba9-44c3-ae20-ad2886498e96",
            },
            "updated_properties": [
                "C%5EN%3D",
            ],
        },
    },
}


def test_event_attributes():
    assert get_event_id(SAMPLE) == "93d6c3c1-deda-445c-addb-a76c9a401cf5"
    assert get_event_type(SAMPLE) == "page.properties_updated"
    assert get_author_types(SAMPLE) == ["person"]
    assert get_author_ids(SAMPLE) == [
        "3e1d872b-594c-8152-a31f-00026246ba3c"
    ]
    assert get_data_source_id(SAMPLE) == "9c7afd69-cba9-44c3-ae20-ad2886498e96"
    assert get_updated_properties(SAMPLE) == ["C%5EN%3D"]


def test_author_is_person():
    assert is_authored_by_person(SAMPLE) is True
    assert is_authored_by_bot(SAMPLE) is False


def test_author_is_bot():
    sample = json.loads(json.dumps(SAMPLE))
    sample["payload"]["authors"] = [
        {
            "id": "bot-id",
            "type": "bot",
        }
    ]

    assert is_authored_by_bot(sample) is True
    assert is_authored_by_person(sample) is False


def test_mixed_authors():
    sample = json.loads(json.dumps(SAMPLE))
    sample["payload"]["authors"] = [
        {"id": "person-id", "type": "person"},
        {"id": "bot-id", "type": "bot"},
    ]

    assert is_authored_by_person(sample) is True
    assert is_authored_by_bot(sample) is True
