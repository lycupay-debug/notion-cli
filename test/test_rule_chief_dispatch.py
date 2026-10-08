from __future__ import annotations

import json

from rule_chief import RuleChief


def _task(record_id: str, *, matched: bool) -> dict:
    return {
        "record_id": record_id,
        "assignee": None,
        "task_completed": None,
        "event_type": "page.properties_updated" if matched else "page.created",
        "author": {
            "is_bot": False,
            "is_person": True,
            "types": ["person"],
        },
        "entity": {"id": "page-id", "type": "page"},
        "parent": {
            "id": "parent-id",
            "type": "data_source",
            "data_source_id": "source-1",
        },
        "updated_properties": ["laTg"] if matched else [],
        "updated_blocks": [],
    }


def _rules() -> list[dict]:
    return [
        {
            "name": "SystemLedger",
            "enabled": True,
            "match": {
                "event_type": "page.properties_updated",
                "parent": {"data_source_id": "source-1"},
                "author": {"is_person": True, "types": ["person"]},
                "updated_properties": ["laTg"],
            },
            "task": {"enabled": True, "mode": "single"},
            "route": {"assignee": "system-ledger", "channel": "system_ledger"},
        }
    ]


def test_rule_chief_scans_all_pending_tasks_and_records_dispatch(tmp_path):
    task_dir = tmp_path / "tasks"
    dispatch_dir = tmp_path / "dispatch"
    task_dir.mkdir()

    first = task_dir / "routed.json"
    second = task_dir / "unmatched.json"

    first.write_text(json.dumps(_task("routed", matched=True)), encoding="utf-8")
    second.write_text(json.dumps(_task("unmatched", matched=False)), encoding="utf-8")

    decisions = RuleChief(
        _rules(),
        task_dir=task_dir,
        dispatch_dir=dispatch_dir,
    ).decide()

    assert [item.record_id for item in decisions] == ["routed"]

    updated = json.loads(first.read_text(encoding="utf-8"))
    assert updated["assignee"] == "system-ledger"
    assert updated["task_completed"] == "任务的已派发"

    dispatch = json.loads(
        (dispatch_dir / "routed.json").read_text(encoding="utf-8")
    )
    assert dispatch == {
        "assignee": "system-ledger",
        "task_completed": "任务的已派发",
    }

    assert not (dispatch_dir / "unmatched.json").exists()


def test_rule_chief_skips_tasks_already_in_dispatch_list(tmp_path):
    task_dir = tmp_path / "tasks"
    dispatch_dir = tmp_path / "dispatch"
    task_dir.mkdir()
    dispatch_dir.mkdir()

    task = task_dir / "routed.json"
    task.write_text(json.dumps(_task("routed", matched=True)), encoding="utf-8")
    (dispatch_dir / "routed.json").write_text(
        json.dumps(
            {
                "assignee": "system-ledger",
                "task_completed": "任务的已派发",
            }
        ),
        encoding="utf-8",
    )

    decisions = RuleChief(
        _rules(),
        task_dir=task_dir,
        dispatch_dir=dispatch_dir,
    ).decide()

    assert decisions == []
