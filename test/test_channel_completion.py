import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from event_bus import Event
from channel import ChannelManager, ChannelTask
from handlers.rule_done import handle_rule_done


class TestChannelCompletion(unittest.IsolatedAsyncioTestCase):
    async def test_submit_and_wait_returns_executor_result(self):
        manager = ChannelManager()

        async def executor(task):
            await asyncio.sleep(0)
            return {"status": "UPDATED", "verified": True}

        with patch("channel.manager.load_callable", return_value=executor):
            manager.load_config({
                "channels": {
                    "system_ledger": {
                        "enabled": True,
                        "module": "unused",
                        "function": "unused",
                    }
                }
            })

        result = await manager.submit_and_wait(
            ChannelTask("record-1", "system-ledger", "system_ledger", {})
        )

        self.assertEqual(
            result,
            {"status": "UPDATED", "verified": True},
        )

    async def test_rule_done_returns_channel_done_event(self):
        result = {"status": "UPDATED", "verified": True}

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
            new=AsyncMock(return_value=result),
        ) as submit:
            event = await handle_rule_done(
                Event(
                    "RULE_DONE",
                    {
                        "record_id": "record-1",
                        "assignee": "system-ledger",
                        "channel": "system_ledger",
                        "task": {"entity": {"id": "page-1"}},
                    },
                )
            )

        submit.assert_awaited_once()
        self.assertEqual(event.event_type, "CHANNEL_DONE")
        self.assertEqual(event.data["record_id"], "record-1")
        self.assertEqual(event.data["channel"], "system_ledger")
        self.assertEqual(event.data["result"], result)

    async def test_channel_done_handler_accepts_completion_event(self):
        from handlers.channel_done import handle_channel_done

        event = Event(
            "CHANNEL_DONE",
            {
                "record_id": "record-1",
                "channel": "system_ledger",
                "result": {"status": "UPDATED"},
            },
        )

        await handle_channel_done(event)


if __name__ == "__main__":
    unittest.main()
