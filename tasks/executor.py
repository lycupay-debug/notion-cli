from .manager import TaskManager
from .recovery import TaskRecovery


class TaskExecutor:
    """
    串行任务执行器。

    职责：

        1. 从 JSON 获取当前任务
        2. 找到一个 PENDING
        3. 标记 RUNNING
        4. 调用外部 handler
        5. 根据执行结果写回 COMPLETED / FAILED

    不负责：

        - 创建任务
        - 任务恢复
        - Listener 路由
        - Notion 操作
        - 多线程
        - 内存任务队列
    """

    def __init__(
        self,
        manager=None,
        recovery=None,
        handler=None,
    ):
        self.manager = manager or TaskManager()

        self.recovery = (
            recovery
            or TaskRecovery(
                manager=self.manager
            )
        )

        self.handler = handler

    # ---------------------------------------------------------
    # 执行一个任务
    # ---------------------------------------------------------

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
        # 4. 没有 handler 暂时不执行
        # -----------------------------------------------------

        if self.handler is None:
            return None

        # -----------------------------------------------------
        # 5. PENDING → RUNNING
        # -----------------------------------------------------

        task = self.manager.update_status(
            task["task_no"],
            self.manager.STATUS_RUNNING,
        )

        try:
            # -------------------------------------------------
            # 6. 执行真正任务
            # -------------------------------------------------

            result = self.handler(task)

            # -------------------------------------------------
            # 7. 成功
            # -------------------------------------------------

            return self.manager.update_status(
                task["task_no"],
                self.manager.STATUS_COMPLETED,
                result=result,
            )

        except Exception as exc:

            # -------------------------------------------------
            # 8. 失败
            # -------------------------------------------------

            return self.manager.update_status(
                task["task_no"],
                self.manager.STATUS_FAILED,
                result={
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                },
            )