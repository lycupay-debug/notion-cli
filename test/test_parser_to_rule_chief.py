import asyncio
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from event_bus import Event
from event_runtime import EventRuntime


class TestParserToRuleChief(unittest.IsolatedAsyncioTestCase):
    TEST_RECORD_ID = "0d091c56-2aaa-4ee6-97f6-a2fbc0cc3826"

    async def test_real_webhook_to_parser_to_rule_chief(self):
        root = Path(__file__).resolve().parent.parent
        event_path = (
            root
            / "data"
            / "webhook_events"
            / f"{self.TEST_RECORD_ID}.json"
        )

        if not event_path.exists():
            self.skipTest(f"test webhook event not found: {event_path}")

        history_path = (
            root
            / "config"
            / "parse_history"
            / f"{self.TEST_RECORD_ID}.json"
        )

        task_path = (
            root
            / "config"
            / "tasks"
            / f"{self.TEST_RECORD_ID}.json"
        )

        if history_path.exists():
            self.skipTest(
                f"webhook event is already parsed: {self.TEST_RECORD_ID}"
            )

        runtime = EventRuntime()

        try:
            with patch("builtins.print") as mocked_print:
                await runtime.bus.publish(
                    Event(
                        "WEBHOOK_RECEIVED",
                        {
                            "record_id": self.TEST_RECORD_ID,
                            "file_path": str(event_path.relative_to(root)),
                            "event_id": self.TEST_RECORD_ID,
                        },
                    )
                )

                await asyncio.sleep(0)
                await asyncio.sleep(0)

                self.assertTrue(
                    task_path.exists(),
                    f"Parser did not create task file: {task_path}",
                )
                self.assertTrue(
                    history_path.exists(),
                    f"Parser did not create parse history: {history_path}",
                )

                task = json.loads(
                    task_path.read_text(encoding="utf-8")
                )

                self.assertEqual(
                    task.get("record_id"),
                    self.TEST_RECORD_ID,
                )

                output = "\n".join(
                    str(call.args[0])
                    for call in mocked_print.call_args_list
                    if call.args
                )

                self.assertIn(
                    "[WebhookReceivedHandler] parsed webhook:",
                    output,
                )
                self.assertIn("[NewTaskHandler]", output)
                self.assertIn("status=UNROUTED", output)
                self.assertIn("reason=NO_RULE_CONFIGURED", output)
        finally:
            runtime.stop()
            if not runtime._loop.is_closed():
                runtime._loop.close()


if __name__ == "__main__":
    unittest.main()
