from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any

from core.json_store import JSONStore
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
    """规则总管：事件驱动单任务判定 + 低频全量补偿扫描。"""

    DISPATCH_DIR = Path("config") / "任务派发清单"
    TASK_DIR = Path("config") / "tasks"
    DISPATCHED_STATUS = "任务的已派发"
    _dispatch_lock = Lock()

    def __init__(
        self,
        rules: list[dict[str, Any]] | None = None,
        task_dir: str | Path | None = None,
        dispatch_dir: str | Path | None = None,
    ) -> None:
        if rules is None:
            rules = []
        if not isinstance(rules, list):
            raise TypeError("rules must be a list")

        self.rules = rules
        self.project_root = Path(__file__).resolve().parent.parent
        self.task_dir = (
            Path(task_dir).resolve()
            if task_dir is not None
            else self.project_root / self.TASK_DIR
        )
        self.dispatch_dir = (
            Path(dispatch_dir).resolve()
            if dispatch_dir is not None
            else self.project_root / self.DISPATCH_DIR
        )
        self.store = JSONStore(base_dir=self.project_root)

    def decide(self, record_id: str) -> list[RuleDecision]:
        """事件驱动路径：只判定指定 record_id。"""
        if not record_id:
            raise ValueError("record_id is required for incremental decision")

        with self._dispatch_lock:
            decision = self._process_task(record_id)
            return [decision] if decision.status == "ROUTED" else []

    def scan_pending(self) -> list[RuleDecision]:
        """补偿路径：低频扫描全部任务，弥补事件丢失/进程重启造成的遗漏。"""
        with self._dispatch_lock:
            task_files = sorted(self.task_dir.glob("*.json"))
            info(
                f"[RuleChief] COMPENSATION_SCAN_START task_dir={self.task_dir} "
                f"task_count={len(task_files)} dispatch_dir={self.dispatch_dir}"
            )

            decisions: list[RuleDecision] = []
            for task_path in task_files:
                decision = self._process_task(task_path.stem)
                if decision.status == "ROUTED":
                    decisions.append(decision)

            info(
                f"[RuleChief] COMPENSATION_SCAN_DONE task_count={len(task_files)} "
                f"routed={len(decisions)}"
            )
            return decisions

    def _process_task(self, record_id: str) -> RuleDecision:
        task_path = self.task_dir / f"{record_id}.json"

        if not task_path.exists():
            info(
                f"[RuleChief] SKIP record_id={record_id} "
                "reason=TASK_NOT_FOUND"
            )
            return RuleDecision(
                status="UNROUTED",
                record_id=record_id,
                reason="TASK_NOT_FOUND",
            )

        if self._is_dispatched(record_id, task_path):
            info(
                f"[RuleChief] SKIP record_id={record_id} "
                "reason=ALREADY_DISPATCHED"
            )
            return RuleDecision(
                status="SKIPPED",
                record_id=record_id,
                reason="ALREADY_DISPATCHED",
            )

        try:
            task = self.store.load(task_path)
        except Exception as exc:
            info(
                f"[RuleChief] SKIP record_id={record_id} "
                f"reason=TASK_LOAD_FAILED error={type(exc).__name__}: {exc}"
            )
            return RuleDecision(
                status="UNROUTED",
                record_id=record_id,
                reason="TASK_LOAD_FAILED",
            )

        if not isinstance(task, dict):
            info(
                f"[RuleChief] SKIP record_id={record_id} "
                "reason=TASK_NOT_OBJECT"
            )
            return RuleDecision(
                status="UNROUTED",
                record_id=record_id,
                reason="TASK_NOT_OBJECT",
            )

        task_record_id = task.get("record_id") or record_id
        if task_record_id != record_id:
            info(
                f"[RuleChief] SKIP record_id={record_id} "
                f"reason=RECORD_ID_MISMATCH task_record_id={task_record_id}"
            )
            return RuleDecision(
                status="UNROUTED",
                record_id=record_id,
                reason="RECORD_ID_MISMATCH",
                task=task,
            )

        decision = self._decide_task(task, task_path)

        if decision.status != "ROUTED":
            info(
                f"[RuleChief] UNROUTED record_id={record_id} "
                f"reason={decision.reason or 'NO_RULE_MATCHED'}"
            )
            return decision

        # 先更新任务，再写派发清单。
        # 若进程在两步之间崩溃，补偿扫描会重新检查该任务。
        updated_task = dict(task)
        updated_task["assignee"] = decision.assignee
        updated_task["task_completed"] = self.DISPATCHED_STATUS
        self.store.save(task_path, updated_task)

        self._write_dispatch_record(
            record_id=record_id,
            assignee=decision.assignee,
            task_completed=self.DISPATCHED_STATUS,
        )

        result = RuleDecision(
            status="ROUTED",
            record_id=record_id,
            assignee=decision.assignee,
            channel=decision.channel,
            reason=decision.reason,
            task=updated_task,
            rule_name=decision.rule_name,
        )

        info(
            f"[RuleChief] DISPATCH_RECORDED record_id={record_id} "
            f"assignee={decision.assignee} channel={decision.channel}"
        )
        return result

    def _decide_task(self, task: dict[str, Any], task_path: Path) -> RuleDecision:
        record_id = task.get("record_id")
        if not record_id:
            return RuleDecision(
                status="UNROUTED",
                record_id="",
                reason="TASK_MISSING_RECORD_ID",
                task=task,
            )

        info(f"[RuleChief] CHECK_TASK record_id={record_id} rules={len(self.rules)}")

        for index, rule in enumerate(self.rules):
            if not isinstance(rule, dict):
                info(
                    f"[RuleChief] SKIP record_id={record_id} "
                    f"rule_index={index} reason=RULE_NOT_OBJECT"
                )
                continue

            rule_name = rule.get("name") or f"rule_{index}"
            info(f"[RuleChief] CHECK record_id={record_id} rule={rule_name}")

            if not rule.get("enabled", True):
                info(
                    f"[RuleChief] SKIP record_id={record_id} rule={rule_name} "
                    "reason=DISABLED"
                )
                continue

            matched, reason = self._matches_with_reason(
                rule.get("match") or {},
                task,
                task_path,
            )
            if not matched:
                info(
                    f"[RuleChief] FAIL record_id={record_id} "
                    f"rule={rule_name} reason={reason}"
                )
                continue

            task_config = rule.get("task") or {}
            if not task_config.get("enabled", True):
                info(
                    f"[RuleChief] SKIP record_id={record_id} rule={rule_name} "
                    "reason=TASK_DISABLED"
                )
                continue

            route = rule.get("route") or {}
            assignee = route.get("assignee")
            channel = route.get("channel")

            if not assignee or not channel:
                info(
                    f"[RuleChief] UNROUTED record_id={record_id} "
                    f"rule={rule_name} reason=RULE_INCOMPLETE"
                )
                continue

            info(
                f"[RuleChief] ROUTED record_id={record_id} "
                f"rule={rule_name} assignee={assignee} channel={channel}"
            )
            return RuleDecision(
                status="ROUTED",
                record_id=record_id,
                assignee=assignee,
                channel=channel,
                reason=reason,
                task=task,
                rule_name=rule_name,
            )

        return RuleDecision(
            status="UNROUTED",
            record_id=record_id,
            reason="NO_RULE_MATCHED",
            task=task,
        )

    def _is_dispatched(self, record_id: str, task_path: Path) -> bool:
        dispatch_path = self.dispatch_dir / f"{record_id}.json"
        if not dispatch_path.exists():
            return False

        try:
            dispatch = self.store.load(dispatch_path)
            task = self.store.load(task_path)
        except Exception as exc:
            info(
                f"[RuleChief] DISPATCH_CHECK_FAILED record_id={record_id} "
                f"error={type(exc).__name__}: {exc}"
            )
            return True

        if not isinstance(dispatch, dict) or not isinstance(task, dict):
            return True

        same_assignee = dispatch.get("assignee") == task.get("assignee")
        same_completion = dispatch.get("task_completed") == task.get("task_completed")

        if same_assignee and same_completion:
            return True

        info(
            f"[RuleChief] DISPATCH_STAGE_CHANGED record_id={record_id} "
            f"dispatch=({dispatch.get('assignee')},{dispatch.get('task_completed')}) "
            f"task=({task.get('assignee')},{task.get('task_completed')})"
        )
        return False

    def _write_dispatch_record(
        self,
        record_id: str,
        assignee: str | None,
        task_completed: str,
    ) -> None:
        path = self.dispatch_dir / f"{record_id}.json"
        data = {
            "assignee": assignee,
            "task_completed": task_completed,
        }
        self.store.save(path, data)

    def _matches_with_reason(
        self,
        match: dict[str, Any],
        task: dict[str, Any],
        task_path: Path,
    ) -> tuple[bool, str]:
        if not isinstance(match, dict):
            return False, "MATCH_NOT_OBJECT"

        if "event_type" in match and task.get("event_type") != match["event_type"]:
            return (
                False,
                f"event_type expected={match['event_type']} "
                f"actual={task.get('event_type')}",
            )

        parent_match = match.get("parent")
        if parent_match is not None:
            if not isinstance(parent_match, dict):
                return False, "parent MATCH_NOT_OBJECT"
            parent = task.get("parent") or {}
            for key, expected in parent_match.items():
                if parent.get(key) != expected:
                    return (
                        False,
                        f"parent.{key} expected={expected} "
                        f"actual={parent.get(key)}",
                    )

        author_match = match.get("author")
        if author_match is not None:
            if not isinstance(author_match, dict):
                return False, "author MATCH_NOT_OBJECT"

            author = task.get("author") or {}

            if (
                "is_person" in author_match
                and author.get("is_person") != author_match["is_person"]
            ):
                return (
                    False,
                    f"author.is_person expected={author_match['is_person']} "
                    f"actual={author.get('is_person')}",
                )

            if (
                "is_bot" in author_match
                and author.get("is_bot") != author_match["is_bot"]
            ):
                return (
                    False,
                    f"author.is_bot expected={author_match['is_bot']} "
                    f"actual={author.get('is_bot')}",
                )

            if "types" in author_match:
                expected_types = author_match["types"]
                actual_types = author.get("types") or []

                if not isinstance(expected_types, list):
                    return False, "author.types EXPECTED_NOT_LIST"

                if not any(item in actual_types for item in expected_types):
                    return (
                        False,
                        f"author.types expected_any={expected_types} "
                        f"actual={actual_types}",
                    )

        for field_name in ("assignee", "task_completed"):
            if field_name not in match:
                continue

            condition = match[field_name]
            actual = task.get(field_name)

            if isinstance(condition, dict):
                if condition.get("is_null") is True and actual is not None:
                    return False, f"{field_name} expected=null actual={actual}"

                if condition.get("not_null") is True and actual is None:
                    return False, f"{field_name} expected=NOT_NULL actual=null"

                if "equals" in condition and actual != condition["equals"]:
                    return False, f"{field_name} expected={condition['equals']} actual={actual}"

                if "in" in condition:
                    expected_values = condition["in"]
                    if not isinstance(expected_values, list):
                        return False, f"{field_name}.in EXPECTED_LIST"
                    if actual not in expected_values:
                        return False, f"{field_name} expected_any={expected_values} actual={actual}"
            else:
                if actual != condition:
                    return False, f"{field_name} expected={condition} actual={actual}"

        created_time = match.get("created_time")
        if created_time is not None:
            if not isinstance(created_time, dict):
                return False, "created_time MATCH_NOT_OBJECT"

            older_than_minutes = created_time.get("older_than_minutes")
            if older_than_minutes is not None:
                try:
                    older_than_minutes = float(older_than_minutes)
                except (TypeError, ValueError):
                    return False, "created_time.older_than_minutes INVALID"

                if older_than_minutes < 0:
                    return False, "created_time.older_than_minutes NEGATIVE"

                import time

                age_seconds = time.time() - task_path.stat().st_ctime
                required_seconds = older_than_minutes * 60
                if age_seconds < required_seconds:
                    return (
                        False,
                        f"created_time age_seconds={age_seconds:.1f} required_seconds={required_seconds:.1f}",
                    )

        if "updated_properties" in match:
            expected = match["updated_properties"]
            actual = task.get("updated_properties") or []

            if not isinstance(expected, list):
                return False, "updated_properties EXPECTED_NOT_LIST"

            if not all(item in actual for item in expected):
                return (
                    False,
                    f"updated_properties expected_all={expected} "
                    f"actual={actual}",
                )

        return True, "MATCHED"
