from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def get_event_handlers_config_path() -> Path:
    """返回事件 Handler 注册配置文件路径。"""
    return PROJECT_ROOT / "config" / "event_handlers.json"
