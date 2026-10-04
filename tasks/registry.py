"""
Task Registry

负责建立：

任务名称
    ↓
业务配置

任务与具体业务的对应关系由：

config/task_registry.json

手动配置。

第一阶段：

task_name
    ↓
listener_id

Registry 不负责：

- 排队
- 状态
- 任务执行
- JSON 任务清单
- 冲突判断
- Listener 实际执行
"""

import json
from pathlib import Path


DEFAULT_CONFIG_FILE = (
    Path(__file__).resolve().parent.parent
    / "config"
    / "task_registry.json"
)


class TaskRegistry:
    """
    任务注册表。

    配置来源：

        config/task_registry.json

    JSON结构：

        {
            "version": 1,
            "tasks": {
                "任务名称": {
                    "enabled": true,
                    "listener_id": "..."
                }
            }
        }

    职责：

        task_name
            ↓
        task configuration

    不负责：

        - 任务创建
        - 任务状态
        - 任务排队
        - 任务恢复
        - Handler 执行
        - Listener 执行
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

        # -----------------------------------------------------
        # 保留原有的运行时注册机制
        # -----------------------------------------------------

        self._handlers = {}

        # -----------------------------------------------------
        # JSON配置
        # -----------------------------------------------------

        self._config = {}

        self.reload()

    # =========================================================
    # JSON
    # =========================================================

    def reload(self):
        """
        从磁盘重新读取 task_registry.json。

        不使用内存缓存作为事实来源。

        每次 reload 都以磁盘文件为准。
        """

        if not self.config_file.exists():
            self._config = {
                "version": 1,
                "tasks": {},
            }

            return self._config

        with self.config_file.open(
            "r",
            encoding="utf-8",
        ) as f:

            data = json.load(f)

        if not isinstance(data, dict):
            raise ValueError(
                "Task registry config must be a JSON object."
            )

        tasks = data.get(
            "tasks",
            {},
        )

        if not isinstance(tasks, dict):
            raise ValueError(
                "Task registry 'tasks' must be an object."
            )

        self._config = data

        return data

    # =========================================================
    # 配置查询
    # =========================================================

    def get_config(self, name):
        """
        获取指定任务的完整配置。

        每次调用都会重新读取 JSON，
        确保配置以磁盘最新版本为准。
        """

        self.reload()

        return self._config.get(
            "tasks",
            {},
        ).get(name)

    def has_config(self, name):
        """
        判断 JSON 中是否存在指定任务。
        """

        return self.get_config(name) is not None

    def is_enabled(self, name):
        """
        判断 JSON 中指定任务是否启用。

        不存在时返回 False。
        """

        config = self.get_config(name)

        if config is None:
            return False

        return config.get(
            "enabled",
            False,
        ) is True

    def get_listener_id(self, name):
        """
        获取任务对应的 Listener ID。

        不存在时返回 None。
        """

        config = self.get_config(name)

        if config is None:
            return None

        return config.get(
            "listener_id"
        )

    def config_names(self):
        """
        返回 JSON 中配置的全部任务名称。
        """

        self.reload()

        return list(
            self._config.get(
                "tasks",
                {},
            ).keys()
        )

    # =========================================================
    # 原有运行时 Handler 注册机制
    # =========================================================

    def register(
        self,
        name,
        handler,
    ):
        """
        注册运行时 Handler。

        该机制保留，用于后续 Handler 接入阶段。

        JSON 配置与运行时 Handler 是两个不同层次。
        """

        if not name:
            raise ValueError(
                "Task name cannot be empty."
            )

        if not callable(handler):
            raise TypeError(
                "Task handler must be callable."
            )

        if name in self._handlers:
            raise ValueError(
                f"Task already registered: {name}"
            )

        self._handlers[name] = handler

    def get(
        self,
        name,
    ):
        """
        获取运行时 Handler。
        """

        return self._handlers.get(name)

    def has(
        self,
        name,
    ):
        """
        判断运行时 Handler 是否存在。
        """

        return name in self._handlers

    def names(self):
        """
        获取所有运行时注册任务。
        """

        return list(
            self._handlers.keys()
        )


registry = TaskRegistry()