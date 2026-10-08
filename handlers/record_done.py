from __future__ import annotations

from core.logger import error, info
from event_bus import Event
from methods.read_json_file import read_json_file
from rule_chief import RuleChief


async def handle_record_done(event: Event) -> Event | None:
    if event.event_type != "RECORD_DONE":
        raise ValueError(f"unexpected event type: {event.event_type}")

    record_id = event.data.get("record_id")
    info(f"[RecordDoneHandler] START record_id={record_id}")

    try:
        config = read_json_file("config/rule_chief.json")
        rules = config.get("rules") if isinstance(config, dict) else None
        if not isinstance(rules, list):
            raise ValueError("rule chief config must contain array: rules")

        decisions = RuleChief(rules).decide()
        routed = [decision for decision in decisions if decision.status == "ROUTED"]

        info(
            f"[RecordDoneHandler] RULE_CHECK_DONE record_id={record_id} "
            f"routed={len(routed)}"
        )

        if not routed:
            return None

        return Event(
            "RULE_DONE",
            {
                "record_id": record_id or routed[0].record_id,
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
            f"[RecordDoneHandler] FAILED record_id={record_id} "
            f"error={type(exc).__name__}: {exc}"
        )
        raise
