from __future__ import annotations

import threading
from datetime import datetime
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_LOG_DIR = _PROJECT_ROOT / "data" / "logs"
_LOG_FILE = _LOG_DIR / "runtime.log"
_LOCK = threading.Lock()


def log(level: str, message: str) -> None:
    timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
    line = f"{timestamp} [{level.upper()}] {message}"
    with _LOCK:
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        with _LOG_FILE.open("a", encoding="utf-8") as file:
            file.write(line + "\n")
    print(line)


def info(message: str) -> None:
    log("INFO", message)


def error(message: str) -> None:
    log("ERROR", message)


def warning(message: str) -> None:
    log("WARNING", message)


def get_log_file() -> Path:
    return _LOG_FILE
