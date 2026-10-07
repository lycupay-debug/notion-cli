from __future__ import annotations

from core.logger import info
from event_bus import Event


async def handle_channel_done(event: Event) -> None:
    if event.event_type != "CHANNEL_DONE":
        raise ValueError(f"unexpected event type: {event.event_type}")

    record_id = event.data.get("record_id")
    if not record_id:
        raise ValueError("CHANNEL_DONE event is missing record_id")

    decisions = event.data.get("decisions")
    info(
        f"[ChannelDoneHandler] DONE record_id={record_id} "
        f"count={len(decisions) if isinstance(decisions, list) else 1}"
    )
