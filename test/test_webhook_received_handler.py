import unittest
from unittest.mock import Mock, patch

from event_bus import Event
from handlers.webhook_received import handle_webhook_received


class TestWebhookReceivedHandler(unittest.IsolatedAsyncioTestCase):
    async def test_handler_delegates_to_parser_worker(self):
        event = Event(
            "WEBHOOK_RECEIVED",
            {
                "record_id": "record-001",
                "file_path": "data/webhook_events/record-001.json",
            },
        )

        parser = Mock()
        parser.parse_file.return_value = {
            "record_id": "record-001",
        }

        with patch(
            "handlers.webhook_received.ParserWorker",
            return_value=parser,
        ):
            await handle_webhook_received(event)

        parser.parse_file.assert_called_once()
        self.assertEqual(
            parser.parse_file.call_args.args[0].as_posix(),
            "data/webhook_events/record-001.json",
        )


    async def test_handler_allows_already_parsed_event(self):
        event = Event(
            "WEBHOOK_RECEIVED",
            {
                "record_id": "record-002",
                "file_path": "data/webhook_events/record-002.json",
            },
        )

        parser = Mock()
        parser.parse_file.return_value = None

        with patch(
            "handlers.webhook_received.ParserWorker",
            return_value=parser,
        ):
            await handle_webhook_received(event)

        parser.parse_file.assert_called_once()


if __name__ == "__main__":
    unittest.main()
