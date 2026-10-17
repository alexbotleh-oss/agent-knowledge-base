import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from edge_correction_registry import register_edge_correction


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha(data):
    return hashlib.sha256(data).hexdigest()


class EdgeCorrectionRegistryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "registry" / "memory_records.jsonl"
        self.registry = self.root / "registry" / "edge_corrections.jsonl"
        self.input = self.root / "correction.json"
        self.receipt = self.root / "approval.json"
        relation = {
            "type": "derived_from", "target_id": "SRC-001", "basis": "source reference",
            "confidence": "high", "status": "accepted", "source_refs": ["fixture:source"],
        }
        self.record = {
            "memory_id": "MEM-CORR-001", "record_type": "lesson", "title": "Correction fixture",
            "summary": "Synthetic", "evidence_status": "observed", "lifecycle_status": "candidate",
            "provenance": [{"source_locator": "fixture:source"}], "relations": [relation],
            "revision": {"revision_id": "REV-001", "revision_of": None},
        }
        self.relation = relation
        self.source_row = {
            "registry_schema_version": "semantic-memory-registry-v1", "promotion_id": "PROMO-CORR-001",
            "memory_id": "MEM-CORR-001", "revision_id": "REV-001",
            "record_sha256": sha(canonical(self.record)), "lifecycle_status": "accepted", "record": self.record,
            "batch_id": "BATCH-CORR-001", "artifact_id": "ARTIFACT-CORR-001",
            "manifest_sha256": "1" * 64, "artifact_sha256": "2" * 64,
            "approval_decision_id": "DECISION-CORR-SOURCE", "approval_receipt_sha256": "3" * 64,
            "promoted_at": "2026-10-16T00:00:00Z", "previous_revision_id": None,
        }
        self.source.parent.mkdir(parents=True)
        self.source.write_bytes(canonical(self.source_row) + b"\n")
        self._write_correction()

    def _write_correction(self, *, status="accepted", target=None, correction_id="CORR-TEST-001"):
        self.correction = {
            "schema_version": "edge-correction-v1", "correction_id": correction_id,
            "action": "add", "status": status, "source_memory_id": "MEM-CORR-001",
            "source_revision_id": "REV-001", "source_record_sha256": self.source_row["record_sha256"],
            "target_relation_sha256": None,
            "relation": {
                "type": "supports", "target_id": "MEM-CORR-002", "basis": "explicit follow-up evidence",
                "confidence": "medium", "status": "accepted", "source_refs": ["fixture:follow-up"],
            },
            "decision_id": "DECISION-CORR-001", "decision_source_ref": "fixture:user-approval",
            "recorded_at": "2026-10-16T01:00:00Z", "rationale": "Synthetic correction for tests",
            "source_refs": ["fixture:follow-up"],
        }
        if target is not None:
            self.correction["action"] = "retract"
            self.correction["target_relation_sha256"] = target
            self.correction.pop("relation")
        raw = json.dumps(self.correction, ensure_ascii=False, sort_keys=True).encode("utf-8")
        self.input.write_bytes(raw)
        receipt = {
            "schema_version": "edge-correction-approval-v1", "decision_id": "DECISION-CORR-001",
            "decision": "approve", "actor_type": "user", "actor_ref": "test-user",
            "decided_at": "2026-10-16T01:01:00Z", "correction_id": correction_id,
            "correction_sha256": sha(raw), "decision_source_ref": "fixture:user-approval",
            "rationale": "Synthetic approval receipt; not a real user decision.",
        }
        self.receipt.write_text(json.dumps(receipt, sort_keys=True), encoding="utf-8")

    def test_dry_run_does_not_write(self):
        result = register_edge_correction(self.input, self.source, self.registry, approval_receipt_path=self.receipt)
        self.assertEqual(result["status"], "DRY_RUN_READY")
        self.assertFalse(self.registry.exists())

    def test_accepted_correction_appends_with_receipt_and_source_hash(self):
        result = register_edge_correction(self.input, self.source, self.registry, approval_receipt_path=self.receipt, apply=True)
        self.assertEqual(result["status"], "APPENDED")
        row = json.loads(self.registry.read_text(encoding="utf-8").splitlines()[0])
        self.assertEqual(row["correction"]["correction_id"], "CORR-TEST-001")
        self.assertEqual(row["source_registry_sha256"], sha(self.source.read_bytes()))
        self.assertEqual(row["approval_receipt_sha256"], sha(self.receipt.read_bytes()))

    def test_exact_replay_is_idempotent(self):
        first = register_edge_correction(self.input, self.source, self.registry, approval_receipt_path=self.receipt, apply=True)
        before = self.registry.read_bytes()
        second = register_edge_correction(self.input, self.source, self.registry, approval_receipt_path=self.receipt, apply=True)
        self.assertEqual(first["status"], "APPENDED")
        self.assertEqual(second["status"], "ALREADY_REGISTERED")
        self.assertEqual(self.registry.read_bytes(), before)

    def test_receipt_for_different_correction_bytes_is_rejected(self):
        self.correction["rationale"] = "changed after approval"
        self.input.write_bytes(json.dumps(self.correction, sort_keys=True).encode("utf-8"))
        result = register_edge_correction(self.input, self.source, self.registry, approval_receipt_path=self.receipt, apply=True)
        self.assertEqual(result["status"], "REJECTED")
        self.assertIn("exact correction bytes", result["reason"])
        self.assertFalse(self.registry.exists())

    def test_stale_source_record_hash_is_rejected(self):
        self.correction["source_record_sha256"] = "0" * 64
        raw = json.dumps(self.correction, sort_keys=True).encode("utf-8")
        self.input.write_bytes(raw)
        receipt = json.loads(self.receipt.read_text(encoding="utf-8"))
        receipt["correction_sha256"] = sha(raw)
        self.receipt.write_text(json.dumps(receipt), encoding="utf-8")
        result = register_edge_correction(self.input, self.source, self.registry, approval_receipt_path=self.receipt, apply=True)
        self.assertEqual(result["status"], "REJECTED")
        self.assertIn("source record hash is stale", result["reason"])

    def test_candidate_correction_can_be_staged_without_approval_but_is_not_accepted(self):
        self._write_correction(status="candidate")
        result = register_edge_correction(self.input, self.source, self.registry, apply=True)
        self.assertEqual(result["status"], "APPENDED")
        row = json.loads(self.registry.read_text(encoding="utf-8").splitlines()[0])
        self.assertEqual(row["correction"]["status"], "candidate")
        self.assertIsNone(row["approval_receipt_sha256"])

    def test_retract_requires_unique_existing_relation_fingerprint(self):
        self._write_correction(target="f" * 64)
        receipt = json.loads(self.receipt.read_text(encoding="utf-8"))
        receipt["correction_sha256"] = sha(self.input.read_bytes())
        self.receipt.write_text(json.dumps(receipt), encoding="utf-8")
        result = register_edge_correction(self.input, self.source, self.registry, approval_receipt_path=self.receipt, apply=True)
        self.assertEqual(result["status"], "REJECTED")
        self.assertIn("missing or ambiguous", result["reason"])

    def test_same_correction_id_with_changed_content_conflicts(self):
        register_edge_correction(self.input, self.source, self.registry, approval_receipt_path=self.receipt, apply=True)
        self._write_correction(correction_id="CORR-TEST-001")
        self.correction["rationale"] = "different content"
        raw = json.dumps(self.correction, sort_keys=True).encode("utf-8")
        self.input.write_bytes(raw)
        receipt = json.loads(self.receipt.read_text(encoding="utf-8"))
        receipt["correction_sha256"] = sha(raw)
        self.receipt.write_text(json.dumps(receipt), encoding="utf-8")
        result = register_edge_correction(self.input, self.source, self.registry, approval_receipt_path=self.receipt, apply=True)
        self.assertEqual(result["status"], "CONFLICT")
        self.assertIn("different content", result["reason"])


if __name__ == "__main__":
    unittest.main()
