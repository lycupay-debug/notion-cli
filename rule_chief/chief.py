from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class RuleDecision:
    """RuleChief 对任务归属的纯判断结果。"""

    status: str
    record_id: str
    assignee: str | None = None
    channel: str | None = None
    reason: str = ""


class RuleChief:
    """规则总管。

    当前阶段只负责：
    1. 根据任务中的 data_source_id 查找显式规则；
    2. 产生归属/Channel 判断结果。

    当前不负责：
    - Notion API 调用；
    - Channel 排队；
    - 业务执行；
    - 修改任务 JSON。

    没有显式规则时必须返回 UNROUTED，禁止猜测业务归属。
    """

    def __init__(self, rules: dict[str, Any] | None = None) -> None:
        self.rules = rules or {}

    def decide(self, task: dict[str, Any]) -> RuleDecision:
        record_id = task.get("record_id")
        if not record_id:
            raise ValueError("task is missing record_id")

        parent = task.get("parent") or {}
        data_source_id = parent.get("data_source_id")
        if not data_source_id:
            return RuleDecision(
                status="UNROUTED",
                record_id=record_id,
                reason="DATA_SOURCE_ID_MISSING",
            )

        rule = self.rules.get(data_source_id)
        if not isinstance(rule, dict) or not rule.get("enabled", True):
            return RuleDecision(
                status="UNROUTED",
                record_id=record_id,
                reason="NO_RULE_CONFIGURED",
            )

        assignee = rule.get("assignee")
        channel = rule.get("channel")
        if not assignee or not channel:
            return RuleDecision(
                status="UNROUTED",
                record_id=record_id,
                reason="RULE_INCOMPLETE",
            )

        return RuleDecision(
            status="ROUTED",
            record_id=record_id,
            assignee=assignee,
            channel=channel,
        )
