from __future__ import annotations

from collections.abc import Awaitable, Callable

from .event import Event

EventHandler = Callable[[Event], Awaitable[None]]


class EventDispatcher:
    """事件分发器。

    根据 event_type 直接找到对应 Handler。
    不使用 if/elif 链，不执行具体业务逻辑。
    """

    def __init__(self) -> None:
        self._handlers: dict[str, EventHandler] = {}

    def register(self, event_type: str, handler: EventHandler) -> None:
        if not event_type:
            raise ValueError("event_type cannot be empty")

        if event_type in self._handlers:
            raise ValueError(
                f"handler already registered: {event_type}"
            )

        self._handlers[event_type] = handler

    def unregister(self, event_type: str) -> None:
        self._handlers.pop(event_type, None)

    def has_handler(self, event_type: str) -> bool:
        return event_type in self._handlers

    async def dispatch(self, event: Event) -> None:
        """将事件直接分发给已注册 Handler。"""
        try:
            handler = self._handlers[event.event_type]
        except KeyError as exc:
            raise LookupError(
                f"no handler registered for event type: {event.event_type}"
            ) from exc

        await handler(event)
