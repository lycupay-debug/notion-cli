from pathlib import Path

from core.json_store import JSONStore
from tasks.manager import TaskManager
from tasks.registry import TaskRegistry


CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
STATE_FILE = CONFIG_DIR / "global_state.json"
LISTENERS_FILE = CONFIG_DIR / "listeners.json"


class Dispatcher:
    """把页面变化转换为任务，不执行 Listener。"""

    def __init__(self, store=None, task_manager=None, task_registry=None):
        self.store = store or JSONStore()
        self.task_manager = task_manager or TaskManager()
        self.task_registry = task_registry or TaskRegistry()

    def _load_state(self):
        return self.store.load(STATE_FILE, default={"pages": {}})

    def _load_listeners(self):
        return self.store.load(LISTENERS_FILE, default={"listeners": {}})

    @staticmethod
    def _get_data_source_id(page):
        object_info = page.get("object")
        if not object_info:
            return None
        return object_info.get("parent", {}).get("data_source_id")

    def dispatch(self, page_id):
        state = self._load_state()
        listeners = self._load_listeners()
        page = state.get("pages", {}).get(page_id)

        if page is None:
            return {"status": "PAGE_NOT_FOUND", "page_id": page_id}

        data_source_id = self._get_data_source_id(page)
        if not data_source_id:
            return {"status": "NO_DATA_SOURCE_ID", "page_id": page_id}

        listener_config = listeners.get("listeners", {}).get(data_source_id)
        if listener_config is None:
            return {"status": "NO_LISTENER", "page_id": page_id, "data_source_id": data_source_id}

        listener_id = data_source_id
        if listener_config.get("enabled", False) is not True:
            return {"status": "LISTENER_DISABLED", "page_id": page_id, "data_source_id": data_source_id, "listener_id": listener_id}

        task_config = self.task_registry.find_task_by_listener_id(listener_id)
        if task_config is None:
            return {"status": "NO_TASK_CONFIG", "page_id": page_id, "data_source_id": data_source_id, "listener_id": listener_id}

        task_name = task_config["task_name"]
        if task_config.get("enabled", False) is not True:
            return {"status": "TASK_DISABLED", "page_id": page_id, "data_source_id": data_source_id, "listener_id": listener_id, "task": task_name}

        # last_edited_time 是一次页面变化事件的稳定版本标识。
        # 同一版本被 Watcher 重复发现时，不创建新任务；版本变化则创建新 task_no。
        last_edited_time = page.get("last_edited_time")
        event_key = "|".join([
            str(page_id),
            str(last_edited_time or ""),
            str(listener_id),
            str(task_name),
            str(task_config.get("target_property") or ""),
        ])

        task = self.task_manager.create_task(
            task=task_name,
            target_page_id=page_id,
            target_property=task_config.get("target_property"),
            metadata={
                "data_source_id": data_source_id,
                "listener_id": listener_id,
                "last_edited_time": last_edited_time,
            },
            event_key=event_key,
        )

        return {
            "status": "TASK_CREATED" if task.get("task_no") else "TASK_EXISTS",
            "page_id": page_id,
            "data_source_id": data_source_id,
            "listener_id": listener_id,
            "task": task,
        }
