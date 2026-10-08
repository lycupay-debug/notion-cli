from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable

from core.logger import error, info
from event_bus import Event, EventBus, set_default_bus
from methods.get_event_handlers_config_path import get_event_handlers_config_path
from methods.load_callable import load_callable

Handler = Callable[[Event], Awaitable[Event | None]]


class EventRuntime:
    """Event Bus 运行时。"""

    def __init__(self) -> None:
        self.bus = EventBus()
        set_default_bus(self.bus)
        self._loop: asyncio.AbstractEventLoop = asyncio.new_event_loop()
        self._started = False
        info("[EventRuntime] INIT")
        self.reload_handlers()

    def _wrap_handler(self, handler: Callable) -> Callable:
        async def wrapped(event: Event) -> None:
            record_id = event.data.get("record_id")
            if not record_id and isinstance(event.data.get("task"), dict):
                record_id = event.data["task"].get("record_id")
            info(f"[EventRuntime] HANDLER_START event_type={event.event_type} event_id={event.event_id} record_id={record_id or '-'}")
            try:
                next_event = await handler(event)
            except Exception as exc:
                error(f"[EventRuntime] HANDLER_FAILED event_type={event.event_type} event_id={event.event_id} record_id={record_id or '-'} error={type(exc).__name__}: {exc}")
                raise
            info(f"[EventRuntime] HANDLER_END event_type={event.event_type} event_id={event.event_id} record_id={record_id or '-'} next_event={next_event.event_type if next_event else '-'}")
            if next_event is None:
                return
            if not isinstance(next_event, Event):
                raise TypeError("handler result must be Event or None")
            info(f"[EventRuntime] NEXT_EVENT event_type={next_event.event_type} event_id={next_event.event_id} record_id={next_event.data.get('record_id', '-')}")
            self.bus.publish(next_event)
        return wrapped

    def _load_handler_registry(self) -> dict:
        config_path = get_event_handlers_config_path()
        info(f"[EventRuntime] LOAD_CONFIG path={config_path}")
        with config_path.open("r", encoding="utf-8") as file:
            config = json.load(file)
        if not isinstance(config, dict):
            raise ValueError("event handler config must be an object")
        handlers_config = config.get("handlers")
        if not isinstance(handlers_config, dict):
            raise ValueError("event handler config must contain object: handlers")
        handlers = {}
        for event_type, item in handlers_config.items():
            if not isinstance(item, dict):
                raise ValueError(f"handler config must be an object: {event_type}")
            if not item.get("enabled", True):
                info(f"[EventRuntime] HANDLER_DISABLED event_type={event_type}")
                continue
            module = item.get("module", "")
            function = item.get("function", "")
            handler = load_callable(module, function)
            handlers[event_type] = self._wrap_handler(handler)
            info(f"[EventRuntime] HANDLER_REGISTERED event_type={event_type} module={module} function={function}")
        return handlers

    def reload_handlers(self) -> None:
        if self.bus.active_task_count() > 0:
            raise RuntimeError("cannot reload handlers while event handlers are active")
        handlers = self._load_handler_registry()
        self.bus.replace_handlers(handlers)
        info(f"[EventRuntime] HANDLERS_RELOADED count={len(handlers)}")

    def start(self) -> None:
        if self._started:
            info("[EventRuntime] START_SKIPPED already_started=true")
            return
        asyncio.set_event_loop(self._loop)
        self._started = True
        info("[EventRuntime] START")
        self._loop.run_forever()
        info("[EventRuntime] LOOP_STOPPED")

    def publish_from_receiver(self, event: Event) -> None:
        if not self._started:
            raise RuntimeError("EventRuntime is not started")
        info(f"[EventRuntime] RECEIVE event_type={event.event_type} event_id={event.event_id} record_id={event.data.get('record_id', '-')}")
        self._loop.call_soon_threadsafe(self.bus.publish_nowait, event)

    def stop(self) -> None:
        if not self._started:
            info("[EventRuntime] STOP_SKIPPED already_stopped=true")
            return
        info("[EventRuntime] STOP")
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._started = False
