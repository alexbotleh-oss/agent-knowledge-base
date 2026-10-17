import hashlib
import json
import sys
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from audit_chat_export_archive import audit_archive


class AuditChatExportArchiveTests(unittest.TestCase):
    def make_zip(self, path, members):
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as archive:
            for name, data in members:
                archive.writestr(name, data)

    def test_valid_zip_inventory_is_read_only_and_hash_bound(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "export.zip"
            conversation_bytes = json.dumps([{"id": "c1"}]).encode("utf-8")
            attachment_bytes = b"opaque-attachment"
            self.make_zip(source, [
                ("account/conversations.json", conversation_bytes),
                ("files/attachment.bin", attachment_bytes),
                ("nested/archive.zip", b"not actually inspected as a nested archive"),
            ])
            original = source.read_bytes()
            expected_hash = hashlib.sha256(original).hexdigest()

            result = audit_archive(source)

            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["source_sha256"], expected_hash)
            self.assertEqual(result["source_bytes"], len(original))
            self.assertEqual(result["conversations_json_candidate_count"], 1)
            self.assertEqual(result["member_count"], 3)
            self.assertEqual(result["nested_archive_name_hints"], ["nested/archive.zip"])
            self.assertTrue(result["read_only"])
            self.assertEqual(source.read_bytes(), original)
            attachment = next(item for item in result["members"] if item["path"] == "files/attachment.bin")
            self.assertEqual(attachment["uncompressed_bytes"], len(attachment_bytes))
            self.assertFalse(attachment["is_conversations_json_candidate"])

    def test_duplicate_member_path_requires_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "duplicate.zip"
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                self.make_zip(source, [
                    ("account/conversations.json", b"[]"),
                    ("files/a.bin", b"first"),
                    ("files/a.bin", b"second"),
                ])

            result = audit_archive(source)

            self.assertEqual(result["status"], "REVIEW_REQUIRED")
            self.assertIn("files/a.bin", result["duplicate_member_paths"])
            self.assertIn("DUPLICATE_MEMBER_PATHS", result["review_reasons"])

    def test_missing_conversations_json_is_review_not_native_export_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "evidence-only.zip"
            self.make_zip(source, [("README.md", b"partial evidence")])

            result = audit_archive(source)

            self.assertEqual(result["status"], "REVIEW_REQUIRED")
            self.assertEqual(result["conversations_json_candidate_count"], 0)
            self.assertIn("EXPECTED_EXACTLY_ONE_CONVERSATIONS_JSON", result["review_reasons"])

    def test_crc_error_is_reported_as_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "good.zip"
            self.make_zip(source, [
                ("account/conversations.json", b"[]"),
                ("files/payload.bin", b"ATTACHMENT_BYTES_FOR_CRC_TEST"),
            ])
            raw = source.read_bytes()
            needle = b"ATTACHMENT_BYTES_FOR_CRC_TEST"
            index = raw.index(needle)
            mutated = bytearray(raw)
            mutated[index] = ord("X")
            broken = root / "crc-broken.zip"
            broken.write_bytes(mutated)

            result = audit_archive(broken)

            self.assertEqual(result["status"], "FAIL")
            self.assertEqual(result["reason"], "MEMBER_CRC_ERROR")
            self.assertEqual(result["crc_error_member"], "files/payload.bin")

    def test_non_zip_input_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "not-a-zip.bin"
            source.write_bytes(b"not a zip")

            result = audit_archive(source)

            self.assertEqual(result["status"], "FAIL")
            self.assertEqual(result["reason"], "SOURCE_IS_NOT_A_VALID_ZIP")

    def test_missing_source_is_reported_without_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "missing.zip"

            result = audit_archive(source)

            self.assertEqual(result["status"], "FAIL")
            self.assertEqual(result["reason"], "SOURCE_FILE_NOT_FOUND")


if __name__ == "__main__":
    unittest.main()
