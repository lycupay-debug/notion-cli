import json

from tasks.listener_loader import ListenerLoader


def test_listener_loader_imports_configured_class(tmp_path, monkeypatch):
    module = tmp_path / "fake_listener_module.py"
    module.write_text(
        """
class FakeListener:
    def __init__(self):
        self.loaded = True

    def handle(self, page_id):
        return {"page_id": page_id}
""",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    config = tmp_path / "listeners.json"
    config.write_text(
        json.dumps(
            {
                "version": 1,
                "listeners": {
                    "listener-1": {
                        "name": "FakeListener",
                        "module": "fake_listener_module",
                        "class": "FakeListener",
                        "enabled": True,
                        "properties": {"name": {"type": "title"}},
                    }
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    loader = ListenerLoader(config_file=config)

    assert loader.is_enabled("listener-1") is True
    instance = loader.load("listener-1")
    assert instance.handle("page-1") == {"page_id": "page-1"}
    assert loader.get_config("listener-1")["properties"]["name"]["type"] == "title"


def test_listener_loader_rejects_disabled_listener(tmp_path):
    config = tmp_path / "listeners.json"
    config.write_text(
        json.dumps(
            {
                "version": 1,
                "listeners": {
                    "listener-1": {
                        "module": "missing_module",
                        "class": "Missing",
                        "enabled": False,
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    loader = ListenerLoader(config_file=config)

    assert loader.is_enabled("listener-1") is False
