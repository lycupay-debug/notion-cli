from __future__ import annotations

from collections.abc import Awaitable, Callable
from types import MappingProxyType

from core.logger import error, info
from .event import Event

EventHandler = Callable[[Event], Awaitable[None]]


class EventDispatcher:
    """事件分发器。"""

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
        info(f"[EventDispatcher] REGISTER event_type={event_type}")

    def unregister(self, event_type: str) -> None:
        self._handlers.pop(event_type, None)
        info(f"[EventDispatcher] UNREGISTER event_type={event_type}")

    def has_handler(self, event_type: str) -> bool:
        return event_type in self._handlers

    def get_handler(self, event_type: str) -> EventHandler:
        try:
            return self._handlers[event_type]
        except KeyError as exc:
            error(f"[EventDispatcher] NO_HANDLER event_type={event_type}")
            raise LookupError(f"no handler registered for event type: {event_type}") from exc

    def snapshot(self) -> MappingProxyType:
        return MappingProxyType(self._handlers.copy())

    def replace(self, handlers: dict[str, EventHandler]) -> None:
        if not isinstance(handlers, dict):
            raise TypeError("handlers must be a dict")
        for event_type, handler in handlers.items():
            if not event_type:
                raise ValueError("event_type cannot be empty")
            if not callable(handler):
                raise TypeError(f"handler for {event_type} must be callable")
        self._handlers = handlers.copy()
        info(f"[EventDispatcher] REPLACED count={len(self._handlers)}")

    async def dispatch(self, event: Event) -> None:
        handler = self.get_handler(event.event_type)
        record_id = event.data.get("record_id")
        if not record_id and isinstance(event.data.get("task"), dict):
            record_id = event.data["task"].get("record_id")
        info(f"[EventDispatcher] DISPATCH event_type={event.event_type} event_id={event.event_id} record_id={record_id or '-'}")
        try:
            await handler(event)
        except Exception as exc:
            error(f"[EventDispatcher] DISPATCH_FAILED event_type={event.event_type} event_id={event.event_id} record_id={record_id or '-'} error={type(exc).__name__}: {exc}")
            raise
        info(f"[EventDispatcher] DISPATCH_DONE event_type={event.event_type} event_id={event.event_id} record_id={record_id or '-'}")
