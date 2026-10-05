from pathlib import Path

from core.json_store import JSONStore


STATE_FILE = (
    Path(__file__).resolve().parent.parent
    / "config"
    / "global_state.json"
)

_store = JSONStore()


def load_state():
    """
    读取 GlobalWatcher 状态。

    统一通过 JSONStore 访问。
    """
    return _store.load(
        STATE_FILE,
        default={
            "pages": {}
        },
    )


def save_state(state):
    """
    保存 GlobalWatcher 状态。

    统一通过 JSONStore 写入。
    """
    return _store.save(
        STATE_FILE,
        state,
    )