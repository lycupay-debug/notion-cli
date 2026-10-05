from .manager import TaskManager


class TaskRecovery:
    """
    任务恢复器。

    WAITING 的唯一调度条件：

        同名且更早的任务仍处于 ACTIVE
            ↓
        继续 WAITING

        更早的同名任务已经 COMPLETED / FAILED
            ↓
        WAITING → PENDING

    FAILED 本身是终态，不自动重试。
    """

    def __init__(self, manager=None):
        self.manager = manager or TaskManager()

    def _get_latest_task(self, task):
        task_no = task.get("task_no")
        if task_no is None:
            return None
        return self.manager.get_task(task_no)

    def can_recover(self, task):
        latest_task = self._get_latest_task(task)
        if latest_task is None:
            return False

        if latest_task.get("status") != self.manager.STATUS_WAITING:
            return False

        current_task_no = latest_task.get("task_no", 0)
        task_name = latest_task.get("task")

        for other in self.manager.list_tasks():
            if other.get("task_no", 0) >= current_task_no:
                continue
            if other.get("task") != task_name:
                continue
            if other.get("status") in self.manager.ACTIVE_STATUSES:
                return False

        return True

    def recover_task(self, task):
        latest_task = self._get_latest_task(task)
        if latest_task is None:
            return None

        if not self.can_recover(latest_task):
            return None

        return self.manager.update_status(
            latest_task["task_no"],
            self.manager.STATUS_PENDING,
        )

    def recover_all(self):
        recovered = []

        for task in self.manager.list_tasks():
            if task.get("status") != self.manager.STATUS_WAITING:
                continue

            recovered_task = self.recover_task(task)
            if recovered_task is not None:
                recovered.append(recovered_task)

        return recovered
