import json

import pytest

from tasks.registry import TaskRegistry


# =========================================================
# 测试 Handler
# =========================================================


def handler_a(task):
    return {
        "handler": "A",
        "task_no": task["task_no"],
    }


def handler_b(task):
    return {
        "handler": "B",
        "task_no": task["task_no"],
    }


# =========================================================
# 创建测试配置
# =========================================================


def create_config(
    tmp_path,
    tasks=None,
):

    if tasks is None:
        tasks = {}

    config_file = (
        tmp_path
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

    return config_file


# =========================================================
# 原有：运行时注册
# =========================================================


def test_register_handler(tmp_path):

    config_file = create_config(
        tmp_path
    )

    registry = TaskRegistry(
        config_file=config_file
    )

    result = registry.register(
        "测试任务",
        handler_a,
    )

    assert result is None

    assert registry.has(
        "测试任务"
    )

    assert (
        registry.get("测试任务")
        is handler_a
    )


# =========================================================
# 原有：获取 Handler
# =========================================================


def test_get_registered_handler(
    tmp_path,
):

    config_file = create_config(
        tmp_path
    )

    registry = TaskRegistry(
        config_file=config_file
    )

    registry.register(
        "测试任务",
        handler_a,
    )

    handler = registry.get(
        "测试任务"
    )

    assert handler is handler_a


# =========================================================
# 原有：不存在
# =========================================================


def test_get_unregistered_handler(
    tmp_path,
):

    config_file = create_config(
        tmp_path
    )

    registry = TaskRegistry(
        config_file=config_file
    )

    assert (
        registry.get("不存在")
        is None
    )

    assert not registry.has(
        "不存在"
    )


# =========================================================
# 原有：多个 Handler
# =========================================================


def test_multiple_handlers(
    tmp_path,
):

    config_file = create_config(
        tmp_path
    )

    registry = TaskRegistry(
        config_file=config_file
    )

    registry.register(
        "任务A",
        handler_a,
    )

    registry.register(
        "任务B",
        handler_b,
    )

    assert (
        registry.get("任务A")
        is handler_a
    )

    assert (
        registry.get("任务B")
        is handler_b
    )


# =========================================================
# 原有：重复注册
# =========================================================


def test_duplicate_registration_fails(
    tmp_path,
):

    config_file = create_config(
        tmp_path
    )

    registry = TaskRegistry(
        config_file=config_file
    )

    registry.register(
        "测试任务",
        handler_a,
    )

    with pytest.raises(
        ValueError
    ):

        registry.register(
            "测试任务",
            handler_b,
        )


# =========================================================
# 新增：读取 JSON 配置
# =========================================================


def test_load_task_config(
    tmp_path,
):

    config_file = create_config(
        tmp_path,
        {
            "更新房源ID": {
                "enabled": True,
                "listener_id": "LISTENER-001",
            }
        },
    )

    registry = TaskRegistry(
        config_file=config_file
    )

    config = registry.get_config(
        "更新房源ID"
    )

    assert config == {
        "enabled": True,
        "listener_id": "LISTENER-001",
    }


# =========================================================
# 新增：判断 JSON 任务是否存在
# =========================================================


def test_has_config(
    tmp_path,
):

    config_file = create_config(
        tmp_path,
        {
            "更新房源ID": {
                "enabled": True,
                "listener_id": "LISTENER-001",
            }
        },
    )

    registry = TaskRegistry(
        config_file=config_file
    )

    assert registry.has_config(
        "更新房源ID"
    )

    assert not registry.has_config(
        "不存在的任务"
    )


# =========================================================
# 新增：读取 enabled
# =========================================================


def test_is_enabled(
    tmp_path,
):

    config_file = create_config(
        tmp_path,
        {
            "任务A": {
                "enabled": True,
                "listener_id": "LISTENER-A",
            },
            "任务B": {
                "enabled": False,
                "listener_id": "LISTENER-B",
            },
        },
    )

    registry = TaskRegistry(
        config_file=config_file
    )

    assert registry.is_enabled(
        "任务A"
    )

    assert not registry.is_enabled(
        "任务B"
    )

    assert not registry.is_enabled(
        "不存在"
    )


# =========================================================
# 新增：读取 Listener ID
# =========================================================


def test_get_listener_id(
    tmp_path,
):

    config_file = create_config(
        tmp_path,
        {
            "更新房源ID": {
                "enabled": True,
                "listener_id": "LISTENER-001",
            }
        },
    )

    registry = TaskRegistry(
        config_file=config_file
    )

    assert (
        registry.get_listener_id(
            "更新房源ID"
        )
        == "LISTENER-001"
    )


# =========================================================
# 新增：不存在 Listener ID
# =========================================================


def test_missing_listener_id(
    tmp_path,
):

    config_file = create_config(
        tmp_path,
        {
            "任务A": {
                "enabled": True,
            }
        },
    )

    registry = TaskRegistry(
        config_file=config_file
    )

    assert (
        registry.get_listener_id(
            "任务A"
        )
        is None
    )


# =========================================================
# 新增：读取全部配置任务
# =========================================================


def test_config_names(
    tmp_path,
):

    config_file = create_config(
        tmp_path,
        {
            "任务A": {
                "enabled": True,
            },
            "任务B": {
                "enabled": False,
            },
        },
    )

    registry = TaskRegistry(
        config_file=config_file
    )

    assert registry.config_names() == [
        "任务A",
        "任务B",
    ]


# =========================================================
# 新增：JSON 配置修改后立即生效
# =========================================================


def test_config_reload_reads_latest_disk_value(
    tmp_path,
):

    config_file = create_config(
        tmp_path,
        {
            "任务A": {
                "enabled": True,
                "listener_id": "LISTENER-A",
            }
        },
    )

    registry = TaskRegistry(
        config_file=config_file
    )

    assert registry.is_enabled(
        "任务A"
    )

    # -----------------------------------------------------
    # 直接修改磁盘 JSON
    # -----------------------------------------------------

    config_file.write_text(
        json.dumps(
            {
                "version": 1,
                "tasks": {
                    "任务A": {
                        "enabled": False,
                        "listener_id": "LISTENER-B",
                    }
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    # -----------------------------------------------------
    # Registry 应读取最新值
    # -----------------------------------------------------

    assert not registry.is_enabled(
        "任务A"
    )

    assert (
        registry.get_listener_id(
            "任务A"
        )
        == "LISTENER-B"
    )


# =========================================================
# 新增：配置文件不存在
# =========================================================


def test_missing_config_file(
    tmp_path,
):

    config_file = (
        tmp_path
        / "not_exists.json"
    )

    registry = TaskRegistry(
        config_file=config_file
    )

    assert registry.config_names() == []

    assert not registry.has_config(
        "任务A"
    )


# =========================================================
# 新增：非法 JSON
# =========================================================


def test_invalid_json(
    tmp_path,
):

    config_file = (
        tmp_path
        / "task_registry.json"
    )

    config_file.write_text(
        "{ invalid json",
        encoding="utf-8",
    )

    with pytest.raises(
        json.JSONDecodeError
    ):

        TaskRegistry(
            config_file=config_file
        )


# =========================================================
# 新增：tasks 必须是对象
# =========================================================


def test_tasks_must_be_object(
    tmp_path,
):

    config_file = (
        tmp_path
        / "task_registry.json"
    )

    config_file.write_text(
        json.dumps(
            {
                "version": 1,
                "tasks": [],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError
    ):

        TaskRegistry(
            config_file=config_file
        )