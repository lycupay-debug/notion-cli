import json

from tasks.manager import TaskManager
from tasks.executor import TaskExecutor


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


# =========================================================
# PENDING → RUNNING → COMPLETED
# =========================================================


def test_execute_pending_task_success(tmp_path):

    manager = create_manager(tmp_path)

    task = manager.create_task(
        task="测试任务",
        target_page_id="PAGE-A",
        target_property="房源ID",
    )

    executed = []

    def handler(current_task):
        executed.append(
            current_task["task_no"]
        )

        return {
            "message": "执行成功"
        }

    executor = TaskExecutor(
        manager=manager,
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

    assert executed == [
        task["task_no"]
    ]

    assert (
        result["result"]["message"]
        == "执行成功"
    )


# =========================================================
# handler 异常 → FAILED
# =========================================================


def test_execute_pending_task_failure(tmp_path):

    manager = create_manager(tmp_path)

    task = manager.create_task(
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


def test_no_pending_task(tmp_path):

    manager = create_manager(tmp_path)

    executor = TaskExecutor(
        manager=manager,
        handler=lambda task: {
            "message": "不应该执行"
        },
    )

    result = executor.run_once()

    assert result is None


# =========================================================
# 没有 handler → 不执行
# =========================================================


def test_no_handler_does_not_change_task(
    tmp_path,
):

    manager = create_manager(tmp_path)

    task = manager.create_task(
        task="测试任务",
        target_page_id="PAGE-A",
        target_property="房源ID",
    )

    executor = TaskExecutor(
        manager=manager,
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

    manager = create_manager(tmp_path)

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
            task["task_no"]
        )

        return {
            "task_no": task["task_no"]
        }

    executor = TaskExecutor(
        manager=manager,
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
        task1["task_no"],
        task2["task_no"],
    ]


# =========================================================
# WAITING 会先恢复，再执行
# =========================================================


def test_waiting_task_recovers_then_executes(
    tmp_path,
):

    manager = create_manager(tmp_path)

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