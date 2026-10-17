import hashlib
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from adapt_archive_staging_to_intake import adapt_archive_staging_to_intake
from archive_registry_staging import build
from resumable_chat_import import import_export
from plan_memory_intake import build_route_plan
from source_evidence_registry import append_source_records
from validate_memory import validate_intake_manifest


class SourceIngestionRoundtripTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.source = self.root / "conversations.json"
        self.staging = self.root / "staging"
        self.intake_root = self.root / "intake"
        self.registry = self.root / "registry" / "source_records.jsonl"

    def tearDown(self):
        self.tmp.cleanup()

    def _write_export(self, text, create_time=1790000000.0):
        payload = [{
            "id": "conversation-test-001",
            "title": "PRIVATE TEST TITLE — must not enter registry",
            "create_time": create_time,
            "mapping": {
                "node-user-001": {
                    "parent": None,
                    "children": ["node-assistant-001"],
                    "message": {
                        "id": "message-user-001",
                        "author": {"role": "user", "name": "PRIVATE AUTHOR — must not enter registry"},
                        "create_time": create_time,
                        "content": {"content_type": "text", "parts": [text]},
                        "metadata": {},
                    },
                },
                "node-assistant-001": {
                    "parent": "node-user-001",
                    "children": [],
                    "message": {
                        "id": "message-assistant-001",
                        "author": {"role": "assistant"},
                        "create_time": create_time + 1,
                        "content": {"content_type": "text", "parts": ["synthetic assistant response"]},
                        "metadata": {},
                    },
                },
            },
        }]
        self.source.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    def _stage_and_adapt(self, text):
        self._write_export(text)
        result = build(self.source, self.staging, archive_id="ARCHIVE-TEST-001")
        self.assertEqual(result["archive_id"], "ARCHIVE-TEST-001")
        adapted = adapt_archive_staging_to_intake(self.staging / "archive_snapshot.json", self.intake_root)
        self.assertIn(adapted["status"], {"ADAPTED", "ALREADY_ADAPTED"})
        return Path(adapted["manifest_path"]), result

    def test_idless_duplicate_conversations_keep_importer_ordinals_in_staging(self):
        self._write_export("synthetic identical ID-less conversation")
        payload = json.loads(self.source.read_text(encoding="utf-8"))
        del payload[0]["id"]
        payload.append(json.loads(json.dumps(payload[0], ensure_ascii=False)))
        self.source.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

        imported = import_export(
            self.source, self.root / "resumable-import",
            "ARCHIVE-IDLESS-TEST", batch_size=1,
        )
        self.assertEqual(imported["status"], "RAW_COMPLETE")
        self.assertEqual(imported["committed_conversations"], 2)
        conn = sqlite3.connect(imported["database_path"])
        try:
            imported_ids = [
                row[0] for row in conn.execute(
                    "SELECT source_conversation_id FROM raw_conversations "
                    "WHERE archive_id=? AND source_sha256=? ORDER BY source_ordinal",
                    ("ARCHIVE-IDLESS-TEST", imported["source_sha256"]),
                ).fetchall()
            ]
        finally:
            conn.close()
        self.assertEqual(len(set(imported_ids)), 2)

        staged = build(self.source, self.staging, archive_id="ARCHIVE-IDLESS-TEST")
        self.assertEqual(staged["coverage"]["conversation_count"], 2)
        self.assertEqual(staged["coverage"]["source_record_count"], 4)
        records_path = self.staging / staged["records_file"]
        staged_rows = [
            json.loads(line)
            for line in records_path.read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual({row["conversation_id"] for row in staged_rows}, set(imported_ids))
        self.assertEqual(len({row["source_locator"] for row in staged_rows}), 4)
        self.assertEqual(len({row["source_record_id"] for row in staged_rows}), 4)

        adapted = adapt_archive_staging_to_intake(
            self.staging / "archive_snapshot.json", self.intake_root
        )
        manifest_path = Path(adapted["manifest_path"])
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        artifact = manifest["artifacts"][0]
        sanitized_rows = [
            json.loads(line)
            for line in (manifest_path.parent / artifact["path"]).read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual({row["conversation_id"] for row in sanitized_rows}, set(imported_ids))
        self.assertEqual(len({row["source_record_id"] for row in sanitized_rows}), 4)

    def test_adapter_emits_valid_project_neutral_metadata_only_batch(self):
        manifest_path, staged = self._stage_and_adapt("synthetic private message text")
        errors = validate_intake_manifest(manifest_path)
        self.assertEqual(errors, [])
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["payload_classification"], "private_reference_only")
        self.assertEqual(manifest["source"]["project_id"], "unknown")
        self.assertEqual(manifest["source"]["parser_version"], staged["parser_version"])
        artifact = manifest["artifacts"][0]
        self.assertEqual(artifact["kind"], "source_records")
        self.assertEqual(artifact["record_count"], 2)
        rows = [json.loads(line) for line in (manifest_path.parent / artifact["path"]).read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(rows), 2)
        for row in rows:
            self.assertNotIn("text", row)
            self.assertNotIn("conversation_title", row)
            self.assertNotIn("author_name", row)
            self.assertNotIn("project_id", row)
            self.assertNotIn("event_time", row)
            self.assertIn("source_time", row)
            self.assertEqual(row["source_snapshot_sha256"], staged["raw_sha256"])
        plan = build_route_plan(manifest_path)
        self.assertEqual(plan["status"], "DRY_RUN_READY")
        self.assertEqual(plan["routes"][0]["logical_view"], "source_evidence_registry")
        self.assertEqual(plan["routes"][0]["planned_operation"], "append_source_records")

    def test_attachment_markers_keep_coverage_partial_and_payloads_unverified(self):
        self._write_export("synthetic attachment marker")
        payload = json.loads(self.source.read_text(encoding="utf-8"))
        user_message = payload[0]["mapping"]["node-user-001"]["message"]
        user_message["metadata"]["attachments"] = [{
            "id": "ATTACHMENT-SYNTHETIC-001",
            "name": "synthetic-attachment.pdf",
        }]
        self.source.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        original_bytes = self.source.read_bytes()
        original_sha = hashlib.sha256(original_bytes).hexdigest()

        staged = build(self.source, self.staging, archive_id="ARCHIVE-ATTACHMENT-TEST")
        self.assertEqual(staged["raw_sha256"], original_sha)
        self.assertEqual(self.source.read_bytes(), original_bytes)
        self.assertEqual(staged["coverage"]["status"], "partial")
        self.assertEqual(staged["coverage"]["records_with_attachment_markers"], 1)

        staged_path = self.staging / staged["records_file"]
        staged_rows = [
            json.loads(line)
            for line in staged_path.read_text(encoding="utf-8").splitlines()
        ]
        user_row = next(row for row in staged_rows if row["role"] == "user")
        self.assertTrue(user_row["has_attachments"])
        self.assertEqual(user_row["attachment_count"], 1)
        self.assertFalse(user_row["attachment_payloads_inspected"])

        adapted = adapt_archive_staging_to_intake(
            self.staging / "archive_snapshot.json", self.intake_root
        )
        manifest_path = Path(adapted["manifest_path"])
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        artifact = manifest["artifacts"][0]
        rows = [
            json.loads(line)
            for line in (manifest_path.parent / artifact["path"]).read_text(encoding="utf-8").splitlines()
        ]
        sanitized_user = next(row for row in rows if row["role"] == "user")
        self.assertEqual(manifest["source"]["scope_status"], "PARTIAL")
        self.assertTrue(sanitized_user["has_attachments"])
        self.assertFalse(sanitized_user["attachment_payloads_inspected"])
        self.assertNotIn("text", sanitized_user)
        self.assertEqual(sanitized_user["source_snapshot_sha256"], original_sha)

    def test_missing_message_id_keeps_coverage_partial_and_node_provenance_stable(self):
        self._write_export("synthetic message without an ID")
        payload = json.loads(self.source.read_text(encoding="utf-8"))
        del payload[0]["mapping"]["node-assistant-001"]["message"]["id"]
        self.source.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        original_bytes = self.source.read_bytes()
        original_sha = hashlib.sha256(original_bytes).hexdigest()

        staged = build(self.source, self.staging, archive_id="ARCHIVE-MISSING-ID-TEST")
        self.assertEqual(staged["raw_sha256"], original_sha)
        self.assertEqual(self.source.read_bytes(), original_bytes)
        self.assertEqual(staged["coverage"]["status"], "partial")
        self.assertEqual(staged["coverage"]["message_id_missing_count"], 1)

        staged_path = self.staging / staged["records_file"]
        staged_rows = [
            json.loads(line)
            for line in staged_path.read_text(encoding="utf-8").splitlines()
        ]
        assistant = next(row for row in staged_rows if row["role"] == "assistant")
        self.assertIsNone(assistant["source_message_id"])
        self.assertEqual(
            assistant["source_locator"],
            "ARCHIVE-MISSING-ID-TEST/conversation-test-001/node-assistant-001",
        )
        self.assertEqual(
            assistant["source_record_id"],
            "SRC-" + hashlib.sha256(assistant["source_locator"].encode("utf-8")).hexdigest()[:24],
        )

        adapted = adapt_archive_staging_to_intake(
            self.staging / "archive_snapshot.json", self.intake_root
        )
        manifest_path = Path(adapted["manifest_path"])
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        artifact = manifest["artifacts"][0]
        rows = [
            json.loads(line)
            for line in (manifest_path.parent / artifact["path"]).read_text(encoding="utf-8").splitlines()
        ]
        sanitized_assistant = next(row for row in rows if row["role"] == "assistant")
        self.assertEqual(manifest["source"]["scope_status"], "PARTIAL")
        self.assertIsNone(sanitized_assistant["source_message_id"])
        self.assertEqual(sanitized_assistant["source_node_id"], "node-assistant-001")
        self.assertEqual(sanitized_assistant["source_snapshot_sha256"], original_sha)
        self.assertNotIn("text", sanitized_assistant)

    def test_registry_dry_run_apply_and_exact_replay_are_safe(self):
        manifest_path, _ = self._stage_and_adapt("synthetic source message")
        dry = append_source_records(manifest_path, self.registry, apply=False)
        self.assertEqual(dry["status"], "DRY_RUN_READY")
        self.assertFalse(self.registry.exists())

        first = append_source_records(manifest_path, self.registry, apply=True)
        self.assertEqual(first["status"], "APPENDED")
        self.assertEqual(first["added_count"], 2)
        before = self.registry.read_bytes()
        replay = append_source_records(manifest_path, self.registry, apply=True)
        self.assertEqual(replay["status"], "ALREADY_REGISTERED")
        self.assertEqual(before, self.registry.read_bytes())

        rows = [json.loads(line) for line in self.registry.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(rows), 2)
        for row in rows:
            self.assertNotIn("text", row)
            self.assertNotIn("conversation_title", row)
            self.assertNotIn("author_name", row)
            self.assertNotIn("project_id", row)
            self.assertEqual(row["schema_version"], "source-record-v1")
            self.assertEqual(row["batch_id"], first["batch_id"])
            self.assertTrue(row["registered_at"])

    def test_new_source_snapshot_is_appended_as_a_revision_not_an_overwrite(self):
        first_manifest, first_stage = self._stage_and_adapt("first version of the source message")
        first = append_source_records(first_manifest, self.registry, apply=True)
        self.assertEqual(first["status"], "APPENDED")

        second_manifest, second_stage = self._stage_and_adapt("second version of the source message")
        self.assertNotEqual(first_stage["raw_sha256"], second_stage["raw_sha256"])
        second = append_source_records(second_manifest, self.registry, apply=True)
        self.assertEqual(second["status"], "APPENDED")

        rows = [json.loads(line) for line in self.registry.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(rows), 4)
        by_locator = {}
        for row in rows:
            by_locator.setdefault(row["source_locator"], []).append(row)
        self.assertEqual(len(by_locator), 2)  # user and assistant nodes
        for versions in by_locator.values():
            self.assertEqual(len(versions), 2)
            self.assertEqual(len({r["source_record_id"] for r in versions}), 1)
            self.assertEqual(len({r["source_snapshot_sha256"] for r in versions}), 2)

    def test_registry_rejects_raw_text_and_project_assignment(self):
        manifest_path, _ = self._stage_and_adapt("synthetic source message")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        artifact_path = manifest_path.parent / manifest["artifacts"][0]["path"]
        rows = [json.loads(line) for line in artifact_path.read_text(encoding="utf-8").splitlines()]
        rows[0]["text"] = "must not persist"
        rows[0]["project_id"] = "B77_HTML_PWA"
        artifact_bytes = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for row in rows).encode("utf-8")
        artifact_path.write_bytes(artifact_bytes)
        manifest["artifacts"][0]["sha256"] = hashlib.sha256(artifact_bytes).hexdigest()
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        result = append_source_records(manifest_path, self.registry, apply=True)
        self.assertEqual(result["status"], "REJECTED")
        self.assertIn("unsupported fields", result["error"])
        self.assertFalse(self.registry.exists())

    def test_adapter_rejects_staged_artifact_hash_mismatch(self):
        self._write_export("synthetic source message")
        build(self.source, self.staging, archive_id="ARCHIVE-TEST-001")
        snapshot = json.loads((self.staging / "archive_snapshot.json").read_text(encoding="utf-8"))
        records_path = self.staging / snapshot["records_file"]
        records_path.write_text(records_path.read_text(encoding="utf-8") + " ", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "records_sha256 mismatch"):
            adapt_archive_staging_to_intake(self.staging / "archive_snapshot.json", self.intake_root)


if __name__ == "__main__":
    unittest.main()
