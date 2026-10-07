from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from .dispatcher import EventDispatcher, EventHandler
from .event import Event


class EventBus:
    """事件总线。

    EventBus 不保存待消费事件，不轮询，也不等待 Queue。
    publish() 到达后立即根据注册表创建 Handler 执行任务。

    Queue 应在需要业务串行化的 Channel 层使用，而不是 Event Bus 层。
    """

    def __init__(
        self,
        dispatcher: EventDispatcher | None = None,
    ) -> None:
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
        """发布事件并立即触发已注册 Handler。

        不等待 Handler 完成。Handler 在当前事件循环中独立执行。
        """
        task = asyncio.create_task(self.dispatcher.dispatch(event))
        self._track_task(task)
        return task

    def publish_nowait(self, event: Event) -> asyncio.Task[None]:
        """在当前事件循环线程中立即触发事件。"""
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
            print(
                f"[EventBus ERROR] "
                f"{type(exception).__name__}: {exception}"
            )

    def active_task_count(self) -> int:
        """返回当前仍在执行的 Handler 数量。"""
        return len(self._tasks)

    async def wait_for_handlers(self) -> None:
        """仅用于测试、优雅关闭或明确需要等待全部 Handler 的场景。"""
        if self._tasks:
            await asyncio.gather(*tuple(self._tasks))
