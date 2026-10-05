import json

from tasks.registry import TaskRegistry


def test_registry_reads_task_and_listener_mapping(tmp_path):
    path = tmp_path / "task_registry.json"
    path.write_text(
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
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    registry = TaskRegistry(config_file=path)

    assert registry.is_enabled("更新房源ID") is True
    assert registry.get_listener_id("更新房源ID") == "listener-1"
    assert registry.find_task_by_listener_id("listener-1")["task_name"] == "更新房源ID"


def test_registry_reload_sees_external_change(tmp_path):
    path = tmp_path / "task_registry.json"
    path.write_text(
        json.dumps({"version": 1, "tasks": {}}, ensure_ascii=False),
        encoding="utf-8",
    )

    registry = TaskRegistry(config_file=path)

    path.write_text(
        json.dumps(
            {
                "version": 1,
                "tasks": {
                    "new-task": {
                        "enabled": True,
                        "listener_id": "listener-2",
                    }
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    assert registry.get_listener_id("new-task") == "listener-2"
