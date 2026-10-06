import json
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from uuid import uuid4

from core.json_store import JSONStore


PROJECT_ROOT = Path(__file__).resolve().parent.parent
EVENT_DIR = PROJECT_ROOT / "data" / "webhook_events"
HOST = "127.0.0.1"
PORT = 8080


class WebhookHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _send_json(self, status_code, body):
        payload = json.dumps(body, ensure_ascii=False).encode("utf-8")

        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self):
        content_length = self.headers.get("Content-Length")

        if content_length is None:
            self._send_json(411, {"status": "error", "message": "Content-Length required"})
            return

        try:
            length = int(content_length)
            raw_body = self.rfile.read(length)
            payload = json.loads(raw_body.decode("utf-8"))
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
            self._send_json(400, {"status": "error", "message": "Invalid JSON"})
            return

        record_id = str(uuid4())
        received_at = datetime.now(timezone.utc).isoformat()

        event_id = payload.get("id")
        event_type = payload.get("type")

        record = {
            "record_id": record_id,
            "event_id": event_id,
            "received_at": received_at,
            "source": "notion_webhook",
            "event_type": event_type,
            "attempt_number": payload.get("attempt_number"),
            "payload": payload,
        }

        event_path = EVENT_DIR / f"{record_id}.json"

        try:
            JSONStore(base_dir=PROJECT_ROOT).save(event_path, record)
        except Exception:
            self._send_json(
                500,
                {"status": "error", "message": "Event persistence failed"},
            )
            return

        self._send_json(
            200,
            {
                "status": "ok",
                "record_id": record_id,
                "event_id": event_id,
            },
        )

    def do_GET(self):
        self._send_json(200, {"status": "ok", "service": "notion_webhook_receiver"})

    def log_message(self, format, *args):
        print(f"[WebhookReceiver] {self.address_string()} - {format % args}")


def create_server():
    return ThreadingHTTPServer((HOST, PORT), WebhookHandler)


def main():
    server = create_server()

    print("=" * 60)
    print("Notion Webhook Receiver")
    print(f"Listening: http://{HOST}:{PORT}")
    print(f"Event directory: {EVENT_DIR}")
    print("=" * 60)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Webhook Receiver...")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
