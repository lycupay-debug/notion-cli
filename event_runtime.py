from __future__ import annotations

import asyncio
import json

from event_bus import Event, EventBus
from methods.get_event_handlers_config_path import (
    get_event_handlers_config_path,
)
from methods.load_callable import load_callable


class EventRuntime:
    """Event Bus 运行时。

    Receiver 发布事件后，EventBus 直接触发注册 Handler。
    运行时不存在永久 Queue Consumer。

    Handler 注册关系来自 config/event_handlers.json。
    reload_handlers() 会先构建完整的新注册表，全部成功后再一次性替换。
    """

    def __init__(self) -> None:
        self.bus = EventBus()
        self._loop: asyncio.AbstractEventLoop = asyncio.new_event_loop()
        self._started = False
        self.reload_handlers()

    def _load_handler_registry(self) -> dict:
        config_path = get_event_handlers_config_path()

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
                raise ValueError(
                    f"handler config must be an object: {event_type}"
                )

            if not item.get("enabled", True):
                continue

            handler = load_callable(
                item.get("module", ""),
                item.get("function", ""),
            )
            handlers[event_type] = handler

        return handlers

    def reload_handlers(self) -> None:
        """热加载 Handler 配置。

        先构建并验证完整新注册表，成功后才替换当前注册表。
        配置错误不会破坏当前正在运行的 Handler 注册关系。
        """
        handlers = self._load_handler_registry()
        self.bus.replace_handlers(handlers)

    def start(self) -> None:
        if self._started:
            return

        asyncio.set_event_loop(self._loop)
        self._started = True
        self._loop.run_forever()

    def publish_from_receiver(self, event: Event) -> None:
        """从同步 Receiver 线程安全地触发事件。"""
        if not self._started:
            raise RuntimeError("EventRuntime is not started")

        self._loop.call_soon_threadsafe(
            self.bus.publish_nowait,
            event,
        )

    def stop(self) -> None:
        if not self._started:
            return

        self._loop.call_soon_threadsafe(self._loop.stop)
        self._started = False
