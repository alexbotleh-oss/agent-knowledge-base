import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from semantic_memory_registry import promote_memory_records


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha(data):
    return hashlib.sha256(data).hexdigest()


class SemanticMemoryRegistryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.batch = self.root / "batch"
        self.batch.mkdir()
        self.manifest_path = self.batch / "manifest.json"
        self.records_path = self.batch / "records.jsonl"
        self.receipt_path = self.batch / "approval.json"
        self.registry = self.root / "registry" / "memory_records.jsonl"
        self.record = {
            "memory_id": "MEM-TEST-001",
            "record_type": "lesson",
            "title": "Synthetic lesson",
            "summary": "A test-only record",
            "evidence_status": "observed",
            "lifecycle_status": "candidate",
            "project_ids": ["TEST_PROJECT"],
            "provenance": [{"source_locator": "fixture:source-message-1", "evidence_role": "supports"}],
            "revision": {"revision_id": "REV-001", "revision_of": None, "reason": "initial candidate"},
        }
        self._write_batch()

    def _write_batch(self, *, records=None, decision="approve", decision_id="DECISION-TEST-001"):
        records = records if records is not None else [self.record]
        payload = b"".join(canonical(row) + b"\n" for row in records)
        self.records_path.write_bytes(payload)
        artifact_sha = sha(payload)
        manifest = {
            "schema_version": "1.0", "command": "IMPORT_READY",
            "batch_id": "BATCH-TEST-001", "created_at": "2026-10-16T00:00:00Z",
            "payload_classification": "sanitized",
            "source": {
                "source_type": "chat_summary", "source_id": "TEST_SOURCE",
                "project_id": "TEST_PROJECT", "conversation_ids": ["TEST_CONVERSATION"],
                "source_locator": "fixture:source", "captured_at": "unknown", "scope_status": "PARTIAL",
            },
            "artifacts": [{
                "artifact_id": "ARTIFACT-TEST-001", "kind": "memory_records",
                "path": "records.jsonl", "sha256": artifact_sha, "record_count": len(records),
                "lifecycle_status": "accepted", "evidence_status": "observed",
                "approval_status": "user_approved", "approval_evidence": decision_id,
            }],
        }
        manifest_bytes = json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        self.manifest_path.write_bytes(manifest_bytes)
        receipt = {
            "schema_version": "semantic-memory-approval-v1", "decision_id": decision_id,
            "decision": decision, "actor_type": "user", "actor_ref": "test-user-approval",
            "decided_at": "2026-10-16T00:05:00Z", "batch_id": manifest["batch_id"],
            "artifact_id": manifest["artifacts"][0]["artifact_id"],
            "manifest_sha256": sha(manifest_bytes), "artifact_sha256": artifact_sha,
            "decision_source_ref": "test:explicit-approval",
            "rationale": "Synthetic approval used only in a unit test.",
        }
        self.receipt_path.write_text(json.dumps(receipt, sort_keys=True), encoding="utf-8")

    def test_dry_run_validates_exact_approval_binding_without_writes(self):
        result = promote_memory_records(self.manifest_path, self.receipt_path, self.registry)
        self.assertEqual(result["status"], "DRY_RUN_READY")
        self.assertFalse(result["writes_performed"])
        self.assertFalse(self.registry.exists())

    def test_apply_promotes_append_only_envelope_with_provenance_and_approval(self):
        result = promote_memory_records(self.manifest_path, self.receipt_path, self.registry, apply=True)
        self.assertEqual(result["status"], "PROMOTED")
        self.assertTrue(result["writes_performed"])
        row = json.loads(self.registry.read_text(encoding="utf-8").splitlines()[0])
        self.assertEqual(row["lifecycle_status"], "accepted")
        self.assertEqual(row["approval_decision_id"], "DECISION-TEST-001")
        self.assertEqual(row["record"], self.record)
        self.assertEqual(row["record_sha256"], sha(canonical(self.record)))
        self.assertIsNone(row["previous_revision_id"])

    def test_exact_replay_is_noop(self):
        first = promote_memory_records(self.manifest_path, self.receipt_path, self.registry, apply=True)
        before = self.registry.read_bytes()
        second = promote_memory_records(self.manifest_path, self.receipt_path, self.registry, apply=True)
        self.assertEqual(first["status"], "PROMOTED")
        self.assertEqual(second["status"], "ALREADY_PROMOTED")
        self.assertEqual(self.registry.read_bytes(), before)

    def test_same_revision_with_different_content_is_conflict(self):
        promote_memory_records(self.manifest_path, self.receipt_path, self.registry, apply=True)
        changed = dict(self.record, summary="different content under same revision")
        self._write_batch(records=[changed], decision_id="DECISION-TEST-002")
        result = promote_memory_records(self.manifest_path, self.receipt_path, self.registry, apply=True)
        self.assertEqual(result["status"], "CONFLICT")
        self.assertIn("same memory revision has different content", result["error"])

    def test_approval_receipt_for_different_artifact_is_rejected(self):
        receipt = json.loads(self.receipt_path.read_text(encoding="utf-8"))
        receipt["artifact_sha256"] = "0" * 64
        self.receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
        result = promote_memory_records(self.manifest_path, self.receipt_path, self.registry, apply=True)
        self.assertEqual(result["status"], "REJECTED")
        self.assertIn("different artifact bytes", result["error"])
        self.assertFalse(self.registry.exists())

    def test_manifest_change_after_approval_is_rejected(self):
        manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        manifest["notes"] = "mutated after approval"
        self.manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        result = promote_memory_records(self.manifest_path, self.receipt_path, self.registry, apply=True)
        self.assertEqual(result["status"], "REJECTED")
        self.assertIn("different manifest", result["error"])
        self.assertFalse(self.registry.exists())

    def test_missing_provenance_is_rejected(self):
        record = dict(self.record, provenance=[])
        self._write_batch(records=[record])
        result = promote_memory_records(self.manifest_path, self.receipt_path, self.registry, apply=True)
        self.assertEqual(result["status"], "REJECTED")
        self.assertIn("non-empty provenance", result["error"])

    def test_non_approval_decision_is_rejected(self):
        self._write_batch(decision="request_changes")
        result = promote_memory_records(self.manifest_path, self.receipt_path, self.registry, apply=True)
        self.assertEqual(result["status"], "REJECTED")
        self.assertIn("does not authorize promotion", result["error"])
        self.assertFalse(self.registry.exists())

    def test_new_revision_must_link_to_current_revision(self):
        promote_memory_records(self.manifest_path, self.receipt_path, self.registry, apply=True)
        revised = dict(self.record, summary="new revision", revision={
            "revision_id": "REV-002", "revision_of": "REV-UNKNOWN", "reason": "correction"
        })
        self._write_batch(records=[revised], decision_id="DECISION-TEST-002")
        result = promote_memory_records(self.manifest_path, self.receipt_path, self.registry, apply=True)
        self.assertEqual(result["status"], "CONFLICT")
        self.assertIn("must reference current revision", result["error"])

    def test_valid_revision_chain_is_append_only(self):
        promote_memory_records(self.manifest_path, self.receipt_path, self.registry, apply=True)
        first_bytes = self.registry.read_bytes()
        revised = dict(self.record, summary="new revision", revision={
            "revision_id": "REV-002", "revision_of": "REV-001", "reason": "correction"
        })
        self._write_batch(records=[revised], decision_id="DECISION-TEST-002")
        result = promote_memory_records(self.manifest_path, self.receipt_path, self.registry, apply=True)
        self.assertEqual(result["status"], "PROMOTED")
        rows = [json.loads(line) for line in self.registry.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["record"], self.record)
        self.assertEqual(rows[1]["previous_revision_id"], "REV-001")
        self.assertTrue(self.registry.read_bytes().startswith(first_bytes))

    def test_corrupt_existing_registry_fails_closed(self):
        self.registry.parent.mkdir(parents=True, exist_ok=True)
        self.registry.write_text("{not json}\n", encoding="utf-8")
        result = promote_memory_records(self.manifest_path, self.receipt_path, self.registry, apply=True)
        self.assertEqual(result["status"], "CONFLICT")
        self.assertEqual(self.registry.read_text(encoding="utf-8"), "{not json}\n")

    def test_changed_receipt_decision_id_must_match_manifest_evidence(self):
        receipt = json.loads(self.receipt_path.read_text(encoding="utf-8"))
        receipt["decision_id"] = "DECISION-OTHER-002"
        self.receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
        result = promote_memory_records(self.manifest_path, self.receipt_path, self.registry, apply=True)
        self.assertEqual(result["status"], "REJECTED")
        self.assertIn("does not match receipt decision_id", result["error"])


if __name__ == "__main__":
    unittest.main()
