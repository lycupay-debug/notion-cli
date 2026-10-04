from .manager import TaskManager
from .recovery import TaskRecovery
from .registry import TaskRegistry
from .listener_loader import ListenerLoader


class TaskExecutor:
    """
    串行任务执行器。

    当前职责：

        1. 从 JSON 获取当前任务
        2. 找到一个 PENDING
        3. 根据 task 名称读取 TaskRegistry
        4. 获取 listener_id
        5. 根据 listener_id 加载 Listener
        6. 标记 RUNNING
        7. 执行 Listener
        8. 根据执行结果写回 COMPLETED / FAILED

    当前执行链：

        TaskRegistry
            ↓
        listener_id
            ↓
        ListenerLoader
            ↓
        Listener instance
            ↓
        handle(page_id)

    兼容机制：

        如果显式传入 handler，
        则继续使用原有 handler 执行方式。

        这样可以保持已有测试与旧调用方式稳定。

    不负责：

        - 创建任务
        - 任务恢复
        - Listener Registry 内部配置管理
        - Listener 实例加载逻辑
        - Notion 操作
        - 多线程
        - 内存任务队列
    """

    def __init__(
        self,
        manager=None,
        recovery=None,
        handler=None,
        registry=None,
        listener_loader=None,
    ):
        self.manager = manager or TaskManager()

        self.recovery = (
            recovery
            or TaskRecovery(
                manager=self.manager
            )
        )

        self.handler = handler

        self.registry = (
            registry
            or TaskRegistry()
        )

        self.listener_loader = (
            listener_loader
            or ListenerLoader()
        )

    # =========================================================
    # 获取任务业务配置
    # =========================================================

    def resolve_task_config(self, task):
        """
        根据任务中的 task 名称读取 JSON 配置。

        返回：

            None
                没有配置 / 未启用 / 没有 listener_id

            dict
                有效任务配置
        """

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
    # 执行 Listener
    # =========================================================

    def execute_listener(
        self,
        task,
        listener_id,
    ):
        """
        根据 Listener ID 加载并执行 Listener。

        执行链：

            listener_id
                ↓
            ListenerLoader
                ↓
            Listener instance
                ↓
            handle(target_page_id)

        Listener 当前统一接收：

            target_page_id

        返回 Listener 的执行结果。
        """

        listener = self.listener_loader.load(
            listener_id
        )

        target_page_id = task.get(
            "target_page_id"
        )

        if not target_page_id:
            raise ValueError(
                "Task target_page_id is required "
                "for Listener execution."
            )

        handle = getattr(
            listener,
            "handle",
            None,
        )

        if not callable(handle):
            raise TypeError(
                f"Listener does not provide "
                f"a callable handle(): {listener!r}"
            )

        return handle(
            target_page_id
        )

    # =========================================================
    # 执行一个任务
    # =========================================================

    def run_once(self):
        """
        执行当前第一个可执行任务。

        返回：

            None
                当前没有可执行任务。

            dict
                执行后的任务。
        """

        # -----------------------------------------------------
        # 1. 先恢复 WAITING
        # -----------------------------------------------------

        self.recovery.recover_all()

        # -----------------------------------------------------
        # 2. 从 JSON 获取最新 PENDING
        # -----------------------------------------------------

        task = self.manager.get_next_pending_task()

        if task is None:
            return None

        # -----------------------------------------------------
        # 3. 再次根据 task_no 从磁盘读取
        # -----------------------------------------------------

        task = self.manager.get_task(
            task["task_no"]
        )

        if task is None:
            return None

        # 防止旧快照导致错误执行。

        if (
            task.get("status")
            != self.manager.STATUS_PENDING
        ):
            return None

        # -----------------------------------------------------
        # 4. 读取任务业务配置
        # -----------------------------------------------------

        task_config = (
            self.resolve_task_config(
                task
            )
        )

        if task_config is None:
            return None

        listener_id = task_config[
            "listener_id"
        ]

        # -----------------------------------------------------
        # 5. PENDING → RUNNING
        # -----------------------------------------------------

        task = self.manager.update_status(
            task["task_no"],
            self.manager.STATUS_RUNNING,
        )

        # -----------------------------------------------------
        # 6. 构造执行上下文
        #
        # 不写入任务原始 JSON。
        # -----------------------------------------------------

        execution_context = {
            "listener_id": listener_id,
        }

        task_for_execution = {
            **task,
            "_execution": execution_context,
        }

        try:

            # -------------------------------------------------
            # 7. 执行
            #
            # 兼容旧 handler：
            #
            #   handler(task)
            #
            # 新 Listener：
            #
            #   ListenerLoader
            #       ↓
            #   Listener.handle(page_id)
            # -------------------------------------------------

            if self.handler is not None:

                result = self.handler(
                    task_for_execution
                )

            else:

                result = self.execute_listener(
                    task_for_execution,
                    listener_id,
                )

            # -------------------------------------------------
            # 8. 成功
            # -------------------------------------------------

            return self.manager.update_status(
                task["task_no"],
                self.manager.STATUS_COMPLETED,
                result=result,
            )

        except Exception as exc:

            # -------------------------------------------------
            # 9. 失败
            # -------------------------------------------------

            return self.manager.update_status(
                task["task_no"],
                self.manager.STATUS_FAILED,
                result={
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                },
            )