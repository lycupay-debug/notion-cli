import json

import pytest

from tasks.listener_registry import ListenerRegistry


def create_config(
    tmp_path,
    listeners=None,
):

    if listeners is None:
        listeners = {}

    config_file = (
        tmp_path
        / "listener_registry.json"
    )

    config_file.write_text(
        json.dumps(
            {
                "version": 1,
                "listeners": listeners,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return config_file


# =========================================================
# 读取 Listener 配置
# =========================================================


def test_load_listener_config(
    tmp_path,
):

    config_file = create_config(
        tmp_path,
        {
            "LISTENER-001": {
                "module": "listeners.dali_property",
                "class": "DaliPropertyListener",
            }
        },
    )

    registry = ListenerRegistry(
        config_file=config_file
    )

    config = registry.get_config(
        "LISTENER-001"
    )

    assert config == {
        "module": "listeners.dali_property",
        "class": "DaliPropertyListener",
    }


# =========================================================
# 判断 Listener 是否存在
# =========================================================


def test_has_config(
    tmp_path,
):

    config_file = create_config(
        tmp_path,
        {
            "LISTENER-001": {
                "module": "listeners.dali_property",
                "class": "DaliPropertyListener",
            }
        },
    )

    registry = ListenerRegistry(
        config_file=config_file
    )

    assert registry.has_config(
        "LISTENER-001"
    )

    assert not registry.has_config(
        "LISTENER-NOT-EXISTS"
    )


# =========================================================
# 获取 module
# =========================================================


def test_get_module(
    tmp_path,
):

    config_file = create_config(
        tmp_path,
        {
            "LISTENER-001": {
                "module": "listeners.dali_property",
                "class": "DaliPropertyListener",
            }
        },
    )

    registry = ListenerRegistry(
        config_file=config_file
    )

    assert (
        registry.get_module(
            "LISTENER-001"
        )
        == "listeners.dali_property"
    )


# =========================================================
# 获取 class
# =========================================================


def test_get_class(
    tmp_path,
):

    config_file = create_config(
        tmp_path,
        {
            "LISTENER-001": {
                "module": "listeners.dali_property",
                "class": "DaliPropertyListener",
            }
        },
    )

    registry = ListenerRegistry(
        config_file=config_file
    )

    assert (
        registry.get_class(
            "LISTENER-001"
        )
        == "DaliPropertyListener"
    )


# =========================================================
# 同时获取 module + class
# =========================================================


def test_get_target(
    tmp_path,
):

    config_file = create_config(
        tmp_path,
        {
            "LISTENER-001": {
                "module": "listeners.dali_property",
                "class": "DaliPropertyListener",
            }
        },
    )

    registry = ListenerRegistry(
        config_file=config_file
    )

    assert registry.get_target(
        "LISTENER-001"
    ) == {
        "module": "listeners.dali_property",
        "class": "DaliPropertyListener",
    }


# =========================================================
# 不存在的 Listener
# =========================================================


def test_missing_listener(
    tmp_path,
):

    config_file = create_config(
        tmp_path
    )

    registry = ListenerRegistry(
        config_file=config_file
    )

    assert (
        registry.get_config(
            "LISTENER-001"
        )
        is None
    )

    assert (
        registry.get_module(
            "LISTENER-001"
        )
        is None
    )

    assert (
        registry.get_class(
            "LISTENER-001"
        )
        is None
    )

    assert (
        registry.get_target(
            "LISTENER-001"
        )
        is None
    )


# =========================================================
# 获取全部 Listener ID
# =========================================================


def test_listener_ids(
    tmp_path,
):

    config_file = create_config(
        tmp_path,
        {
            "LISTENER-001": {
                "module": "listeners.dali_property",
                "class": "DaliPropertyListener",
            },
            "LISTENER-002": {
                "module": "listeners.course_record",
                "class": "CourseRecordListener",
            },
        },
    )

    registry = ListenerRegistry(
        config_file=config_file
    )

    assert registry.listener_ids() == [
        "LISTENER-001",
        "LISTENER-002",
    ]


# =========================================================
# 磁盘修改后重新读取
# =========================================================


def test_reload_reads_latest_disk_value(
    tmp_path,
):

    config_file = create_config(
        tmp_path,
        {
            "LISTENER-001": {
                "module": "listeners.dali_property",
                "class": "DaliPropertyListener",
            }
        },
    )

    registry = ListenerRegistry(
        config_file=config_file
    )

    assert (
        registry.get_class(
            "LISTENER-001"
        )
        == "DaliPropertyListener"
    )

    config_file.write_text(
        json.dumps(
            {
                "version": 1,
                "listeners": {
                    "LISTENER-001": {
                        "module": "listeners.course_record",
                        "class": "CourseRecordListener",
                    }
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    assert (
        registry.get_module(
            "LISTENER-001"
        )
        == "listeners.course_record"
    )

    assert (
        registry.get_class(
            "LISTENER-001"
        )
        == "CourseRecordListener"
    )


# =========================================================
# 配置文件不存在
# =========================================================


def test_missing_config_file(
    tmp_path,
):

    config_file = (
        tmp_path
        / "not_exists.json"
    )

    registry = ListenerRegistry(
        config_file=config_file
    )

    assert registry.listener_ids() == []

    assert not registry.has_config(
        "LISTENER-001"
    )


# =========================================================
# 非法 JSON
# =========================================================


def test_invalid_json(
    tmp_path,
):

    config_file = (
        tmp_path
        / "listener_registry.json"
    )

    config_file.write_text(
        "{ invalid json",
        encoding="utf-8",
    )

    with pytest.raises(
        json.JSONDecodeError
    ):

        ListenerRegistry(
            config_file=config_file
        )


# =========================================================
# listeners 必须是对象
# =========================================================


def test_listeners_must_be_object(
    tmp_path,
):

    config_file = (
        tmp_path
        / "listener_registry.json"
    )

    config_file.write_text(
        json.dumps(
            {
                "version": 1,
                "listeners": [],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError
    ):

        ListenerRegistry(
            config_file=config_file
        )