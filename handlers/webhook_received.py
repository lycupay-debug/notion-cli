from __future__ import annotations

from pathlib import Path

from core.logger import error, info
from event_bus import Event
from parser.worker import ParserWorker


async def handle_webhook_received(event: Event) -> Event | None:
    record_path = event.data.get("file_path")
    record_id = event.data.get("record_id")
    if not record_path:
        raise ValueError("WEBHOOK_RECEIVED event is missing file_path")

    info(f"[WebhookReceivedHandler] START record_id={record_id}")
    try:
        result = ParserWorker().parse_file(Path(record_path))
    except Exception as exc:
        error(f"[WebhookReceivedHandler] FAILED record_id={record_id} error={type(exc).__name__}: {exc}")
        raise

    if result is None:
        info(f"[WebhookReceivedHandler] ALREADY_PARSED record_id={record_id}")
        return None

    info(f"[WebhookReceivedHandler] PARSED record_id={result.get('record_id')}")
    return Event("NEW_TASK", {"task": result})
