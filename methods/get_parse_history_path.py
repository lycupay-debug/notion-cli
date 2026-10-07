from __future__ import annotations

from pathlib import Path


def get_parse_history_path(record_id: str) -> Path:
    """返回 parse history 文件的相对路径。"""
    return Path("config") / "parse_history" / f"{record_id}.json"
