import json
import os
import unittest
from pathlib import Path

from event_bus import Event
from event_runtime import EventRuntime


class TestRealSystemLedgerChain(unittest.IsolatedAsyncioTestCase):
    async def test_rule_done_to_real_system_ledger_channel(self):
        """真实调用 SystemLedgerListener；目标页面由本地环境变量指定。"""
        record_id = os.environ.get("NOTION_CLI_TEST_RECORD_ID")
        page_id = os.environ.get("NOTION_CLI_TEST_PAGE_ID")

        if not record_id or not page_id:
            self.skipTest(
                "set NOTION_CLI_TEST_RECORD_ID and "
                "NOTION_CLI_TEST_PAGE_ID before running"
            )

        root = Path(__file__).resolve().parent.parent
        task_path = root / "config" / "tasks" / f"{record_id}.json"
        original_task = (
            task_path.read_text(encoding="utf-8")
            if task_path.exists()
            else None
        )

        task = {
            "record_id": record_id,
            "assignee": "system-ledger",
            "task_completed": None,
            "incomplete_reason": "",
            "event_id": "real-system-ledger-chain-test",
            "event_type": "page.updated",
            "author": {},
            "entity": {"id": page_id, "type": "page"},
            "parent": {
                "id": "test-parent",
                "type": "data_source",
                "data_source_id": "test-data-source",
            },
            "updated_properties": [],
            "updated_blocks": [],
        }

        runtime = EventRuntime()
        channel_done_events = []

        async def capture_channel_done(event):
            channel_done_events.append(event)
            return None

        try:
            task_path.parent.mkdir(parents=True, exist_ok=True)
            task_path.write_text(
                json.dumps(task, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            from handlers.rule_done import handle_rule_done

            runtime.bus.replace_handlers({
                "RULE_DONE": runtime._wrap_handler(handle_rule_done),
                "CHANNEL_DONE": runtime._wrap_handler(
                    capture_channel_done
                ),
            })

            await runtime.bus.publish(
                Event(
                    "RULE_DONE",
                    {
                        "record_id": record_id,
                        "assignee": "system-ledger",
                        "channel": "system_ledger",
                        "task": task,
                    },
                )
            )

            await runtime.bus.wait_for_handlers()

            self.assertEqual(len(channel_done_events), 1)
            completed = channel_done_events[0]
            self.assertEqual(completed.event_type, "CHANNEL_DONE")
            self.assertEqual(completed.data["record_id"], record_id)
            self.assertEqual(
                completed.data["channel"],
                "system_ledger",
            )
            self.assertIn(
                completed.data["result"]["status"],
                {"UPDATED", "UNCHANGED"},
            )

            if completed.data["result"]["status"] == "UPDATED":
                self.assertTrue(completed.data["result"]["verified"])

        finally:
            runtime.stop()
            if not runtime._loop.is_closed():
                runtime._loop.close()

            if original_task is None:
                task_path.unlink(missing_ok=True)
            else:
                task_path.write_text(
                    original_task,
                    encoding="utf-8",
                )


if __name__ == "__main__":
    unittest.main()
