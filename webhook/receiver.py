import hashlib
import hmac
import json
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from uuid import uuid4

from core.json_store import JSONStore
from core.logger import error, info
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
        info(f"[WebhookReceiver] RESPONSE status={status_code} body_status={body.get('status', '-')}")

    def _load_verification_token(self):
        try:
            credentials = JSONStore(base_dir=PROJECT_ROOT).load(CREDENTIALS_FILE)
        except (FileNotFoundError, json.JSONDecodeError):
            return None
        return credentials.get("verification_token")

    def _save_verification_token(self, verification_token):
        JSONStore(base_dir=PROJECT_ROOT).save(CREDENTIALS_FILE, {"verification_token": verification_token, "saved_at": datetime.now(timezone.utc).isoformat()})
        info("[WebhookReceiver] VERIFICATION_TOKEN_SAVED")

    def _verify_signature(self, raw_body, verification_token):
        signature = self.headers.get("X-Notion-Signature")
        if not signature or not signature.startswith("sha256="):
            return False
        digest = hmac.new(verification_token.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
        expected_signature = f"sha256={digest}"
        return hmac.compare_digest(expected_signature, signature)

    def do_POST(self):
        info(f"[WebhookReceiver] POST_START client={self.address_string()}")
        content_length = self.headers.get("Content-Length")
        if content_length is None:
            self._send_json(411, {"status": "error", "message": "Content-Length required"})
            return
        try:
            length = int(content_length)
            raw_body = self.rfile.read(length)
            payload = json.loads(raw_body.decode("utf-8"))
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            error(f"[WebhookReceiver] INVALID_JSON error={type(exc).__name__}: {exc}")
            self._send_json(400, {"status": "error", "message": "Invalid JSON"})
            return

        verification_token = payload.get("verification_token")
        if verification_token:
            try:
                self._save_verification_token(verification_token)
            except Exception as exc:
                error(f"[WebhookReceiver] TOKEN_SAVE_FAILED error={type(exc).__name__}: {exc}")
                self._send_json(500, {"status": "error", "message": "Verification token persistence failed"})
                return
            self._send_json(200, {"status": "ok", "message": "Verification token received"})
            return

        stored_token = self._load_verification_token()
        if not stored_token:
            error("[WebhookReceiver] VERIFICATION_NOT_CONFIGURED")
            self._send_json(503, {"status": "error", "message": "Webhook verification is not configured"})
            return

        if not self._verify_signature(raw_body, stored_token):
            error("[WebhookReceiver] SIGNATURE_INVALID")
            self._send_json(401, {"status": "error", "message": "Invalid webhook signature"})
            return

        record_id = str(uuid4())
        received_at = datetime.now(timezone.utc).isoformat()
        event_id = payload.get("id")
        event_type = payload.get("type")
        info(f"[WebhookReceiver] VERIFIED record_id={record_id} event_id={event_id} event_type={event_type}")

        record = {"record_id": record_id, "event_id": event_id, "received_at": received_at, "source": "notion_webhook", "event_type": event_type, "attempt_number": payload.get("attempt_number"), "payload": payload}
        event_path = EVENT_DIR / f"{record_id}.json"

        try:
            JSONStore(base_dir=PROJECT_ROOT).save(event_path, record)
        except Exception as exc:
            error(f"[WebhookReceiver] EVENT_SAVE_FAILED record_id={record_id} error={type(exc).__name__}: {exc}")
            self._send_json(500, {"status": "error", "message": "Event persistence failed"})
            return

        info(f"[WebhookReceiver] EVENT_SAVED record_id={record_id} path={event_path}")
        relative_event_path = event_path.relative_to(PROJECT_ROOT)
        event = Event("WEBHOOK_RECEIVED", {"record_id": record_id, "file_path": str(relative_event_path), "event_id": event_id})
        info(f"[WebhookReceiver] PUBLISH record_id={record_id} event_type=WEBHOOK_RECEIVED event_id={event.event_id}")
        self.server.event_runtime.publish_from_receiver(event)
        self._send_json(200, {"status": "ok", "record_id": record_id, "event_id": event_id})

    def do_GET(self):
        info(f"[WebhookReceiver] GET client={self.address_string()}")
        self._send_json(200, {"status": "ok", "service": "notion_webhook_receiver"})

    def log_message(self, format, *args):
        info(f"[WebhookReceiver] HTTP {self.address_string()} - {format % args}")


def create_server(event_runtime: EventRuntime):
    server = HTTPServer((HOST, PORT), WebhookHandler)
    server.event_runtime = event_runtime
    info(f"[WebhookReceiver] SERVER_CREATED host={HOST} port={PORT}")
    return server


def main():
    info("[WebhookReceiver] START")
    event_runtime = EventRuntime()
    server = create_server(event_runtime)
    server_thread = threading.Thread(target=server.serve_forever, name="WebhookHTTPServer", daemon=True)
    server_thread.start()
    info(f"[WebhookReceiver] SERVER_THREAD_STARTED host={HOST} port={PORT}")
    try:
        event_runtime.start()
    except KeyboardInterrupt:
        info("[WebhookReceiver] KEYBOARD_INTERRUPT")
    finally:
        info("[WebhookReceiver] SHUTDOWN")
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
