import asyncio
import unittest
from unittest.mock import AsyncMock

from event_bus import Event
from event_runtime import EventRuntime


class TestEventRuntime(unittest.IsolatedAsyncioTestCase):
    async def test_runtime_loads_handlers_from_json_config(self):
        runtime = EventRuntime()

        self.assertTrue(runtime.bus.has_handler("WEBHOOK_RECEIVED"))
        self.assertTrue(runtime.bus.has_handler("NEW_TASK"))

        runtime._loop.close()

    async def test_reload_is_rejected_while_handler_is_active(self):
        runtime = EventRuntime()

        async def active_handler():
            await asyncio.Event().wait()

        task = asyncio.create_task(active_handler())
        runtime.bus._track_task(task)

        with self.assertRaisesRegex(RuntimeError, "active"):
            runtime.reload_handlers()

        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        runtime._loop.close()

    async def test_handler_result_event_is_published(self):
        runtime = EventRuntime()

        next_event = Event(
            "NEW_TASK",
            {"task": {"record_id": "record-001"}},
        )

        async def first_handler(event):
            return next_event

        second_handler = AsyncMock()

        runtime.bus.replace_handlers({
            "WEBHOOK_RECEIVED": runtime._wrap_handler(first_handler),
            "NEW_TASK": runtime._wrap_handler(second_handler),
        })

        await runtime.bus.publish(
            Event("WEBHOOK_RECEIVED", {})
        )
        await asyncio.sleep(0)

        second_handler.assert_awaited_once()
        received = second_handler.await_args.args[0]

        self.assertEqual(received.event_type, "NEW_TASK")
        self.assertEqual(
            received.data,
            {"task": {"record_id": "record-001"}},
        )

        runtime._loop.close()


if __name__ == "__main__":
    unittest.main()
