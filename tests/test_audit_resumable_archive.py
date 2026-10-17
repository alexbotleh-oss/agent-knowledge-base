import hashlib
import json
import sqlite3
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from archive_registry_staging import build as build_staging
from audit_resumable_archive import audit_archive
from resumable_chat_import import import_export


def sample_conversation(text="original source text", *, attachment=False):
    metadata = {}
    if attachment:
        metadata["attachments"] = [{"id": "ATT-AUDIT-001", "name": "synthetic.pdf"}]
    return {
        "id": "CONV-AUDIT-001",
        "title": "synthetic audit fixture",
        "mapping": {
            "NODE-AUDIT-USER": {
                "parent": None,
                "children": ["NODE-AUDIT-ASSISTANT"],
                "message": {
                    "id": "MSG-AUDIT-USER",
                    "create_time": 1790000000,
                    "author": {"role": "user"},
                    "content": {"content_type": "text", "parts": [text]},
                    "metadata": metadata,
                },
            },
            # Equal timestamp and lexically earlier ID: stable source order must win.
            "NODE-AUDIT-ASSISTANT": {
                "parent": "NODE-AUDIT-USER",
                "children": [],
                "message": {
                    "id": "MSG-AUDIT-ASSISTANT",
                    "create_time": 1790000000,
                    "author": {"role": "assistant"},
                    "content": {"content_type": "text", "parts": ["synthetic response"]},
                    "metadata": {},
                },
            }
        },
    }


