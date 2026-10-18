import json
import sys
import tempfile
import unittest
import warnings
import zipfile
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import audit_chat_attachment_references as attachment_audit_module
from audit_chat_attachment_references import audit_references


class AuditChatAttachmentReferencesTests(unittest.TestCase):
    def make_zip(self, path, conversation, other_members=()):
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as archive:
            archive.writestr("account/conversations.json", json.dumps([conversation], ensure_ascii=False))
            for name, data in other_members:
                archive.writestr(name, data)

    def test_exact_member_path_is_reported_without_semantic_overclaim(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "export.zip"
            conversation = {
                "id": "c1",
                "mapping": {"n1": {"message": {"content": {"parts": [
                    {"attachment_path": "files/photo.png"}
                ]}}}},
            }
            self.make_zip(source, conversation, [("files/photo.png", b"image bytes")])

            result = audit_references(source)

            self.assertEqual(result["status"], "SCAN_COMPLETE_REVIEW_REQUIRED")
            self.assertEqual(result["conversation_count_scanned"], 1)
            self.assertEqual(result["candidate_reference_count"], 1)
            self.assertEqual(result["exact_member_path_matches"], 1)
            self.assertEqual(result["references"][0]["match_status"], "EXACT_MEMBER_PATH_MATCH")
            self.assertFalse(result["raw_payloads_modified"])
            self.assertIn("not proof", result["interpretation_boundary"])

    def test_uri_like_reference_is_not_guessed_from_filename_or_identifier(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "export.zip"
            conversation = {
                "id": "c2",
                "mapping": {"n2": {"message": {"content": {"parts": [
                    {"file_reference": "file-service://file-123"}
                ]}}}},
            }
            self.make_zip(source, conversation, [("files/file-123.bin", b"bytes")])

            result = audit_references(source)

            self.assertEqual(result["candidate_reference_count"], 1)
            self.assertEqual(result["unresolved_candidates"], 1)
            self.assertEqual(result["references"][0]["match_status"], "UNRESOLVED")
            self.assertEqual(result["references"][0]["source_value"], "file-service://file-123")

    def test_duplicate_member_path_is_ambiguous_not_exact(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "duplicate.zip"
            conversation = {"id": "c3", "attachment_path": "files/photo.png"}
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                self.make_zip(source, conversation, [
                    ("files/photo.png", b"first"),
                    ("files/photo.png", b"second"),
                ])

            result = audit_references(source)

            self.assertEqual(result["ambiguous_duplicate_path_candidates"], 1)
            self.assertEqual(result["references"][0]["match_status"], "AMBIGUOUS_DUPLICATE_MEMBER_PATH")
            self.assertEqual(result["references"][0]["exact_member_match_count"], 2)

    def test_json_pointer_escapes_slashes_and_tildes(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "conversations.json"
            source.write_text(json.dumps([{"id": "c4", "file/path~id": "missing.bin"}]), encoding="utf-8")

            result = audit_references(source)

            self.assertEqual(result["source_format"], "JSON")
            self.assertEqual(result["references"][0]["json_pointer"], "/file~1path~0id")
            self.assertEqual(result["unresolved_candidates"], 1)

    def test_zip_without_conversations_json_fails_scan_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "evidence.zip"
            with zipfile.ZipFile(source, "w") as archive:
                archive.writestr("README.md", "partial evidence")

            result = audit_references(source)

            self.assertEqual(result["status"], "FAIL")
            self.assertEqual(result["reason"], "SOURCE_SCAN_FAILED")
            self.assertFalse(result["raw_payloads_modified"])

    def test_source_digest_change_during_scan_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "conversations.json"
            source.write_text('[{"id":"c1","title":"plain conversation"}]', encoding="utf-8")
            initial_digest = __import__("hashlib").sha256(source.read_bytes()).hexdigest()
            with patch.object(attachment_audit_module, "sha256_file",
                              side_effect=[initial_digest, "f" * 64]):
                result = audit_references(source)
            self.assertEqual(result["status"], "FAIL")
            self.assertEqual(result["reason"], "SOURCE_CHANGED_DURING_SCAN")
            self.assertFalse(result["raw_payloads_modified"])

    def test_unreadable_source_returns_structured_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "conversations.json"
            source.write_text('[{"id":"c1"}]', encoding="utf-8")
            with patch.object(attachment_audit_module, "sha256_file",
                              side_effect=PermissionError("denied")):
                result = audit_references(source)
            self.assertEqual(result["status"], "FAIL")
            self.assertEqual(result["reason"], "SOURCE_UNREADABLE")
            self.assertEqual(result["error_type"], "PermissionError")
            self.assertFalse(result["raw_payloads_modified"])

    def test_no_candidate_references_is_not_claimed_as_proof_of_no_attachments(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "conversations.json"
            source.write_text(json.dumps([{"id": "c5", "title": "plain conversation"}]), encoding="utf-8")

            result = audit_references(source)

            self.assertEqual(result["status"], "SCAN_COMPLETE_REVIEW_REQUIRED")
            self.assertEqual(result["candidate_reference_count"], 0)
            self.assertIn("heuristic", result["reason"].lower())


if __name__ == "__main__":
    unittest.main()
