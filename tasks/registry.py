"""
Task Registry

负责建立：

任务名称
    ↓
具体执行函数

第一阶段只建立注册机制。

真实任务后续逐个接入。
"""


class TaskRegistry:
    """
    任务注册表。

    不负责：
    - 排队
    - 状态
    - JSON
    - 冲突判断

    只负责：
        task_name -> handler
    """

    def __init__(self):
        self._handlers = {}

    def register(
        self,
        name,
        handler,
    ):
        """
        注册一个任务。
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

    def get(self, name):
        """
        获取任务处理函数。
        """
        return self._handlers.get(name)

    def has(self, name):
        """
        判断任务是否存在。
        """
        return name in self._handlers

    def names(self):
        """
        获取所有已注册任务。
        """
        return list(
            self._handlers.keys()
        )


registry = TaskRegistry()