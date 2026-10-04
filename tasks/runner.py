from .manager import TaskManager
from .registry import registry


class TaskRunner:
    """
    单线程任务执行器。

    第一阶段：

    1. 从 JSON 找到最早 PENDING
    2. 判断目标冲突
    3. 查找 Registry
    4. 执行任务
    5. 写回 JSON

    不建立内存任务队列。
    """

    def __init__(
        self,
        manager=None,
        task_registry=None,
    ):
        self.manager = (
            manager
            or TaskManager()
        )

        self.registry = (
            task_registry
            or registry
        )

    def run_once(self):
        """
        执行一次任务循环。

        返回结果：

            None
                没有任务。

            dict
                本次任务处理结果。
        """

        task = (
            self.manager
            .get_next_pending_task()
        )

        if task is None:
            return None

        # -------------------------------------------------
        # 冲突检查
        # -------------------------------------------------

        if self.manager.has_conflict(task):

            self.manager.update_status(
                task["task_no"],
                TaskManager.STATUS_WAITING,
            )

            return {
                "status": "WAITING",
                "task_no": task["task_no"],
                "task_id": task["task_id"],
            }

        # -------------------------------------------------
        # 查找任务处理器
        # -------------------------------------------------

        handler = self.registry.get(
            task["task"]
        )

        if handler is None:

            result = {
                "status": "FAILED",
                "reason": (
                    "TASK_NOT_REGISTERED"
                ),
                "task": task["task"],
            }

            self.manager.update_status(
                task["task_no"],
                TaskManager.STATUS_FAILED,
                result=result,
            )

            return result

        # -------------------------------------------------
        # 标记 RUNNING
        # -------------------------------------------------

        self.manager.update_status(
            task["task_no"],
            TaskManager.STATUS_RUNNING,
        )

        try:

            result = handler(task)

            self.manager.update_status(
                task["task_no"],
                TaskManager.STATUS_COMPLETED,
                result=result,
            )

            return {
                "status": "COMPLETED",
                "task_no": task["task_no"],
                "task_id": task["task_id"],
                "result": result,
            }

        except Exception as exc:

            result = {
                "status": "FAILED",
                "error": str(exc),
                "error_type": type(
                    exc
                ).__name__,
            }

            self.manager.update_status(
                task["task_no"],
                TaskManager.STATUS_FAILED,
                result=result,
            )

            return {
                "status": "FAILED",
                "task_no": task["task_no"],
                "task_id": task["task_id"],
                "result": result,
            }