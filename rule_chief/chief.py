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
    """规则总管：事件触发时扫描全部任务，只处理尚未进入任务派发清单的任务。"""

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

    def decide(self) -> list[RuleDecision]:
        """
        由一次事件触发全量扫描 config/tasks。

        任务是否已经派发，不依赖内存状态，而是通过
        config/task_dispatch_list/{record_id}.json 判断。
        """
        with self._dispatch_lock:
            return self._scan_and_dispatch()

    def _scan_and_dispatch(self) -> list[RuleDecision]:
        task_files = sorted(self.task_dir.glob("*.json"))
        info(
            f"[RuleChief] SCAN_START task_dir={self.task_dir} "
            f"task_count={len(task_files)} dispatch_dir={self.dispatch_dir}"
        )

        decisions: list[RuleDecision] = []

        for task_path in task_files:
            record_id = task_path.stem

            if self._is_dispatched(record_id):
                info(
                    f"[RuleChief] SKIP record_id={record_id} "
                    f"reason=ALREADY_DISPATCHED"
                )
                continue

            try:
                task = self.store.load(task_path)
            except Exception as exc:
                info(
                    f"[RuleChief] SKIP record_id={record_id} "
                    f"reason=TASK_LOAD_FAILED error={type(exc).__name__}: {exc}"
                )
                continue

            if not isinstance(task, dict):
                info(
                    f"[RuleChief] SKIP record_id={record_id} "
                    f"reason=TASK_NOT_OBJECT"
                )
                continue

            task_record_id = task.get("record_id") or record_id
            if task_record_id != record_id:
                info(
                    f"[RuleChief] SKIP record_id={record_id} "
                    f"reason=RECORD_ID_MISMATCH task_record_id={task_record_id}"
                )
                continue

            decision = self._decide_task(task)

            if decision.status != "ROUTED":
                info(
                    f"[RuleChief] UNROUTED record_id={record_id} "
                    f"reason={decision.reason or 'NO_RULE_MATCHED'}"
                )
                continue

            # 先更新任务本身，再写派发清单。
            # 如果此处之后进程崩溃，派发清单仍不存在，
            # 下一次事件触发时该任务仍会被重新检查。
            updated_task = dict(task)
            updated_task["assignee"] = decision.assignee
            updated_task["task_completed"] = self.DISPATCHED_STATUS
            self.store.save(task_path, updated_task)

            self._write_dispatch_record(
                record_id=record_id,
                assignee=decision.assignee,
                task_completed=self.DISPATCHED_STATUS,
            )

            decisions.append(
                RuleDecision(
                    status="ROUTED",
                    record_id=record_id,
                    assignee=decision.assignee,
                    channel=decision.channel,
                    reason=decision.reason,
                    task=updated_task,
                    rule_name=decision.rule_name,
                )
            )

            info(
                f"[RuleChief] DISPATCH_RECORDED record_id={record_id} "
                f"assignee={decision.assignee} channel={decision.channel}"
            )

        info(
            f"[RuleChief] SCAN_DONE task_count={len(task_files)} "
            f"routed={len(decisions)}"
        )
        return decisions

    def _decide_task(self, task: dict[str, Any]) -> RuleDecision:
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
                    f"reason=DISABLED"
                )
                continue

            matched, reason = self._matches_with_reason(
                rule.get("match") or {},
                task,
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
                    f"[RuleChief] SKIP record_id={record_id} "
                    f"rule={rule_name} reason=TASK_DISABLED"
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
                task=task,
                rule_name=rule_name,
            )

        return RuleDecision(
            status="UNROUTED",
            record_id=record_id,
            reason="NO_RULE_MATCHED",
            task=task,
        )

    def _is_dispatched(self, record_id: str) -> bool:
        return (self.dispatch_dir / f"{record_id}.json").exists()

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
