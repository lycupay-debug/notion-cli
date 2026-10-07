from __future__ import annotations

from collections.abc import Awaitable, Callable
from types import MappingProxyType

from .event import Event

EventHandler = Callable[[Event], Awaitable[None]]


class EventDispatcher:
    """事件分发器。

    维护 event_type -> Handler 的运行时注册表。
    不执行具体业务规则，也不负责事件等待或队列消费。
    """

    def __init__(self) -> None:
        self._handlers: dict[str, EventHandler] = {}

    def register(self, event_type: str, handler: EventHandler) -> None:
        if not event_type:
            raise ValueError("event_type cannot be empty")
        if not callable(handler):
            raise TypeError("handler must be callable")
        if event_type in self._handlers:
            raise ValueError(f"handler already registered: {event_type}")

        self._handlers[event_type] = handler

    def unregister(self, event_type: str) -> None:
        self._handlers.pop(event_type, None)

    def has_handler(self, event_type: str) -> bool:
        return event_type in self._handlers

    def get_handler(self, event_type: str) -> EventHandler:
        try:
            return self._handlers[event_type]
        except KeyError as exc:
            raise LookupError(
                f"no handler registered for event type: {event_type}"
            ) from exc

    def snapshot(self) -> MappingProxyType:
        """返回当前注册表的只读快照。"""
        return MappingProxyType(self._handlers.copy())

    def replace(self, handlers: dict[str, EventHandler]) -> None:
        """一次性替换整个注册表。

        调用方应先完成全部配置校验与 Handler 加载，再调用本方法。
        """
        if not isinstance(handlers, dict):
            raise TypeError("handlers must be a dict")

        for event_type, handler in handlers.items():
            if not event_type:
                raise ValueError("event_type cannot be empty")
            if not callable(handler):
                raise TypeError(
                    f"handler for {event_type} must be callable"
                )

        self._handlers = handlers.copy()

    async def dispatch(self, event: Event) -> None:
        """将事件直接分发给已注册 Handler。"""
        handler = self.get_handler(event.event_type)
        await handler(event)
