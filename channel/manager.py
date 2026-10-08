from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from core.logger import error, info
from event_bus import Event
from methods.load_callable import load_callable

ChannelExecutor = Callable[["ChannelTask"], Awaitable[Any]]


@dataclass(frozen=True, slots=True)
class ChannelTask:
    record_id: str
    assignee: str
    channel: str
    data: dict[str, Any]
    route_rule: str | None = None

    @property
    def resource_id(self) -> str:
        entity = self.data.get("entity")
        if isinstance(entity, dict) and entity.get("id"):
            return str(entity["id"])
        return self.record_id


@dataclass(slots=True)
class _QueuedTask:
    task: ChannelTask
    result: asyncio.Future[Any] | None = None


@dataclass(slots=True)
class _ResourceLockState:
    lock: asyncio.Lock
    users: int = 0


@dataclass(slots=True)
class _ChannelState:
    queue: asyncio.Queue[_QueuedTask]
    executor: ChannelExecutor
    max_workers: int = 1
    enabled: bool = True
    running: int = 0
    workers: set[asyncio.Task[None]] | None = None
    resource_locks: dict[str, _ResourceLockState] | None = None
    pending_config: dict[str, Any] | None = None


class ChannelManager:
    """业务 Channel 运行时。

    同一资源严格串行；不同资源可在同一 Channel 内并行。
    每个 Channel 的并发度由 config/channels.json 的 max_workers 控制。
    """

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

            max_workers = item.get("max_workers", 1)
            if (
                not isinstance(max_workers, int)
                or isinstance(max_workers, bool)
                or max_workers < 1
            ):
                raise ValueError(
                    f"channel max_workers must be a positive integer: {name}"
                )

            executor = load_callable(
                item.get("module", ""),
                item.get("function", ""),
            )
            state = self._channels.get(name)

            if state is None:
                self._channels[name] = _ChannelState(
                    queue=asyncio.Queue(),
                    executor=executor,
                    max_workers=max_workers,
                    enabled=enabled,
                    workers=set(),
                    resource_locks={},
                )
                info(
                    f"[ChannelManager] CHANNEL_CREATED "
                    f"channel={name} enabled={enabled} max_workers={max_workers}"
                )
                continue

            if state.running or not state.queue.empty():
                state.pending_config = {
                    "enabled": enabled,
                    "executor": executor,
                    "max_workers": max_workers,
                }
                info(
                    f"[ChannelManager] CONFIG_DEFERRED "
                    f"channel={name} reason=BUSY"
                )
            else:
                state.enabled = enabled
                state.executor = executor
                state.max_workers = max_workers
                info(
                    f"[ChannelManager] CHANNEL_UPDATED "
                    f"channel={name} enabled={enabled} max_workers={max_workers}"
                )

        for name, state in list(self._channels.items()):
            if name in configured:
                continue
            state.enabled = False
            state.pending_config = None
            info(
                f"[ChannelManager] CHANNEL_DISABLED "
                f"channel={name} reason=REMOVED_FROM_CONFIG"
            )
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

        info(
            f"[ChannelManager] ENQUEUE record_id={task.record_id} "
            f"assignee={task.assignee} channel={task.channel} "
            f"resource={task.resource_id} wait={wait} "
            f"queue_size_before={state.queue.qsize()}"
        )

        future = (
            asyncio.get_running_loop().create_future()
            if wait
            else None
        )
        await state.queue.put(_QueuedTask(task=task, result=future))

        info(
            f"[ChannelManager] ENQUEUED record_id={task.record_id} "
            f"channel={task.channel} queue_size={state.queue.qsize()}"
        )
        self._ensure_workers(task.channel, state)

        if future is not None:
            return await future
        return None

    @staticmethod
    def _final_result(result: Any) -> str:
        if isinstance(result, dict):
            status = result.get("status")
            if status == "UPDATED" and result.get("verified") is True:
                return "SUCCESS"
            if status in {
                "SUCCESS",
                "UNCHANGED",
                "FAILED",
                "EXECUTE_FAILED",
            }:
                return status
        raise ValueError(f"executor returned unsupported result: {result!r}")

    @staticmethod
    def _publish_execution_result(task: ChannelTask, result: str) -> None:
        if task.assignee == "garbage-cleaner":
            info(
                f"[ChannelManager] EXECUTION_RESULT_SKIP "
                f"record_id={task.record_id} result={result} "
                f"reason=TERMINAL_CLEANUP"
            )
            return

        from event_bus import publish_default

        event = Event(
            "EXECUTION_RESULT",
            {
                "record_id": task.record_id,
                "assignee": task.assignee,
                "channel": task.channel,
                "result": result,
            },
        )
        try:
            publish_default(event)
        except Exception as exc:
            error(
                f"[ChannelManager] EXECUTION_RESULT_PUBLISH_FAILED "
                f"record_id={task.record_id} result={result} "
                f"error={type(exc).__name__}: {exc}"
            )
            return

        info(
            f"[ChannelManager] EXECUTION_RESULT_PUBLISHED "
            f"record_id={task.record_id} result={result}"
        )

    def _ensure_workers(self, name: str, state: _ChannelState) -> None:
        if state.workers is None:
            state.workers = set()

        while len(state.workers) < state.max_workers and not state.queue.empty():
            worker = asyncio.create_task(self._worker(name, state))
            state.workers.add(worker)
            worker.add_done_callback(state.workers.discard)
            info(
                f"[ChannelManager] WORKER_STARTED "
                f"channel={name} workers={len(state.workers)} "
                f"max_workers={state.max_workers}"
            )

    def _acquire_resource(
        self,
        state: _ChannelState,
        resource_id: str,
    ) -> _ResourceLockState:
        if state.resource_locks is None:
            state.resource_locks = {}

        resource = state.resource_locks.get(resource_id)
        if resource is None:
            resource = _ResourceLockState(lock=asyncio.Lock())
            state.resource_locks[resource_id] = resource

        resource.users += 1
        return resource

    def _release_resource(
        self,
        state: _ChannelState,
        resource_id: str,
        resource: _ResourceLockState,
    ) -> None:
        resource.users -= 1
        if (
            resource.users == 0
            and not resource.lock.locked()
            and state.resource_locks is not None
        ):
            state.resource_locks.pop(resource_id, None)

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
            state.running += 1
            task = queued.task
            resource = self._acquire_resource(state, task.resource_id)

            info(
                f"[ChannelManager] EXECUTE_WAIT "
                f"record_id={task.record_id} channel={name} "
                f"resource={task.resource_id} "
                f"queue_remaining={state.queue.qsize()}"
            )

            try:
                async with resource.lock:
                    info(
                        f"[ChannelManager] EXECUTE_START "
                        f"record_id={task.record_id} channel={name} "
                        f"resource={task.resource_id} assignee={task.assignee} "
                        f"queue_remaining={state.queue.qsize()}"
                    )

                    try:
                        result = await state.executor(task)
                    except BaseException as exc:
                        error(
                            f"[ChannelManager] EXECUTE_FAILED "
                            f"record_id={task.record_id} channel={name} "
                            f"error={type(exc).__name__}: {exc}"
                        )
                        self._publish_execution_result(
                            task,
                            "EXECUTE_FAILED",
                        )
                        if (
                            queued.result is not None
                            and not queued.result.done()
                        ):
                            queued.result.set_exception(exc)
                    else:
                        try:
                            final_result = self._final_result(result)
                        except Exception as exc:
                            error(
                                f"[ChannelManager] RESULT_INVALID "
                                f"record_id={task.record_id} channel={name} "
                                f"error={type(exc).__name__}: {exc}"
                            )
                            final_result = "EXECUTE_FAILED"

                        info(
                            f"[ChannelManager] EXECUTE_DONE "
                            f"record_id={task.record_id} channel={name} "
                            f"result={final_result}"
                        )
                        self._publish_execution_result(
                            task,
                            final_result,
                        )
                        if (
                            queued.result is not None
                            and not queued.result.done()
                        ):
                            queued.result.set_result(result)
            finally:
                self._release_resource(
                    state,
                    task.resource_id,
                    resource,
                )
                state.running -= 1
                state.queue.task_done()
                self._apply_pending(name, state)
                self._ensure_workers(name, state)
                info(
                    f"[ChannelManager] TASK_RELEASED "
                    f"record_id={task.record_id} channel={name} "
                    f"resource={task.resource_id} "
                    f"queue_size={state.queue.qsize()}"
                )

    def _apply_pending(self, name: str, state: _ChannelState) -> None:
        if state.running or state.pending_config is None:
            return

        pending = state.pending_config
        state.pending_config = None
        state.enabled = pending["enabled"]
        state.executor = pending["executor"]
        state.max_workers = pending["max_workers"]

        info(
            f"[ChannelManager] CONFIG_APPLIED "
            f"channel={name} enabled={state.enabled} "
            f"max_workers={state.max_workers}"
        )

        if not state.enabled and state.queue.empty():
            self._channels.pop(name, None)
            info(f"[ChannelManager] CHANNEL_REMOVED channel={name}")

    def is_busy(self, channel: str) -> bool:
        state = self._channels.get(channel)
        return bool(
            state
            and (state.running > 0 or not state.queue.empty())
        )

    def has_channel(self, channel: str) -> bool:
        return channel in self._channels

    async def wait_for_idle(self, channel: str) -> None:
        state = self._channels.get(channel)
        if state is None:
            return

        info(f"[ChannelManager] WAIT_IDLE_START channel={channel}")
        await state.queue.join()

        while state.running > 0:
            await asyncio.sleep(0)

        if state.workers:
            await asyncio.gather(
                *list(state.workers),
                return_exceptions=True,
            )

        info(f"[ChannelManager] WAIT_IDLE_DONE channel={channel}")
