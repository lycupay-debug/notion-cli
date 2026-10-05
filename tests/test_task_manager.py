from tasks.manager import TaskManager


def test_create_and_get_task(tmp_path):
    manager = TaskManager(task_file=tmp_path / "tasks.json")

    task = manager.create_task(
        "更新房源ID",
        target_page_id="page-1",
        target_property="房源ID",
    )

    assert task["task_no"] == 1
    assert task["status"] == manager.STATUS_PENDING
    assert manager.get_task(1)["task_id"] == task["task_id"]


def test_task_numbers_increment_and_pending_order(tmp_path):
    manager = TaskManager(task_file=tmp_path / "tasks.json")

    first = manager.create_task("task-a")
    second = manager.create_task("task-b")

    assert first["task_no"] == 1
    assert second["task_no"] == 2
    assert manager.get_next_pending_task()["task_no"] == 1


def test_conflict_uses_page_and_property(tmp_path):
    manager = TaskManager(task_file=tmp_path / "tasks.json")

    first = manager.create_task(
        "task-a", target_page_id="page-1", target_property="name"
    )
    second = manager.create_task(
        "task-b", target_page_id="page-1", target_property="name"
    )
    third = manager.create_task(
        "task-c", target_page_id="page-1", target_property="price"
    )

    assert manager.has_conflict(first) is False
    assert manager.has_conflict(second) is True
    assert manager.has_conflict(third) is False


def test_waiting_task_is_not_pending(tmp_path):
    manager = TaskManager(task_file=tmp_path / "tasks.json")

    first = manager.create_task(
        "task-a", target_page_id="page-1", target_property="name"
    )
    second = manager.create_task(
        "task-b", target_page_id="page-1", target_property="name"
    )

    assert manager.mark_waiting_if_conflict(second) is True
    assert manager.get_task(second["task_no"])["status"] == manager.STATUS_WAITING
    assert manager.get_next_pending_task()["task_no"] == first["task_no"]
