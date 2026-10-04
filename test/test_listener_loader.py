import json

import pytest

from tasks.listener_loader import ListenerLoader
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
# 测试 Listener
# =========================================================


class TestListener:

    def __init__(self):
        self.name = "test_listener"


# =========================================================
# 加载 Class
# =========================================================


def test_load_class(
    tmp_path,
):

    config_file = create_config(
        tmp_path,
        {
            "LISTENER-001": {
                "module": "test.test_listener_loader",
                "class": "TestListener",
            }
        },
    )

    registry = ListenerRegistry(
        config_file=config_file
    )

    loader = ListenerLoader(
        registry=registry
    )

    listener_class = loader.load_class(
        "LISTENER-001"
    )

    assert listener_class is TestListener


# =========================================================
# 加载 Instance
# =========================================================


def test_load_instance(
    tmp_path,
):

    config_file = create_config(
        tmp_path,
        {
            "LISTENER-001": {
                "module": "test.test_listener_loader",
                "class": "TestListener",
            }
        },
    )

    registry = ListenerRegistry(
        config_file=config_file
    )

    loader = ListenerLoader(
        registry=registry
    )

    listener = loader.load(
        "LISTENER-001"
    )

    assert isinstance(
        listener,
        TestListener,
    )

    assert (
        listener.name
        == "test_listener"
    )


# =========================================================
# Listener 不存在
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

    loader = ListenerLoader(
        registry=registry
    )

    with pytest.raises(
        ValueError,
        match="Listener not found",
    ):

        loader.load(
            "LISTENER-001"
        )


# =========================================================
# module 不存在
# =========================================================


def test_missing_module(
    tmp_path,
):

    config_file = create_config(
        tmp_path,
        {
            "LISTENER-001": {
                "module": "not.exists.module",
                "class": "TestListener",
            }
        },
    )

    registry = ListenerRegistry(
        config_file=config_file
    )

    loader = ListenerLoader(
        registry=registry
    )

    with pytest.raises(
        ModuleNotFoundError,
    ):

        loader.load_class(
            "LISTENER-001"
        )


# =========================================================
# class 不存在
# =========================================================


def test_missing_class(
    tmp_path,
):

    config_file = create_config(
        tmp_path,
        {
            "LISTENER-001": {
                "module": "test.test_listener_loader",
                "class": "NotExistsListener",
            }
        },
    )

    registry = ListenerRegistry(
        config_file=config_file
    )

    loader = ListenerLoader(
        registry=registry
    )

    with pytest.raises(
        ValueError,
        match="Listener class not found",
    ):

        loader.load_class(
            "LISTENER-001"
        )


# =========================================================
# module 缺失
# =========================================================


def test_missing_module_config(
    tmp_path,
):

    config_file = create_config(
        tmp_path,
        {
            "LISTENER-001": {
                "class": "TestListener",
            }
        },
    )

    registry = ListenerRegistry(
        config_file=config_file
    )

    loader = ListenerLoader(
        registry=registry
    )

    with pytest.raises(
        ValueError,
        match="Listener module is missing",
    ):

        loader.load_class(
            "LISTENER-001"
        )


# =========================================================
# class 配置缺失
# =========================================================


def test_missing_class_config(
    tmp_path,
):

    config_file = create_config(
        tmp_path,
        {
            "LISTENER-001": {
                "module": "test.test_listener_loader",
            }
        },
    )

    registry = ListenerRegistry(
        config_file=config_file
    )

    loader = ListenerLoader(
        registry=registry
    )

    with pytest.raises(
        ValueError,
        match="Listener class is missing",
    ):

        loader.load_class(
            "LISTENER-001"
        )