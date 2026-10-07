from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class RuleDecision:
    """RuleChief 对单条规则命中的判断结果。"""

    status: str
    record_id: str
    assignee: str | None = None
    channel: str | None = None
    reason: str = ""
    task: dict[str, Any] | None = None
    rule_name: str | None = None


class RuleChief:
    """规则总管。

    RuleChief 只负责规则匹配、任务粒度判断和执行路由。
    不调用 Notion API，不排队，不执行 Channel，不修改任务 JSON。

    一次事件允许命中多条规则；每条命中规则独立产生一个 RuleDecision。
    """

    def __init__(self, rules: list[dict[str, Any]] | None = None) -> None:
        if rules is None:
            rules = []
        if not isinstance(rules, list):
            raise TypeError("rules must be a list")
        self.rules = rules

    def decide(self, task: dict[str, Any]) -> list[RuleDecision]:
        record_id = task.get("record_id")
        if not record_id:
            raise ValueError("task is missing record_id")

        decisions: list[RuleDecision] = []

        for index, rule in enumerate(self.rules):
            if not isinstance(rule, dict):
                continue
            if not rule.get("enabled", True):
                continue
            if not self._matches(rule.get("match") or {}, task):
                continue

            task_config = rule.get("task") or {}
            if not task_config.get("enabled", True):
                continue

            route = rule.get("route") or {}
            assignee = route.get("assignee")
            channel = route.get("channel")
            rule_name = rule.get("name") or f"rule_{index}"

            if not assignee or not channel:
                decisions.append(RuleDecision(
                    status="UNROUTED",
                    record_id=record_id,
                    reason="RULE_INCOMPLETE",
                    task=task,
                    rule_name=rule_name,
                ))
                continue

            decisions.append(RuleDecision(
                status="ROUTED",
                record_id=record_id,
                assignee=assignee,
                channel=channel,
                task=self._build_task(task, task_config),
                rule_name=rule_name,
            ))

        if not decisions:
            return [RuleDecision(
                status="UNROUTED",
                record_id=record_id,
                reason="NO_RULE_MATCHED",
                task=task,
            )]

        return decisions

    def _matches(self, match: dict[str, Any], task: dict[str, Any]) -> bool:
        if not isinstance(match, dict):
            return False

        if "event_type" in match and task.get("event_type") != match["event_type"]:
            return False

        parent_match = match.get("parent")
        if parent_match is not None:
            if not isinstance(parent_match, dict):
                return False
            parent = task.get("parent") or {}
            for key, expected in parent_match.items():
                if parent.get(key) != expected:
                    return False

        author_match = match.get("author")
        if author_match is not None:
            if not isinstance(author_match, dict):
                return False
            author = task.get("author") or {}

            if "is_person" in author_match and author.get("is_person") != author_match["is_person"]:
                return False
            if "is_bot" in author_match and author.get("is_bot") != author_match["is_bot"]:
                return False
            if "types" in author_match:
                expected_types = author_match["types"]
                actual_types = author.get("types") or []
                if not isinstance(expected_types, list):
                    return False
                if not any(item in actual_types for item in expected_types):
                    return False

        if "updated_properties" in match:
            expected = match["updated_properties"]
            actual = task.get("updated_properties") or []
            if not isinstance(expected, list):
                return False
            if not all(item in actual for item in expected):
                return False

        return True

    @staticmethod
    def _build_task(task: dict[str, Any], task_config: dict[str, Any]) -> dict[str, Any]:
        mode = task_config.get("mode", "single")
        if mode == "single":
            return task
        raise ValueError(f"unsupported task mode: {mode}")
