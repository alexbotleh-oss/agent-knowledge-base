import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from archive_temporal_index import load_archive


class ArchiveTemporalIndexTests(unittest.TestCase):
    def test_zip_selection_uses_exact_basename(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "sample.zip"
            with zipfile.ZipFile(source, "w") as archive:
                archive.writestr(
                    "backup_conversations.json",
                    json.dumps([{"id": "wrong", "mapping": {}}]),
                )
                archive.writestr(
                    "nested/conversations.json",
                    json.dumps([{"id": "expected", "mapping": {}}]),
                )

            conversations, messages = load_archive(str(source))
            self.assertEqual([item["conversation_id"] for item in conversations], ["expected"])
            self.assertEqual(messages, [])

    def test_zip_with_multiple_exact_conversations_members_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "ambiguous.zip"
            payload = json.dumps([{"id": "conversation", "mapping": {}}])
            with zipfile.ZipFile(source, "w") as archive:
                archive.writestr("one/conversations.json", payload)
                archive.writestr("two/conversations.json", payload)

            with self.assertRaisesRegex(ValueError, "Expected exactly one conversations.json in ZIP; found 2"):
                load_archive(str(source))

    def test_zip_without_exact_conversations_member_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "wrong-name.zip"
            with zipfile.ZipFile(source, "w") as archive:
                archive.writestr(
                    "backup_conversations.json",
                    json.dumps([{"id": "wrong", "mapping": {}}]),
                )

            with self.assertRaisesRegex(ValueError, "found 0"):
                load_archive(str(source))


if __name__ == "__main__":
    unittest.main()
