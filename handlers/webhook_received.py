from __future__ import annotations

from pathlib import Path

from event_bus import Event
from parser.worker import ParserWorker


async def handle_webhook_received(event: Event) -> Event | None:
    """
    处理 WEBHOOK_RECEIVED。

    Webhook JSON 已经由 Receiver 成功落盘。
    Handler 只负责把事件交给现有 ParserWorker。
    ParserWorker 再通过 read_json_file.py 读取原始 JSON。

    解析成功后返回 NEW_TASK，由 EventRuntime 统一发布。
    """
    record_path = event.data.get("file_path")
    if not record_path:
        raise ValueError("WEBHOOK_RECEIVED event is missing file_path")

    parser = ParserWorker()
    result = parser.parse_file(Path(record_path))

    if result is None:
        print(
            f"[WebhookReceivedHandler] already parsed: "
            f"{event.data.get('record_id')}"
        )
        return None

    print(
        f"[WebhookReceivedHandler] parsed webhook: "
        f"{result.get('record_id')}"
    )

    return Event(
        "NEW_TASK",
        {
            "task": result,
        },
    )
