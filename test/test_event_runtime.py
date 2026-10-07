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


    async def test_rule_done_to_channel_done_is_full_event_chain(self):
        from unittest.mock import patch
        from handlers.rule_done import handle_rule_done

        runtime = EventRuntime()

        rule_done_event = Event(
            "RULE_DONE",
            {
                "record_id": "record-chain-001",
                "assignee": "system-ledger",
                "channel": "system_ledger",
                "task": {"entity": {"id": "page-chain-001"}},
            },
        )

        async def new_task_handler(event):
            return rule_done_event

        channel_done_handler = AsyncMock()

        with patch(
            "handlers.rule_done.read_json_file",
            return_value={
                "channels": {
                    "system_ledger": {
                        "enabled": True,
                        "module": "unused",
                        "function": "unused",
                    }
                }
            },
        ), patch(
            "handlers.rule_done._channel_manager.load_config"
        ), patch(
            "handlers.rule_done._channel_manager.submit_and_wait",
            new=AsyncMock(
                return_value={"status": "UPDATED", "verified": True}
            ),
        ):
            runtime.bus.replace_handlers({
                "NEW_TASK": runtime._wrap_handler(new_task_handler),
                "RULE_DONE": runtime._wrap_handler(handle_rule_done),
                "CHANNEL_DONE": runtime._wrap_handler(channel_done_handler),
            })

            await runtime.bus.publish(
                Event(
                    "NEW_TASK",
                    {"task": {"record_id": "record-chain-001"}},
                )
            )

            await asyncio.sleep(0)
            await asyncio.sleep(0)

        channel_done_handler.assert_awaited_once()
        received = channel_done_handler.await_args.args[0]

        self.assertEqual(received.event_type, "CHANNEL_DONE")
        self.assertEqual(received.data["record_id"], "record-chain-001")
        self.assertEqual(received.data["channel"], "system_ledger")
        self.assertEqual(
            received.data["result"],
            {"status": "UPDATED", "verified": True},
        )

        runtime._loop.close()


if __name__ == "__main__":
    unittest.main()
