from __future__ import annotations

from pathlib import Path
from typing import Any

from core.json_store import JSONStore
from methods.webhook_event import (
    get_authors,
    get_data_source_id,
    get_event_id,
    get_event_type,
    get_entity_id,
    get_entity_type,
    get_parent_id,
    get_parent_type,
    get_record_id,
    get_updated_blocks,
    get_updated_properties,
    is_authored_by_bot,
    is_authored_by_person,
)


class ParserWorker:
    """
    解析员。

    当前阶段负责：
    1. 读取 webhook_events 中的原始 webhook JSON；
    2. 检查解析历史，避免重复解析；
    3. 使用个人方法库提取通用字段；
    4. 将解析结果通过 JSONStore 原子写入 config/tasks/<record_id>.json；
    5. 成功建立任务后，通过 JSONStore 原子写入 config/parse_history/<record_id>.json。

    不负责：
    - Notion API 调用；
    - 任务执行；
    - 规则总管调度；
    - 修改原始 webhook JSON；
    - 修改解析历史中的任务完成状态或处理方式。
    """

    def __init__(
        self,
        event_dir: str | Path | None = None,
        config_dir: str | Path | None = None,
        history_dir: str | Path | None = None,
    ):
        project_root = Path(__file__).resolve().parent.parent
        self.event_dir = (
            Path(event_dir).resolve()
            if event_dir is not None
            else project_root / "data" / "webhook_events"
        )
        self.config_dir = (
            Path(config_dir).resolve()
            if config_dir is not None
            else project_root / "config" / "tasks"
        )
        self.history_dir = (
            Path(history_dir).resolve()
            if history_dir is not None
            else project_root / "config" / "parse_history"
        )
        self.store = JSONStore(base_dir=project_root)

    def load_event(self, file_path: str | Path) -> dict[str, Any]:
        return self.store.load(file_path)

    def get_history_path(self, record_id: str) -> Path:
        return self.history_dir / f"{record_id}.json"

    def is_parsed(self, record_id: str) -> bool:
        return self.get_history_path(record_id).exists()

    def create_history(self, record_id: str) -> dict[str, Any]:
        if not record_id:
            raise ValueError("解析历史缺少 record_id")

        history = {
            "任务完成状态": None,
            "任务处理方式": None,
        }
        return self.store.save(self.get_history_path(record_id), history)

    def parse(self, record: dict[str, Any]) -> dict[str, Any]:
        record_id = get_record_id(record)

        if not record_id:
            raise ValueError("webhook event 缺少 record_id")

        return {
            "recordid": record_id,
            "event_id": get_event_id(record),
            "event_type": get_event_type(record),
            "author": {
                "is_bot": is_authored_by_bot(record),
                "is_person": is_authored_by_person(record),
                "types": [
                    author.get("type")
                    for author in get_authors(record)
                    if isinstance(author, dict)
                ],
            },
            "entity": {
                "id": get_entity_id(record),
                "type": get_entity_type(record),
            },
            "parent": {
                "id": get_parent_id(record),
                "type": get_parent_type(record),
                "data_source_id": get_data_source_id(record),
            },
            "updated_properties": get_updated_properties(record),
            "updated_blocks": get_updated_blocks(record),
        }

    def save_parsed(
        self,
        parsed: dict[str, Any],
    ) -> dict[str, Any]:
        record_id = parsed.get("recordid")

        if not record_id:
            raise ValueError("解析结果缺少 recordid")

        file_path = self.config_dir / f"{record_id}.json"
        return self.store.save(file_path, parsed)

    def parse_file(self, file_path: str | Path) -> dict[str, Any] | None:
        record = self.load_event(file_path)
        record_id = get_record_id(record)

        if not record_id:
            raise ValueError("webhook event 缺少 record_id")

        if self.is_parsed(record_id):
            return None

        parsed = self.parse(record)
        saved = self.save_parsed(parsed)
        self.create_history(record_id)
        return saved

    def parse_pending_events(self) -> list[dict[str, Any]]:
        parsed_tasks = []

        for file_path in sorted(self.event_dir.glob("*.json")):
            result = self.parse_file(file_path)
            if result is not None:
                parsed_tasks.append(result)

        return parsed_tasks
