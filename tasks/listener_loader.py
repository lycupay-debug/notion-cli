"""
Listener Loader

负责：

Listener ID
    ↓
config/listeners.json
    ↓
module + class
    ↓
动态 import
    ↓
Listener class
    ↓
Listener instance

不负责：

- TaskRegistry
- 任务创建
- 任务状态
- 任务排队
- 任务恢复
- 任务执行
- Listener 实际业务逻辑
"""

import importlib
import json
from pathlib import Path


DEFAULT_CONFIG_FILE = (
    Path(__file__).resolve().parent.parent
    / "config"
    / "listeners.json"
)


class ListenerLoader:
    """
    根据 Listener ID 从 listeners.json 加载 Listener。

    listeners.json 是 Listener 的唯一配置源，包含：

        listener_id
            ↓
        name
        module
        class
        enabled
        properties

    ListenerLoader 只使用其中的 module/class 完成动态加载，
    并负责检查 Listener 是否启用。
    """

    def __init__(self, config_file=None):
        self.config_file = (
            Path(config_file)
            if config_file
            else DEFAULT_CONFIG_FILE
        )

        self._config = {}
        self.reload()

    # =========================================================
    # JSON 配置
    # =========================================================

    def reload(self):
        """
        从磁盘重新读取 listeners.json。
        """

        if not self.config_file.exists():
            self._config = {
                "version": 1,
                "listeners": {},
            }
            return self._config

        with self.config_file.open(
            "r",
            encoding="utf-8",
        ) as f:
            data = json.load(f)

        if not isinstance(data, dict):
            raise ValueError(
                "Listener config must be a JSON object."
            )

        listeners = data.get("listeners", {})

        if not isinstance(listeners, dict):
            raise ValueError(
                "Listener config 'listeners' must be an object."
            )

        self._config = data
        return data

    # =========================================================
    # Listener 配置
    # =========================================================

    def get_config(self, listener_id):
        """
        根据 Listener ID 获取完整 Listener 配置。

        不存在时返回 None。
        """

        self.reload()

        return self._config.get(
            "listeners",
            {},
        ).get(listener_id)

    def has_config(self, listener_id):
        """
        判断 Listener ID 是否存在。
        """

        return self.get_config(listener_id) is not None

    def is_enabled(self, listener_id):
        """
        判断 Listener 是否启用。

        不存在或 enabled 不是 True 时均视为未启用。
        """

        config = self.get_config(listener_id)

        if config is None:
            return False

        return config.get("enabled", False) is True

    # =========================================================
    # 获取 Listener Class
    # =========================================================

    def load_class(self, listener_id):
        """
        根据 Listener ID 动态加载 Python Listener Class。

        Listener 不存在、未启用、module/class 缺失，
        或 Python 类不存在时抛出 ValueError。
        """

        config = self.get_config(listener_id)

        if config is None:
            raise ValueError(
                f"Listener not found: {listener_id}"
            )

        if config.get("enabled", False) is not True:
            raise ValueError(
                f"Listener is disabled: {listener_id}"
            )

        module_name = config.get("module")
        class_name = config.get("class")

        if not module_name:
            raise ValueError(
                f"Listener module is missing: {listener_id}"
            )

        if not class_name:
            raise ValueError(
                f"Listener class is missing: {listener_id}"
            )

        module = importlib.import_module(module_name)

        try:
            listener_class = getattr(
                module,
                class_name,
            )
        except AttributeError as exc:
            raise ValueError(
                f"Listener class not found: "
                f"{module_name}.{class_name}"
            ) from exc

        return listener_class

    # =========================================================
    # 创建 Listener Instance
    # =========================================================

    def load(self, listener_id):
        """
        根据 Listener ID 加载并实例化 Listener。
        """

        listener_class = self.load_class(listener_id)
        return listener_class()
