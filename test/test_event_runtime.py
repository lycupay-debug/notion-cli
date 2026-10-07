import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from event_bus import Event
from event_runtime import EventRuntime


class TestEventRuntime(unittest.TestCase):
    def test_runtime_loads_handlers_from_json_config(self):
        runtime = EventRuntime()

        self.assertTrue(runtime.bus.has_handler("WEBHOOK_RECEIVED"))
        self.assertTrue(runtime.bus.has_handler("NEW_TASK"))

        runtime._loop.close()

    def test_reload_is_rejected_while_handler_is_active(self):
        runtime = EventRuntime()

        async def active_handler():
            await asyncio.Event().wait()

        loop = runtime._loop
        asyncio.set_event_loop(loop)
        task = loop.create_task(active_handler())
        runtime.bus._track_task(task)

        with self.assertRaisesRegex(RuntimeError, "active"):
            runtime.reload_handlers()

        task.cancel()
        loop.run_until_complete(asyncio.gather(task, return_exceptions=True))
        loop.close()

    def test_handler_result_event_is_published(self):
        runtime = EventRuntime()
        loop = runtime._loop
        asyncio.set_event_loop(loop)

        next_event = Event("NEW_TASK", {"task": {"record_id": "record-001"}})

        async def first_handler(event):
            return next_event

        second_handler = AsyncMock()

        runtime.bus.replace_handlers({
            "WEBHOOK_RECEIVED": runtime._wrap_handler(first_handler),
            "NEW_TASK": runtime._wrap_handler(second_handler),
        })

        loop.run_until_complete(
            runtime.bus.publish(Event("WEBHOOK_RECEIVED", {}))
        )
        loop.run_until_complete(asyncio.sleep(0))

        second_handler.assert_awaited_once()
        received = second_handler.await_args.args[0]
        self.assertEqual(received.event_type, "NEW_TASK")
        self.assertEqual(received.data, {"task": {"record_id": "record-001"}})

        loop.close()


if __name__ == "__main__":
    unittest.main()
