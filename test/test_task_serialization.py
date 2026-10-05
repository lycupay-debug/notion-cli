from tasks.manager import TaskManager


def test_same_business_task_is_not_created_twice_after_completion(tmp_path):
    manager = TaskManager(task_file=tmp_path / "tasks.json")

    first = manager.create_task(
        "同步Listener字段",
        target_page_id="page-1",
        target_property="listener_id",
    )
    manager.update_status(first["task_no"], manager.STATUS_RUNNING)
    manager.update_status(
        first["task_no"],
        manager.STATUS_COMPLETED,
        result={"verified": True},
    )

    duplicate = manager.create_task(
        "同步Listener字段",
        target_page_id="page-1",
        target_property="listener_id",
    )

    assert duplicate["task_id"] == first["task_id"]
    assert len(manager.list_tasks()) == 1
    assert manager.get_next_pending_task() is None


def test_same_business_task_is_not_created_twice_after_failure(tmp_path):
    manager = TaskManager(task_file=tmp_path / "tasks.json")

    first = manager.create_task(
        "同步Listener字段",
        target_page_id="page-1",
        target_property="listener_id",
    )
    manager.update_status(first["task_no"], manager.STATUS_RUNNING)
    manager.update_status(
        first["task_no"],
        manager.STATUS_FAILED,
        result={"error": "test"},
    )

    duplicate = manager.create_task(
        "同步Listener字段",
        target_page_id="page-1",
        target_property="listener_id",
    )

    assert duplicate["task_id"] == first["task_id"]
    assert duplicate["status"] == manager.STATUS_FAILED
    assert len(manager.list_tasks()) == 1
    assert manager.get_next_pending_task() is None


def test_same_name_different_business_waits_for_previous(tmp_path):
    manager = TaskManager(task_file=tmp_path / "tasks.json")

    first = manager.create_task(
        "更新系统结构notion页面ID",
        target_page_id="page-1",
        target_property="Notion页面ID",
    )
    second = manager.create_task(
        "更新系统结构notion页面ID",
        target_page_id="page-2",
        target_property="Notion页面ID",
    )

    assert first["status"] == manager.STATUS_PENDING
    assert second["status"] == manager.STATUS_WAITING
    assert manager.get_next_pending_task()["task_id"] == first["task_id"]


def test_same_name_waiting_releases_after_previous_success(tmp_path):
    manager = TaskManager(task_file=tmp_path / "tasks.json")

    first = manager.create_task(
        "更新系统结构notion页面ID",
        target_page_id="page-1",
        target_property="Notion页面ID",
    )
    second = manager.create_task(
        "更新系统结构notion页面ID",
        target_page_id="page-2",
        target_property="Notion页面ID",
    )

    manager.update_status(first["task_no"], manager.STATUS_RUNNING)
    assert manager.get_next_pending_task() is None

    manager.update_status(first["task_no"], manager.STATUS_COMPLETED)

    next_task = manager.get_next_pending_task()
    assert next_task["task_id"] == second["task_id"]
    assert manager.get_task(second["task_no"])["status"] == manager.STATUS_PENDING


def test_same_name_waiting_releases_after_previous_failure_without_retrying_failed_task(tmp_path):
    manager = TaskManager(task_file=tmp_path / "tasks.json")

    first = manager.create_task(
        "更新系统结构notion页面ID",
        target_page_id="page-1",
        target_property="Notion页面ID",
    )
    second = manager.create_task(
        "更新系统结构notion页面ID",
        target_page_id="page-2",
        target_property="Notion页面ID",
    )

    manager.update_status(first["task_no"], manager.STATUS_RUNNING)
    manager.update_status(
        first["task_no"],
        manager.STATUS_FAILED,
        result={"error": "test"},
    )

    next_task = manager.get_next_pending_task()

    assert next_task["task_id"] == second["task_id"]
    assert manager.get_task(first["task_no"])["status"] == manager.STATUS_FAILED
