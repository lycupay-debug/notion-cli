from .manager import TaskManager


class TaskRecovery:
    """
    任务恢复器。

    WAITING 任务只有在其之前的同名任务全部进入终态
    （COMPLETED 或 FAILED）后，才恢复为 PENDING。

    FAILED 表示该任务已经执行结束，不会重新执行，
    但不会阻塞后续同名任务。
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

        task_name = latest_task.get("task")
        current_task_no = latest_task.get("task_no", 0)

        if not task_name:
            return True

        for other in self.manager.list_tasks():
            other_task_no = other.get("task_no", 0)

            if other_task_no >= current_task_no:
                continue

            if other.get("task") != task_name:
                continue

            # 前一个同名任务只要尚未结束，就继续等待。
            if other.get("status") in {
                self.manager.STATUS_PENDING,
                self.manager.STATUS_RUNNING,
                self.manager.STATUS_WAITING,
            }:
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
