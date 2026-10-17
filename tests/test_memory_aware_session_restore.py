import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))
import canonical_memory_index as indexer
import memory_aware_session_restore as restore


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def envelope(memory_id="MEM-RESTORE-001", revision_id="REV-001", parent=None, project="AGENT_MEMORY_SYSTEM", summary="verified restore lesson"):
    record = {
        "memory_id": memory_id, "record_type": "lesson", "title": "Restore lesson",
        "summary": summary, "project_ids": [project], "task_ids": ["TASK-RESTORE-1"],
        "context_ids": ["CTX-RESTORE-1"], "tags": ["restore", "provenance"],
        "evidence_status": "observed", "lifecycle_status": "candidate",
        "provenance": [{"source_locator": "fixture:source-1"}],
        "relations": [{"type": "contradicts", "target_id": "MEM-OTHER-001"}],
        "revision": {"revision_id": revision_id, "revision_of": parent, "reason": "fixture"},
    }
    return {
        "registry_schema_version": "semantic-memory-registry-v1",
        "promotion_id": "PROMO-" + memory_id + "-" + revision_id,
        "memory_id": memory_id, "revision_id": revision_id,
        "record_sha256": hashlib.sha256(canonical(record)).hexdigest(),
        "lifecycle_status": "accepted", "record": record,
        "batch_id": "BATCH-RESTORE-001", "artifact_id": "ARTIFACT-RESTORE-001",
        "manifest_sha256": "1" * 64, "artifact_sha256": "2" * 64,
        "approval_decision_id": "DECISION-RESTORE-001", "approval_receipt_sha256": "3" * 64,
        "promoted_at": "2026-10-16T00:01:00Z", "previous_revision_id": parent,
    }


class MemoryAwareRestoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.registry = self.root / "registry" / "memory_records.jsonl"
        self.index_root = self.root / "registry" / "memory_index"
        self.registry.parent.mkdir(parents=True)
        self.write_rows([envelope()])
        built = indexer.refresh_canonical_index(self.registry, self.index_root, apply=True)
        self.assertEqual(built["status"], "BUILT_PARTIAL")
        self.base_packet = {
            "status": "RESTORED_PACKET",
            "project_scope": {
                "task_project_id": "AGENT_MEMORY_SYSTEM",
                "handoff_project_id": "AGENT_MEMORY_SYSTEM",
                "event_log_project_id": "AGENT_MEMORY_SYSTEM",
            },
            "warnings": [],
        }

    def write_rows(self, rows):
        self.registry.write_bytes(b"".join(canonical(row) + b"\n" for row in rows))

    def test_retrieves_current_project_record_with_provenance_and_contradictions(self):
        result = restore.retrieve_approved_memory(
            "AGENT_MEMORY_SYSTEM", task_id="TASK-RESTORE-1",
            context_id="CTX-RESTORE-1", query="verified restore lesson",
            registry_path=self.registry, index_root=self.index_root,
        )
        self.assertEqual(result["status"], "PARTIAL")
        self.assertEqual(result["coverage_status"], "PARTIAL")
        self.assertEqual(result["returned_count"], 1)
        self.assertEqual(result["records"][0]["memory_id"], "MEM-RESTORE-001")
        self.assertTrue(result["records"][0]["provenance"])
        self.assertEqual(len(result["unresolved_contradictions"]), 1)
        self.assertIn("no embedding/semantic ranking", result["retrieval_method"])

    def test_project_boundary_excludes_other_project(self):
        result = restore.retrieve_approved_memory("CARD111", registry_path=self.registry, index_root=self.index_root)
        self.assertEqual(result["status"], "PARTIAL_NO_MATCH")
        self.assertEqual(result["records"], [])
        self.assertTrue(any("does not prove" in warning for warning in result["warnings"]))

    def test_stale_index_is_not_treated_as_empty_memory(self):
        with self.registry.open("ab") as stream:
            stream.write(b" ")
        result = restore.retrieve_approved_memory("AGENT_MEMORY_SYSTEM", registry_path=self.registry, index_root=self.index_root)
        self.assertEqual(result["status"], "STALE")
        self.assertEqual(result["coverage_status"], "UNKNOWN")
        self.assertFalse(result["records"])
        self.assertTrue(result["warnings"])

    def test_missing_index_is_unavailable_not_no_match(self):
        result = restore.retrieve_approved_memory("AGENT_MEMORY_SYSTEM", registry_path=self.registry, index_root=self.root / "missing-index")
        self.assertEqual(result["status"], "UNAVAILABLE")
        self.assertEqual(result["coverage_status"], "UNKNOWN")

    def test_restore_packet_composes_task_packet_and_partial_memory_status(self):
        with mock.patch.object(restore, "build_verified_session_packet", return_value=dict(self.base_packet)):
            packet = restore.build_memory_aware_packet(
                Path("projects/AGENT_MEMORY_SYSTEM/TASK_STATE.md"),
                Path("projects/AGENT_MEMORY_SYSTEM/HANDOFF.md"),
                Path("projects/AGENT_MEMORY_SYSTEM/events.jsonl"),
                "alexbotleh-oss/agent-knowledge-base",
                registry_path=self.registry, index_root=self.index_root,
            )
        self.assertEqual(packet["status"], "RESTORED_PACKET_WITH_PARTIAL_MEMORY")
        self.assertEqual(packet["semantic_memory"]["status"], "PARTIAL")
        self.assertEqual(packet["semantic_memory"]["index_freshness"]["status"], "CURRENT_PARTIAL")

    def test_partial_no_match_triggers_read_only_relocation_discovery(self):
        archive = self.root / "archive"
        archive.mkdir()
        (archive / "old_notes.md").write_text(
            "The missing source marker is retained here with historical context.",
            encoding="utf-8",
        )
        no_match = {
            "status": "PARTIAL_NO_MATCH", "coverage_status": "PARTIAL",
            "records": [], "warnings": ["No match in the current partial index."],
        }
        with mock.patch.object(restore, "build_verified_session_packet", return_value=dict(self.base_packet)), \
             mock.patch.object(restore, "retrieve_approved_memory", return_value=no_match):
            packet = restore.build_memory_aware_packet(
                Path("projects/AGENT_MEMORY_SYSTEM/TASK_STATE.md"),
                Path("projects/AGENT_MEMORY_SYSTEM/HANDOFF.md"),
                Path("projects/AGENT_MEMORY_SYSTEM/events.jsonl"),
                "alexbotleh-oss/agent-knowledge-base",
                query="missing source marker",
                registry_path=self.registry, index_root=self.index_root,
            )
        discovery = packet["semantic_memory"]["relocation_discovery"]
        self.assertEqual(discovery["status"], "CANDIDATES_FOUND")
        self.assertEqual(discovery["searches"][0]["status"], "CANDIDATES_UNVERIFIED")
        self.assertFalse(discovery["writes_performed"])
        self.assertEqual(packet["semantic_memory"]["status"], "PARTIAL_NO_MATCH")

    def test_adaptive_catalog_finds_stable_identity_elsewhere(self):
        source_root = self.root / "catalog-source"
        (source_root / "nested").mkdir(parents=True)
        identity = "SRC-ADAPTIVE-RESTORE-20261017"
        (source_root / "nested" / "record.json").write_text(
            json.dumps({"source_record_id": identity}), encoding="utf-8"
        )
        catalog_path = self.root / "source_catalog.json"
        catalog_path.write_text(json.dumps({
            "sources": [{
                "source_id": "temporary-source",
                "root": "catalog-source",
                "expected_path": "expected.json",
                "formats": ["json"],
                "priority": 1,
            }]
        }), encoding="utf-8")
        no_match = {
            "status": "PARTIAL_NO_MATCH", "coverage_status": "PARTIAL",
            "records": [], "warnings": ["No match in the current partial index."],
        }
        with mock.patch.object(restore, "build_verified_session_packet", return_value=dict(self.base_packet)), \
             mock.patch.object(restore, "retrieve_approved_memory", return_value=no_match):
            packet = restore.build_memory_aware_packet(
                Path("projects/AGENT_MEMORY_SYSTEM/TASK_STATE.md"),
                Path("projects/AGENT_MEMORY_SYSTEM/HANDOFF.md"),
                Path("projects/AGENT_MEMORY_SYSTEM/events.jsonl"),
                "alexbotleh-oss/agent-knowledge-base",
                task_id=identity,
                registry_path=self.registry, index_root=self.index_root,
                source_catalog_path=catalog_path,
            )
        discovery = packet["semantic_memory"]["relocation_discovery"]
        self.assertEqual(discovery["status"], "VERIFIED_MATCH_FOUND")
        self.assertFalse(discovery["writes_performed"])
        self.assertFalse(discovery["automatic_relocation_performed"])
        self.assertEqual(packet["semantic_memory"]["status"], "PARTIAL_NO_MATCH")

    def test_mismatched_project_scope_blocks_memory_retrieval(self):
        base = dict(self.base_packet)
        base["project_scope"] = dict(self.base_packet["project_scope"], event_log_project_id="CARD111")
        with mock.patch.object(restore, "build_verified_session_packet", return_value=base):
            packet = restore.build_memory_aware_packet(
                Path("projects/AGENT_MEMORY_SYSTEM/TASK_STATE.md"),
                Path("projects/AGENT_MEMORY_SYSTEM/HANDOFF.md"),
                Path("projects/AGENT_MEMORY_SYSTEM/events.jsonl"),
                "alexbotleh-oss/agent-knowledge-base",
                registry_path=self.registry, index_root=self.index_root,
            )
        self.assertEqual(packet["semantic_memory"]["status"], "AMBIGUOUS_SCOPE")
        self.assertEqual(packet["status"], "RESTORED_PACKET_WITH_MEMORY_UNAVAILABLE")

    def test_blocked_base_restore_does_not_attempt_memory_retrieval(self):
        with mock.patch.object(restore, "build_verified_session_packet", return_value={"status":"REVISION_CHECK_BLOCKED"}), \
             mock.patch.object(restore, "retrieve_approved_memory") as retrieval:
            packet = restore.build_memory_aware_packet(
                Path("task"), Path("handoff"), Path("events"), "alexbotleh-oss/agent-knowledge-base",
                registry_path=self.registry, index_root=self.index_root,
            )
        self.assertEqual(packet["semantic_memory"]["status"], "NOT_ATTEMPTED")
        retrieval.assert_not_called()

    def test_limit_is_validated(self):
        result = restore.retrieve_approved_memory("AGENT_MEMORY_SYSTEM", limit=0, registry_path=self.registry, index_root=self.index_root)
        self.assertEqual(result["status"], "INVALID")


if __name__ == "__main__":
    unittest.main()
