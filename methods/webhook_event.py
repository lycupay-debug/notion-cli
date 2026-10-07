from __future__ import annotations

from typing import Any


def get_record_id(record: dict[str, Any]) -> str | None:
    return record.get("record_id")


def get_event_id(record: dict[str, Any]) -> str | None:
    return record.get("event_id")


def get_received_at(record: dict[str, Any]) -> str | None:
    return record.get("received_at")


def get_source(record: dict[str, Any]) -> str | None:
    return record.get("source")


def get_event_type(record: dict[str, Any]) -> str | None:
    return record.get("event_type")


def get_attempt_number(record: dict[str, Any]) -> int | None:
    return record.get("attempt_number")


def get_payload(record: dict[str, Any]) -> dict[str, Any]:
    payload = record.get("payload")
    return payload if isinstance(payload, dict) else {}


def get_timestamp(record: dict[str, Any]) -> str | None:
    return get_payload(record).get("timestamp")


def get_workspace_id(record: dict[str, Any]) -> str | None:
    return get_payload(record).get("workspace_id")


def get_workspace_name(record: dict[str, Any]) -> str | None:
    return get_payload(record).get("workspace_name")


def get_subscription_id(record: dict[str, Any]) -> str | None:
    return get_payload(record).get("subscription_id")


def get_integration_id(record: dict[str, Any]) -> str | None:
    return get_payload(record).get("integration_id")


def get_authors(record: dict[str, Any]) -> list[dict[str, Any]]:
    authors = get_payload(record).get("authors")
    return authors if isinstance(authors, list) else []


def get_author_types(record: dict[str, Any]) -> list[str]:
    return [
        author.get("type")
        for author in get_authors(record)
        if isinstance(author, dict) and isinstance(author.get("type"), str)
    ]


def get_author_ids(record: dict[str, Any]) -> list[str]:
    return [
        author.get("id")
        for author in get_authors(record)
        if isinstance(author, dict) and isinstance(author.get("id"), str)
    ]


def is_authored_by_bot(record: dict[str, Any]) -> bool:
    return any(author_type == "bot" for author_type in get_author_types(record))


def is_authored_by_person(record: dict[str, Any]) -> bool:
    return any(author_type == "person" for author_type in get_author_types(record))


def get_entity(record: dict[str, Any]) -> dict[str, Any]:
    entity = get_payload(record).get("entity")
    return entity if isinstance(entity, dict) else {}


def get_entity_id(record: dict[str, Any]) -> str | None:
    return get_entity(record).get("id")


def get_entity_type(record: dict[str, Any]) -> str | None:
    return get_entity(record).get("type")


def get_data(record: dict[str, Any]) -> dict[str, Any]:
    data = get_payload(record).get("data")
    return data if isinstance(data, dict) else {}


def get_parent(record: dict[str, Any]) -> dict[str, Any]:
    parent = get_data(record).get("parent")
    return parent if isinstance(parent, dict) else {}


def get_parent_id(record: dict[str, Any]) -> str | None:
    return get_parent(record).get("id")


def get_parent_type(record: dict[str, Any]) -> str | None:
    return get_parent(record).get("type")


def get_data_source_id(record: dict[str, Any]) -> str | None:
    return get_parent(record).get("data_source_id")


def get_updated_properties(record: dict[str, Any]) -> list[str]:
    properties = get_data(record).get("updated_properties")
    return properties if isinstance(properties, list) else []


def get_updated_blocks(record: dict[str, Any]) -> list[dict[str, Any]]:
    blocks = get_data(record).get("updated_blocks")
    return blocks if isinstance(blocks, list) else []
