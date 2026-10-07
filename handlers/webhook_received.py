from __future__ import annotations

from pathlib import Path

from event_bus import Event
from methods.read_json_file import read_json_file
from parser.worker import ParserWorker


async def handle_webhook_received(event: Event) -> None:
    """
    处理 WEBHOOK_RECEIVED。

    事件已经保证对应 webhook JSON 成功落盘。
    Handler 负责读取该 JSON，并交给现有 ParserWorker。
    """
    record_path = event.data.get("file_path")
    record_id = event.data.get("record_id")

    if not record_path:
        raise ValueError("WEBHOOK_RECEIVED event is missing file_path")

    record = read_json_file(record_path)
    if not isinstance(record, dict):
        raise ValueError("webhook event JSON must contain an object")

    if record_id and record.get("record_id") != record_id:
        raise ValueError("WEBHOOK_RECEIVED record_id does not match file content")

    parser = ParserWorker()
    result = parser.parse_file(Path(record_path))

    if result is None:
        print(
            f"[WebhookReceivedHandler] already parsed: "
            f"{record.get('record_id')}"
        )
        return

    print(
        f"[WebhookReceivedHandler] parsed webhook: "
        f"{result.get('record_id')}"
    )
