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


class FakeExecutor:
    def __init__(self):
        self.calls = 0

    def run_once(self):
        self.calls += 1
        if self.calls == 1:
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
