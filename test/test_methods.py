from pathlib import Path

from methods.get_event_handlers_config_path import get_event_handlers_config_path
from methods.get_parse_history_path import get_parse_history_path
from methods.get_task_path import get_task_path
from methods.get_webhook_event_path import get_webhook_event_path
from methods.is_assigned_to_rule_chief import is_assigned_to_rule_chief
from methods.load_callable import load_callable
from methods.read_json_file import read_json_file


def test_get_task_path():
    assert get_task_path("record-1") == Path("config") / "tasks" / "record-1.json"


def test_get_webhook_event_path():
    assert get_webhook_event_path("record-1") == (
        Path("data") / "webhook_events" / "record-1.json"
    )


def test_get_parse_history_path():
    assert get_parse_history_path("record-1") == (
        Path("config") / "parse_history" / "record-1.json"
    )


def test_read_json_file_uses_relative_path(tmp_path):
    file_path = tmp_path / "data" / "sample.json"
    file_path.parent.mkdir(parents=True)
    file_path.write_text('{"value": 1}', encoding="utf-8")

    assert read_json_file("data/sample.json", base_dir=tmp_path) == {"value": 1}


def test_read_json_file_rejects_absolute_path(tmp_path):
    file_path = tmp_path / "sample.json"
    file_path.write_text('{"value": 1}', encoding="utf-8")

    try:
        read_json_file(str(file_path), base_dir=tmp_path)
    except ValueError as exc:
        assert str(exc) == "relative_path must be relative"
    else:
        raise AssertionError("absolute path must be rejected")


def test_is_assigned_to_rule_chief():
    assert is_assigned_to_rule_chief({"assignee": "rule_chief"}, "rule_chief") is True
    assert is_assigned_to_rule_chief({"assignee": "another_rule"}, "rule_chief") is False
    assert is_assigned_to_rule_chief({"assignee": None}, "rule_chief") is False


def test_get_event_handlers_config_path():
    expected = Path(__file__).resolve().parent.parent / "config" / "event_handlers.json"
    assert get_event_handlers_config_path() == expected

def test_load_callable():
    handler = load_callable("handlers.webhook_received", "handle_webhook_received")
    assert callable(handler)


def test_load_callable_rejects_missing_function():
    try:
        load_callable("handlers.webhook_received", "missing_handler")
    except AttributeError as exc:
        assert "missing_handler" in str(exc)
    else:
        raise AssertionError("missing callable must be rejected")
