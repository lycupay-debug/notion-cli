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


def test_every_event_creates_a_new_task(tmp_path):
    manager = TaskManager(task_file=tmp_path / "tasks.json")

    first = manager.create_task(
        "更新房源ID",
        target_page_id="page-1",
        target_property="房源ID",
    )
    second = manager.create_task(
        "更新房源ID",
        target_page_id="page-1",
        target_property="房源ID",
    )

    assert first["task_no"] == 1
    assert second["task_no"] == 2
    assert first["task_id"] != second["task_id"]
    assert second["status"] == manager.STATUS_WAITING


def test_task_numbers_define_priority(tmp_path):
    manager = TaskManager(task_file=tmp_path / "tasks.json")

    first = manager.create_task("task-a")
    second = manager.create_task("task-b")

    assert first["task_no"] == 1
    assert second["task_no"] == 2
    assert manager.get_next_pending_task()["task_no"] == 1


def test_different_task_names_are_not_serialized_by_name(tmp_path):
    manager = TaskManager(task_file=tmp_path / "tasks.json")

    first = manager.create_task(
        "task-a", target_page_id="page-1", target_property="name"
    )
    second = manager.create_task(
        "task-b", target_page_id="page-1", target_property="name"
    )

    assert first["status"] == manager.STATUS_PENDING
    assert second["status"] == manager.STATUS_PENDING


def test_failed_task_is_terminal_and_not_reexecuted(tmp_path):
    manager = TaskManager(task_file=tmp_path / "tasks.json")

    first = manager.create_task("task-a")
    manager.update_status(first["task_no"], manager.STATUS_RUNNING)
    manager.update_status(
        first["task_no"],
        manager.STATUS_FAILED,
        result={"error": "test"},
    )

    assert manager.get_next_pending_task() is None
    assert manager.get_task(first["task_no"])["status"] == manager.STATUS_FAILED


def test_same_name_waits_until_previous_task_finishes(tmp_path):
    manager = TaskManager(task_file=tmp_path / "tasks.json")

    first = manager.create_task("task-a")
    second = manager.create_task("task-a")
    third = manager.create_task("task-a")

    assert first["status"] == manager.STATUS_PENDING
    assert second["status"] == manager.STATUS_WAITING
    assert third["status"] == manager.STATUS_WAITING
