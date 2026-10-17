import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from resumable_chat_import import import_export
from verify_resumable_chat_import import verify_import


def sample_conversations(count=4):
    return [
        {
            "id": f"conversation-{i}",
            "title": f"Диалог {i}",
            "create_time": 1700000000 + i,
            "mapping": {
                f"node-{i}": {
                    "id": f"node-{i}",
                    "parent": None,
                    "children": [],
                    "message": {
                        "id": f"message-{i}",
                        "create_time": 1700000000 + i,
                        "author": {"role": "user"},
                        "content": {"content_type": "text", "parts": [f"текст {i} 🌍"]},
                    },
                }
            },
        }
        for i in range(count)
    ]


class VerifyResumableChatImportTests(unittest.TestCase):
    def make_source(self, root, count=4):
        source = root / "conversations.json"
        source.write_text(json.dumps(sample_conversations(count), ensure_ascii=False), encoding="utf-8")
        return source

    def test_complete_import_passes_full_source_readback(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self.make_source(root)
            out = root / "state"
            imported = import_export(source, out, "VERIFY-COMPLETE", batch_size=2)

            result = verify_import(out, "VERIFY-COMPLETE")
            self.assertEqual(result["verification"], "PASS")
            self.assertEqual(result["reason"], "COMPLETE_SOURCE_READBACK_MATCH")
            self.assertEqual(result["source_sha256"], imported["source_sha256"])
            self.assertEqual(result["source_conversations"], 4)
            self.assertEqual(result["staged_conversations"], 4)
            self.assertTrue(result["read_only"])

    def test_paused_import_is_partial_only_when_staged_prefix_matches(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self.make_source(root, 5)
            out = root / "state"
            import_export(source, out, "VERIFY-PAUSED", batch_size=2, stop_after_batches=1)

            result = verify_import(out, "VERIFY-PAUSED")
            self.assertEqual(result["verification"], "PARTIAL")
            self.assertEqual(result["source_conversations"], 5)
            self.assertEqual(result["staged_conversations"], 2)
            self.assertEqual(result["import_status"], "PAUSED")

    def test_corrupt_payload_is_detected_even_if_stored_hash_is_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self.make_source(root)
            out = root / "state"
            imported = import_export(source, out, "VERIFY-CORRUPT", batch_size=2)
            conn = sqlite3.connect(out / "import.sqlite3")
            try:
                conn.execute(
                    """UPDATE raw_conversations SET payload_json=?
                       WHERE archive_id=? AND source_sha256=? AND source_ordinal=1""",
                    ('{"id":"tampered"}', "VERIFY-CORRUPT", imported["source_sha256"]),
                )
                conn.commit()
            finally:
                conn.close()

            result = verify_import(out, "VERIFY-CORRUPT")
            self.assertEqual(result["verification"], "FAIL")
            self.assertEqual(result["reason"], "SOURCE_READBACK_MISMATCH")
            self.assertIn("payload_json", result["first_mismatches"][0]["fields"])

    def test_missing_row_cannot_pass_when_import_claims_complete(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self.make_source(root)
            out = root / "state"
            imported = import_export(source, out, "VERIFY-MISSING", batch_size=2)
            conn = sqlite3.connect(out / "import.sqlite3")
            try:
                conn.execute(
                    """DELETE FROM raw_conversations
                       WHERE archive_id=? AND source_sha256=? AND source_ordinal=2""",
                    ("VERIFY-MISSING", imported["source_sha256"]),
                )
                conn.commit()
            finally:
                conn.close()

            result = verify_import(out, "VERIFY-MISSING")
            self.assertEqual(result["verification"], "FAIL")
            self.assertEqual(result["reason"], "SOURCE_READBACK_MISMATCH")
            self.assertTrue(any(
                item.get("kind") == "MISSING_STAGED_ORDINAL" and item.get("source_ordinal") == 2
                for item in result["first_mismatches"]
            ))

    def test_changed_snapshot_is_detected_before_readback(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self.make_source(root)
            out = root / "state"
            imported = import_export(source, out, "VERIFY-SNAPSHOT", batch_size=2)
            snapshot = Path(imported["snapshot_path"])
            snapshot.write_bytes(snapshot.read_bytes() + b" ")

            result = verify_import(out, "VERIFY-SNAPSHOT")
            self.assertEqual(result["verification"], "FAIL")
            self.assertEqual(result["reason"], "SNAPSHOT_SIZE_MISMATCH")

    def test_multiple_snapshots_require_explicit_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self.make_source(root, 2)
            out = root / "state"
            first = import_export(source, out, "VERIFY-MULTI", batch_size=2)
            source.write_text(json.dumps(sample_conversations(3), ensure_ascii=False), encoding="utf-8")
            import_export(source, out, "VERIFY-MULTI", batch_size=2)

            ambiguous = verify_import(out, "VERIFY-MULTI")
            self.assertEqual(ambiguous["verification"], "FAIL")
            self.assertEqual(ambiguous["reason"], "SOURCE_SNAPSHOT_AMBIGUOUS")
            selected = verify_import(out, "VERIFY-MULTI", first["source_sha256"])
            self.assertEqual(selected["verification"], "PASS")

    def test_empty_export_is_a_valid_complete_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self.make_source(root, 0)
            out = root / "state"
            import_export(source, out, "VERIFY-EMPTY", batch_size=2)

            result = verify_import(out, "VERIFY-EMPTY")
            self.assertEqual(result["verification"], "PASS")
            self.assertEqual(result["source_conversations"], 0)
            self.assertEqual(result["staged_conversations"], 0)


if __name__ == "__main__":
    unittest.main()
