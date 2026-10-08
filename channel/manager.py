from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from core.logger import error, info
from methods.load_callable import load_callable

ChannelExecutor = Callable[["ChannelTask"], Awaitable[Any]]

@dataclass(frozen=True, slots=True)
class ChannelTask:
    record_id: str
    assignee: str
    channel: str
    data: dict[str, Any]

@dataclass(slots=True)
class _QueuedTask:
    task: ChannelTask
    result: asyncio.Future[Any] | None = None

@dataclass(slots=True)
class _ChannelState:
    queue: asyncio.Queue[_QueuedTask]
    executor: ChannelExecutor
    enabled: bool = True
    running: bool = False
    worker: asyncio.Task[None] | None = None
    pending_config: dict[str, Any] | None = None

class ChannelManager:
    """业务 Channel 运行时。"""

    def __init__(self) -> None:
        self._channels: dict[str, _ChannelState] = {}

    def load_config(self, config: dict[str, Any]) -> None:
        channels = config.get("channels")
        if not isinstance(channels, dict):
            raise ValueError("channel config must contain object: channels")
        info(f"[ChannelManager] CONFIG_START channels={list(channels)}")
        configured = set(channels)
        for name, item in channels.items():
            if not isinstance(item, dict):
                raise ValueError(f"channel config must be an object: {name}")
            enabled = item.get("enabled", True)
            if not isinstance(enabled, bool):
                raise ValueError(f"channel enabled must be bool: {name}")
            executor = load_callable(item.get("module", ""), item.get("function", ""))
            state = self._channels.get(name)
            if state is None:
                self._channels[name] = _ChannelState(queue=asyncio.Queue(), executor=executor, enabled=enabled)
                info(f"[ChannelManager] CHANNEL_CREATED channel={name} enabled={enabled}")
                continue
            if state.running or not state.queue.empty():
                state.pending_config = {"enabled": enabled, "executor": executor}
                info(f"[ChannelManager] CONFIG_DEFERRED channel={name} reason=BUSY")
            else:
                state.enabled = enabled
                state.executor = executor
                info(f"[ChannelManager] CHANNEL_UPDATED channel={name} enabled={enabled}")
        for name, state in list(self._channels.items()):
            if name in configured:
                continue
            state.enabled = False
            state.pending_config = None
            info(f"[ChannelManager] CHANNEL_DISABLED channel={name} reason=REMOVED_FROM_CONFIG")
            if not state.running and state.queue.empty():
                self._channels.pop(name, None)
                info(f"[ChannelManager] CHANNEL_REMOVED channel={name}")
        info(f"[ChannelManager] CONFIG_DONE active={list(self._channels)}")

    async def submit(self, task: ChannelTask) -> None:
        await self._enqueue(task, wait=False)

    async def submit_and_wait(self, task: ChannelTask) -> Any:
        return await self._enqueue(task, wait=True)

    async def _enqueue(self, task: ChannelTask, *, wait: bool) -> Any:
        state = self._channels.get(task.channel)
        if state is None:
            raise LookupError(f"channel is not configured: {task.channel}")
        if not state.enabled:
            raise RuntimeError(f"channel is disabled: {task.channel}")
        info(f"[ChannelManager] ENQUEUE record_id={task.record_id} assignee={task.assignee} channel={task.channel} wait={wait} queue_size_before={state.queue.qsize()}")
        future = asyncio.get_running_loop().create_future() if wait else None
        await state.queue.put(_QueuedTask(task=task, result=future))
        info(f"[ChannelManager] ENQUEUED record_id={task.record_id} channel={task.channel} queue_size={state.queue.qsize()}")
        if state.worker is None or state.worker.done():
            state.worker = asyncio.create_task(self._worker(task.channel, state))
            info(f"[ChannelManager] WORKER_STARTED channel={task.channel}")
        if future is not None:
            return await future
        return None

    async def _worker(self, name: str, state: _ChannelState) -> None:
        info(f"[ChannelManager] WORKER_LOOP_START channel={name}")
        while True:
            if state.queue.empty():
                self._apply_pending(name, state)
                if state.queue.empty():
                    if not state.enabled:
                        self._channels.pop(name, None)
                    info(f"[ChannelManager] WORKER_IDLE channel={name}")
                    return
            queued = await state.queue.get()
            state.running = True
            task = queued.task
            info(f"[ChannelManager] EXECUTE_START record_id={task.record_id} channel={name} assignee={task.assignee} queue_remaining={state.queue.qsize()}")
            try:
                result = await state.executor(task)
            except BaseException as exc:
                error(f"[ChannelManager] EXECUTE_FAILED record_id={task.record_id} channel={name} error={type(exc).__name__}: {exc}")
                if queued.result is not None and not queued.result.done():
                    queued.result.set_exception(exc)
            else:
                info(f"[ChannelManager] EXECUTE_DONE record_id={task.record_id} channel={name} result={result!r}")
                if queued.result is not None and not queued.result.done():
                    queued.result.set_result(result)
            finally:
                state.running = False
                state.queue.task_done()
                self._apply_pending(name, state)
                info(f"[ChannelManager] TASK_RELEASED record_id={task.record_id} channel={name} queue_size={state.queue.qsize()}")

    def _apply_pending(self, name: str, state: _ChannelState) -> None:
        if state.running or state.pending_config is None:
            return
        pending = state.pending_config
        state.pending_config = None
        state.enabled = pending["enabled"]
        state.executor = pending["executor"]
        info(f"[ChannelManager] CONFIG_APPLIED channel={name} enabled={state.enabled}")
        if not state.enabled and state.queue.empty():
            self._channels.pop(name, None)
            info(f"[ChannelManager] CHANNEL_REMOVED channel={name}")

    def is_busy(self, channel: str) -> bool:
        state = self._channels.get(channel)
        return bool(state and (state.running or not state.queue.empty()))

    def has_channel(self, channel: str) -> bool:
        return channel in self._channels

    async def wait_for_idle(self, channel: str) -> None:
        state = self._channels.get(channel)
        if state is None:
            return
        info(f"[ChannelManager] WAIT_IDLE_START channel={channel}")
        await state.queue.join()
        if state.worker is not None:
            await state.worker
        info(f"[ChannelManager] WAIT_IDLE_DONE channel={channel}")
