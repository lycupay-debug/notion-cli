from .manager import TaskManager
from .recovery import TaskRecovery
from .registry import TaskRegistry
from .listener_loader import ListenerLoader


class TaskExecutor:
    """
    串行任务执行器。

    正式执行链：

        TaskManager
            ↓
        TaskRegistry
            ↓
        listener_id
            ↓
        ListenerLoader
            ↓
        Listener
            ↓
        handle(page_id)

    不负责：

        - 创建任务
        - 任务恢复逻辑
        - Listener Registry
        - Listener 加载逻辑
        - Notion API
        - 并发执行
    """

    def __init__(
        self,
        manager=None,
        recovery=None,
        registry=None,
        listener_loader=None,
    ):
        self.manager = (
            manager
            or TaskManager()
        )

        self.recovery = (
            recovery
            or TaskRecovery(
                manager=self.manager
            )
        )

        self.registry = (
            registry
            or TaskRegistry()
        )

        self.listener_loader = (
            listener_loader
            or ListenerLoader()
        )

    # =========================================================
    # 任务配置
    # =========================================================

    def resolve_task_config(
        self,
        task,
    ):
        task_name = task.get(
            "task"
        )

        if not task_name:
            return None

        config = self.registry.get_config(
            task_name
        )

        if config is None:
            return None

        if config.get(
            "enabled",
            False,
        ) is not True:
            return None

        listener_id = config.get(
            "listener_id"
        )

        if not listener_id:
            return None

        return config

    # =========================================================
    # Listener 执行
    # =========================================================

    def execute_listener(
        self,
        task,
        listener_id,
    ):
        listener = self.listener_loader.load(
            listener_id
        )

        page_id = task.get(
            "target_page_id"
        )

        if not page_id:
            raise ValueError(
                "Task target_page_id is required."
            )

        handle = getattr(
            listener,
            "handle",
            None,
        )

        if not callable(handle):
            raise TypeError(
                "Listener must provide "
                "a callable handle(page_id)."
            )

        return handle(page_id)

    # =========================================================
    # 执行一个任务
    # =========================================================

    def run_once(self):
        """
        执行当前第一个可执行任务。

        返回：

        None
            没有可执行任务。

        dict
            执行后的任务。
        """

        self.recovery.recover_all()

        task = (
            self.manager
            .get_next_pending_task()
        )

        if task is None:
            return None

        task = self.manager.get_task(
            task["task_no"]
        )

        if task is None:
            return None

        if (
            task.get("status")
            != self.manager.STATUS_PENDING
        ):
            return None

        task_config = (
            self.resolve_task_config(
                task
            )
        )

        if task_config is None:
            return None

        listener_id = (
            task_config["listener_id"]
        )

        task = self.manager.update_status(
            task["task_no"],
            self.manager.STATUS_RUNNING,
        )

        try:

            result = self.execute_listener(
                task,
                listener_id,
            )

            return self.manager.update_status(
                task["task_no"],
                self.manager.STATUS_COMPLETED,
                result=result,
            )

        except Exception as exc:

            return self.manager.update_status(
                task["task_no"],
                self.manager.STATUS_FAILED,
                result={
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                },
            )