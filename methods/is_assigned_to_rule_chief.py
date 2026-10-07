from __future__ import annotations

from typing import Any


def is_assigned_to_rule_chief(
    task: dict[str, Any],
    rule_chief_id: str,
) -> bool:
    """判断任务当前是否由指定的规则总管执行。"""
    return task.get("assignee") == rule_chief_id
