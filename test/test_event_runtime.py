import asyncio
import json
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

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

        channel_done_handler = AsyncMock(return_value=None)

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

            for _ in range(3):
                await runtime.bus.wait_for_handlers()
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

    async def test_real_webhook_to_channel_done_full_chain(self):
        """使用真实 ParserWorker，验证 webhook 文件到 CHANNEL_DONE 的完整事件链。"""
        root = Path(__file__).resolve().parent.parent
        record_id = "record-runtime-full-chain-001"
        event_path = root / "data" / "webhook_events" / f"{record_id}.json"
        task_path = root / "config" / "tasks" / f"{record_id}.json"
        history_path = (
            root / "config" / "parse_history" / f"{record_id}.json"
        )

        raw_event = {
            "record_id": record_id,
            "event_id": "event-runtime-full-chain-001",
            "event_type": "page.updated",
            "payload": {
                "authors": [
                    {"type": "person", "id": "person-001"}
                ],
                "entity": {
                    "id": "page-runtime-full-chain-001",
                    "type": "page",
                },
                "data": {
                    "parent": {
                        "id": "parent-runtime-full-chain-001",
                        "type": "data_source",
                        "data_source_id": "data-source-runtime-full-chain-001",
                    },
                    "updated_properties": ["Name"],
                    "updated_blocks": [],
                },
            },
        }

        for path in (event_path, task_path, history_path):
            path.unlink(missing_ok=True)

        runtime = EventRuntime()
        channel_done_handler = AsyncMock()
        channel_result = {
            "status": "UPDATED",
            "verified": True,
        }

        try:
            with patch(
                "handlers.new_task.read_json_file",
                return_value={
                    "rules": {
                        "data-source-runtime-full-chain-001": {
                            "enabled": True,
                            "assignee": "system-ledger",
                            "channel": "system_ledger",
                        }
                    }
                },
            ), patch(
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
                new=AsyncMock(return_value=channel_result),
            ):
                runtime.bus.replace_handlers({
                    "WEBHOOK_RECEIVED": runtime._wrap_handler(
                        __import__(
                            "handlers.webhook_received",
                            fromlist=["handle_webhook_received"],
                        ).handle_webhook_received
                    ),
                    "NEW_TASK": runtime._wrap_handler(
                        __import__(
                            "handlers.new_task",
                            fromlist=["handle_new_task"],
                        ).handle_new_task
                    ),
                    "RULE_DONE": runtime._wrap_handler(
                        __import__(
                            "handlers.rule_done",
                            fromlist=["handle_rule_done"],
                        ).handle_rule_done
                    ),
                    "CHANNEL_DONE": runtime._wrap_handler(
                        channel_done_handler
                    ),
                })

                event_path.write_text(
                    json.dumps(raw_event, ensure_ascii=False),
                    encoding="utf-8",
                )

                await runtime.bus.publish(
                    Event(
                        "WEBHOOK_RECEIVED",
                        {
                            "record_id": record_id,
                            "file_path": str(
                                event_path.relative_to(root)
                            ),
                            "event_id": raw_event["event_id"],
                        },
                    )
                )

                for _ in range(5):
                    await runtime.bus.wait_for_handlers()
                    await asyncio.sleep(0)

            self.assertTrue(task_path.exists())
            self.assertTrue(history_path.exists())

            task = json.loads(task_path.read_text(encoding="utf-8"))
            self.assertEqual(task["record_id"], record_id)
            self.assertEqual(
                task["entity"]["id"],
                "page-runtime-full-chain-001",
            )
            self.assertEqual(
                task["parent"]["data_source_id"],
                "data-source-runtime-full-chain-001",
            )

            channel_done_handler.assert_awaited_once()
            received = channel_done_handler.await_args.args[0]
            self.assertEqual(received.event_type, "CHANNEL_DONE")
            self.assertEqual(received.data["record_id"], record_id)
            self.assertEqual(
                received.data["assignee"],
                "system-ledger",
            )
            self.assertEqual(
                received.data["channel"],
                "system_ledger",
            )
            self.assertEqual(
                received.data["result"],
                channel_result,
            )
        finally:
            runtime.stop()
            if not runtime._loop.is_closed():
                runtime._loop.close()
            for path in (event_path, task_path, history_path):
                path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
