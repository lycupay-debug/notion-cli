from __future__ import annotations

from typing import Any


RULE_CHIEF = "rule_chief"


def is_assigned_to_rule_chief(task: dict[str, Any]) -> bool:
    """判断任务当前是否由规则总管自己执行。"""
    return task.get("assignee") == RULE_CHIEF
