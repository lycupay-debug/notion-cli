from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.logger import info

@dataclass(frozen=True, slots=True)
class RuleDecision:
    status: str
    record_id: str
    assignee: str | None = None
    channel: str | None = None
    reason: str = ""
    task: dict[str, Any] | None = None
    rule_name: str | None = None

class RuleChief:
    """规则总管：只判断传入的单个 task，不扫描 config/tasks。"""

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
        info(f"[RuleChief] START record_id={record_id} rules={len(self.rules)}")
        decisions: list[RuleDecision] = []
        for index, rule in enumerate(self.rules):
            if not isinstance(rule, dict):
                info(f"[RuleChief] SKIP record_id={record_id} rule_index={index} reason=RULE_NOT_OBJECT")
                continue
            rule_name = rule.get("name") or f"rule_{index}"
            info(f"[RuleChief] CHECK record_id={record_id} rule={rule_name}")
            if not rule.get("enabled", True):
                info(f"[RuleChief] SKIP record_id={record_id} rule={rule_name} reason=DISABLED")
                continue
            matched, reason = self._matches_with_reason(rule.get("match") or {}, task)
            if not matched:
                info(f"[RuleChief] FAIL record_id={record_id} rule={rule_name} reason={reason}")
                continue
            task_config = rule.get("task") or {}
            if not task_config.get("enabled", True):
                info(f"[RuleChief] SKIP record_id={record_id} rule={rule_name} reason=TASK_DISABLED")
                continue
            route = rule.get("route") or {}
            assignee = route.get("assignee")
            channel = route.get("channel")
            if not assignee or not channel:
                decisions.append(RuleDecision(status="UNROUTED", record_id=record_id, reason="RULE_INCOMPLETE", task=task, rule_name=rule_name))
                info(f"[RuleChief] UNROUTED record_id={record_id} rule={rule_name} reason=RULE_INCOMPLETE")
                continue
            decisions.append(RuleDecision(status="ROUTED", record_id=record_id, assignee=assignee, channel=channel, task=self._build_task(task, task_config), rule_name=rule_name))
            info(f"[RuleChief] ROUTED record_id={record_id} rule={rule_name} assignee={assignee} channel={channel}")
        if not decisions:
            decisions = [RuleDecision(status="UNROUTED", record_id=record_id, reason="NO_RULE_MATCHED", task=task)]
            info(f"[RuleChief] DONE record_id={record_id} status=UNROUTED reason=NO_RULE_MATCHED")
        else:
            info(f"[RuleChief] DONE record_id={record_id} decisions={len(decisions)}")
        return decisions

    def _matches_with_reason(self, match: dict[str, Any], task: dict[str, Any]) -> tuple[bool, str]:
        if not isinstance(match, dict):
            return False, "MATCH_NOT_OBJECT"
        if "event_type" in match and task.get("event_type") != match["event_type"]:
            return False, f"event_type expected={match['event_type']} actual={task.get('event_type')}"
        parent_match = match.get("parent")
        if parent_match is not None:
            if not isinstance(parent_match, dict):
                return False, "parent MATCH_NOT_OBJECT"
            parent = task.get("parent") or {}
            for key, expected in parent_match.items():
                if parent.get(key) != expected:
                    return False, f"parent.{key} expected={expected} actual={parent.get(key)}"
        author_match = match.get("author")
        if author_match is not None:
            if not isinstance(author_match, dict):
                return False, "author MATCH_NOT_OBJECT"
            author = task.get("author") or {}
            if "is_person" in author_match and author.get("is_person") != author_match["is_person"]:
                return False, f"author.is_person expected={author_match['is_person']} actual={author.get('is_person')}"
            if "is_bot" in author_match and author.get("is_bot") != author_match["is_bot"]:
                return False, f"author.is_bot expected={author_match['is_bot']} actual={author.get('is_bot')}"
            if "types" in author_match:
                expected_types = author_match["types"]
                actual_types = author.get("types") or []
                if not isinstance(expected_types, list):
                    return False, "author.types EXPECTED_NOT_LIST"
                if not any(item in actual_types for item in expected_types):
                    return False, f"author.types expected_any={expected_types} actual={actual_types}"
        if "updated_properties" in match:
            expected = match["updated_properties"]
            actual = task.get("updated_properties") or []
            if not isinstance(expected, list):
                return False, "updated_properties EXPECTED_NOT_LIST"
            if not all(item in actual for item in expected):
                return False, f"updated_properties expected_all={expected} actual={actual}"
        return True, "MATCHED"

    @staticmethod
    def _build_task(task: dict[str, Any], task_config: dict[str, Any]) -> dict[str, Any]:
        mode = task_config.get("mode", "single")
        if mode == "single":
            return task
        raise ValueError(f"unsupported task mode: {mode}")
