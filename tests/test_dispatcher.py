import json

from tasks.manager import TaskManager
from watcher import dispatcher as dispatcher_module
from watcher.dispatcher import Dispatcher


def test_dispatcher_creates_task_without_executing_listener(tmp_path, monkeypatch):
    state_file = tmp_path / "global_state.json"
    listeners_file = tmp_path / "listeners.json"
    tasks_file = tmp_path / "tasks.json"
    registry_file = tmp_path / "task_registry.json"

    state_file.write_text(
        json.dumps(
            {
                "pages": {
                    "page-1": {
                        "last_edited_time": "t1",
                        "url": "https://notion/page-1",
                        "object": {
                            "type": "data_source",
                            "parent": {"data_source_id": "listener-1"},
                        },
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    listeners_file.write_text(
        json.dumps(
            {
                "version": 1,
                "listeners": {
                    "listener-1": {
                        "enabled": True,
                        "module": "unused",
                        "class": "Unused",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    registry_file.write_text(
        json.dumps(
            {
                "version": 1,
                "tasks": {
                    "更新房源ID": {
                        "enabled": True,
                        "listener_id": "listener-1",
                        "target_property": "房源ID",
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(dispatcher_module, "STATE_FILE", state_file)
    monkeypatch.setattr(dispatcher_module, "LISTENERS_FILE", listeners_file)

    manager = TaskManager(task_file=tasks_file)
    registry = __import__("tasks.registry", fromlist=["TaskRegistry"]).TaskRegistry(
        config_file=registry_file
    )
    dispatcher = Dispatcher(
        task_manager=manager,
        task_registry=registry,
    )

    result = dispatcher.dispatch("page-1")

    assert result["status"] == "TASK_CREATED"
    task = manager.get_task(1)
    assert task["task"] == "更新房源ID"
    assert task["target_property"] == "房源ID"
