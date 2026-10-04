from .manager import TaskManager
from .recovery import TaskRecovery
from .registry import TaskRegistry


class TaskExecutor:
    """
    串行任务执行器。

    当前职责：

        1. 从 JSON 获取当前任务
        2. 找到一个 PENDING
        3. 根据 task 名称读取 TaskRegistry
        4. 获取 listener_id
        5. 标记 RUNNING
        6. 调用外部 handler
        7. 根据执行结果写回 COMPLETED / FAILED

    当前阶段：

        TaskRegistry 只负责：

            task
              ↓
            enabled
              ↓
            listener_id

        Executor 暂时不负责实例化 Listener。

    不负责：

        - 创建任务
        - 任务恢复
        - Listener 实例加载
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

        示例：

            task["task"]
                ↓
            "更新房源ID"
                ↓
            TaskRegistry
                ↓
            {
                "enabled": True,
                "listener_id": "..."
            }
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

        # -----------------------------------------------------
        # 5. 当前阶段仍要求 handler
        #
        # listener_id 已经成功解析，
        # 但 Listener Loader 尚未接入。
        # -----------------------------------------------------

        if self.handler is None:
            return None

        # -----------------------------------------------------
        # 6. PENDING → RUNNING
        # -----------------------------------------------------

        task = self.manager.update_status(
            task["task_no"],
            self.manager.STATUS_RUNNING,
        )

        # -----------------------------------------------------
        # 7. 将 listener_id 放入执行上下文
        #
        # 不修改任务原始 JSON。
        #
        # Handler 可以通过：
        #
        #     task["_execution"]["listener_id"]
        #
        # 获取当前任务对应的 Listener。
        # -----------------------------------------------------

        execution_context = {
            "listener_id": task_config[
                "listener_id"
            ]
        }

        task_for_execution = {
            **task,
            "_execution": execution_context,
        }

        try:
            # -------------------------------------------------
            # 8. 执行真正任务
            # -------------------------------------------------

            result = self.handler(
                task_for_execution
            )

            # -------------------------------------------------
            # 9. 成功
            # -------------------------------------------------

            return self.manager.update_status(
                task["task_no"],
                self.manager.STATUS_COMPLETED,
                result=result,
            )

        except Exception as exc:

            # -------------------------------------------------
            # 10. 失败
            # -------------------------------------------------

            return self.manager.update_status(
                task["task_no"],
                self.manager.STATUS_FAILED,
                result={
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                },
            )