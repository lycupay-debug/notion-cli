from pathlib import Path

from core.json_store import JSONStore

from .executor import ListenerExecutor


CONFIG_DIR = (
    Path(__file__).resolve().parent.parent
    / "config"
)

STATE_FILE = CONFIG_DIR / "global_state.json"
LISTENERS_FILE = CONFIG_DIR / "listeners.json"


class Dispatcher:
    """
    本地 Dispatcher。

    Dispatcher 不直接操作 JSON 文件。

    所有 JSON 数据访问统一交给 JSONStore。

    因此：
        global_state.json
        listeners.json

    都具备自动 mtime 检测能力。

    外部修改 JSON 后，下一次 dispatch()
    会自动读取最新内容。
    """

    def __init__(self):
        self.store = JSONStore()
        self.executor = ListenerExecutor()

    def dispatch(self, page_id):
        """
        根据 page_id：

        1. 读取页面状态
        2. 获取 object 身份
        3. 获取 data_source_id
        4. 查找对应 listener
        5. 检查 listener 是否启用
        6. 执行 listener
        """

        # --------------------------------------------------
        # 1. 读取 GlobalWatcher 状态
        # --------------------------------------------------

        state = self.store.load(
            STATE_FILE,
            default={
                "pages": {}
            },
        )

        # --------------------------------------------------
        # 2. 读取 listeners 配置
        # --------------------------------------------------

        listeners = self.store.load(
            LISTENERS_FILE,
            default={
                "listeners": {}
            },
        )

        # --------------------------------------------------
        # 3. 获取页面状态
        # --------------------------------------------------

        pages = state.get(
            "pages",
            {},
        )

        page = pages.get(page_id)

        if page is None:
            return {
                "status": "PAGE_NOT_FOUND",
                "page_id": page_id,
            }

        # --------------------------------------------------
        # 4. 获取 object 身份
        # --------------------------------------------------

        object_info = page.get("object")

        if not object_info:
            return {
                "status": "NO_IDENTITY",
                "page_id": page_id,
            }

        # --------------------------------------------------
        # 5. 获取 parent
        # --------------------------------------------------

        parent = object_info.get(
            "parent",
            {},
        )

        # --------------------------------------------------
        # 6. 获取 data_source_id
        # --------------------------------------------------

        data_source_id = parent.get(
            "data_source_id"
        )

        if not data_source_id:
            return {
                "status": "NO_DATA_SOURCE_ID",
                "page_id": page_id,
            }

        # --------------------------------------------------
        # 7. 根据 data_source_id 查 listener
        # --------------------------------------------------

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

        # --------------------------------------------------
        # 8. 检查 listener 是否启用
        # --------------------------------------------------

        if not listener_config.get(
            "enabled",
            False,
        ):
            return {
                "status": "LISTENER_DISABLED",
                "page_id": page_id,
                "data_source_id": data_source_id,
                "listener": listener_config,
            }

        # --------------------------------------------------
        # 9. 执行 listener
        # --------------------------------------------------

        execution = self.executor.execute(
            listener_config,
            page_id,
        )

        # --------------------------------------------------
        # 10. 返回统一结果
        # --------------------------------------------------

        return {
            "status": "ROUTED",
            "page_id": page_id,
            "data_source_id": data_source_id,
            "listener": listener_config,
            "execution": execution,
        }