from __future__ import annotations

from pathlib import Path
from typing import Any

from core.json_store import JSONStore
from core.logger import error, info
from methods.get_parse_history_path import get_parse_history_path
from methods.get_task_path import get_task_path
from methods.read_json_file import read_json_file
from methods.webhook_event import (
    get_authors, get_data_source_id, get_event_id, get_event_type,
    get_entity_id, get_entity_type, get_parent_id, get_parent_type,
    get_record_id, get_updated_blocks, get_updated_properties,
    is_authored_by_bot, is_authored_by_person,
)


class ParserWorker:
    """解析员。只处理当前传入事件，不负责规则和执行。"""

    def __init__(self, event_dir: str | Path | None = None, config_dir: str | Path | None = None, history_dir: str | Path | None = None):
        self.project_root = Path(__file__).resolve().parent.parent
        self.event_dir = Path(event_dir).resolve() if event_dir is not None else self.project_root / "data" / "webhook_events"
        self.config_dir = Path(config_dir).resolve() if config_dir is not None else self.project_root / "config" / "tasks"
        self.history_dir = Path(history_dir).resolve() if history_dir is not None else self.project_root / "config" / "parse_history"
        self.store = JSONStore(base_dir=self.project_root)

    def load_event(self, file_path: str | Path) -> dict[str, Any]:
        path = Path(file_path).resolve()
        info(f"[Parser] LOAD_EVENT path={path}")
        try:
            relative_path = path.relative_to(self.project_root)
        except ValueError:
            return self.store.load(path)
        return read_json_file(str(relative_path))

    def get_history_path(self, record_id: str) -> Path:
        if self.history_dir == self.project_root / "config" / "parse_history":
            return self.project_root / get_parse_history_path(record_id)
        return self.history_dir / f"{record_id}.json"

    def is_parsed(self, record_id: str) -> bool:
        parsed = self.get_history_path(record_id).exists()
        info(f"[Parser] HISTORY_CHECK record_id={record_id} parsed={parsed}")
        return parsed

    def create_history(self, record_id: str) -> dict[str, Any]:
        info(f"[Parser] HISTORY_CREATE record_id={record_id}")
        history = {"task_completed": None, "task_action": None}
        return self.store.save(self.get_history_path(record_id), history)

    def parse(self, record: dict[str, Any]) -> dict[str, Any]:
        record_id = get_record_id(record)
        if not record_id:
            raise ValueError("webhook event is missing record_id")
        info(f"[Parser] PARSE_START record_id={record_id}")
        task = {
            "record_id": record_id,
            "assignee": None,
            "task_completed": None,
            "incomplete_reason": "",
            "event_id": get_event_id(record),
            "event_type": get_event_type(record),
            "author": {
                "is_bot": is_authored_by_bot(record),
                "is_person": is_authored_by_person(record),
                "types": [author.get("type") for author in get_authors(record) if isinstance(author, dict)],
            },
            "entity": {"id": get_entity_id(record), "type": get_entity_type(record)},
            "parent": {"id": get_parent_id(record), "type": get_parent_type(record), "data_source_id": get_data_source_id(record)},
            "updated_properties": get_updated_properties(record),
            "updated_blocks": get_updated_blocks(record),
        }
        info(f"[Parser] PARSE_DONE record_id={record_id} event_type={task['event_type']} entity_id={task['entity']['id']} parent_data_source_id={task['parent']['data_source_id']} author={task['author']} updated_properties={task['updated_properties']}")
        return task

    def save_parsed(self, parsed: dict[str, Any]) -> dict[str, Any]:
        record_id = parsed.get("record_id")
        if not record_id:
            raise ValueError("parsed result is missing record_id")
        file_path = self.project_root / get_task_path(record_id) if self.config_dir == self.project_root / "config" / "tasks" else self.config_dir / f"{record_id}.json"
        info(f"[Parser] TASK_SAVE_START record_id={record_id} path={file_path}")
        saved = self.store.save(file_path, parsed)
        info(f"[Parser] TASK_SAVE_DONE record_id={record_id} path={file_path}")
        return saved

    def parse_file(self, file_path: str | Path) -> dict[str, Any] | None:
        path = Path(file_path)
        info(f"[Parser] PARSE_FILE_START path={path}")
        try:
            record = self.load_event(path)
            record_id = get_record_id(record)
            if not record_id:
                raise ValueError("webhook event is missing record_id")
            if self.is_parsed(record_id):
                info(f"[Parser] ALREADY_PARSED record_id={record_id}")
                return None
            parsed = self.parse(record)
            saved = self.save_parsed(parsed)
            self.create_history(record_id)
            info(f"[Parser] PARSE_FILE_DONE record_id={record_id}")
            return saved
        except Exception as exc:
            error(f"[Parser] PARSE_FILE_FAILED path={path} error={type(exc).__name__}: {exc}")
            raise

    def parse_pending_events(self) -> list[dict[str, Any]]:
        info(f"[Parser] PARSE_PENDING_START event_dir={self.event_dir}")
        parsed_tasks = []
        for file_path in sorted(self.event_dir.glob("*.json")):
            result = self.parse_file(file_path)
            if result is not None:
                parsed_tasks.append(result)
        info(f"[Parser] PARSE_PENDING_DONE count={len(parsed_tasks)}")
        return parsed_tasks
