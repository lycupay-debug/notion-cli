import json
from pathlib import Path


STATE_FILE = Path(__file__).resolve().parent.parent / "config" / "global_state.json"


def load_state():
    """读取本地 GlobalWatcher 状态"""
    if not STATE_FILE.exists():
        return {"pages": {}}

    with STATE_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state):
    """保存本地 GlobalWatcher 状态"""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

    temp_file = STATE_FILE.with_suffix(".tmp")

    with temp_file.open("w", encoding="utf-8") as f:
        json.dump(
            state,
            f,
            ensure_ascii=False,
            indent=2,
        )

    temp_file.replace(STATE_FILE)