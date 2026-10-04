import json
from pathlib import Path

from .executor import ListenerExecutor


CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"

STATE_FILE = CONFIG_DIR / "global_state.json"
LISTENERS_FILE = CONFIG_DIR / "listeners.json"


class Dispatcher:
    """
    本地 Dispatcher。

    职责：
    1. 接收 GlobalWatcher 传递的 page_id
    2. 从 global_state.json 获取对象归属
    3. 从 listeners.json 获取 Listener 配置
    4. 将事件路由给对应 Listener
    5. 返回路由及执行结果

    不负责：
    - 判断页面变化
    - 获取页面身份
    - 执行具体业务逻辑
    """

    def __init__(self):
        self.state = self._load_json(STATE_FILE)
        self.listeners = self._load_json(LISTENERS_FILE)
        self.executor = ListenerExecutor()

    @staticmethod
    def _load_json(file_path):
        with file_path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def dispatch(self, page_id):
        """
        根据 Page ID 进行本地路由，
        并将已确定的事件交给 ListenerExecutor 执行。

        本阶段 Dispatcher 本身不调用 Notion API。
        """

        pages = self.state.get("pages", {})
        page = pages.get(page_id)

        if page is None:
            return {
                "status": "PAGE_NOT_FOUND",
                "page_id": page_id,
            }

        object_info = page.get("object")

        if not object_info:
            return {
                "status": "NO_IDENTITY",
                "page_id": page_id,
            }

        parent = object_info.get("parent", {})

        data_source_id = parent.get("data_source_id")

        if not data_source_id:
            return {
                "status": "NO_DATA_SOURCE_ID",
                "page_id": page_id,
            }

        listener_config = (
            self.listeners
            .get("listeners", {})
            .get(data_source_id)
        )

        if listener_config is None:
            return {
                "status": "NO_LISTENER",
                "page_id": page_id,
                "data_source_id": data_source_id,
            }

        if not listener_config.get("enabled", False):
            return {
                "status": "LISTENER_DISABLED",
                "page_id": page_id,
                "data_source_id": data_source_id,
                "listener": listener_config,
            }

        execution = self.executor.execute(
            listener_config,
            page_id,
        )

        return {
            "status": "ROUTED",
            "page_id": page_id,
            "data_source_id": data_source_id,
            "listener": listener_config,
            "execution": execution,
        }