class ResumableArchiveAuditTests(unittest.TestCase):
    def test_zip_import_and_staging_audit_reports_partial_coverage_honestly(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "export.zip"
            conversation_bytes = json.dumps(
                [sample_conversation(attachment=True)], ensure_ascii=False
            ).encode("utf-8")
            with zipfile.ZipFile(source, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("conversations.json", conversation_bytes)
                archive.writestr("files/synthetic.pdf", b"%PDF-1.4\nsynthetic\n%%EOF")
            source_bytes = source.read_bytes()
            import_dir = root / "import"
            imported = import_export(source, import_dir, "ARCHIVE-AUDIT-001", batch_size=1)
            staging_root = root / "staging"
            staged = build_staging(
                Path(imported["snapshot_path"]), staging_root, "ARCHIVE-AUDIT-001"
            )
            manifest_path = staging_root / "archive_snapshot.json"

            report = audit_archive(
                import_dir, "ARCHIVE-AUDIT-001",
                source_sha256=imported["source_sha256"],
                staging_manifest=manifest_path,
            )
            self.assertEqual(report["integrity_status"], "PASS", report)
            self.assertEqual(report["status"], "INTEGRITY_PASS_COVERAGE_PARTIAL", report)
            self.assertTrue(report["checks"]["snapshot_sha256_valid"])
            self.assertTrue(report["checks"]["snapshot_size_valid"])
            self.assertTrue(report["checks"]["source_ordinals_contiguous"])
            self.assertTrue(report["checks"]["committed_count_matches"])
            self.assertTrue(report["checks"]["staging_integrity_valid"])
            self.assertEqual(report["coverage_status"], "partial")
            self.assertEqual(report["conversation_count"], 1)
            self.assertEqual(Path(imported["snapshot_path"]).read_bytes(), source_bytes)
            self.assertEqual(staged["raw_sha256"], hashlib.sha256(source_bytes).hexdigest())
            self.assertTrue(any("binary attachment payloads" in warning for warning in report["warnings"]))

            # The audit is read-only: tampering with a derived artifact is detected,
            # not silently repaired.
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            records_path = staging_root / manifest["records_file"]
            original_records = records_path.read_bytes()
            records_path.write_bytes(original_records + b" ")
            failed = audit_archive(
                import_dir, "ARCHIVE-AUDIT-001",
                source_sha256=imported["source_sha256"],
                staging_manifest=manifest_path,
            )
            self.assertEqual(failed["integrity_status"], "FAIL", failed)
            self.assertTrue(any("staged records SHA-256" in error for error in failed["errors"]))
            self.assertEqual(records_path.read_bytes(), original_records + b" ")

    def test_audit_detects_staging_order_drift_even_when_manifest_hash_is_updated(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "conversations.json"
            source.write_text(json.dumps([sample_conversation()]), encoding="utf-8")
            import_dir = root / "import"
            imported = import_export(source, import_dir, "ARCHIVE-ORDER-AUDIT", batch_size=1)
            staging_root = root / "staging"
            build_staging(Path(imported["snapshot_path"]), staging_root, "ARCHIVE-ORDER-AUDIT")
            manifest_path = staging_root / "archive_snapshot.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            records_path = staging_root / manifest["records_file"]
            rows = [
                json.loads(line)
                for line in records_path.read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual(
                [row["source_node_id"] for row in rows],
                ["NODE-AUDIT-USER", "NODE-AUDIT-ASSISTANT"],
            )

            reordered = list(reversed(rows))
            artifact_bytes = "".join(
                json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
                for row in reordered
            ).encode("utf-8")
            records_path.write_bytes(artifact_bytes)
            manifest["records_sha256"] = hashlib.sha256(artifact_bytes).hexdigest()
            manifest_path.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            report = audit_archive(
                import_dir, "ARCHIVE-ORDER-AUDIT",
                source_sha256=imported["source_sha256"],
                staging_manifest=manifest_path,
            )
            self.assertEqual(report["integrity_status"], "FAIL", report)
            self.assertTrue(
                any("stable timestamp/source order" in error for error in report["errors"]),
                report["errors"],
            )

    def test_payload_hash_mismatch_is_detected_without_repairing_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "conversations.json"
            source.write_text(json.dumps([sample_conversation()]), encoding="utf-8")
            imported = import_export(source, root / "import", "ARCHIVE-AUDIT-HASH", batch_size=1)
            connection = sqlite3.connect(imported["database_path"])
            try:
                row = connection.execute(
                    "SELECT payload_json FROM raw_conversations WHERE archive_id=?",
                    ("ARCHIVE-AUDIT-HASH",),
                ).fetchone()
                tampered = row[0].replace("original source text", "tampered source text")
                connection.execute(
                    "UPDATE raw_conversations SET payload_json=? WHERE archive_id=?",
                    (tampered, "ARCHIVE-AUDIT-HASH"),
                )
                connection.commit()
            finally:
                connection.close()

            report = audit_archive(root / "import", "ARCHIVE-AUDIT-HASH")
            self.assertEqual(report["integrity_status"], "FAIL", report)
            self.assertTrue(any("payload SHA-256 mismatch" in error for error in report["errors"]))
            connection = sqlite3.connect(imported["database_path"])
            try:
                after = connection.execute(
                    "SELECT payload_json FROM raw_conversations WHERE archive_id=?",
                    ("ARCHIVE-AUDIT-HASH",),
                ).fetchone()[0]
            finally:
                connection.close()
            self.assertEqual(after, tampered)
            self.assertFalse(report["writes_performed"])

    def test_multiple_snapshots_require_explicit_source_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "conversations.json"
            output = root / "import"
            source.write_text(json.dumps([sample_conversation("first version")]), encoding="utf-8")
            first = import_export(source, output, "ARCHIVE-MULTI-SNAPSHOT", batch_size=1)
            source.write_text(json.dumps([sample_conversation("second version")]), encoding="utf-8")
            import_export(source, output, "ARCHIVE-MULTI-SNAPSHOT", batch_size=1)

            report = audit_archive(output, "ARCHIVE-MULTI-SNAPSHOT")
            self.assertEqual(report["status"], "AMBIGUOUS", report)
            self.assertEqual(report["integrity_status"], "NOT_CHECKED")
            self.assertIn(first["source_sha256"], report["available_source_sha256"])


if __name__ == "__main__":
    unittest.main()
