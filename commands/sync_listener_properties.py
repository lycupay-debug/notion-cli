from pathlib import Path

from core.json_store import JSONStore
from notion.data_sources import get_data_source


BASE_DIR = Path(__file__).resolve().parent.parent

LISTENERS_FILE = (
    BASE_DIR
    / "config"
    / "listeners.json"
)


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


def sync_listener_properties():
    """
    根据 listeners.json 中已有的 Data Source ID，
    自动读取对应 Data Source 的全部字段属性，
    并直接补全回 listeners.json。

    注意：

    1. 不修改 version
    2. 不修改 Data Source ID
    3. 不修改 name
    4. 不修改 module
    5. 不修改 class
    6. 不修改 enabled
    7. 不新增 data_source
    8. enabled=false 仍然执行同步
    9. properties 使用 Notion 返回的完整字段定义
    """

    store = JSONStore()

    config = load_listeners(store)

    listeners = config["listeners"]

    print("=" * 60)
    print("Listener 字段属性同步")
    print("=" * 60)

    print(
        f"Listener 数量: {len(listeners)}"
    )

    print()

    for data_source_id, listener_config in listeners.items():

        if not isinstance(listener_config, dict):
            raise ValueError(
                f"Listener 配置格式错误: {data_source_id}"
            )

        print(
            f"正在读取 Data Source:"
            f" {data_source_id}"
        )

        print(
            f"Listener:"
            f" {listener_config.get('name')}"
        )

        print(
            f"Enabled:"
            f" {listener_config.get('enabled')}"
        )

        # --------------------------------------------------
        # 注意：
        # 这里故意不判断 enabled。
        #
        # enabled=False 也必须补全 properties。
        # --------------------------------------------------

        data_source = get_data_source(
            data_source_id
        )

        properties = get_properties(
            data_source
        )

        # --------------------------------------------------
        # 直接写入当前 Listener。
        #
        # 原有：
        # name
        # module
        # class
        # enabled
        #
        # 完全保留。
        #
        # properties：
        # - 不存在 → 新增
        # - 已存在 → 用 Notion 最新结构更新
        #
        # 不增加 data_source。
        # --------------------------------------------------

        listener_config["properties"] = properties

        print(
            f"字段数量: {len(properties)}"
        )

        print()

    # ------------------------------------------------------
    # 直接写回原 listeners.json
    # ------------------------------------------------------

    store.save(
        LISTENERS_FILE,
        config,
    )

    return config


def print_result(config):
    """
    输出最终同步结果。
    """
    listeners = config.get(
        "listeners",
        {},
    )

    print("=" * 60)
    print("同步完成")
    print("=" * 60)

    for data_source_id, listener_config in listeners.items():

        properties = listener_config.get(
            "properties",
            {},
        )

        print()
        print(
            f"Listener: "
            f"{listener_config.get('name')}"
        )

        print(
            f"Data Source ID: "
            f"{data_source_id}"
        )

        print(
            f"Enabled: "
            f"{listener_config.get('enabled')}"
        )

        print(
            f"字段数量: "
            f"{len(properties)}"
        )

        for property_name, property_schema in properties.items():

            property_type = property_schema.get(
                "type",
                "unknown",
            )

            property_id = property_schema.get(
                "id",
                "",
            )

            print(
                f"  - {property_name}"
                f" | type={property_type}"
                f" | id={property_id}"
            )

    print()
    print(
        f"已更新文件: {LISTENERS_FILE}"
    )


def main():
    try:
        config = sync_listener_properties()

        print_result(config)

    except Exception as exc:
        print()
        print("=" * 60)
        print("同步失败")
        print("=" * 60)
        print(
            f"{type(exc).__name__}: {exc}"
        )

        raise


if __name__ == "__main__":
    main()