import unittest
from unittest.mock import patch

from event_bus import Event
from event_runtime import EventRuntime


class TestRuleChiefToChannel(unittest.IsolatedAsyncioTestCase):
    async def test_routed_rule_produces_rule_done_event(self):
        runtime = EventRuntime()

        try:
            with patch(
                "handlers.new_task.read_json_file",
                return_value={
                    "version": 1,
                    "rules": {
                        "ds-001": {
                            "enabled": True,
                            "assignee": "notion",
                            "channel": "chat",
                        }
                    },
                },
            ):
                received = []

                async def capture_rule_done(event):
                    received.append(event)

                runtime.bus.unregister("RULE_DONE")
                runtime.bus.register("RULE_DONE", capture_rule_done)

                await runtime.bus.publish(
                    Event(
                        "NEW_TASK",
                        {
                            "task": {
                                "record_id": "record-001",
                                "parent": {
                                    "data_source_id": "ds-001"
                                },
                            }
                        },
                    )
                )
                await runtime.bus.wait_for_handlers()

                self.assertEqual(len(received), 1)
                event = received[0]
                self.assertEqual(event.event_type, "RULE_DONE")
                self.assertEqual(event.data["record_id"], "record-001")
                self.assertEqual(event.data["assignee"], "notion")
                self.assertEqual(event.data["channel"], "chat")
        finally:
            runtime.stop()
            if not runtime._loop.is_closed():
                runtime._loop.close()


if __name__ == "__main__":
    unittest.main()
