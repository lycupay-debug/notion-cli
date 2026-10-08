from __future__ import annotations

from core.logger import error, info
from event_bus import Event
from methods.read_json_file import read_json_file
from rule_chief import RuleChief

RULE_DONE_EVENT = "RULE_DONE"


async def handle_new_task(event: Event) -> Event | None:
    if event.event_type != "NEW_TASK":
        raise ValueError(f"unexpected event type: {event.event_type}")

    trigger_record_id = event.data.get("record_id")
    info(
        f"[NewTaskHandler] START trigger_record_id={trigger_record_id} "
        "mode=FULL_TASK_SCAN"
    )

    try:
        config = read_json_file("config/rule_chief.json")
        rules = config.get("rules") if isinstance(config, dict) else None
        if not isinstance(rules, list):
            raise ValueError("rule chief config must contain array: rules")

        info(
            f"[NewTaskHandler] RULE_CONFIG_LOADED "
            f"trigger_record_id={trigger_record_id} rules={len(rules)}"
        )

        decisions = RuleChief(rules).decide()
        routed = [decision for decision in decisions if decision.status == "ROUTED"]

        for decision in decisions:
            info(
                f"[NewTaskHandler] DECISION record_id={decision.record_id} "
                f"rule={decision.rule_name or '-'} status={decision.status} "
                f"assignee={decision.assignee or '-'} "
                f"channel={decision.channel or '-'} "
                f"reason={decision.reason or '-'}"
            )

        if not routed:
            info(
                f"[NewTaskHandler] STOP trigger_record_id={trigger_record_id} "
                "reason=NO_PENDING_ROUTED_TASK"
            )
            return None

        info(
            f"[NewTaskHandler] ROUTED trigger_record_id={trigger_record_id} "
            f"count={len(routed)} next={RULE_DONE_EVENT}"
        )

        return Event(
            RULE_DONE_EVENT,
            {
                "record_id": trigger_record_id or routed[0].record_id,
                "decisions": [
                    {
                        "record_id": decision.record_id,
                        "assignee": decision.assignee,
                        "channel": decision.channel,
                        "reason": decision.reason,
                        "task": decision.task,
                        "rule_name": decision.rule_name,
                    }
                    for decision in routed
                ],
            },
        )
    except Exception as exc:
        error(
            f"[NewTaskHandler] FAILED trigger_record_id={trigger_record_id} "
            f"error={type(exc).__name__}: {exc}"
        )
        raise
