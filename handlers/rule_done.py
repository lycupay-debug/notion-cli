from __future__ import annotations

from event_bus import Event


async def handle_rule_done(event: Event) -> None:
    """接收 RuleChief 完成事件，作为 Channel 阶段的正式入口。"""
    if event.event_type != "RULE_DONE":
        raise ValueError(f"unexpected event type: {event.event_type}")

    record_id = event.data.get("record_id")
    channel = event.data.get("channel")
    assignee = event.data.get("assignee")

    if not record_id:
        raise ValueError("RULE_DONE event is missing record_id")
    if not channel:
        raise ValueError("RULE_DONE event is missing channel")
    if not assignee:
        raise ValueError("RULE_DONE event is missing assignee")

    print(
        "[RuleDoneHandler] "
        f"record_id={record_id} "
        f"assignee={assignee} "
        f"channel={channel}"
    )
