from tasks.manager import TaskManager
from tasks.recovery import TaskRecovery


def test_waiting_recovers_after_previous_same_name_completes(tmp_path):
    manager = TaskManager(task_file=tmp_path / "tasks.json")
    recovery = TaskRecovery(manager=manager)

    first = manager.create_task("task-a", target_page_id="page-1")
    second = manager.create_task("task-a", target_page_id="page-2")

    assert second["status"] == manager.STATUS_WAITING

    manager.update_status(first["task_no"], manager.STATUS_RUNNING)
    assert recovery.can_recover(second) is False

    manager.update_status(first["task_no"], manager.STATUS_COMPLETED)

    assert recovery.can_recover(second) is True
    recovered = recovery.recover_task(second)
    assert recovered["status"] == manager.STATUS_PENDING


def test_waiting_recovers_after_previous_same_name_fails(tmp_path):
    manager = TaskManager(task_file=tmp_path / "tasks.json")
    recovery = TaskRecovery(manager=manager)

    first = manager.create_task("task-a", target_page_id="page-1")
    second = manager.create_task("task-a", target_page_id="page-2")

    manager.update_status(first["task_no"], manager.STATUS_RUNNING)
    manager.update_status(first["task_no"], manager.STATUS_FAILED)

    assert recovery.can_recover(second) is True
    recovered = recovery.recover_task(second)
    assert recovered["status"] == manager.STATUS_PENDING


def test_different_task_name_does_not_wait(tmp_path):
    manager = TaskManager(task_file=tmp_path / "tasks.json")
    recovery = TaskRecovery(manager=manager)

    first = manager.create_task("task-a", target_page_id="page-1")
    second = manager.create_task("task-b", target_page_id="page-1")

    assert first["status"] == manager.STATUS_PENDING
    assert second["status"] == manager.STATUS_PENDING
    assert recovery.can_recover(second) is False
