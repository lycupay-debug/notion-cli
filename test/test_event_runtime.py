import asyncio
import unittest

from event_runtime import EventRuntime


class TestEventRuntime(unittest.TestCase):
    def test_runtime_loads_handlers_from_json_config(self):
        runtime = EventRuntime()

        self.assertTrue(runtime.bus.has_handler("WEBHOOK_RECEIVED"))
        self.assertFalse(runtime.bus.has_handler("NEW_TASK"))

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


if __name__ == "__main__":
    unittest.main()
