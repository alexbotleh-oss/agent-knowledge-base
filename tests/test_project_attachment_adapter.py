import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import project_attachment_adapter as adapter


class ProjectAttachmentAdapterTests(unittest.TestCase):
    TOKEN = "attachment-bridge-test-token-0123456789abcdef"
    ORIGIN = "chrome-extension://unit-test"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "library"
        self.root.mkdir()
        self.server = ThreadingHTTPServer(
            ("127.0.0.1", 0),
            adapter.make_handler(self.root, self.TOKEN, {self.ORIGIN}, {"AGENT_MEMORY_SYSTEM"}),
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

    def request(self, method, path, body=None, headers=None):
        req = urllib.request.Request(self.base + path, data=body, headers=headers or {}, method=method)
        try:
            with urllib.request.urlopen(req, timeout=3) as response:
                raw = response.read()
                return response.status, response.headers, json.loads(raw) if raw else None
        except urllib.error.HTTPError as exc:
            raw = exc.read()
            return exc.code, exc.headers, json.loads(raw) if raw else None

    def upload(self, *, token=TOKEN, origin=ORIGIN, project="AGENT_MEMORY_SYSTEM",
               conversation="CHAT-1", message="MSG-1", filename="report.txt", body=b"private upload bytes"):
        headers = {
            "Content-Type": "text/plain",
            "Content-Length": str(len(body)),
            "X-Rima-Project-ID": project,
            "X-Rima-Conversation-ID": conversation,
            "X-Rima-Source-Message-ID": message,
            "X-Rima-Filename": filename,
        }
        if token:
            headers["Authorization"] = "Bearer " + token
        if origin:
            headers["Origin"] = origin
        return self.request("POST", "/v1/attachments", body=body, headers=headers)

    def rows(self, path):
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]

    def test_auth_and_origin_are_required(self):
        status, _, body = self.upload(token=None)
        self.assertEqual(status, 401)
        self.assertEqual(body["error"], "unauthorized")
        status, _, body = self.upload(origin="https://evil.example")
        self.assertEqual(status, 403)
        self.assertEqual(body["error"], "origin_not_allowed")

    def test_upload_requires_explicit_project_and_source_provenance(self):
        status, _, body = self.request(
            "POST", "/v1/attachments", body=b"x",
            headers={"Authorization": "Bearer " + self.TOKEN, "Content-Length": "1",
                     "Content-Type": "text/plain", "Origin": self.ORIGIN},
        )
        self.assertEqual(status, 400)
        self.assertIn("X-Rima-Project-ID", body["error"])

    def test_attachment_is_stored_and_only_reference_metadata_is_returned(self):
        status, _, result = self.upload(filename="../../private report.txt")
        self.assertEqual(status, 201)
        attachment = result["attachment"]
        self.assertEqual(attachment["access_status"], "AVAILABLE")
        self.assertTrue(attachment["library_ref"].startswith("project-library://AGENT_MEMORY_SYSTEM/"))
        self.assertNotIn("storage_locator", attachment)
        serialized = json.dumps(result)
        self.assertNotIn("private upload bytes", serialized)
        obj = self.root / "objects" / "AGENT_MEMORY_SYSTEM" / attachment["sha256"][:2] / attachment["sha256"]
        self.assertEqual(obj.read_bytes(), b"private upload bytes")
        reference = self.rows(self.root / "references.jsonl")[0]
        self.assertEqual(reference["source_message_id"], "MSG-1")
        self.assertEqual(reference["original_name"], "private report.txt")

    def test_encoded_unicode_filename_is_preserved(self):
        status, _, result = self.upload(filename="%D0%BE%D1%82%D1%87%D0%B5%D1%82.txt")
        self.assertEqual(status, 201)
        self.assertEqual(result["attachment"]["original_name"], "отчет.txt")

    def test_exact_replay_is_idempotent_and_new_message_reuses_object(self):
        first_status, _, first = self.upload()
        replay_status, _, replay = self.upload()
        second_status, _, second = self.upload(message="MSG-2")
        self.assertEqual(first_status, 201)
        self.assertEqual(replay_status, 200)
        self.assertEqual(second_status, 201)
        self.assertEqual(first["attachment"]["attachment_id"], replay["attachment"]["attachment_id"])
        self.assertNotEqual(first["attachment"]["attachment_id"], second["attachment"]["attachment_id"])
        self.assertEqual(first["attachment"]["library_ref"], second["attachment"]["library_ref"])
        self.assertEqual(len(self.rows(self.root / "objects.jsonl")), 1)
        self.assertEqual(len(self.rows(self.root / "references.jsonl")), 2)

    def test_invalid_project_is_rejected_without_storing_object(self):
        status, _, body = self.upload(project="../escape")
        self.assertEqual(status, 403)
        self.assertEqual(body["error"], "project_not_allowed")
        self.assertFalse((self.root / "objects").exists())

    def test_empty_attachment_is_rejected(self):
        status, _, body = self.upload(body=b"")
        self.assertEqual(status, 400)
        self.assertEqual(body["error"], "empty_attachment")
        self.assertFalse((self.root / "objects").exists())

    def test_untrusted_origin_does_not_receive_cors_permission(self):
        status, headers, _ = self.request("OPTIONS", "/v1/attachments", headers={"Origin": "https://evil.example"})
        self.assertEqual(status, 403)
        self.assertIsNone(headers.get("Access-Control-Allow-Origin"))


if __name__ == "__main__":
    unittest.main()
