from __future__ import annotations

from event_bus import Event


async def handle_channel_done(event: Event) -> None:
    """接收 Channel 实际执行完成事件。"""
    if event.event_type != "CHANNEL_DONE":
        raise ValueError(f"unexpected event type: {event.event_type}")

    record_id = event.data.get("record_id")
    channel = event.data.get("channel")

    if not record_id:
        raise ValueError("CHANNEL_DONE event is missing record_id")
    if not channel:
        raise ValueError("CHANNEL_DONE event is missing channel")

    print(
        "[ChannelDoneHandler] "
        f"record_id={record_id} "
        f"channel={channel} "
        "status=DONE"
    )
