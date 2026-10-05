from pathlib import Path

from core.json_store import JSONStore
from tasks.manager import TaskManager
from tasks.registry import TaskRegistry


CONFIG_DIR = (
    Path(__file__).resolve().parent.parent
    / "config"
)

STATE_FILE = CONFIG_DIR / "global_state.json"
LISTENERS_FILE = CONFIG_DIR / "listeners.json"


class Dispatcher:
    """
    页面变化任务路由器。

    页面变化只负责产生“业务任务请求”。
    TaskManager 负责去重与同名任务串行化。
    """

    def __init__(self, store=None, task_manager=None, task_registry=None):
        self.store = store or JSONStore()
        self.task_manager = task_manager or TaskManager()
        self.task_registry = task_registry or TaskRegistry()

    def _load_state(self):
        return self.store.load(STATE_FILE, default={"pages": {}})

    def _load_listeners(self):
        return self.store.load(LISTENERS_FILE, default={"listeners": {}})

    def _get_page(self, state, page_id):
        return state.get("pages", {}).get(page_id)

    @staticmethod
    def _get_data_source_id(page):
        object_info = page.get("object")
        if not object_info:
            return None
        return object_info.get("parent", {}).get("data_source_id")

    def _get_listener_config(self, listeners, data_source_id):
        return listeners.get("listeners", {}).get(data_source_id)

    def dispatch(self, page_id):
        state = self._load_state()
        listeners = self._load_listeners()

        page = self._get_page(state, page_id)
        if page is None:
            return {"status": "PAGE_NOT_FOUND", "page_id": page_id}

        data_source_id = self._get_data_source_id(page)
        if not data_source_id:
            return {"status": "NO_DATA_SOURCE_ID", "page_id": page_id}

        listener_config = self._get_listener_config(listeners, data_source_id)
        if listener_config is None:
            return {
                "status": "NO_LISTENER",
                "page_id": page_id,
                "data_source_id": data_source_id,
            }

        listener_id = data_source_id
        if listener_config.get("enabled", False) is not True:
            return {
                "status": "LISTENER_DISABLED",
                "page_id": page_id,
                "data_source_id": data_source_id,
                "listener_id": listener_id,
            }

        task_config = self.task_registry.find_task_by_listener_id(listener_id)
        if task_config is None:
            return {
                "status": "NO_TASK_CONFIG",
                "page_id": page_id,
                "data_source_id": data_source_id,
                "listener_id": listener_id,
            }

        task_name = task_config["task_name"]
        if task_config.get("enabled", False) is not True:
            return {
                "status": "TASK_DISABLED",
                "page_id": page_id,
                "data_source_id": data_source_id,
                "listener_id": listener_id,
                "task": task_name,
            }

        target_property = task_config.get("target_property")
        existing = self.task_manager.find_existing_business_task(
            task_name,
            page_id,
            target_property,
        )

        if existing is not None:
            return {
                "status": "TASK_SKIPPED",
                "reason": "BUSINESS_ALREADY_EXISTS",
                "page_id": page_id,
                "data_source_id": data_source_id,
                "listener_id": listener_id,
                "task": existing,
            }

        task = self.task_manager.create_task(
            task=task_name,
            target_page_id=page_id,
            target_property=target_property,
            metadata={
                "data_source_id": data_source_id,
                "listener_id": listener_id,
            },
        )

        return {
            "status": "TASK_CREATED",
            "page_id": page_id,
            "data_source_id": data_source_id,
            "listener_id": listener_id,
            "task": task,
        }
