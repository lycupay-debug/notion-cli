from __future__ import annotations

from event_bus import Event
from rule_chief import RuleChief


async def handle_new_task(event: Event) -> None:
    """处理 NEW_TASK；当前只完成 RuleChief 判断，不进入 Channel。"""
    task = event.data.get("task")
    if not isinstance(task, dict):
        raise ValueError("NEW_TASK event is missing task")

    decision = RuleChief().decide(task)
    print(
        "[NewTaskHandler] "
        f"record_id={decision.record_id} "
        f"status={decision.status} "
        f"assignee={decision.assignee} "
        f"channel={decision.channel} "
        f"reason={decision.reason}"
    )
