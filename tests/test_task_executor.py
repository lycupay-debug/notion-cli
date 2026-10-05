from tasks.executor import TaskExecutor
from tasks.manager import TaskManager


class FakeRecovery:
    def __init__(self):
        self.calls = 0

    def recover_all(self):
        self.calls += 1
        return []


class FakeRegistry:
    def get_config(self, task_name):
        return {
            "enabled": True,
            "listener_id": "listener-1",
        }


class FakeLoader:
    def __init__(self):
        self.loaded = []

    def is_enabled(self, listener_id):
        return True

    def load(self, listener_id):
        self.loaded.append(listener_id)
        return FakeListener()


class FakeListener:
    def handle(self, page_id):
        return {"status": "UPDATED", "page_id": page_id}


def test_executor_runs_listener_and_completes_task(tmp_path):
    manager = TaskManager(task_file=tmp_path / "tasks.json")
    recovery = FakeRecovery()
    loader = FakeLoader()

    manager.create_task(
        "更新房源ID",
        target_page_id="page-1",
        target_property="房源ID",
    )

    executor = TaskExecutor(
        manager=manager,
        recovery=recovery,
        registry=FakeRegistry(),
        listener_loader=loader,
    )

    result = executor.run_once()

    assert recovery.calls == 1
    assert loader.loaded == ["listener-1"]
    assert result["status"] == manager.STATUS_COMPLETED
    assert result["result"]["page_id"] == "page-1"


def test_executor_marks_listener_error_as_failed(tmp_path):
    class BrokenListener:
        def handle(self, page_id):
            raise RuntimeError("boom")

    class BrokenLoader(FakeLoader):
        def load(self, listener_id):
            return BrokenListener()

    manager = TaskManager(task_file=tmp_path / "tasks.json")
    manager.create_task("更新房源ID", target_page_id="page-1")

    executor = TaskExecutor(
        manager=manager,
        recovery=FakeRecovery(),
        registry=FakeRegistry(),
        listener_loader=BrokenLoader(),
    )

    result = executor.run_once()

    assert result["status"] == manager.STATUS_FAILED
    assert result["result"]["error"] == "boom"
    assert result["result"]["error_type"] == "RuntimeError"


def test_executor_does_not_run_disabled_listener(tmp_path):
    class DisabledLoader(FakeLoader):
        def is_enabled(self, listener_id):
            return False

    manager = TaskManager(task_file=tmp_path / "tasks.json")
    task = manager.create_task("更新房源ID", target_page_id="page-1")

    executor = TaskExecutor(
        manager=manager,
        recovery=FakeRecovery(),
        registry=FakeRegistry(),
        listener_loader=DisabledLoader(),
    )

    assert executor.run_once() is None
    assert manager.get_task(task["task_no"])["status"] == manager.STATUS_PENDING
