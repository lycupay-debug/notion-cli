from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

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
    """业务 Channel 运行时。

    每个 Channel 独立拥有一个 FIFO Queue 和 Worker：
    - 同一 Channel 严格串行。
    - 不同 Channel 可以并行。
    - Channel 配置变更在 BUSY 时延迟到当前任务完成后应用。
    - 删除 Channel 不取消正在执行的任务。

    ChannelManager 不调用 Notion API，也不决定任务归属。
    """

    def __init__(self) -> None:
        self._channels: dict[str, _ChannelState] = {}

    def load_config(self, config: dict[str, Any]) -> None:
        """加载完整 Channel 配置。"""
        channels = config.get("channels")
        if not isinstance(channels, dict):
            raise ValueError("channel config must contain object: channels")

        configured = set(channels)

        for name, item in channels.items():
            if not isinstance(item, dict):
                raise ValueError(f"channel config must be an object: {name}")

            enabled = item.get("enabled", True)
            if not isinstance(enabled, bool):
                raise ValueError(f"channel enabled must be bool: {name}")

            executor = load_callable(
                item.get("module", ""),
                item.get("function", ""),
            )

            state = self._channels.get(name)
            if state is None:
                self._channels[name] = _ChannelState(
                    queue=asyncio.Queue(),
                    executor=executor,
                    enabled=enabled,
                )
                continue

            if state.running or not state.queue.empty():
                state.pending_config = {
                    "enabled": enabled,
                    "executor": executor,
                }
            else:
                state.enabled = enabled
                state.executor = executor

        for name, state in list(self._channels.items()):
            if name in configured:
                continue

            state.enabled = False
            state.pending_config = None
            if not state.running and state.queue.empty():
                self._channels.pop(name, None)

    async def submit(self, task: ChannelTask) -> None:
        await self._enqueue(task, wait=False)

    async def submit_and_wait(self, task: ChannelTask) -> Any:
        """提交任务，并等待该任务实际执行完成。"""
        return await self._enqueue(task, wait=True)

    async def _enqueue(self, task: ChannelTask, *, wait: bool) -> Any:
        state = self._channels.get(task.channel)
        if state is None:
            raise LookupError(f"channel is not configured: {task.channel}")
        if not state.enabled:
            raise RuntimeError(f"channel is disabled: {task.channel}")

        future: asyncio.Future[Any] | None = None
        if wait:
            future = asyncio.get_running_loop().create_future()

        await state.queue.put(_QueuedTask(task=task, result=future))

        if state.worker is None or state.worker.done():
            state.worker = asyncio.create_task(self._worker(task.channel, state))

        if future is not None:
            return await future
        return None

    async def _worker(self, name: str, state: _ChannelState) -> None:
        while True:
            if state.queue.empty():
                self._apply_pending(name, state)
                if state.queue.empty():
                    if not state.enabled:
                        self._channels.pop(name, None)
                    return

            queued = await state.queue.get()
            state.running = True
            try:
                result = await state.executor(queued.task)
            except BaseException as error:
                if queued.result is not None and not queued.result.done():
                    queued.result.set_exception(error)
            else:
                if queued.result is not None and not queued.result.done():
                    queued.result.set_result(result)
            finally:
                state.running = False
                state.queue.task_done()
                self._apply_pending(name, state)

    def _apply_pending(self, name: str, state: _ChannelState) -> None:
        if state.running or state.pending_config is None:
            return

        pending = state.pending_config
        state.pending_config = None
        state.enabled = pending["enabled"]
        state.executor = pending["executor"]

        if not state.enabled and state.queue.empty():
            self._channels.pop(name, None)

    def is_busy(self, channel: str) -> bool:
        state = self._channels.get(channel)
        return bool(state and (state.running or not state.queue.empty()))

    def has_channel(self, channel: str) -> bool:
        return channel in self._channels

    async def wait_for_idle(self, channel: str) -> None:
        state = self._channels.get(channel)
        if state is None:
            return
        await state.queue.join()
        if state.worker is not None:
            await state.worker
