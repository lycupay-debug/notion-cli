from tasks.manager import TaskManager
from tasks.recovery import TaskRecovery


def test_waiting_recovers_only_after_all_previous_conflicts_complete(tmp_path):
    manager = TaskManager(task_file=tmp_path / "tasks.json")
    recovery = TaskRecovery(manager=manager)

    first = manager.create_task(
        "task-a", target_page_id="page-1", target_property="name"
    )
    second = manager.create_task(
        "task-b", target_page_id="page-1", target_property="name"
    )

    manager.update_status(first["task_no"], manager.STATUS_RUNNING)
    manager.update_status(second["task_no"], manager.STATUS_WAITING)

    assert recovery.can_recover(second) is False

    manager.update_status(first["task_no"], manager.STATUS_COMPLETED)

    assert recovery.can_recover(second) is True
    recovered = recovery.recover_task(second)
    assert recovered["status"] == manager.STATUS_PENDING


def test_different_property_does_not_block_recovery(tmp_path):
    manager = TaskManager(task_file=tmp_path / "tasks.json")
    recovery = TaskRecovery(manager=manager)

    first = manager.create_task(
        "task-a", target_page_id="page-1", target_property="name"
    )
    second = manager.create_task(
        "task-b", target_page_id="page-1", target_property="price"
    )

    manager.update_status(first["task_no"], manager.STATUS_RUNNING)
    manager.update_status(second["task_no"], manager.STATUS_WAITING)

    assert recovery.can_recover(second) is True
