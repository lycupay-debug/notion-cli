from __future__ import annotations

from core.logger import info
from event_bus import Event
from methods.read_json_file import read_json_file
from rule_chief import RuleChief

RULE_DONE_EVENT = "RULE_DONE"


async def handle_new_task(event: Event) -> Event | None:
    task = event.data.get("task")
    if not isinstance(task, dict):
        raise ValueError("NEW_TASK event is missing task")

    record_id = task.get("record_id")
    info(f"[NewTaskHandler] START record_id={record_id}")

    config = read_json_file("config/rule_chief.json")
    rules = config.get("rules") if isinstance(config, dict) else None
    if not isinstance(rules, list):
        raise ValueError("rule chief config must contain array: rules")

    decisions = RuleChief(rules).decide(task)
    routed = [decision for decision in decisions if decision.status == "ROUTED"]

    for decision in decisions:
        info(
            f"[NewTaskHandler] MATCH record_id={decision.record_id} "
            f"rule={decision.rule_name or '-'} status={decision.status} "
            f"assignee={decision.assignee or '-'} channel={decision.channel or '-'} "
            f"reason={decision.reason or '-'}"
        )

    if not routed:
        info(f"[NewTaskHandler] STOP record_id={record_id} reason=NO_ROUTED_RULE")
        return None

    info(f"[NewTaskHandler] ROUTED record_id={record_id} count={len(routed)}")
    return Event(
        RULE_DONE_EVENT,
        {
            "record_id": record_id,
            "decisions": [
                {
                    "record_id": decision.record_id,
                    "assignee": decision.assignee,
                    "channel": decision.channel,
                    "reason": decision.reason,
                    "task": decision.task or task,
                    "rule_name": decision.rule_name,
                }
                for decision in routed
            ],
        },
    )
