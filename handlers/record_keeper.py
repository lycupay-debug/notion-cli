from __future__ import annotations

import json
from pathlib import Path

from core.logger import error, info
from event_bus import Event

_ALLOWED_RESULTS = {"SUCCESS", "UNCHANGED", "FAILED", "EXECUTE_FAILED"}
_TASK_DIR = Path("config") / "tasks"


async def handle_execution_result(event: Event) -> None:
    if event.event_type != "EXECUTION_RESULT":
        raise ValueError(f"unexpected event type: {event.event_type}")

    record_id = event.data.get("record_id")
    result = event.data.get("result")
    if not record_id:
        raise ValueError("EXECUTION_RESULT event is missing record_id")
    if result not in _ALLOWED_RESULTS:
        raise ValueError(f"unsupported execution result: {result!r}")

    task_path = _TASK_DIR / f"{record_id}.json"
    try:
        with task_path.open("r", encoding="utf-8") as file:
            task_data = json.load(file)
        if not isinstance(task_data, dict):
            raise ValueError(f"task is not an object: {record_id}")

        task_data["task_completed"] = result
        with task_path.open("w", encoding="utf-8") as file:
            json.dump(task_data, file, ensure_ascii=False, indent=2)
            file.write("\n")
    except Exception as exc:
        error(
            f"[RecordKeeper] FAILED record_id={record_id} "
            f"result={result} error={type(exc).__name__}: {exc}"
        )
        raise

    info(
        f"[RecordKeeper] RECORDED record_id={record_id} "
        f"task_completed={result} path={task_path}"
    )
