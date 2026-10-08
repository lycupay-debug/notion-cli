from __future__ import annotations

from core.logger import error, info
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

    try:
        config = read_json_file("config/rule_chief.json")
        rules = config.get("rules") if isinstance(config, dict) else None
        if not isinstance(rules, list):
            raise ValueError("rule chief config must contain array: rules")
        info(f"[NewTaskHandler] RULE_CONFIG_LOADED record_id={record_id} rules={len(rules)}")

        decisions = RuleChief(rules).decide(task)
        routed = [decision for decision in decisions if decision.status == "ROUTED"]

        for decision in decisions:
            info(f"[NewTaskHandler] DECISION record_id={decision.record_id} rule={decision.rule_name or '-'} status={decision.status} assignee={decision.assignee or '-'} channel={decision.channel or '-'} reason={decision.reason or '-'}")

        if not routed:
            info(f"[NewTaskHandler] STOP record_id={record_id} reason=NO_ROUTED_RULE")
            return None

        info(f"[NewTaskHandler] ROUTED record_id={record_id} count={len(routed)} next={RULE_DONE_EVENT}")
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
    except Exception as exc:
        error(f"[NewTaskHandler] FAILED record_id={record_id} error={type(exc).__name__}: {exc}")
        raise
