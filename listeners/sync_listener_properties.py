from pathlib import Path

from core.json_store import JSONStore
from notion.data_sources import retrieve_data_source


BASE_DIR = Path(__file__).resolve().parent.parent

LISTENERS_FILE = (
    BASE_DIR
    / "config"
    / "listeners.json"
)


class SyncListenerProperties:
    """
    同步 listeners.json 中所有 Listener 的 Data Source 字段定义。

    这是一个纯业务 Listener：
    - 接收 GlobalWatcher / TaskExecutor 传入的 page_id 作为触发来源
    - 不根据 page_id 判断业务对象
    - 不负责监听
    - 不负责任务路由
    - 不负责任务状态
    - 实际业务统一执行 sync_listener_properties()
    """

    def handle(self, page_id):
        print(
            f"[SyncListenerProperties] "
            f"开始处理 page_id: {page_id}"
        )

        return self.sync_listener_properties()

    @staticmethod
    def load_listeners(store):
        """
        读取 listeners.json。

        listeners.json 是 Listener 配置的唯一来源。
        """
        config = store.load(LISTENERS_FILE)

        if not isinstance(config, dict):
            raise ValueError(
                "config/listeners.json 格式错误：根节点必须是对象"
            )

        if "listeners" not in config:
            raise ValueError(
                "config/listeners.json 缺少 listeners"
            )

        listeners = config["listeners"]

        if not isinstance(listeners, dict):
            raise ValueError(
                "config/listeners.json 中的 listeners 必须是对象"
            )

        return config

    @staticmethod
    def get_properties(data_source):
        """
        提取 Notion Data Source 的完整 properties。

        不筛选字段。
        不根据 enabled 判断。
        不修改 Notion 返回的属性结构。
        """
        properties = data_source.get("properties")

        if not isinstance(properties, dict):
            raise ValueError(
                "Notion Data Source 返回结果中不存在有效的 properties"
            )

        return properties

    def sync_listener_properties(self):
        """
        根据 listeners.json 中已有的 Data Source ID，
        读取对应 Data Source 的全部字段属性，
        并直接补全回 listeners.json。

        不修改 Listener 的其他配置字段。
        enabled=false 也执行字段同步。
        """
        store = JSONStore()
        config = self.load_listeners(store)
        listeners = config["listeners"]

        print("=" * 60)
        print("Listener 字段属性同步")
        print("=" * 60)
        print(f"Listener 数量: {len(listeners)}")
        print()

        for data_source_id, listener_config in listeners.items():
            if not isinstance(listener_config, dict):
                raise ValueError(
                    f"Listener 配置格式错误: {data_source_id}"
                )

            print(
                f"正在读取 Data Source: {data_source_id}"
            )
            print(
                f"Listener: {listener_config.get('name')}"
            )
            print(
                f"Enabled: {listener_config.get('enabled')}"
            )

            data_source = retrieve_data_source(data_source_id)
            properties = self.get_properties(data_source)

            listener_config["properties"] = properties

            print(f"字段数量: {len(properties)}")
            print()

        store.save(
            LISTENERS_FILE,
            config,
        )

        return config
