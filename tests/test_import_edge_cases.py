"""Focused regressions for source ambiguities at the raw-import boundary."""
import json
import sqlite3
import sys
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from audit_chat_export_archive import audit_archive
from resumable_chat_import import import_export


class ImportEdgeCaseTests(unittest.TestCase):
    def test_duplicate_json_object_keys_fail_closed_before_staging_lossy_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "conversations.json"
            # Standard JSON decoders commonly keep only the last value for a
            # repeated key. The importer must not silently stage that rewrite.
            source.write_text('[{"id":"original","id":"overwritten"}]', encoding="utf-8")
            out = root / "state"

            with self.assertRaisesRegex(ValueError, "Duplicate JSON object key"):
                import_export(source, out, "DUPLICATE-JSON-KEYS", batch_size=1)

            conn = sqlite3.connect(out / "import.sqlite3")
            try:
                status, error = conn.execute(
                    "SELECT status,last_error FROM imports"
                ).fetchone()
                staged = conn.execute(
                    "SELECT COUNT(*) FROM raw_conversations"
                ).fetchone()[0]
                self.assertEqual(status, "FAILED")
                self.assertIn("Duplicate JSON object key", error)
                self.assertEqual(staged, 0)
            finally:
                conn.close()

    def test_directory_named_conversations_json_is_not_an_import_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "export.zip"
            payload = json.dumps([{"id": "valid-conversation"}])
            with zipfile.ZipFile(source, "w") as archive:
                archive.writestr("conversations.json/", "")
                archive.writestr("nested/conversations.json", payload)

            inventory = audit_archive(source)
            self.assertEqual(inventory["status"], "PASS")
            self.assertEqual(inventory["conversations_json_candidate_count"], 1)
            self.assertEqual(inventory["conversations_json_candidates"],
                             ["nested/conversations.json"])

            imported = import_export(source, root / "state", "DIRECTORY-CANDIDATE", batch_size=1)
            self.assertEqual(imported["status"], "RAW_COMPLETE")
            self.assertEqual(imported["committed_conversations"], 1)

    def test_duplicate_conversations_member_path_is_rejected_by_importer_and_flagged_by_audit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "duplicate-members.zip"
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                with zipfile.ZipFile(source, "w") as archive:
                    archive.writestr("nested/conversations.json", '[{"id":"first"}]')
                    archive.writestr("nested/conversations.json", '[{"id":"second"}]')

            inventory = audit_archive(source)
            self.assertEqual(inventory["status"], "REVIEW_REQUIRED")
            self.assertIn("DUPLICATE_MEMBER_PATHS", inventory["review_reasons"])
            self.assertEqual(inventory["conversations_json_candidate_count"], 2)

            with self.assertRaisesRegex(ValueError, "Expected exactly one conversations.json"):
                import_export(source, root / "state", "DUPLICATE-ZIP-MEMBER", batch_size=1)

            conn = sqlite3.connect(root / "state" / "import.sqlite3")
            try:
                status, staged = conn.execute(
                    "SELECT status, (SELECT COUNT(*) FROM raw_conversations) FROM imports"
                ).fetchone()
                self.assertEqual(status, "FAILED")
                self.assertEqual(staged, 0)
            finally:
                conn.close()


if __name__ == "__main__":
    unittest.main()
