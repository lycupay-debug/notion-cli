from __future__ import annotations

from pathlib import Path


def get_webhook_event_path(record_id: str) -> Path:
    """返回 webhook event 文件的相对路径。"""
    return Path("data") / "webhook_events" / f"{record_id}.json"
