from __future__ import annotations

from event_bus import Event
from methods.read_json_file import read_json_file
from rule_chief import RuleChief


RULE_DONE_EVENT = "RULE_DONE"


async def handle_new_task(event: Event) -> None:
    """处理 NEW_TASK；当前只完成 RuleChief 判断，不进入 Channel。"""
    task = event.data.get("task")
    if not isinstance(task, dict):
        raise ValueError("NEW_TASK event is missing task")

    config = read_json_file("config/rule_chief.json")
    if not isinstance(config, dict):
        raise ValueError("rule chief config must be an object")

    rules = config.get("rules")
    if not isinstance(rules, dict):
        raise ValueError("rule chief config must contain object: rules")

    decision = RuleChief(rules).decide(task)
    if decision.status != "ROUTED":
        print(
            "[NewTaskHandler] "
            f"record_id={decision.record_id} "
            f"status={decision.status} "
            f"reason={decision.reason}"
        )
        return None

    print(
        "[NewTaskHandler] "
        f"record_id={decision.record_id} "
        f"status={decision.status} "
        f"assignee={decision.assignee} "
        f"channel={decision.channel}"
    )

    return Event(
        RULE_DONE_EVENT,
        {
            "record_id": decision.record_id,
            "assignee": decision.assignee,
            "channel": decision.channel,
            "reason": decision.reason,
            "task": task,
        },
    )
