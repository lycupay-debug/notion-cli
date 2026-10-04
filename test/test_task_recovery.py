import json

from tasks.manager import TaskManager
from tasks.recovery import TaskRecovery


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
# 前置任务完成
# WAITING → PENDING
# =========================================================


def test_waiting_task_recovers_after_previous_completed(
    tmp_path,
):

    manager = create_manager(
        tmp_path
    )

    task1 = manager.create_task(
        task="任务A",
        target_page_id="PAGE-A",
        target_property="房源ID",
    )

    task2 = manager.create_task(
        task="任务B",
        target_page_id="PAGE-A",
        target_property="房源ID",
    )

    # 模拟：
    # task1 已经执行完成
    # task2 正在等待
    manager.update_status(
        task1["task_no"],
        TaskManager.STATUS_COMPLETED,
    )

    manager.update_status(
        task2["task_no"],
        TaskManager.STATUS_WAITING,
    )

    recovery = TaskRecovery(
        manager=manager
    )

    recovered = recovery.recover_task(
        task2
    )

    assert recovered is not None

    assert (
        recovered["status"]
        == TaskManager.STATUS_PENDING
    )


# =========================================================
# 前置任务 RUNNING
# 不恢复
# =========================================================


def test_waiting_task_does_not_recover_when_previous_running(
    tmp_path,
):

    manager = create_manager(
        tmp_path
    )

    task1 = manager.create_task(
        task="任务A",
        target_page_id="PAGE-A",
        target_property="房源ID",
    )

    task2 = manager.create_task(
        task="任务B",
        target_page_id="PAGE-A",
        target_property="房源ID",
    )

    manager.update_status(
        task1["task_no"],
        TaskManager.STATUS_RUNNING,
    )

    manager.update_status(
        task2["task_no"],
        TaskManager.STATUS_WAITING,
    )

    recovery = TaskRecovery(
        manager=manager
    )

    recovered = recovery.recover_task(
        task2
    )

    assert recovered is None

    current = manager.get_task(
        task2["task_no"]
    )

    assert (
        current["status"]
        == TaskManager.STATUS_WAITING
    )


# =========================================================
# 前置任务 FAILED
# 不恢复
# =========================================================


def test_waiting_task_does_not_recover_when_previous_failed(
    tmp_path,
):

    manager = create_manager(
        tmp_path
    )

    task1 = manager.create_task(
        task="任务A",
        target_page_id="PAGE-A",
        target_property="房源ID",
    )

    task2 = manager.create_task(
        task="任务B",
        target_page_id="PAGE-A",
        target_property="房源ID",
    )

    manager.update_status(
        task1["task_no"],
        TaskManager.STATUS_FAILED,
        result={
            "error": "测试失败"
        },
    )

    manager.update_status(
        task2["task_no"],
        TaskManager.STATUS_WAITING,
    )

    recovery = TaskRecovery(
        manager=manager
    )

    recovered = recovery.recover_task(
        task2
    )

    assert recovered is None

    current = manager.get_task(
        task2["task_no"]
    )

    assert (
        current["status"]
        == TaskManager.STATUS_WAITING
    )


# =========================================================
# 同页面不同属性
# 不存在前置冲突
# =========================================================


def test_different_property_can_recover(
    tmp_path,
):

    manager = create_manager(
        tmp_path
    )

    task1 = manager.create_task(
        task="任务A",
        target_page_id="PAGE-A",
        target_property="房源ID",
    )

    task2 = manager.create_task(
        task="任务B",
        target_page_id="PAGE-A",
        target_property="房源状态",
    )

    manager.update_status(
        task1["task_no"],
        TaskManager.STATUS_RUNNING,
    )

    manager.update_status(
        task2["task_no"],
        TaskManager.STATUS_WAITING,
    )

    recovery = TaskRecovery(
        manager=manager
    )

    recovered = recovery.recover_task(
        task2
    )

    assert recovered is not None

    assert (
        recovered["status"]
        == TaskManager.STATUS_PENDING
    )


# =========================================================
# 多个前置任务
# 必须全部 COMPLETED
# =========================================================


def test_all_previous_tasks_must_be_completed(
    tmp_path,
):

    manager = create_manager(
        tmp_path
    )

    task1 = manager.create_task(
        task="任务A",
        target_page_id="PAGE-A",
        target_property="房源ID",
    )

    task2 = manager.create_task(
        task="任务B",
        target_page_id="PAGE-A",
        target_property="房源ID",
    )

    task3 = manager.create_task(
        task="任务C",
        target_page_id="PAGE-A",
        target_property="房源ID",
    )

    # task1 完成
    manager.update_status(
        task1["task_no"],
        TaskManager.STATUS_COMPLETED,
    )

    # task2 仍然没有完成
    manager.update_status(
        task2["task_no"],
        TaskManager.STATUS_RUNNING,
    )

    manager.update_status(
        task3["task_no"],
        TaskManager.STATUS_WAITING,
    )

    recovery = TaskRecovery(
        manager=manager
    )

    recovered = recovery.recover_task(
        task3
    )

    # task2 未完成，所以 task3 不能恢复。
    assert recovered is None

    # task2 完成
    manager.update_status(
        task2["task_no"],
        TaskManager.STATUS_COMPLETED,
    )

    recovered = recovery.recover_task(
        task3
    )

    assert recovered is not None

    assert (
        recovered["status"]
        == TaskManager.STATUS_PENDING
    )


# =========================================================
# 批量恢复
# =========================================================


def test_recover_all(
    tmp_path,
):

    manager = create_manager(
        tmp_path
    )

    task1 = manager.create_task(
        task="任务A",
        target_page_id="PAGE-A",
        target_property="房源ID",
    )

    task2 = manager.create_task(
        task="任务B",
        target_page_id="PAGE-A",
        target_property="房源ID",
    )

    task3 = manager.create_task(
        task="任务C",
        target_page_id="PAGE-B",
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

    manager.update_status(
        task3["task_no"],
        TaskManager.STATUS_WAITING,
    )

    recovery = TaskRecovery(
        manager=manager
    )

    recovered = recovery.recover_all()

    recovered_numbers = [
        task["task_no"]
        for task in recovered
    ]

    assert (
        task2["task_no"]
        in recovered_numbers
    )

    assert (
        task3["task_no"]
        in recovered_numbers
    )

    assert (
        manager.get_task(
            task2["task_no"]
        )["status"]
        == TaskManager.STATUS_PENDING
    )

    assert (
        manager.get_task(
            task3["task_no"]
        )["status"]
        == TaskManager.STATUS_PENDING
    )