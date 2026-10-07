from __future__ import annotations

import asyncio
import threading
from event_bus import EventBus, EventDispatcher

from handlers.webhook_received import handle_webhook_received


class EventRuntime:
    """
    Event Bus 运行时。

    HTTP Receiver 只负责接收并持久化 Webhook。
    EventRuntime 持有 EventBus、Dispatcher 和 Handler 注册表，
    并在同一事件循环中串行消费事件。
    """

    def __init__(self) -> None:
        self.bus = EventBus()
        self.dispatcher = EventDispatcher()
        self.dispatcher.register(
            "WEBHOOK_RECEIVED",
            handle_webhook_received,
        )

        self._loop: asyncio.AbstractEventLoop | None = None
        self._consumer_task: asyncio.Task[None] | None = None

    def start(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._consumer_task = self._loop.create_task(self._consume())
        self._loop.run_forever()

    async def _consume(self) -> None:
        while True:
            event = await self.bus.next_event()
            try:
                await self.dispatcher.dispatch(event)
            except Exception as exc:
                print(
                    f"[EventRuntime ERROR] "
                    f"{event.event_type}: {type(exc).__name__}: {exc}"
                )
            finally:
                self.bus.task_done()

    def publish_from_receiver(self, event) -> None:
        """
        从同步 HTTP Receiver 线程安全地发布事件。

        Receiver 本身不执行 Handler，也不访问 Notion。
        """
        if self._loop is None:
            raise RuntimeError("EventRuntime is not started")

        self._loop.call_soon_threadsafe(
            self.bus.publish_nowait,
            event,
        )

    def stop(self) -> None:
        if self._loop is None:
            return

        self._loop.call_soon_threadsafe(self._loop.stop)
