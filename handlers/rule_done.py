from __future__ import annotations

import asyncio

from event_bus import Event
from methods.read_json_file import read_json_file

from channel import ChannelManager, ChannelTask


_channel_manager = ChannelManager()


async def handle_rule_done(event: Event) -> Event:
    """接收 RULE_DONE，并等待所有命中的 Channel 任务完成。"""
    if event.event_type != "RULE_DONE":
        raise ValueError(f"unexpected event type: {event.event_type}")

    decisions = event.data.get("decisions")

    # 兼容单任务 RULE_DONE，避免历史事件无法处理。
    if decisions is None:
        decisions = [{
            "record_id": event.data.get("record_id"),
            "assignee": event.data.get("assignee"),
            "channel": event.data.get("channel"),
            "task": event.data.get("task"),
            "reason": event.data.get("reason", ""),
        }]

    if not isinstance(decisions, list) or not decisions:
        raise ValueError("RULE_DONE event must contain non-empty decisions")

    config = read_json_file("config/channels.json")
    if not isinstance(config, dict):
        raise ValueError("channel config must be an object")

    _channel_manager.load_config(config)

    channel_tasks: list[ChannelTask] = []

    for decision in decisions:
        if not isinstance(decision, dict):
            raise ValueError("RULE_DONE decision must be an object")

        record_id = decision.get("record_id")
        assignee = decision.get("assignee")
        channel = decision.get("channel")
        task = decision.get("task")

        if not record_id:
            raise ValueError("RULE_DONE decision is missing record_id")
        if not channel:
            raise ValueError("RULE_DONE decision is missing channel")
        if not assignee:
            raise ValueError("RULE_DONE decision is missing assignee")
        if not isinstance(task, dict):
            raise ValueError("RULE_DONE decision is missing task")

        channel_tasks.append(
            ChannelTask(
                record_id=record_id,
                assignee=assignee,
                channel=channel,
                data=task,
            )
        )

    results = await asyncio.gather(
        *(
            _channel_manager.submit_and_wait(channel_task)
            for channel_task in channel_tasks
        )
    )

    completed = []
    for channel_task, result in zip(channel_tasks, results):
        print(
            "[RuleDoneHandler] "
            f"record_id={channel_task.record_id} "
            f"assignee={channel_task.assignee} "
            f"channel={channel_task.channel} "
            "status=COMPLETED"
        )
        completed.append({
            "record_id": channel_task.record_id,
            "assignee": channel_task.assignee,
            "channel": channel_task.channel,
            "task": channel_task.data,
            "result": result,
        })

    return Event(
        "CHANNEL_DONE",
        {
            "record_id": event.data.get("record_id") or channel_tasks[0].record_id,
            "decisions": completed,
        },
    )
