from __future__ import annotations

import asyncio
import json
import shutil
from pathlib import Path
from typing import Any

from core.logger import error, info
from event_bus import Event
from channel.manager import ChannelTask


_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_RULE_CONFIG = _PROJECT_ROOT / "config" / "rule_chief.json"


def _load_cleanup_rule(rule_name: str) -> dict[str, Any]:
    with _RULE_CONFIG.open("r", encoding="utf-8") as file:
        config = json.load(file)

    for rule in config.get("rules", []):
        if isinstance(rule, dict) and rule.get("name") == rule_name:
            cleanup = rule.get("cleanup")
            if isinstance(cleanup, dict):
                return cleanup

    raise ValueError(f"cleanup rule not found: {rule_name}")


def _resolve_target(relative_path: str, record_id: str) -> Path:
    return _PROJECT_ROOT / relative_path.replace("{record_id}", record_id)


def _delete_targets(record_id: str, targets: list[str]) -> None:
    for target in targets:
        path = _resolve_target(target, record_id)
        if path.exists():
            if not path.is_file():
                raise IsADirectoryError(f"cleanup target is not a file: {path}")
            path.unlink()
            info(f"[GarbageCleaner] DELETED record_id={record_id} path={path}")
        else:
            info(f"[GarbageCleaner] DELETE_SKIP record_id={record_id} path={path} reason=NOT_FOUND")


def _move_task(record_id: str, source: str, target: str) -> None:
    source_path = _resolve_target(source, record_id)
    target_path = _resolve_target(target, record_id)

    if not source_path.exists():
        raise FileNotFoundError(f"cleanup source not found: {source_path}")
    if not source_path.is_file():
        raise IsADirectoryError(f"cleanup source is not a file: {source_path}")

    target_path.parent.mkdir(parents=True, exist_ok=True)
    if target_path.exists():
        raise FileExistsError(f"cleanup target already exists: {target_path}")

    shutil.move(str(source_path), str(target_path))
    info(
        f"[GarbageCleaner] MOVED record_id={record_id} "
        f"source={source_path} target={target_path}"
    )


def _execute_cleanup(record_id: str, rule_name: str) -> str:
    cleanup = _load_cleanup_rule(rule_name)
    if not cleanup.get("enabled", True):
        raise RuntimeError(f"cleanup is disabled for rule: {rule_name}")

    action = cleanup.get("action")
    if action == "DELETE":
        targets = cleanup.get("targets")
        if not isinstance(targets, list):
            raise ValueError(f"DELETE rule targets must be a list: {rule_name}")
        _delete_targets(record_id, targets)
        return "SUCCESS"

    if action == "MOVE":
        source = cleanup.get("source")
        target = cleanup.get("target")
        if not isinstance(source, str) or not isinstance(target, str):
            raise ValueError(f"MOVE rule requires source and target: {rule_name}")
        _move_task(record_id, source, target)
        return "SUCCESS"

    raise ValueError(f"unsupported cleanup action: {action!r}")


async def execute_garbage_cleaner(task: ChannelTask) -> dict[str, str]:
    rule_name = task.route_rule
    if not rule_name:
        raise ValueError(f"garbage cleaner task is missing route_rule: {task.record_id}")

    info(
        f"[GarbageCleaner] START record_id={task.record_id} "
        f"rule={rule_name}"
    )

    try:
        result = await asyncio.to_thread(
            _execute_cleanup,
            task.record_id,
            rule_name,
        )
    except Exception as exc:
        error(
            f"[GarbageCleaner] FAILED record_id={task.record_id} "
            f"rule={rule_name} error={type(exc).__name__}: {exc}"
        )
        raise

    info(
        f"[GarbageCleaner] DONE record_id={task.record_id} "
        f"rule={rule_name} result={result}"
    )
    return {"status": result}
