"""
Task Registry

负责：

任务名称
    ↓
listener_id

配置来源：

config/task_registry.json

TaskRegistry 不负责：

- 创建任务
- 任务状态
- 任务排队
- 任务恢复
- Listener 执行
"""

import json
from pathlib import Path


DEFAULT_CONFIG_FILE = (
    Path(__file__).resolve().parent.parent
    / "config"
    / "task_registry.json"
)


class TaskRegistry:

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
    # 配置
    # =========================================================

    def reload(self):
        """
        每次从磁盘重新读取正式任务配置。
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
    # 查询
    # =========================================================

    def get_config(self, task_name):
        self.reload()

        return (
            self._config
            .get("tasks", {})
            .get(task_name)
        )

    def has_config(self, task_name):
        return (
            self.get_config(task_name)
            is not None
        )

    def is_enabled(self, task_name):
        config = self.get_config(
            task_name
        )

        if config is None:
            return False

        return (
            config.get(
                "enabled",
                False,
            )
            is True
        )

    def get_listener_id(self, task_name):
        config = self.get_config(
            task_name
        )

        if config is None:
            return None

        return config.get(
            "listener_id"
        )

    def config_names(self):
        self.reload()

        return list(
            self._config
            .get("tasks", {})
            .keys()
        )

    def find_task_by_listener_id(
        self,
        listener_id,
    ):
        """
        根据 Listener ID 找到对应的正式任务配置。

        Dispatcher 使用该方法完成：

        data_source
            ↓
        listener_id
            ↓
        task_name
        """

        self.reload()

        tasks = self._config.get(
            "tasks",
            {},
        )

        for task_name, config in tasks.items():

            if not isinstance(
                config,
                dict,
            ):
                continue

            if config.get(
                "listener_id"
            ) != listener_id:
                continue

            return {
                "task_name": task_name,
                **config,
            }

        return None