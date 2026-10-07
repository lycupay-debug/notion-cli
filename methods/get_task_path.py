from __future__ import annotations

from pathlib import Path


def get_task_path(record_id: str) -> Path:
    """返回任务文件的相对路径。"""
    return Path("config") / "tasks" / f"{record_id}.json"
