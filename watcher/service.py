import time

from tasks.executor import TaskExecutor

from .global_watcher import GlobalWatcher


class WatcherService:
    """GlobalWatcher 常驻服务。

    调度规则：

    1. 先检查是否存在未完成任务。
    2. 任务队列非空时，只允许 TaskExecutor 工作，禁止新一轮 Watcher 扫描。
    3. 只有任务队列完全清空后，才开始下一轮 Watcher 扫描。
    4. Watcher 创建本轮任务后，立即串行排空任务队列。
    """

    def __init__(self, interval=10, watcher=None, task_executor=None):
        self.interval = interval
        self.watcher = watcher or GlobalWatcher()
        self.task_executor = task_executor or TaskExecutor()
        self.running = False

    def _has_unfinished_tasks(self):
        """判断任务清单中是否仍存在非终态任务。"""
        manager = getattr(self.task_executor, "manager", None)
        if manager is None:
            return False

        tasks = manager.list_tasks()
        terminal = {
            manager.STATUS_COMPLETED,
            manager.STATUS_FAILED,
        }
        return any(
            task.get("status") not in terminal
            for task in tasks
        )

    def _drain_tasks(self):
        """持续执行任务，直到队列没有可执行任务。"""
        executed = []

        while True:
            result = self.task_executor.run_once()
            if result is None:
                break
            executed.append(result)

        return executed

    def run_once(self):
        executed = []

        # 关键时序：上一轮还有任务时，不得再次扫描 Notion。
        if self._has_unfinished_tasks():
            print("[Watcher] 任务队列未清空，暂停新一轮监听扫描")
            executed = self._drain_tasks()
            print(f"[TaskExecutor] 本轮继续执行任务：{len(executed)}")
            return {
                "changes": [],
                "tasks": executed,
                "watcher_skipped": True,
            }

        # 队列为空，才允许开启新的监听周期。
        changes = self.watcher.check()

        changed = [
            item
            for item in changes
            if item["status"] in ("NEW", "CHANGED")
        ]

        print(
            f"[Watcher] 页面：{len(changes)} | "
            f"变化：{len(changed)}"
        )

        for item in changed:
            print(
                f"  [{item['status']}] "
                f"{item['id']} "
                f"{item['last_edited_time']}"
            )

        # Watcher/Dispatcher 已经在 check() 中创建任务；现在排空本轮任务。
        executed = self._drain_tasks()

        print(f"[TaskExecutor] 本轮执行任务：{len(executed)}")

        return {
            "changes": changed,
            "tasks": executed,
            "watcher_skipped": False,
        }

    def run(self):
        self.running = True

        print("WatcherService 已启动")
        print(f"监听间隔：{self.interval} 秒")
        print("按 Ctrl+C 停止")
        print("-" * 60)

        while self.running:
            try:
                self.run_once()
            except Exception as exc:
                print(
                    f"[Watcher ERROR] "
                    f"{type(exc).__name__}: {exc}"
                )

            time.sleep(self.interval)

    def stop(self):
        self.running = False
