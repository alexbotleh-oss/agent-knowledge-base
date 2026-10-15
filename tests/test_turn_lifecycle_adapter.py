import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from http.server import ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import turn_lifecycle_adapter as adapter


class TurnLifecycleAdapterTests(unittest.TestCase):
    TOKEN = "test-secret-token-that-is-long-enough-123456789"
    ORIGIN = "chrome-extension://unit-test"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ledger = Path(self.tmp.name) / "events.jsonl"
        self.server = ThreadingHTTPServer(
            ("127.0.0.1", 0),
            adapter.make_handler(self.ledger, self.TOKEN, {self.ORIGIN}),
        )
        self.server.daemon_threads = True
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.tmp.cleanup()

    def request(self, method, path, payload=None, token=TOKEN, origin=None):
        data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if data is not None:
            headers["Content-Type"] = "application/json"
        if origin:
            headers["Origin"] = origin
        req = urllib.request.Request(self.base + path, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=3) as response:
                raw = response.read()
                return response.status, response.headers, json.loads(raw) if raw else None
        except urllib.error.HTTPError as exc:
            raw = exc.read()
            return exc.code, exc.headers, json.loads(raw) if raw else None

    def receive(self, turn_id="turn-1"):
        return self.request("POST", "/v1/turns", {
            "turn_id": turn_id,
            "task_id": "TASK-AGMS-1",
            "user_text": "продолжай дальше",
            "previous_checkpoint": "CKPT-001",
        })

    def test_exact_message_is_durably_registered_before_work(self):
        status, _, result = self.receive()
        self.assertEqual(status, 201)
        self.assertEqual(result["status"], "APPENDED")
        status, _, turn = self.request("GET", "/v1/turns/turn-1")
        self.assertEqual(status, 200)
        self.assertEqual(turn["exact_user_text"], "продолжай дальше")
        self.assertEqual(turn["previous_checkpoint"], "CKPT-001")
        self.assertEqual(turn["state"], "AWAITING_START")

    def test_duplicate_receipt_is_idempotent(self):
        self.receive()
        status, _, result = self.receive()
        self.assertEqual(status, 200)
        self.assertEqual(result["status"], "ALREADY_REGISTERED")

    def test_progress_and_prepared_report_remain_incomplete_until_ack(self):
        self.receive()
        status, _, _ = self.request("POST", "/v1/turns/turn-1/events", {"event_type": "WORK_STARTED"})
        self.assertEqual(status, 201)
        self.request("POST", "/v1/turns/turn-1/events", {
            "event_type": "PROGRESS", "detail": "Проверен файл A"
        })
        self.request("POST", "/v1/turns/turn-1/events", {
            "event_type": "REPORT_PREPARED", "report": {"path": "report.md", "sha256": "abc"}
        })
        status, _, result = self.request("GET", "/v1/turns?incomplete=true")
        self.assertEqual(status, 200)
        self.assertEqual(result["incomplete_turn_ids"], ["turn-1"])
        self.assertEqual(result["turns"][0]["state"], "REPORT_PREPARED_UNCONFIRMED")
        self.assertEqual(result["turns"][0]["progress"], ["Проверен файл A"])

    def test_delivery_acknowledgement_closes_turn(self):
        self.receive()
        self.request("POST", "/v1/turns/turn-1/events", {"event_type": "WORK_STARTED"})
        self.request("POST", "/v1/turns/turn-1/events", {
            "event_type": "RESPONSE_SUBMITTED", "submission": {"reference": "host-submission-1"}
        })
        status, _, result = self.request("POST", "/v1/turns/turn-1/events", {
            "event_type": "DELIVERY_ACKNOWLEDGED", "delivery": {"reference": "host-ack-1"}
        })
        self.assertEqual(status, 201)
        self.assertEqual(result["event"]["event_type"], "DELIVERY_ACKNOWLEDGED")
        status, _, inspection = self.request("GET", "/v1/turns?incomplete=true")
        self.assertEqual(status, 200)
        self.assertEqual(inspection["incomplete_turn_ids"], [])

    def test_authentication_required(self):
        status, _, body = self.request("GET", "/v1/turns", token=None)
        self.assertEqual(status, 401)
        self.assertEqual(body["error"], "unauthorized")

    def test_bad_origin_rejected_and_allowlisted_origin_echoed(self):
        self.receive()
        status, _, body = self.request("POST", "/v1/turns/turn-1/events",
                                       {"event_type": "WORK_STARTED"}, origin="https://evil.example")
        self.assertEqual(status, 403)
        status, headers, _ = self.request("GET", "/v1/turns", origin=self.ORIGIN)
        self.assertEqual(status, 200)
        self.assertEqual(headers.get("Access-Control-Allow-Origin"), self.ORIGIN)

    def test_invalid_turn_and_unknown_event_rejected(self):
        status, _, body = self.request("POST", "/v1/turns", {
            "turn_id": "turn-x", "task_id": "TASK", "user_text": "hello", "extra": "not allowed"
        })
        self.assertEqual(status, 400)
        self.assertIn("unsupported fields", body["error"])
        status, _, body = self.request("POST", "/v1/turns/turn-x/events", {"event_type": "INVENTED"})
        self.assertEqual(status, 400)
        self.assertIn("unsupported event_type", body["error"])

    def test_event_for_unknown_turn_fails_closed(self):
        status, _, body = self.request("POST", "/v1/turns/missing/events", {"event_type": "WORK_STARTED"})
        self.assertEqual(status, 400)
        self.assertIn("unknown turn_id", body["error"])


if __name__ == "__main__":
    unittest.main()
