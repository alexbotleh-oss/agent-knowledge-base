import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import preflight_chat_export as preflight_module
from preflight_chat_export import preflight_chat_export


class PreflightChatExportTests(unittest.TestCase):
    def make_zip(self, path, members):
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as archive:
            for name, data in members:
                archive.writestr(name, data)

    def test_valid_inventory_still_requires_attachment_semantic_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "export.zip"
            self.make_zip(source, [
                ("account/conversations.json", json.dumps([{"id": "c1"}]).encode("utf-8")),
                ("files/opaque.bin", b"bytes"),
            ])
            original = source.read_bytes()

            result = preflight_chat_export(source)

            self.assertEqual(result["status"], "REVIEW_REQUIRED")
            self.assertIn("ATTACHMENT_REFERENCE_DETECTION_REMAINS_HEURISTIC",
                          result["review_reasons"])
            self.assertTrue(result["source_hashes_match"])
            self.assertEqual(result["inventory_status"], "PASS")
            self.assertEqual(result["attachment_reference_status"],
                             "SCAN_COMPLETE_REVIEW_REQUIRED")
            self.assertFalse(result["raw_source_modified"])
            self.assertEqual(source.read_bytes(), original)

    def test_unsafe_member_path_propagates_review_requirement(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "unsafe.zip"
            self.make_zip(source, [
                ("account/conversations.json", b"[]"),
                ("../outside.txt", b"not extracted"),
            ])

            result = preflight_chat_export(source)

            self.assertEqual(result["status"], "REVIEW_REQUIRED")
            self.assertEqual(result["inventory_status"], "REVIEW_REQUIRED")
            self.assertIn("ARCHIVE_INVENTORY_REQUIRES_REVIEW",
                          result["review_reasons"])

    def test_inventory_crc_failure_fails_combined_preflight(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "good.zip"
            self.make_zip(source, [
                ("account/conversations.json", b"[]"),
                ("files/payload.bin", b"PAYLOAD_FOR_CRC_FAILURE"),
            ])
            raw = source.read_bytes()
            pos = raw.index(b"PAYLOAD_FOR_CRC_FAILURE")
            damaged = bytearray(raw)
            damaged[pos] ^= 1
            source.write_bytes(damaged)

            result = preflight_chat_export(source)

            self.assertEqual(result["status"], "FAIL")
            self.assertEqual(result["reason"], "SUBAUDIT_FAILED")
            self.assertEqual(result["inventory"]["reason"], "MEMBER_CRC_ERROR")
            self.assertFalse(result["raw_source_modified"])

    def test_hash_disagreement_between_subaudits_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "export.zip"
            source.write_bytes(b"placeholder")
            with patch.object(preflight_module, "audit_archive", return_value={
                "status": "PASS", "source_sha256": "a" * 64
            }), patch.object(preflight_module, "audit_references", return_value={
                "status": "SCAN_COMPLETE_REVIEW_REQUIRED", "source_sha256": "b" * 64
            }):
                result = preflight_chat_export(source)

            self.assertEqual(result["status"], "FAIL")
            self.assertEqual(result["reason"], "SOURCE_DIGEST_MISMATCH_BETWEEN_AUDITS")
            self.assertFalse(result["raw_source_modified"])

    def test_missing_source_fails_combined_preflight(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "missing.zip"

            result = preflight_chat_export(source)

            self.assertEqual(result["status"], "FAIL")
            self.assertEqual(result["reason"], "SUBAUDIT_FAILED")
            self.assertEqual(result["inventory"]["reason"], "SOURCE_FILE_NOT_FOUND")
            self.assertEqual(result["attachment_references"]["reason"], "SOURCE_FILE_NOT_FOUND")


if __name__ == "__main__":
    unittest.main()
