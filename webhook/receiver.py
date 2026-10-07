import hashlib
import hmac
import json
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from uuid import uuid4

from core.json_store import JSONStore
from event_bus import Event
from event_runtime import EventRuntime


PROJECT_ROOT = Path(__file__).resolve().parent.parent
EVENT_DIR = PROJECT_ROOT / "data" / "webhook_events"
CREDENTIALS_FILE = PROJECT_ROOT / "data" / "webhook_credentials.json"
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

    def _load_verification_token(self):
        try:
            credentials = JSONStore(base_dir=PROJECT_ROOT).load(CREDENTIALS_FILE)
        except (FileNotFoundError, json.JSONDecodeError):
            return None

        return credentials.get("verification_token")

    def _save_verification_token(self, verification_token):
        JSONStore(base_dir=PROJECT_ROOT).save(
            CREDENTIALS_FILE,
            {
                "verification_token": verification_token,
                "saved_at": datetime.now(timezone.utc).isoformat(),
            },
        )

    def _verify_signature(self, raw_body, verification_token):
        signature = self.headers.get("X-Notion-Signature")

        if not signature or not signature.startswith("sha256="):
            return False

        digest = hmac.new(
            verification_token.encode("utf-8"),
            raw_body,
            hashlib.sha256,
        ).hexdigest()

        expected_signature = f"sha256={digest}"
        return hmac.compare_digest(expected_signature, signature)

    def do_POST(self):
        content_length = self.headers.get("Content-Length")

        if content_length is None:
            self._send_json(
                411,
                {"status": "error", "message": "Content-Length required"},
            )
            return

        try:
            length = int(content_length)
            raw_body = self.rfile.read(length)
            payload = json.loads(raw_body.decode("utf-8"))
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
            self._send_json(
                400,
                {"status": "error", "message": "Invalid JSON"},
            )
            return

        verification_token = payload.get("verification_token")

        if verification_token:
            try:
                self._save_verification_token(verification_token)
            except Exception:
                self._send_json(
                    500,
                    {
                        "status": "error",
                        "message": "Verification token persistence failed",
                    },
                )
                return

            self._send_json(
                200,
                {"status": "ok", "message": "Verification token received"},
            )
            return

        stored_token = self._load_verification_token()

        if not stored_token:
            self._send_json(
                503,
                {
                    "status": "error",
                    "message": "Webhook verification is not configured",
                },
            )
            return

        if not self._verify_signature(raw_body, stored_token):
            self._send_json(
                401,
                {"status": "error", "message": "Invalid webhook signature"},
            )
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

        relative_event_path = event_path.relative_to(PROJECT_ROOT)

        self.server.event_runtime.publish_from_receiver(
            Event(
                "WEBHOOK_RECEIVED",
                {
                    "record_id": record_id,
                    "file_path": str(relative_event_path),
                    "event_id": event_id,
                },
            )
        )

        self._send_json(
            200,
            {
                "status": "ok",
                "record_id": record_id,
                "event_id": event_id,
            },
        )

    def do_GET(self):
        self._send_json(
            200,
            {"status": "ok", "service": "notion_webhook_receiver"},
        )

    def log_message(self, format, *args):
        print(f"[WebhookReceiver] {self.address_string()} - {format % args}")


def create_server(event_runtime: EventRuntime):
    server = HTTPServer((HOST, PORT), WebhookHandler)
    server.event_runtime = event_runtime
    return server


def main():
    event_runtime = EventRuntime()
    server = create_server(event_runtime)
    server_thread = threading.Thread(
        target=server.serve_forever,
        name="WebhookHTTPServer",
        daemon=True,
    )
    server_thread.start()

    print("=" * 60)
    print("Notion Webhook Receiver")
    print(f"Listening: http://{HOST}:{PORT}")
    print(f"Event directory: {EVENT_DIR}")
    print(f"Credential file: {CREDENTIALS_FILE}")
    print("=" * 60)

    try:
        event_runtime.start()
    except KeyboardInterrupt:
        print("\nStopping Webhook Receiver...")
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
