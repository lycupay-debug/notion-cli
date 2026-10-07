import hashlib
import hmac
import json
import os
import tempfile
import threading
import time
import unittest
from http.client import HTTPConnection
from http.server import HTTPServer
from pathlib import Path
from unittest.mock import patch

import webhook.receiver as receiver
from event_runtime import EventRuntime


class TestRealWebhookToChannel(unittest.TestCase):
    def test_real_webhook_to_system_ledger_channel(self):
        """通过真实 HTTP Webhook 入口验证到真实 SystemLedger Channel。"""
        page_id = os.environ.get("NOTION_CLI_TEST_PAGE_ID")
        data_source_id = os.environ.get("NOTION_CLI_TEST_DATA_SOURCE_ID")

        if not page_id or not data_source_id:
            self.skipTest(
                "set NOTION_CLI_TEST_PAGE_ID and "
                "NOTION_CLI_TEST_DATA_SOURCE_ID before running"
            )

        token = "real-webhook-chain-test-token"
        runtime = EventRuntime()
        channel_done = threading.Event()
        channel_done_events = []

        async def capture_channel_done(event):
            channel_done_events.append(event)
            channel_done.set()
            return None

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
            "CHANNEL_DONE": runtime._wrap_handler(capture_channel_done),
        })

        project_root = Path(__file__).resolve().parent.parent

        with tempfile.TemporaryDirectory(dir=project_root) as temp_dir:
            temp_root = Path(temp_dir)
            event_dir = temp_root / "webhook_events"
            credentials_file = temp_root / "webhook_credentials.json"
            event_dir.mkdir()

            server = HTTPServer(("127.0.0.1", 0), receiver.WebhookHandler)
            server.event_runtime = runtime

            runtime_thread = threading.Thread(
                target=runtime.start,
                name="RealWebhookEventRuntime",
                daemon=True,
            )
            server_thread = threading.Thread(
                target=server.handle_request,
                name="RealWebhookHTTPServer",
                daemon=True,
            )

            try:
                credentials_file.write_text(
                    json.dumps({"verification_token": token}),
                    encoding="utf-8",
                )

                with patch.object(receiver, "EVENT_DIR", event_dir),                      patch.object(
                         receiver,
                         "CREDENTIALS_FILE",
                         credentials_file,
                     ),                      patch(
                         "handlers.new_task.read_json_file",
                         return_value={
                             "version": 1,
                             "rules": {
                                 data_source_id: {
                                     "enabled": True,
                                     "assignee": "system-ledger",
                                     "channel": "system_ledger",
                                 }
                             },
                         },
                     ):
                    runtime_thread.start()

                    deadline = time.time() + 5
                    while not runtime._started and time.time() < deadline:
                        time.sleep(0.01)

                    self.assertTrue(
                        runtime._started,
                        "EventRuntime failed to start",
                    )

                    server_thread.start()

                    payload = {
                        "id": "real-webhook-chain-event",
                        "type": "page.updated",
                        "timestamp": "2026-10-08T00:00:00.000Z",
                        "workspace_id": "test-workspace",
                        "authors": [
                            {
                                "type": "person",
                                "id": "test-person",
                            }
                        ],
                        "entity": {
                            "id": page_id,
                            "type": "page",
                        },
                        "data": {
                            "parent": {
                                "id": data_source_id,
                                "type": "data_source",
                                "data_source_id": data_source_id,
                            },
                            "updated_properties": ["Notion页面ID"],
                            "updated_blocks": [],
                        },
                    }

                    raw_body = json.dumps(
                        payload,
                        ensure_ascii=False,
                        separators=(",", ":"),
                    ).encode("utf-8")

                    signature = "sha256=" + hmac.new(
                        token.encode("utf-8"),
                        raw_body,
                        hashlib.sha256,
                    ).hexdigest()

                    connection = HTTPConnection(
                        "127.0.0.1",
                        server.server_address[1],
                        timeout=10,
                    )
                    try:
                        connection.request(
                            "POST",
                            "/",
                            body=raw_body,
                            headers={
                                "Content-Type": "application/json",
                                "Content-Length": str(len(raw_body)),
                                "X-Notion-Signature": signature,
                            },
                        )
                        response = connection.getresponse()
                        response_body = response.read().decode("utf-8")
                    finally:
                        connection.close()

                    self.assertEqual(response.status, 200)
                    response_data = json.loads(response_body)
                    record_id = response_data["record_id"]

                    self.assertTrue(
                        channel_done.wait(timeout=20),
                        "CHANNEL_DONE was not produced",
                    )

                    self.assertEqual(len(channel_done_events), 1)
                    completed = channel_done_events[0]
                    self.assertEqual(
                        completed.data["record_id"],
                        record_id,
                    )
                    self.assertEqual(
                        completed.data["channel"],
                        "system_ledger",
                    )
                    self.assertIn(
                        completed.data["result"]["status"],
                        {"UPDATED", "UNCHANGED"},
                    )

                    task_path = (
                        project_root
                        / "config"
                        / "tasks"
                        / f"{record_id}.json"
                    )
                    history_path = (
                        project_root
                        / "config"
                        / "parse_history"
                        / f"{record_id}.json"
                    )

                    self.assertTrue(task_path.exists())
                    self.assertTrue(history_path.exists())

                    task = json.loads(
                        task_path.read_text(encoding="utf-8")
                    )
                    self.assertEqual(task["entity"]["id"], page_id)
                    self.assertEqual(
                        task["parent"]["data_source_id"],
                        data_source_id,
                    )

                    event_file = event_dir / f"{record_id}.json"
                    self.assertTrue(event_file.exists())

                    task_path.unlink(missing_ok=True)
                    history_path.unlink(missing_ok=True)
                    event_file.unlink(missing_ok=True)

            finally:
                server.server_close()
                runtime.stop()
                runtime_thread.join(timeout=5)
                server_thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
