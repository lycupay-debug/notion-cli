from __future__ import annotations

from event_bus import Event
from methods.read_json_file import read_json_file

from channel import ChannelManager, ChannelTask


_channel_manager = ChannelManager()


async def handle_rule_done(event: Event) -> None:
    """接收 RULE_DONE，并将任务提交到对应 Channel。"""
    if event.event_type != "RULE_DONE":
        raise ValueError(f"unexpected event type: {event.event_type}")

    record_id = event.data.get("record_id")
    channel = event.data.get("channel")
    assignee = event.data.get("assignee")
    task = event.data.get("task")

    if not record_id:
        raise ValueError("RULE_DONE event is missing record_id")
    if not channel:
        raise ValueError("RULE_DONE event is missing channel")
    if not assignee:
        raise ValueError("RULE_DONE event is missing assignee")
    if not isinstance(task, dict):
        raise ValueError("RULE_DONE event is missing task")

    config = read_json_file("config/channels.json")
    if not isinstance(config, dict):
        raise ValueError("channel config must be an object")

    _channel_manager.load_config(config)

    await _channel_manager.submit(
        ChannelTask(
            record_id=record_id,
            assignee=assignee,
            channel=channel,
            data=task,
        )
    )

    print(
        "[RuleDoneHandler] "
        f"record_id={record_id} "
        f"assignee={assignee} "
        f"channel={channel} "
        "status=QUEUED"
    )
