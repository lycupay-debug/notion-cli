import json

from watcher import global_watcher as watcher_module
from watcher.global_watcher import GlobalWatcher


def _patch_snapshot(monkeypatch, pages):
    monkeypatch.setattr(
        watcher_module,
        "search",
        lambda **kwargs: {
            "results": pages,
            "has_more": False,
            "next_cursor": None,
        },
    )


def test_global_watcher_new_page_identifies_and_routes(tmp_path, monkeypatch):
    state_file = tmp_path / "global_state.json"
    state_file.write_text(
        json.dumps({"version": 1, "pages": {}}, ensure_ascii=False),
        encoding="utf-8",
    )

    monkeypatch.setattr(watcher_module, "STATE_FILE", state_file)

    watcher = GlobalWatcher()

    watcher.identity_service.check_page = lambda page_id: {
        "status": "IDENTIFIED",
        "page_id": page_id,
        "object": {
            "type": "data_source",
            "parent": {"data_source_id": "listener-1"},
        },
    }

    watcher.dispatcher.dispatch = lambda page_id: {
        "status": "TASK_CREATED",
        "page_id": page_id,
    }

    _patch_snapshot(
        monkeypatch,
        [
            {
                "id": "page-1",
                "last_edited_time": "t1",
                "url": "https://notion/page-1",
            }
        ],
    )

    changes = watcher.check()

    assert changes[0]["status"] == "NEW"
    assert changes[0]["route"]["status"] == "TASK_CREATED"

    state = json.loads(state_file.read_text(encoding="utf-8"))
    assert state["pages"]["page-1"]["last_edited_time"] == "t1"


def test_global_watcher_detects_changed_page(tmp_path, monkeypatch):
    state_file = tmp_path / "global_state.json"
    state_file.write_text(
        json.dumps(
            {
                "version": 1,
                "pages": {
                    "page-1": {
                        "last_edited_time": "old",
                        "url": "https://notion/page-1",
                        "object": {"type": "data_source", "parent": {}},
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(watcher_module, "STATE_FILE", state_file)

    watcher = GlobalWatcher()
    watcher.identity_service.check_page = lambda page_id, force=False: {
        "status": "IDENTIFIED",
        "page_id": page_id,
        "object": {"type": "data_source", "parent": {}},
    }
    watcher.dispatcher.dispatch = lambda page_id: {
        "status": "TASK_CREATED",
        "page_id": page_id,
    }

    _patch_snapshot(
        monkeypatch,
        [
            {
                "id": "page-1",
                "last_edited_time": "new",
                "url": "https://notion/page-1",
            }
        ],
    )

    changes = watcher.check()

    assert changes[0]["status"] == "CHANGED"
    assert changes[0]["route"]["status"] == "TASK_CREATED"

    state = json.loads(state_file.read_text(encoding="utf-8"))
    assert state["pages"]["page-1"]["last_edited_time"] == "new"
