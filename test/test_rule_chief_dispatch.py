from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor

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


def test_rule_chief_decides_only_triggered_task(tmp_path):
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
    ).decide("routed")

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

    # 未被事件触发的任务不会被增量路径顺带处理。
    assert not (dispatch_dir / "unmatched.json").exists()


def test_rule_chief_compensation_scan_finds_task_without_event(tmp_path):
    task_dir = tmp_path / "tasks"
    dispatch_dir = tmp_path / "dispatch"
    task_dir.mkdir()

    task = task_dir / "missed-event.json"
    task.write_text(
        json.dumps(_task("missed-event", matched=True)),
        encoding="utf-8",
    )

    decisions = RuleChief(
        _rules(),
        task_dir=task_dir,
        dispatch_dir=dispatch_dir,
    ).scan_pending()

    assert [item.record_id for item in decisions] == ["missed-event"]
    assert (dispatch_dir / "missed-event.json").exists()


def test_rule_chief_skips_task_already_in_dispatch_list(tmp_path):
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
    ).decide("routed")

    assert decisions == []


def test_rule_chief_serializes_burst_of_incremental_events(tmp_path):
    task_dir = tmp_path / "tasks"
    dispatch_dir = tmp_path / "dispatch"
    task_dir.mkdir()

    record_ids = [f"routed-{index}" for index in range(100)]
    for record_id in record_ids:
        (task_dir / f"{record_id}.json").write_text(
            json.dumps(_task(record_id, matched=True)),
            encoding="utf-8",
        )

    chief = RuleChief(
        _rules(),
        task_dir=task_dir,
        dispatch_dir=dispatch_dir,
    )

    def dispatch(record_id: str) -> str:
        decisions = chief.decide(record_id)
        assert len(decisions) == 1
        return decisions[0].record_id

    with ThreadPoolExecutor(max_workers=16) as executor:
        results = list(executor.map(dispatch, record_ids))

    assert sorted(results) == sorted(record_ids)

    for record_id in record_ids:
        dispatch_path = dispatch_dir / f"{record_id}.json"
        assert dispatch_path.exists()
        data = json.loads(dispatch_path.read_text(encoding="utf-8"))
        assert data["assignee"] == "system-ledger"
        assert data["task_completed"] == "任务的已派发"
