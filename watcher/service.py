import time

from tasks.executor import TaskExecutor

from .global_watcher import GlobalWatcher


class WatcherService:
    """
    GlobalWatcher 常驻服务。

    每一轮：

        1. 检查 Notion 页面变化
        2. Dispatcher 创建任务
        3. TaskExecutor 顺序执行全部待处理任务
    """

    def __init__(
        self,
        interval=10,
        watcher=None,
        task_executor=None,
    ):
        self.interval = interval

        self.watcher = (
            watcher
            or GlobalWatcher()
        )

        self.task_executor = (
            task_executor
            or TaskExecutor()
        )

        self.running = False

    def run_once(self):

        changes = self.watcher.check()

        changed = [
            item
            for item in changes
            if item["status"]
            in (
                "NEW",
                "CHANGED",
            )
        ]

        print(
            f"[Watcher] "
            f"页面：{len(changes)} | "
            f"变化：{len(changed)}"
        )

        for item in changed:
            print(
                f"  [{item['status']}] "
                f"{item['id']} "
                f"{item['last_edited_time']}"
            )

        # -----------------------------------------------------
        # 顺序执行任务
        # -----------------------------------------------------

        executed = []

        while True:

            result = (
                self.task_executor
                .run_once()
            )

            if result is None:
                break

            executed.append(result)

        print(
            f"[TaskExecutor] "
            f"本轮执行任务：{len(executed)}"
        )

        return {
            "changes": changed,
            "tasks": executed,
        }

    def run(self):

        self.running = True

        print(
            "WatcherService 已启动"
        )

        print(
            f"监听间隔：{self.interval} 秒"
        )

        print(
            "按 Ctrl+C 停止"
        )

        print("-" * 60)

        while self.running:

            try:
                self.run_once()

            except Exception as exc:

                print(
                    f"[Watcher ERROR] "
                    f"{type(exc).__name__}: {exc}"
                )

            time.sleep(
                self.interval
            )

    def stop(self):
        self.running = False