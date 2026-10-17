import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from canonical_memory_index import build_index_payload


class CanonicalMemoryLifecycleIndexTests(unittest.TestCase):
    def test_embedded_candidate_lifecycle_is_separate_from_accepted_registry_status(self):
        record = {
            "memory_id": "MEM-LIFECYCLE-001",
            "record_type": "lesson",
            "title": "Synthetic",
            "summary": "Lifecycle status remains distinct",
            "lifecycle_status": "candidate",
            "evidence_status": "observed",
            "provenance": [{"source_locator": "fixture:source"}],
            "revision": {"revision_id": "REV-001", "revision_of": None},
        }
        canonical = lambda value: json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        digest = hashlib.sha256(canonical(record)).hexdigest()
        envelope = {
            "registry_schema_version": "semantic-memory-registry-v1",
            "promotion_id": "PROMO-LIFECYCLE-001",
            "memory_id": "MEM-LIFECYCLE-001",
            "revision_id": "REV-001",
            "record_sha256": digest,
            "lifecycle_status": "accepted",
            "record": record,
            "batch_id": "BATCH-LIFECYCLE-001",
            "artifact_id": "ARTIFACT-LIFECYCLE-001",
            "manifest_sha256": "1" * 64,
            "artifact_sha256": "2" * 64,
            "approval_decision_id": "DECISION-LIFECYCLE-001",
            "approval_receipt_sha256": "3" * 64,
            "promoted_at": "2026-10-16T00:00:00Z",
            "previous_revision_id": None,
        }
        payload = build_index_payload(canonical(envelope) + b"\n")
        self.assertEqual(payload["records"][0]["lifecycle_status"], "accepted")
        self.assertEqual(payload["records"][0]["record_lifecycle_status"], "candidate")
        self.assertIn(
            "MEM-LIFECYCLE-001",
            [item["memory_id"] for item in payload["indexes"]["by_record_lifecycle_status"]["candidate"]],
        )


if __name__ == "__main__":
    unittest.main()
