import json

from tasks.manager import TaskManager
from tasks.executor import TaskExecutor
from tasks.registry import TaskRegistry


def create_manager(tmp_path):

    config_dir = tmp_path / "config"
    config_dir.mkdir()

    task_file = config_dir / "tasks.json"

    task_file.write_text(
        json.dumps(
            {
                "version": 1,
                "tasks": {},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return TaskManager(
        task_file=task_file
    )


def create_registry(
    tmp_path,
    tasks,
):

    config_file = (
        tmp_path
        / "config"
        / "task_registry.json"
    )

    config_file.write_text(
        json.dumps(
            {
                "version": 1,
                "tasks": tasks,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return TaskRegistry(
        config_file=config_file
    )


# =========================================================
# PENDING → RUNNING → COMPLETED
# =========================================================


def test_execute_pending_task_success(
    tmp_path,
):

    manager = create_manager(
        tmp_path
    )

    registry = create_registry(
        tmp_path,
        {
            "测试任务": {
                "enabled": True,
                "listener_id": "LISTENER-001",
            }
        },
    )

    task = manager.create_task(
        task="测试任务",
        target_page_id="PAGE-A",
        target_property="房源ID",
    )

    executed = []

    def handler(current_task):

        executed.append(
            current_task
        )

        return {
            "message": "执行成功"
        }

    executor = TaskExecutor(
        manager=manager,
        registry=registry,
        handler=handler,
    )

    result = executor.run_once()

    assert result is not None

    assert (
        result["status"]
        == TaskManager.STATUS_COMPLETED
    )

    assert (
        result["task_no"]
        == task["task_no"]
    )

    assert (
        executed[0]["task_no"]
        == task["task_no"]
    )

    assert (
        executed[0][
            "_execution"
        ]["listener_id"]
        == "LISTENER-001"
    )

    assert (
        result["result"]["message"]
        == "执行成功"
    )


# =========================================================
# handler 异常 → FAILED
# =========================================================


def test_execute_pending_task_failure(
    tmp_path,
):

    manager = create_manager(
        tmp_path
    )

    registry = create_registry(
        tmp_path,
        {
            "失败任务": {
                "enabled": True,
                "listener_id": "LISTENER-001",
            }
        },
    )

    manager.create_task(
        task="失败任务",
        target_page_id="PAGE-A",
        target_property="房源ID",
    )

    def handler(current_task):

        raise RuntimeError(
            "模拟执行失败"
        )

    executor = TaskExecutor(
        manager=manager,
        registry=registry,
        handler=handler,
    )

    result = executor.run_once()

    assert result is not None

    assert (
        result["status"]
        == TaskManager.STATUS_FAILED
    )

    assert (
        result["result"]["error"]
        == "模拟执行失败"
    )

    assert (
        result["result"]["error_type"]
        == "RuntimeError"
    )


# =========================================================
# 没有 PENDING → 不执行
# =========================================================


def test_no_pending_task(
    tmp_path,
):

    manager = create_manager(
        tmp_path
    )

    registry = create_registry(
        tmp_path,
        {},
    )

    executor = TaskExecutor(
        manager=manager,
        registry=registry,
        handler=lambda task: {
            "message": "不应该执行"
        },
    )

    result = executor.run_once()

    assert result is None


# =========================================================
# 没有 Registry 配置 → 不执行
# =========================================================


def test_no_registry_config_does_not_execute(
    tmp_path,
):

    manager = create_manager(
        tmp_path
    )

    registry = create_registry(
        tmp_path,
        {},
    )

    task = manager.create_task(
        task="没有配置的任务",
        target_page_id="PAGE-A",
        target_property="房源ID",
    )

    executed = []

    def handler(current_task):

        executed.append(
            current_task
        )

        return {
            "message": "不应该执行"
        }

    executor = TaskExecutor(
        manager=manager,
        registry=registry,
        handler=handler,
    )

    result = executor.run_once()

    assert result is None

    assert executed == []

    current = manager.get_task(
        task["task_no"]
    )

    assert (
        current["status"]
        == TaskManager.STATUS_PENDING
    )


# =========================================================
# enabled=false → 不执行
# =========================================================


def test_disabled_task_does_not_execute(
    tmp_path,
):

    manager = create_manager(
        tmp_path
    )

    registry = create_registry(
        tmp_path,
        {
            "禁用任务": {
                "enabled": False,
                "listener_id": "LISTENER-001",
            }
        },
    )

    task = manager.create_task(
        task="禁用任务",
        target_page_id="PAGE-A",
        target_property="房源ID",
    )

    executed = []

    def handler(current_task):

        executed.append(
            current_task
        )

        return {
            "message": "不应该执行"
        }

    executor = TaskExecutor(
        manager=manager,
        registry=registry,
        handler=handler,
    )

    result = executor.run_once()

    assert result is None

    assert executed == []

    current = manager.get_task(
        task["task_no"]
    )

    assert (
        current["status"]
        == TaskManager.STATUS_PENDING
    )


# =========================================================
# 没有 listener_id → 不执行
# =========================================================


def test_missing_listener_id_does_not_execute(
    tmp_path,
):

    manager = create_manager(
        tmp_path
    )

    registry = create_registry(
        tmp_path,
        {
            "缺少Listener任务": {
                "enabled": True,
            }
        },
    )

    task = manager.create_task(
        task="缺少Listener任务",
        target_page_id="PAGE-A",
        target_property="房源ID",
    )

    executed = []

    def handler(current_task):

        executed.append(
            current_task
        )

        return {
            "message": "不应该执行"
        }

    executor = TaskExecutor(
        manager=manager,
        registry=registry,
        handler=handler,
    )

    result = executor.run_once()

    assert result is None

    assert executed == []

    current = manager.get_task(
        task["task_no"]
    )

    assert (
        current["status"]
        == TaskManager.STATUS_PENDING
    )


# =========================================================
# 没有 handler → 不执行
# =========================================================


def test_no_handler_does_not_change_task(
    tmp_path,
):

    manager = create_manager(
        tmp_path
    )

    registry = create_registry(
        tmp_path,
        {
            "测试任务": {
                "enabled": True,
                "listener_id": "LISTENER-001",
            }
        },
    )

    task = manager.create_task(
        task="测试任务",
        target_page_id="PAGE-A",
        target_property="房源ID",
    )

    executor = TaskExecutor(
        manager=manager,
        registry=registry,
    )

    result = executor.run_once()

    assert result is None

    current = manager.get_task(
        task["task_no"]
    )

    assert (
        current["status"]
        == TaskManager.STATUS_PENDING
    )


# =========================================================
# 串行执行
# =========================================================


def test_tasks_are_executed_sequentially(
    tmp_path,
):

    manager = create_manager(
        tmp_path
    )

    registry = create_registry(
        tmp_path,
        {
            "任务1": {
                "enabled": True,
                "listener_id": "LISTENER-001",
            },
            "任务2": {
                "enabled": True,
                "listener_id": "LISTENER-002",
            },
        },
    )

    task1 = manager.create_task(
        task="任务1",
        target_page_id="PAGE-A",
        target_property="房源ID",
    )

    task2 = manager.create_task(
        task="任务2",
        target_page_id="PAGE-A",
        target_property="房源状态",
    )

    execution_order = []

    def handler(task):

        execution_order.append(
            (
                task["task_no"],
                task["_execution"][
                    "listener_id"
                ],
            )
        )

        return {
            "task_no": task["task_no"]
        }

    executor = TaskExecutor(
        manager=manager,
        registry=registry,
        handler=handler,
    )

    result1 = executor.run_once()

    assert (
        result1["task_no"]
        == task1["task_no"]
    )

    result2 = executor.run_once()

    assert (
        result2["task_no"]
        == task2["task_no"]
    )

    assert execution_order == [
        (
            task1["task_no"],
            "LISTENER-001",
        ),
        (
            task2["task_no"],
            "LISTENER-002",
        ),
    ]


# =========================================================
# WAITING 会先恢复，再执行
# =========================================================


def test_waiting_task_recovers_then_executes(
    tmp_path,
):

    manager = create_manager(
        tmp_path
    )

    registry = create_registry(
        tmp_path,
        {
            "任务1": {
                "enabled": True,
                "listener_id": "LISTENER-001",
            },
            "任务2": {
                "enabled": True,
                "listener_id": "LISTENER-001",
            },
        },
    )

    task1 = manager.create_task(
        task="任务1",
        target_page_id="PAGE-A",
        target_property="房源ID",
    )

    task2 = manager.create_task(
        task="任务2",
        target_page_id="PAGE-A",
        target_property="房源ID",
    )

    manager.update_status(
        task1["task_no"],
        TaskManager.STATUS_COMPLETED,
    )

    manager.update_status(
        task2["task_no"],
        TaskManager.STATUS_WAITING,
    )

    executed = []

    def handler(task):

        executed.append(
            task["task_no"]
        )

        return {
            "message": "恢复后执行"
        }

    executor = TaskExecutor(
        manager=manager,
        registry=registry,
        handler=handler,
    )

    result = executor.run_once()

    assert result is not None

    assert (
        result["task_no"]
        == task2["task_no"]
    )

    assert (
        result["status"]
        == TaskManager.STATUS_COMPLETED
    )

    assert executed == [
        task2["task_no"]
    ]

    assert (
        result["_execution"]
        if "_execution" in result
        else True
    )