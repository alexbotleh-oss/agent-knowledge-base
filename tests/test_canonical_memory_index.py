import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import canonical_memory_index as indexer


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def envelope(memory_id="MEM-INDEX-001", revision_id="REV-001", parent=None, summary="synthetic"):
    record = {
        "memory_id": memory_id, "record_type": "lesson", "title": "Synthetic",
        "summary": summary, "project_ids": ["AGENT_MEMORY_SYSTEM", "SHARED_METHODS"],
        "task_ids": ["TASK-INDEX-1"], "context_ids": ["CTX-INDEX-1"],
        "tags": ["append-only", "provenance"], "sign": "negative",
        "decision_status": "accepted", "evidence_status": "observed",
        "event_time": "2026-10-16T00:00:00Z", "source_time": "unknown",
        "provenance": [{"source_locator": "fixture:message-1"}],
        "relations": [{"type": "derived_from", "target_id": "SRC-INDEX-1"}],
        "revision": {"revision_id": revision_id, "revision_of": parent, "reason": "test fixture"},
    }
    digest = indexer._sha(canonical(record))
    return {
        "registry_schema_version": "semantic-memory-registry-v1",
        "promotion_id": "PROMO-" + memory_id + "-" + revision_id,
        "memory_id": memory_id, "revision_id": revision_id, "record_sha256": digest,
        "lifecycle_status": "accepted", "record": record,
        "batch_id": "BATCH-INDEX-TEST", "artifact_id": "ARTIFACT-INDEX-TEST",
        "manifest_sha256": "1" * 64, "artifact_sha256": "2" * 64,
        "approval_decision_id": "DECISION-INDEX-TEST", "approval_receipt_sha256": "3" * 64,
        "promoted_at": "2026-10-16T00:01:00Z", "previous_revision_id": parent,
    }


class CanonicalMemoryIndexTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.registry = self.root / "registry" / "memory_records.jsonl"
        self.index_root = self.root / "registry" / "memory_index"
        self.registry.parent.mkdir(parents=True)

    def write_rows(self, rows):
        self.registry.write_bytes(b"".join(canonical(row) + b"\n" for row in rows))

    def test_index_payload_is_deterministic_and_multidimensional(self):
        self.write_rows([envelope()])
        raw = self.registry.read_bytes()
        first = indexer.build_index_payload(raw)
        second = indexer.build_index_payload(raw)
        self.assertEqual(canonical(first), canonical(second))
        self.assertEqual(first["coverage"]["status"], "PARTIAL")
        self.assertEqual(first["coverage"]["correction_overlay_status"], "NOT_AVAILABLE_NO_CANONICAL_OVERLAY_SOURCE")
        self.assertEqual(len(first["records"]), 1)
        ref = {"memory_id": "MEM-INDEX-001", "revision_id": "REV-001", "record_sha256": first["records"][0]["record_sha256"]}
        self.assertIn(ref, first["indexes"]["by_project"]["AGENT_MEMORY_SYSTEM"])
        self.assertIn(ref, first["indexes"]["by_project"]["SHARED_METHODS"])
        self.assertIn(ref, first["indexes"]["by_task"]["TASK-INDEX-1"])
        self.assertIn(ref, first["indexes"]["by_topic"]["append-only"])
        self.assertIn(ref, first["indexes"]["by_source_ref"]["source_locator:fixture:message-1"])
        self.assertIn(ref, first["indexes"]["by_relation_target"]["SRC-INDEX-1"])

    def test_revision_history_is_retained_and_current_revision_is_explicit(self):
        self.write_rows([envelope(), envelope(revision_id="REV-002", parent="REV-001", summary="corrected")])
        payload = indexer.build_index_payload(self.registry.read_bytes())
        self.assertEqual(len(payload["records"]), 2)
        self.assertEqual(payload["current_revision_by_memory_id"]["MEM-INDEX-001"], "REV-002")
        current = [row for row in payload["records"] if row["current_revision"]]
        self.assertEqual([(row["memory_id"], row["revision_id"]) for row in current], [("MEM-INDEX-001", "REV-002")])

    def test_refresh_and_freshness_report_partial_but_current(self):
        self.write_rows([envelope()])
        dry = indexer.refresh_canonical_index(self.registry, self.index_root)
        self.assertEqual(dry["status"], "DRY_RUN_READY")
        self.assertFalse((self.index_root / "CURRENT.json").exists())
        built = indexer.refresh_canonical_index(self.registry, self.index_root, apply=True)
        self.assertEqual(built["status"], "BUILT_PARTIAL")
        freshness = indexer.check_index_freshness(self.registry, self.index_root)
        self.assertEqual(freshness["status"], "CURRENT_PARTIAL")
        self.assertEqual(freshness["generation_id"], built["generation_id"])

    def test_repeated_refresh_reuses_same_generation(self):
        self.write_rows([envelope()])
        first = indexer.refresh_canonical_index(self.registry, self.index_root, apply=True)
        before = (self.index_root / "CURRENT.json").read_bytes()
        second = indexer.refresh_canonical_index(self.registry, self.index_root, apply=True)
        self.assertEqual(first["generation_id"], second["generation_id"])
        self.assertEqual((self.index_root / "CURRENT.json").read_bytes(), before)
        self.assertEqual(len(list((self.index_root / "generations").glob("*.json"))), 1)

    def test_changed_registry_is_reported_stale(self):
        self.write_rows([envelope()])
        indexer.refresh_canonical_index(self.registry, self.index_root, apply=True)
        with self.registry.open("ab") as stream:
            stream.write(b" ")
        self.assertEqual(indexer.check_index_freshness(self.registry, self.index_root)["status"], "STALE")

    def test_corrupt_registry_blocks_build_without_publishing(self):
        self.registry.write_text("{bad json}\n", encoding="utf-8")
        result = indexer.refresh_canonical_index(self.registry, self.index_root, apply=True)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertFalse((self.index_root / "CURRENT.json").exists())

    def test_broken_revision_chain_blocks_build(self):
        self.write_rows([envelope(), envelope(revision_id="REV-002", parent="REV-WRONG", summary="bad chain")])
        result = indexer.refresh_canonical_index(self.registry, self.index_root, apply=True)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertFalse((self.index_root / "CURRENT.json").exists())

    def test_failed_pointer_publish_preserves_previous_generation(self):
        self.write_rows([envelope()])
        indexer.refresh_canonical_index(self.registry, self.index_root, apply=True)
        pointer_path = self.index_root / "CURRENT.json"
        old_pointer = pointer_path.read_bytes()
        self.write_rows([envelope(), envelope("MEM-INDEX-002", "REV-001", None, "second")])
        original = indexer._atomic_write
        def fail_current(path, payload):
            if Path(path).name == "CURRENT.json":
                raise OSError("injected pointer publication failure")
            return original(path, payload)
        with mock.patch.object(indexer, "_atomic_write", side_effect=fail_current):
            result = indexer.refresh_canonical_index(self.registry, self.index_root, apply=True)
        self.assertEqual(result["status"], "WRITE_FAILED")
        self.assertEqual(pointer_path.read_bytes(), old_pointer)
        self.assertEqual(indexer.check_index_freshness(self.registry, self.index_root)["status"], "STALE")

    def test_missing_registry_blocks_build(self):
        result = indexer.refresh_canonical_index(self.registry, self.index_root, apply=True)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertFalse((self.index_root / "CURRENT.json").exists())


if __name__ == "__main__":
    unittest.main()
