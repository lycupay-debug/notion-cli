from pathlib import Path

from core.json_store import JSONStore
from tasks.manager import TaskManager
from tasks.registry import TaskRegistry


CONFIG_DIR = (
    Path(__file__).resolve().parent.parent
    / "config"
)

STATE_FILE = (
    CONFIG_DIR
    / "global_state.json"
)

LISTENERS_FILE = (
    CONFIG_DIR
    / "listeners.json"
)


class Dispatcher:
    """
    页面变化路由器。

    正式职责：

        page_id
            ↓
        object
            ↓
        data_source_id
            ↓
        listener_id
            ↓
        task_name
            ↓
        TaskManager.create_task()

    Dispatcher 不执行 Listener。

    Dispatcher 不负责：

        - Listener 实例化
        - Listener 执行
        - Notion 业务处理
        - 任务状态管理
    """

    def __init__(
        self,
        store=None,
        task_manager=None,
        task_registry=None,
    ):
        self.store = (
            store
            or JSONStore()
        )

        self.task_manager = (
            task_manager
            or TaskManager()
        )

        self.task_registry = (
            task_registry
            or TaskRegistry()
        )

    def dispatch(self, page_id):

        state = self.store.load(
            STATE_FILE,
            default={
                "pages": {}
            },
        )

        listeners = self.store.load(
            LISTENERS_FILE,
            default={
                "listeners": {}
            },
        )

        page = (
            state
            .get("pages", {})
            .get(page_id)
        )

        if page is None:
            return {
                "status": "PAGE_NOT_FOUND",
                "page_id": page_id,
            }

        object_info = page.get(
            "object"
        )

        if not object_info:
            return {
                "status": "NO_IDENTITY",
                "page_id": page_id,
            }

        parent = object_info.get(
            "parent",
            {}
        )

        data_source_id = parent.get(
            "data_source_id"
        )

        if not data_source_id:
            return {
                "status": "NO_DATA_SOURCE_ID",
                "page_id": page_id,
            }

        listener_config = (
            listeners
            .get("listeners", {})
            .get(data_source_id)
        )

        if listener_config is None:
            return {
                "status": "NO_LISTENER",
                "page_id": page_id,
                "data_source_id": data_source_id,
            }

        if not listener_config.get(
            "enabled",
            False,
        ):
            return {
                "status": "LISTENER_DISABLED",
                "page_id": page_id,
                "data_source_id": data_source_id,
            }

        listener_id = data_source_id

        task_config = (
            self.task_registry
            .find_task_by_listener_id(
                listener_id
            )
        )

        if task_config is None:
            return {
                "status": "NO_TASK_CONFIG",
                "page_id": page_id,
                "data_source_id": data_source_id,
                "listener_id": listener_id,
            }

        if task_config.get(
            "enabled",
            False,
        ) is not True:
            return {
                "status": "TASK_DISABLED",
                "page_id": page_id,
                "data_source_id": data_source_id,
                "listener_id": listener_id,
                "task": task_config[
                    "task_name"
                ],
            }

        task_name = task_config[
            "task_name"
        ]

        target_property = (
            task_config.get(
                "target_property"
            )
        )

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