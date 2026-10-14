import json
import sqlite3
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from resumable_chat_import import _commit_batch, connect, import_export, iter_json_array


def sample_conversations(count=5):
    rows = []
    for i in range(count):
        rows.append({
            "id": f"conversation-{i}",
            "title": f"Conversation {i}",
            "create_time": 1700000000 + i,
            "mapping": {
                f"node-{i}-user": {
                    "id": f"node-{i}-user",
                    "parent": None,
                    "children": [f"node-{i}-assistant"],
                    "message": {
                        "id": f"message-{i}-user",
                        "create_time": 1700000000 + i,
                        "author": {"role": "user"},
                        "content": {"content_type": "text", "parts": [f"question {i}"]},
                    },
                },
                f"node-{i}-assistant": {
                    "id": f"node-{i}-assistant",
                    "parent": f"node-{i}-user",
                    "children": [],
                    "message": {
                        "id": f"message-{i}-assistant",
                        "create_time": 1700000001 + i,
                        "author": {"role": "assistant"},
                        "content": {"content_type": "text", "parts": [f"answer {i}"]},
                    },
                },
            },
        })
    return rows


class ResumableChatImportTests(unittest.TestCase):
    def make_source(self, folder, count=5):
        source = folder / "conversations.json"
        source.write_text(json.dumps(sample_conversations(count), ensure_ascii=False), encoding="utf-8")
        return source

    def query_counts(self, out):
        conn = sqlite3.connect(out / "import.sqlite3")
        try:
            records = conn.execute("SELECT COUNT(*), COUNT(DISTINCT source_locator) FROM raw_conversations").fetchone()
            events = conn.execute("SELECT event_type FROM import_events ORDER BY event_id").fetchall()
            payloads = conn.execute("SELECT payload_json FROM raw_conversations ORDER BY source_ordinal").fetchall()
            state = conn.execute("SELECT status,next_ordinal,committed_conversations FROM imports").fetchone()
            return records, [row[0] for row in events], [json.loads(row[0]) for row in payloads], state
        finally:
            conn.close()

    def test_interrupt_and_resume_keeps_all_conversations(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self.make_source(root, 5)
            out = root / "state"
            paused = import_export(source, out, "ARCHIVE-001", batch_size=2, stop_after_batches=1)
            self.assertEqual(paused["status"], "PAUSED")
            self.assertEqual(paused["next_ordinal"], 2)
            done = import_export(source, out, "ARCHIVE-001", batch_size=2)
            self.assertEqual(done["status"], "RAW_COMPLETE")
            self.assertEqual(done["committed_conversations"], 5)
            counts, events, payloads, state = self.query_counts(out)
            self.assertEqual(counts, (5, 5))
            self.assertIn("PAUSED_FOR_TEST", events)
            self.assertEqual([p["id"] for p in payloads], [f"conversation-{i}" for i in range(5)])
            self.assertEqual(state, ("RAW_COMPLETE", 5, 5))

    def test_rerun_is_idempotent_and_preserves_original_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self.make_source(root, 3)
            original = source.read_bytes()
            out = root / "state"
            first = import_export(source, out, "ARCHIVE-002", batch_size=2)
            second = import_export(source, out, "ARCHIVE-002", batch_size=2)
            self.assertEqual(first["source_sha256"], second["source_sha256"])
            self.assertEqual(second["committed_conversations"], 3)
            self.assertEqual(source.read_bytes(), original)
            self.assertEqual(Path(second["snapshot_path"]).read_bytes(), original)
            counts, _, _, _ = self.query_counts(out)
            self.assertEqual(counts, (3, 3))

    def test_zip_input_is_supported_and_nested_message_structure_is_not_summarized(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "export.zip"
            payload = sample_conversations(2)
            with zipfile.ZipFile(source, "w") as archive:
                archive.writestr("account/conversations.json", json.dumps(payload, ensure_ascii=False))
            result = import_export(source, root / "state", "ARCHIVE-003", batch_size=1)
            self.assertEqual(result["status"], "RAW_COMPLETE")
            _, _, staged, _ = self.query_counts(root / "state")
            self.assertEqual(staged[0]["mapping"]["node-0-user"]["message"]["content"]["parts"], ["question 0"])
            self.assertEqual(staged[0]["mapping"]["node-0-user"]["children"], ["node-0-assistant"])

    def test_replayed_committed_batch_models_lost_ack_without_duplicate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self.make_source(root, 2)
            out = root / "state"
            paused = import_export(source, out, "ARCHIVE-005", batch_size=1, stop_after_batches=1)
            conn = connect(out / "import.sqlite3")
            try:
                record = conn.execute(
                    "SELECT archive_id,source_sha256,source_locator,source_conversation_id,identity_method,source_ordinal,payload_json,payload_sha256,imported_at FROM raw_conversations ORDER BY source_ordinal LIMIT 1"
                ).fetchone()
                _commit_batch(conn, "ARCHIVE-005", paused["source_sha256"], [record])
                count = conn.execute(
                    "SELECT COUNT(*) FROM raw_conversations WHERE archive_id=? AND source_sha256=?",
                    ("ARCHIVE-005", paused["source_sha256"]),
                ).fetchone()[0]
                self.assertEqual(count, 1)
                cursor = conn.execute(
                    "SELECT next_ordinal FROM imports WHERE archive_id=? AND source_sha256=?",
                    ("ARCHIVE-005", paused["source_sha256"]),
                ).fetchone()[0]
                self.assertEqual(cursor, 1)
            finally:
                conn.close()
            resumed = import_export(source, out, "ARCHIVE-005", batch_size=1)
            self.assertEqual(resumed["status"], "RAW_COMPLETE")
            self.assertEqual(resumed["committed_conversations"], 2)

    def test_duplicate_source_conversation_ids_are_not_silently_dropped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "conversations.json"
            rows = sample_conversations(2)
            rows[1]["id"] = rows[0]["id"]
            source.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
            with self.assertRaises(RuntimeError):
                import_export(source, root / "state", "ARCHIVE-006", batch_size=1)
            conn = sqlite3.connect(root / "state" / "import.sqlite3")
            try:
                state = conn.execute("SELECT status FROM imports").fetchone()[0]
                count = conn.execute("SELECT COUNT(*) FROM raw_conversations").fetchone()[0]
                self.assertEqual(state, "FAILED")
                self.assertEqual(count, 1)
            finally:
                conn.close()

    def test_incremental_decoder_handles_small_chunks_and_unicode(self):
        import io
        rows = [{"id": "один", "title": "Привет 🌍"}, {"id": "two", "title": "second"}]
        stream = io.BytesIO(json.dumps(rows, ensure_ascii=False).encode("utf-8"))
        parsed = list(iter_json_array(stream, chunk_size=5))
        self.assertEqual([ordinal for ordinal, _ in parsed], [0, 1])
        self.assertEqual(parsed[0][1]["title"], "Привет 🌍")

    def test_invalid_source_is_not_marked_complete(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "bad.json"
            source.write_text('{"not":"an array"}', encoding="utf-8")
            with self.assertRaises(ValueError):
                import_export(source, root / "state", "ARCHIVE-004", batch_size=2)
            conn = sqlite3.connect(root / "state" / "import.sqlite3")
            try:
                state = conn.execute("SELECT status,last_error FROM imports").fetchone()
                self.assertEqual(state[0], "FAILED")
                self.assertTrue(state[1])
            finally:
                conn.close()


if __name__ == "__main__":
    unittest.main()
