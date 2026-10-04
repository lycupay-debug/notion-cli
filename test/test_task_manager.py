import json
import tempfile
from pathlib import Path

from tasks.manager import TaskManager


def create_manager(tmp_path):
    """
    创建一个独立测试用 tasks.json。
    """

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


def test_create_task(tmp_path):

    manager = create_manager(
        tmp_path
    )

    task = manager.create_task(
        task="同步房源ID",
        target_page_id="PAGE-A",
        target_property="房源ID",
    )

    assert task["task_no"] == 1
    assert task["task_id"]
    assert task["task"] == "同步房源ID"
    assert task["status"] == "PENDING"

    assert (
        task["target_page_id"]
        == "PAGE-A"
    )

    assert (
        task["target_property"]
        == "房源ID"
    )


def test_task_number_increments(tmp_path):

    manager = create_manager(
        tmp_path
    )

    task1 = manager.create_task(
        task="任务A"
    )

    task2 = manager.create_task(
        task="任务B"
    )

    task3 = manager.create_task(
        task="任务C"
    )

    assert task1["task_no"] == 1
    assert task2["task_no"] == 2
    assert task3["task_no"] == 3


def test_read_from_disk(tmp_path):

    manager = create_manager(
        tmp_path
    )

    task = manager.create_task(
        task="任务A"
    )

    # 直接修改 JSON 文件。
    data = json.loads(
        manager.task_file.read_text(
            encoding="utf-8"
        )
    )

    data["tasks"]["000001"]["task"] = (
        "外部修改任务"
    )

    manager.task_file.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    # TaskManager 必须读取磁盘最新内容。
    loaded = manager.get_task(
        task["task_no"]
    )

    assert (
        loaded["task"]
        == "外部修改任务"
    )


def test_update_status(tmp_path):

    manager = create_manager(
        tmp_path
    )

    task = manager.create_task(
        task="任务A"
    )

    updated = manager.update_status(
        task["task_no"],
        TaskManager.STATUS_COMPLETED,
        result={
            "message": "完成"
        },
    )

    assert (
        updated["status"]
        == "COMPLETED"
    )

    assert (
        updated["result"]["message"]
        == "完成"
    )

    loaded = manager.get_task(
        task["task_no"]
    )

    assert (
        loaded["status"]
        == "COMPLETED"
    )


def test_get_next_pending_task(tmp_path):

    manager = create_manager(
        tmp_path
    )

    task1 = manager.create_task(
        task="任务A"
    )

    task2 = manager.create_task(
        task="任务B"
    )

    next_task = (
        manager.get_next_pending_task()
    )

    assert (
        next_task["task_no"]
        == task1["task_no"]
    )

    manager.update_status(
        task1["task_no"],
        TaskManager.STATUS_COMPLETED,
    )

    next_task = (
        manager.get_next_pending_task()
    )

    assert (
        next_task["task_no"]
        == task2["task_no"]
    )


def test_same_page_different_property_no_conflict(
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

    assert (
        manager.has_conflict(task1)
        is False
    )

    assert (
        manager.has_conflict(task2)
        is False
    )


def test_same_page_same_property_has_conflict(
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

    assert (
        manager.has_conflict(task2)
        is True
    )


def test_completed_task_does_not_block(
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
        TaskManager.STATUS_COMPLETED,
    )

    assert (
        manager.has_conflict(task2)
        is False
    )