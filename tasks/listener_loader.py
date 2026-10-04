"""
Listener Loader

负责：

Listener ID
    ↓
ListenerRegistry
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
"""

import importlib

from .listener_registry import ListenerRegistry


class ListenerLoader:
    """
    根据 Listener ID 动态加载 Listener。

    职责边界：

        ListenerRegistry
            负责：
                listener_id
                    ↓
                module + class

        ListenerLoader
            负责：
                module + class
                    ↓
                Python class
                    ↓
                instance
    """

    def __init__(
        self,
        registry=None,
    ):
        self.registry = (
            registry
            or ListenerRegistry()
        )

    # =========================================================
    # 获取 Listener Class
    # =========================================================

    def load_class(
        self,
        listener_id,
    ):
        """
        根据 Listener ID 加载 Python Listener Class。

        返回：

            Listener class

        不存在时：

            ValueError
        """

        target = self.registry.get_target(
            listener_id
        )

        if target is None:
            raise ValueError(
                f"Listener not found: {listener_id}"
            )

        module_name = target.get(
            "module"
        )

        class_name = target.get(
            "class"
        )

        if not module_name:
            raise ValueError(
                f"Listener module is missing: {listener_id}"
            )

        if not class_name:
            raise ValueError(
                f"Listener class is missing: {listener_id}"
            )

        module = importlib.import_module(
            module_name
        )

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

    def load(
        self,
        listener_id,
    ):
        """
        根据 Listener ID 加载并实例化 Listener。

        返回：

            Listener instance
        """

        listener_class = self.load_class(
            listener_id
        )

        return listener_class()