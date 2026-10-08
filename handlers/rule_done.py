from __future__ import annotations

import asyncio

from core.logger import error, info
from event_bus import Event
from methods.read_json_file import read_json_file
from channel import ChannelManager, ChannelTask

_channel_manager = ChannelManager()


async def handle_rule_done(event: Event) -> Event:
    if event.event_type != "RULE_DONE":
        raise ValueError(f"unexpected event type: {event.event_type}")

    record_id = event.data.get("record_id")
    info(f"[RuleDoneHandler] START record_id={record_id}")

    try:
        decisions = event.data.get("decisions")
        if decisions is None:
            decisions = [{
                "record_id": record_id,
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
        info(f"[RuleDoneHandler] CHANNEL_CONFIG_LOADED record_id={record_id}")

        channel_tasks = []
        for decision in decisions:
            if not isinstance(decision, dict):
                raise ValueError("RULE_DONE decision must be an object")
            decision_record_id = decision.get("record_id")
            assignee = decision.get("assignee")
            channel = decision.get("channel")
            task = decision.get("task")
            if not decision_record_id or not channel or not assignee or not isinstance(task, dict):
                raise ValueError("RULE_DONE decision is incomplete")
            channel_tasks.append(
                ChannelTask(
                    record_id=decision_record_id,
                    assignee=assignee,
                    channel=channel,
                    data=task,
                    route_rule=decision.get("rule_name"),
                )
            )

        info(f"[RuleDoneHandler] SUBMIT record_id={record_id} count={len(channel_tasks)} records={[t.record_id for t in channel_tasks]}")
        results = await asyncio.gather(*(_channel_manager.submit_and_wait(channel_task) for channel_task in channel_tasks))

        completed = []
        for channel_task, result in zip(channel_tasks, results):
            info(f"[RuleDoneHandler] COMPLETED record_id={channel_task.record_id} assignee={channel_task.assignee} channel={channel_task.channel}")
            completed.append({
                "record_id": channel_task.record_id,
                "assignee": channel_task.assignee,
                "channel": channel_task.channel,
                "task": channel_task.data,
                "result": result,
            })

        info(f"[RuleDoneHandler] DONE record_id={record_id} next=CHANNEL_DONE")
        return Event("CHANNEL_DONE", {"record_id": record_id or channel_tasks[0].record_id, "decisions": completed})
    except Exception as exc:
        error(f"[RuleDoneHandler] FAILED record_id={record_id} error={type(exc).__name__}: {exc}")
        raise
