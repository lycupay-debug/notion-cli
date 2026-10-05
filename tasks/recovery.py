from .manager import TaskManager


class TaskRecovery:
    """
    任务恢复器。

    只负责：

        WAITING
            ↓
        检查前置任务
            ↓
        全部 COMPLETED
            ↓
        PENDING

    不负责：

        - 创建任务
        - 执行任务
        - 调用 Listener
        - 调用 Notion
        - 调度 Runner
    """

    def __init__(self, manager=None):
        self.manager = manager or TaskManager()

    # ---------------------------------------------------------
    # 获取磁盘中的最新任务
    # ---------------------------------------------------------

    def _get_latest_task(self, task):
        """
        根据 task_no 从磁盘重新读取任务。

        调用方传入的 task 可能是旧快照，
        因此不能直接使用其中的 status。
        """

        task_no = task.get("task_no")

        if task_no is None:
            return None

        return self.manager.get_task(task_no)

    # ---------------------------------------------------------
    # 判断 WAITING 是否可以恢复
    # ---------------------------------------------------------

    def can_recover(self, task):
        """
        判断一个 WAITING 任务是否可以恢复为 PENDING。

        始终以 tasks.json 当前状态为准。
        """

        # -----------------------------------------------------
        # 重新从磁盘读取最新版本
        # -----------------------------------------------------

        latest_task = self._get_latest_task(task)

        if latest_task is None:
            return False

        # -----------------------------------------------------
        # 必须是真正的 WAITING
        # -----------------------------------------------------

        if (
            latest_task.get("status")
            != self.manager.STATUS_WAITING
        ):
            return False

        page_id = latest_task.get(
            "target_page_id"
        )

        target_property = latest_task.get(
            "target_property"
        )

        # -----------------------------------------------------
        # 没有明确目标，不存在目标冲突
        # -----------------------------------------------------

        if not page_id or not target_property:
            return True

        current_task_no = latest_task.get(
            "task_no",
            0,
        )

        # -----------------------------------------------------
        # 从磁盘读取全部最新任务
        # -----------------------------------------------------

        tasks = self.manager.list_tasks()

        for other in tasks:

            other_task_no = other.get(
                "task_no",
                0,
            )

            # 只检查前置任务
            if other_task_no >= current_task_no:
                continue

            # 必须是同一个 Page
            if (
                other.get("target_page_id")
                != page_id
            ):
                continue

            # 必须是同一个 Property
            if (
                other.get("target_property")
                != target_property
            ):
                continue

            # -------------------------------------------------
            # 只有 COMPLETED 才释放后续任务
            # -------------------------------------------------

            if (
                other.get("status")
                != self.manager.STATUS_COMPLETED
            ):
                return False

        return True

    # ---------------------------------------------------------
    # 恢复单个任务
    # ---------------------------------------------------------

    def recover_task(self, task):
        """
        尝试恢复一个 WAITING 任务。

        返回：

            None
                当前任务不能恢复。

            dict
                恢复后的最新任务。
        """

        # -----------------------------------------------------
        # 再次获取磁盘最新状态
        # -----------------------------------------------------

        latest_task = self._get_latest_task(task)

        if latest_task is None:
            return None

        if not self.can_recover(latest_task):
            return None

        # -----------------------------------------------------
        # WAITING → PENDING
        # -----------------------------------------------------

        return self.manager.update_status(
            latest_task["task_no"],
            self.manager.STATUS_PENDING,
        )

    # ---------------------------------------------------------
    # 批量恢复
    # ---------------------------------------------------------

    def recover_all(self):
        """
        扫描全部 WAITING 任务。

        每个任务都会重新从磁盘确认最新状态。
        """

        recovered = []

        # 当前磁盘快照
        tasks = self.manager.list_tasks()

        for task in tasks:

            if (
                task.get("status")
                != self.manager.STATUS_WAITING
            ):
                continue

            recovered_task = self.recover_task(
                task
            )

            if recovered_task is not None:
                recovered.append(
                    recovered_task
                )

        return recovered