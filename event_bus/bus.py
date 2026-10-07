from __future__ import annotations

import asyncio

from .event import Event


class EventBus:
    """事件总线。

    职责只有两个：
    1. 发布事件；
    2. 取出下一个事件。

    EventBus 不判断事件类型，不调用 Handler，不执行业务规则。
    """

    def __init__(self) -> None:
        self._queue: asyncio.Queue[Event] = asyncio.Queue()

    async def publish(self, event: Event) -> None:
        """将事件放入事件流。"""
        await self._queue.put(event)

    def publish_nowait(self, event: Event) -> None:
        """在当前事件循环线程中立即放入事件。"""
        self._queue.put_nowait(event)

    async def next_event(self) -> Event:
        """等待并取出下一个事件。

        asyncio.Queue 在没有事件时挂起等待，不进行轮询。
        """
        return await self._queue.get()

    def task_done(self) -> None:
        """标记最近取出的事件已经完成消费。"""
        self._queue.task_done()

    def qsize(self) -> int:
        """返回当前等待处理的事件数量。"""
        return self._queue.qsize()
