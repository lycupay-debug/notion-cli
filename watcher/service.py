import time

from .global_watcher import GlobalWatcher


class WatcherService:
    """
    GlobalWatcher 常驻服务。

    职责：
    - 持续运行
    - 按固定间隔调用 GlobalWatcher
    - 暂时只输出检测结果
    - 不负责具体业务处理
    """

    def __init__(self, interval=5):
        self.interval = interval
        self.watcher = GlobalWatcher()
        self.running = False

    def run_once(self):
        """执行一次监听。"""
        changes = self.watcher.check()

        changed = [
            item
            for item in changes
            if item["status"] in ("NEW", "CHANGED")
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

        return changed

    def run(self):
        """持续运行监听服务。"""
        self.running = True

        print("WatcherService 已启动")
        print(f"监听间隔：{self.interval} 秒")
        print("按 Ctrl+C 停止")
        print("-" * 60)

        while self.running:
            try:
                self.run_once()

            except Exception as e:
                print(
                    f"[Watcher ERROR] "
                    f"{type(e).__name__}: {e}"
                )

            time.sleep(self.interval)

    def stop(self):
        """停止服务。"""
        self.running = False