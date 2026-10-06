from watcher.service import WatcherService


class FakeWatcher:
    def __init__(self):
        self.calls = 0

    def check(self):
        self.calls += 1
        return [
            {"status": "NEW", "id": "page-1", "last_edited_time": "t1"},
            {"status": "UNCHANGED", "id": "page-2", "last_edited_time": "t2"},
        ]


class FakeManager:
    STATUS_COMPLETED = "COMPLETED"
    STATUS_FAILED = "FAILED"

    def __init__(self, tasks=None):
        self.tasks = tasks or []

    def list_tasks(self):
        return list(self.tasks)


class FakeExecutor:
    def __init__(self, tasks=None):
        self.calls = 0
        self.manager = FakeManager(tasks)

    def run_once(self):
        self.calls += 1
        if self.calls == 1:
            self.manager.tasks = []
            return {"task_no": 1, "status": "COMPLETED"}
        return None


def test_service_filters_changes_and_drains_executor():
    watcher = FakeWatcher()
    executor = FakeExecutor()

    service = WatcherService(
        interval=0,
        watcher=watcher,
        task_executor=executor,
    )

    result = service.run_once()

    assert watcher.calls == 1
    assert result["changes"] == [
        {"status": "NEW", "id": "page-1", "last_edited_time": "t1"}
    ]
    assert result["tasks"] == [
        {"task_no": 1, "status": "COMPLETED"}
    ]
    assert executor.calls == 2
    assert result["watcher_skipped"] is False


def test_service_skips_watcher_when_tasks_are_unfinished():
    watcher = FakeWatcher()
    executor = FakeExecutor(
        tasks=[
            {"task_no": 1, "status": "PENDING"},
            {"task_no": 2, "status": "WAITING"},
        ]
    )

    service = WatcherService(
        interval=0,
        watcher=watcher,
        task_executor=executor,
    )

    result = service.run_once()

    assert watcher.calls == 0
    assert result["changes"] == []
    assert result["watcher_skipped"] is True
    assert result["tasks"] == [
        {"task_no": 1, "status": "COMPLETED"}
    ]
