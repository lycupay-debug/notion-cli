"""
Listener Registry

负责建立：

listener_id
    ↓
Listener 配置
    ↓
module + class

配置来源：

config/listener_registry.json

Listener Registry 不负责：

- 任务创建
- 任务状态
- 任务排队
- 任务恢复
- TaskRegistry
- Listener 实际执行
- Listener 实例化
"""

import json
from pathlib import Path


DEFAULT_CONFIG_FILE = (
    Path(__file__).resolve().parent.parent
    / "config"
    / "listener_registry.json"
)


class ListenerRegistry:
    """
    Listener 注册表。

    JSON结构：

        {
            "version": 1,
            "listeners": {
                "LISTENER-ID": {
                    "module": "...",
                    "class": "..."
                }
            }
        }

    职责：

        listener_id
            ↓
        listener configuration

    不负责：

        - TaskRegistry
        - 任务执行
        - Listener 实例化
        - importlib
    """

    def __init__(
        self,
        config_file=None,
    ):
        self.config_file = (
            Path(config_file)
            if config_file
            else DEFAULT_CONFIG_FILE
        )

        self._config = {}

        self.reload()

    # =========================================================
    # JSON
    # =========================================================

    def reload(self):
        """
        从磁盘重新读取 listener_registry.json。
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
                "Listener registry config must be a JSON object."
            )

        listeners = data.get(
            "listeners",
            {},
        )

        if not isinstance(listeners, dict):
            raise ValueError(
                "Listener registry 'listeners' must be an object."
            )

        self._config = data

        return data

    # =========================================================
    # 配置查询
    # =========================================================

    def get_config(self, listener_id):
        """
        根据 Listener ID 获取完整配置。

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

        return self.get_config(
            listener_id
        ) is not None

    def get_module(self, listener_id):
        """
        获取 Listener 对应的 Python module。

        不存在时返回 None。
        """

        config = self.get_config(
            listener_id
        )

        if config is None:
            return None

        return config.get(
            "module"
        )

    def get_class(self, listener_id):
        """
        获取 Listener 对应的 Python class。

        不存在时返回 None。
        """

        config = self.get_config(
            listener_id
        )

        if config is None:
            return None

        return config.get(
            "class"
        )

    def get_target(self, listener_id):
        """
        一次获取 module + class。

        返回：

            {
                "module": "...",
                "class": "..."
            }

        不存在时返回 None。
        """

        config = self.get_config(
            listener_id
        )

        if config is None:
            return None

        return {
            "module": config.get(
                "module"
            ),
            "class": config.get(
                "class"
            ),
        }

    def listener_ids(self):
        """
        返回全部 Listener ID。
        """

        self.reload()

        return list(
            self._config.get(
                "listeners",
                {},
            ).keys()
        )