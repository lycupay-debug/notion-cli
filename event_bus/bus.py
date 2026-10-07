from __future__ import annotations

import asyncio

from core.logger import error, info
from .dispatcher import EventDispatcher, EventHandler
from .event import Event


class EventBus:
    """事件总线。"""

    def __init__(self, dispatcher: EventDispatcher | None = None) -> None:
        self.dispatcher = dispatcher or EventDispatcher()
        self._tasks: set[asyncio.Task[None]] = set()

    def register(self, event_type: str, handler: EventHandler) -> None:
        self.dispatcher.register(event_type, handler)

    def unregister(self, event_type: str) -> None:
        self.dispatcher.unregister(event_type)

    def has_handler(self, event_type: str) -> bool:
        return self.dispatcher.has_handler(event_type)

    def replace_handlers(self, handlers: dict[str, EventHandler]) -> None:
        self.dispatcher.replace(handlers)

    def publish(self, event: Event) -> asyncio.Task[None]:
        info(f"[EventBus] PUBLISH event_type={event.event_type} event_id={event.event_id}")
        task = asyncio.create_task(self.dispatcher.dispatch(event))
        self._track_task(task)
        return task

    def publish_nowait(self, event: Event) -> asyncio.Task[None]:
        return self.publish(event)

    def _track_task(self, task: asyncio.Task[None]) -> None:
        self._tasks.add(task)
        task.add_done_callback(self._on_task_done)

    def _on_task_done(self, task: asyncio.Task[None]) -> None:
        self._tasks.discard(task)
        if task.cancelled():
            return
        exception = task.exception()
        if exception is not None:
            error(f"[EventBus] HANDLER_ERROR {type(exception).__name__}: {exception}")

    def active_task_count(self) -> int:
        return len(self._tasks)

    async def wait_for_handlers(self) -> None:
        if self._tasks:
            await asyncio.gather(*tuple(self._tasks))
