import asyncio
import unittest

from event_bus import Event, EventBus, EventDispatcher


class TestEventBus(unittest.IsolatedAsyncioTestCase):
    async def test_publish_directly_triggers_registered_handler(self):
        bus = EventBus()
        received = []

        async def handle(event: Event) -> None:
            received.append(event)

        bus.register("NEW_TASK", handle)
        task = bus.publish(Event("NEW_TASK"))

        self.assertIsInstance(task, asyncio.Task)
        await task

        self.assertEqual(received[0].event_type, "NEW_TASK")
        self.assertEqual(bus.active_task_count(), 0)

    async def test_different_events_can_run_without_waiting_for_each_other(self):
        bus = EventBus()
        started = []
        release = asyncio.Event()

        async def handle_a(event: Event) -> None:
            started.append("A")
            await release.wait()

        async def handle_b(event: Event) -> None:
            started.append("B")

        bus.register("A", handle_a)
        bus.register("B", handle_b)

        task_a = bus.publish(Event("A"))
        task_b = bus.publish(Event("B"))

        await asyncio.sleep(0)

        self.assertEqual(started, ["A", "B"])
        self.assertFalse(task_a.done())
        self.assertTrue(task_b.done())

        release.set()
        await task_a

    async def test_replace_handlers_switches_registration(self):
        bus = EventBus()
        received = []

        async def old_handler(event: Event) -> None:
            received.append("old")

        async def new_handler(event: Event) -> None:
            received.append("new")

        bus.register("TEST", old_handler)
        await bus.publish(Event("TEST"))

        bus.replace_handlers({"TEST": new_handler})

        await bus.publish(Event("TEST"))

        self.assertEqual(received, ["old", "new"])

    async def test_unknown_event_raises_when_handler_task_is_awaited(self):
        bus = EventBus()

        task = bus.publish(Event("UNKNOWN"))

        with self.assertRaisesRegex(LookupError, "UNKNOWN"):
            await task

    async def test_handler_failure_does_not_break_bus(self):
        bus = EventBus()
        received = []

        async def failing(event: Event) -> None:
            raise RuntimeError("handler failed")

        async def succeeding(event: Event) -> None:
            received.append("ok")

        bus.register("FAIL", failing)
        bus.register("OK", succeeding)

        failed = bus.publish(Event("FAIL"))
        succeeded = bus.publish(Event("OK"))

        await asyncio.gather(
            failed,
            succeeded,
            return_exceptions=True,
        )

        self.assertEqual(received, ["ok"])

    def test_dispatcher_replace(self):
        dispatcher = EventDispatcher()

        async def handle(event: Event) -> None:
            return None

        dispatcher.replace({"EVENT": handle})

        self.assertTrue(dispatcher.has_handler("EVENT"))
        self.assertFalse(dispatcher.has_handler("OTHER"))


if __name__ == "__main__":
    unittest.main()
