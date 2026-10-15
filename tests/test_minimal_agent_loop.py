import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from context_extractor import extract_semantic_context
from minimal_agent_loop import retrieve_experience_candidates, run_minimal_agent_loop
from restore_session_packet import build_session_packet


class MinimalAgentLoopTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.project = self.root / "projects" / "TEST"
        self.project.mkdir(parents=True)
        self.task = self.project / "TASK_STATE.md"
        self.handoff = self.project / "HANDOFF.md"
        self.events = self.project / "events.jsonl"
        self.experience = self.root / "shared-events.jsonl"
        self._write_events(self.events, [{
            "event_id": "EVT-CURRENT-1",
            "type": "checkpoint",
            "summary": "Current task checkpoint",
            "status": "verified",
            "lifecycle_status": "accepted",
        }])
        self.task.write_text(
            "# TASK_STATE\n"
            "- **Активная задача в текущей сессии:** восстановить staging snapshot\n"
            "- **Последнее событие:** EVT-CURRENT-1\n",
            encoding="utf-8",
        )
        self.handoff.write_text(
            "# HANDOFF\n"
            "- **Следующий шаг:** проверить staging snapshot\n",
            encoding="utf-8",
        )

    def tearDown(self):
        self.tmp.cleanup()

    @staticmethod
    def _write_events(path, events):
        path.write_text(
            "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in events),
            encoding="utf-8",
        )

    def test_restore_then_retrieve_returns_provenance_without_auto_applicability(self):
        self._write_events(self.experience, [
            {
                "event_id": "EVT-EXP-1",
                "type": "test_result",
                "summary": "Staging snapshot crash recovery succeeded",
                "status": "verified",
                "lifecycle_status": "accepted",
                "tool_tags": ["Python", "SQLite"],
                "evidence": [{"kind": "test", "ref": "tests/test_staging.py"}],
            }
        ])
        result = run_minimal_agent_loop(
            self.task, self.handoff, self.events,
            "Investigate staging snapshot crash recovery", [self.experience],
        )
        self.assertEqual(result["status"], "READY_FOR_REVIEW")
        self.assertEqual(result["restore_packet_status"], "RESTORED_PACKET")
        self.assertEqual(result["context"]["active_goal"], "восстановить staging snapshot")
        self.assertTrue(result["context"]["freshness_verified"])
        self.assertEqual(result["retrieval"]["status"], "CANDIDATES_FOUND")
        candidate = result["retrieval"]["candidates"][0]
        self.assertEqual(candidate["event_id"], "EVT-EXP-1")
        self.assertEqual(candidate["transfer_decision"], "UNASSESSED")
        self.assertEqual(candidate["source"]["path"], str(self.experience))
        self.assertEqual(candidate["source"]["line"], 1)
        self.assertEqual(candidate["evidence_refs"][0]["ref"], "tests/test_staging.py")
        self.assertEqual(
            result["checkpoint_currentness_gate"]["status"],
            "BLOCKED_CURRENTNESS_UNVERIFIED",
        )
        self.assertFalse(result["checkpoint_currentness_gate"]["authorized_for_planning"])
        self.assertFalse(result["writes_performed"])
        self.assertFalse(result["execution_performed"])

    def test_real_agms_sources_do_not_claim_semantic_currentness_from_hashes(self):
        # Exercise the actual repository checkpoint and event log, not a fixture.
        project = ROOT / "projects" / "AGENT_MEMORY_SYSTEM"
        result = run_minimal_agent_loop(
            project / "TASK_STATE.md",
            project / "HANDOFF.md",
            project / "events.jsonl",
            "memory archive reconciliation",
            [project / "events.jsonl"],
        )
        self.assertEqual(
            result["context"]["source_freshness"],
            {"task_state": "CURRENT", "handoff": "CURRENT", "events": "CURRENT"},
        )
        self.assertEqual(
            result["checkpoint_currentness_gate"]["status"],
            "BLOCKED_CURRENTNESS_UNVERIFIED",
        )
        self.assertFalse(result["checkpoint_currentness_gate"]["authorized_for_planning"])
        self.assertFalse(result["writes_performed"])
        self.assertFalse(result["execution_performed"])

    def test_project_match_is_only_a_precondition_not_applicability(self):
        self._write_events(self.experience, [
            {
                "event_id": "EVT-SAME-PROJECT",
                "project_id": "CARD111",
                "type": "lesson",
                "summary": "QR cache invalidation after deploy",
                "status": "verified",
            },
            {
                "event_id": "EVT-OTHER-PROJECT",
                "project_id": "ORGANISM",
                "type": "lesson",
                "summary": "QR cache invalidation after deploy",
                "status": "verified",
            },
            {
                "event_id": "EVT-UNKNOWN-PROJECT",
                "type": "lesson",
                "summary": "QR cache invalidation after deploy",
                "status": "verified",
            },
        ])
        result = retrieve_experience_candidates(
            "QR cache invalidation after deploy",
            [self.experience],
            current_project_id="CARD111",
        )
        by_id = {item["event_id"]: item for item in result["candidates"]}
        self.assertEqual(by_id["EVT-SAME-PROJECT"]["project_scope_match"], "MATCH")
        self.assertEqual(
            by_id["EVT-SAME-PROJECT"]["applicability_gate"],
            "SCOPE_MATCHED_REQUIRES_REVIEW",
        )
        self.assertEqual(
            by_id["EVT-OTHER-PROJECT"]["applicability_gate"],
            "OUT_OF_PROJECT_SCOPE",
        )
        self.assertEqual(
            by_id["EVT-UNKNOWN-PROJECT"]["applicability_gate"],
            "PROJECT_SCOPE_UNKNOWN",
        )
        self.assertTrue(all(item["transfer_decision"] == "UNASSESSED" for item in by_id.values()))
        self.assertTrue(result["applicability_policy"]["project_match_is_necessary_not_sufficient"])
        self.assertEqual(
            result["applicability_policy"]["task_branch_match"],
            "NOT_EVALUATED_SCHEMA_FIELD_NOT_GUARANTEED",
        )

    def test_project_scope_is_unknown_without_explicit_current_project(self):
        self._write_events(self.experience, [{
            "event_id": "EVT-PROJECT",
            "project_id": "CARD111",
            "summary": "QR cache invalidation after deploy",
        }])
        result = retrieve_experience_candidates(
            "QR cache invalidation after deploy", [self.experience]
        )
        candidate = result["candidates"][0]
        self.assertEqual(candidate["project_scope_match"], "UNKNOWN")
        self.assertEqual(candidate["applicability_gate"], "PROJECT_SCOPE_UNKNOWN")
        self.assertEqual(candidate["transfer_decision"], "UNASSESSED")

    def test_evidence_quality_gate_requires_review_and_never_auto_accepts_verified(self):
        self._write_events(self.experience, [
            {
                "event_id": "EVT-VERIFIED-WITH-REF",
                "project_id": "CARD111",
                "summary": "QR cache recovery verified",
                "status": "verified",
                "evidence": [{"kind": "test", "ref": "tests/test_cache.py"}],
            },
            {
                "event_id": "EVT-VERIFIED-NO-REF",
                "project_id": "CARD111",
                "summary": "QR cache recovery verified",
                "status": "verified",
            },
            {
                "event_id": "EVT-OBSERVED",
                "project_id": "CARD111",
                "summary": "QR cache recovery observed",
                "status": "observed",
            },
            {
                "event_id": "EVT-REPORTED",
                "project_id": "CARD111",
                "summary": "QR cache recovery reported",
                "status": "reported",
            },
            {
                "event_id": "EVT-DISPUTED",
                "project_id": "CARD111",
                "summary": "QR cache recovery disputed",
                "status": "verified",
                "lifecycle_status": "disputed",
                "evidence": [{"kind": "test", "ref": "tests/test_cache.py"}],
            },
            {
                "event_id": "EVT-OTHER-SCOPE",
                "project_id": "ORGANISM",
                "summary": "QR cache recovery verified",
                "status": "verified",
                "evidence": [{"kind": "test", "ref": "tests/test_cache.py"}],
            },
        ])
        result = retrieve_experience_candidates(
            "QR cache recovery", [self.experience], current_project_id="CARD111"
        )
        by_id = {item["event_id"]: item for item in result["candidates"]}

        self.assertEqual(
            by_id["EVT-VERIFIED-WITH-REF"]["evidence_quality"]["state"],
            "VERIFIED_LABEL_WITH_EVIDENCE_POINTERS",
        )
        self.assertEqual(
            by_id["EVT-VERIFIED-WITH-REF"]["candidate_review_gate"],
            "SCOPE_MATCHED_VERIFIED_LABEL_WITH_REFS_REVIEW_REQUIRED",
        )
        self.assertEqual(
            by_id["EVT-VERIFIED-NO-REF"]["evidence_quality"]["state"],
            "VERIFIED_LABEL_WITHOUT_EVIDENCE_POINTERS",
        )
        self.assertEqual(
            by_id["EVT-VERIFIED-NO-REF"]["candidate_review_gate"],
            "SCOPE_MATCHED_VERIFIED_LABEL_NO_REFS_REVIEW_REQUIRED",
        )
        self.assertEqual(
            by_id["EVT-OBSERVED"]["candidate_review_gate"],
            "SCOPE_MATCHED_OBSERVED_NO_REFS_REVIEW_REQUIRED",
        )
        self.assertEqual(
            by_id["EVT-REPORTED"]["candidate_review_gate"],
            "SCOPE_MATCHED_LOW_EVIDENCE_REVIEW_REQUIRED",
        )
        self.assertEqual(
            by_id["EVT-DISPUTED"]["candidate_review_gate"],
            "SCOPE_MATCHED_DISPUTED_REQUIRES_CONFLICT_REVIEW",
        )
        self.assertEqual(
            by_id["EVT-OTHER-SCOPE"]["candidate_review_gate"],
            "OUT_OF_PROJECT_SCOPE",
        )
        self.assertTrue(all(item["transfer_decision"] == "UNASSESSED" for item in by_id.values()))
        self.assertTrue(result["applicability_policy"]["verified_label_alone_is_never_sufficient"])
        self.assertTrue(result["applicability_policy"]["evidence_quality_is_metadata_not_claim_validation"])

    def test_missing_local_evidence_file_blocks_verified_candidate(self):
        evidence_root = self.root / "evidence-root"
        evidence_root.mkdir()
        evidence_file = evidence_root / "test_result.txt"
        evidence_file.write_text("temporary supporting material", encoding="utf-8")
        evidence_file.unlink()

        self._write_events(self.experience, [{
            "event_id": "EVT-BROKEN-EVIDENCE",
            "project_id": "CARD111",
            "type": "test_result",
            "summary": "QR cache recovery verified",
            "status": "verified",
            "evidence": [{"kind": "file", "ref": "test_result.txt"}],
        }])
        result = retrieve_experience_candidates(
            "QR cache recovery",
            [self.experience],
            current_project_id="CARD111",
            evidence_root=evidence_root,
        )
        candidate = result["candidates"][0]
        self.assertEqual(
            candidate["evidence_source_validation"]["status"], "MISSING_SOURCE"
        )
        self.assertEqual(
            candidate["evidence_source_validation"]["references"][0]["status"],
            "MISSING",
        )
        self.assertEqual(
            candidate["candidate_review_gate"],
            "SCOPE_MATCHED_EVIDENCE_SOURCE_UNAVAILABLE_BLOCKED",
        )
        self.assertEqual(candidate["transfer_decision"], "UNASSESSED")
        self.assertFalse(result["writes_performed"])

    def test_empty_local_evidence_file_blocks_verified_candidate(self):
        evidence_root = self.root / "evidence-root"
        evidence_root.mkdir()
        (evidence_root / "empty.txt").write_bytes(b"")

        self._write_events(self.experience, [{
            "event_id": "EVT-EMPTY-EVIDENCE",
            "project_id": "CARD111",
            "type": "test_result",
            "summary": "QR cache recovery verified",
            "status": "verified",
            "evidence": [{"kind": "file", "ref": "empty.txt"}],
        }])
        result = retrieve_experience_candidates(
            "QR cache recovery",
            [self.experience],
            current_project_id="CARD111",
            evidence_root=evidence_root,
        )
        candidate = result["candidates"][0]
        self.assertEqual(candidate["evidence_source_validation"]["status"], "EMPTY_SOURCE")
        self.assertEqual(
            candidate["evidence_source_validation"]["references"][0]["status"],
            "EMPTY_FILE",
        )
        self.assertEqual(
            candidate["candidate_review_gate"],
            "SCOPE_MATCHED_EVIDENCE_SOURCE_UNAVAILABLE_BLOCKED",
        )
        self.assertEqual(candidate["transfer_decision"], "UNASSESSED")
        self.assertFalse(result["writes_performed"])

    def test_binary_local_evidence_file_blocks_verified_candidate(self):
        evidence_root = self.root / "evidence-root"
        evidence_root.mkdir()
        (evidence_root / "binary.dat").write_bytes(b"\x00\x01\xff")

        self._write_events(self.experience, [{
            "event_id": "EVT-BINARY-EVIDENCE",
            "project_id": "CARD111",
            "type": "test_result",
            "summary": "QR cache recovery verified",
            "status": "verified",
            "evidence": [{"kind": "file", "ref": "binary.dat"}],
        }])
        result = retrieve_experience_candidates(
            "QR cache recovery",
            [self.experience],
            current_project_id="CARD111",
            evidence_root=evidence_root,
        )
        candidate = result["candidates"][0]
        self.assertEqual(candidate["evidence_source_validation"]["status"], "BINARY_SOURCE")
        self.assertEqual(
            candidate["evidence_source_validation"]["references"][0]["status"],
            "BINARY_FILE",
        )
        self.assertEqual(
            candidate["candidate_review_gate"],
            "SCOPE_MATCHED_EVIDENCE_SOURCE_UNAVAILABLE_BLOCKED",
        )
        self.assertEqual(candidate["transfer_decision"], "UNASSESSED")
        self.assertFalse(result["writes_performed"])

    def test_local_evidence_validation_requires_explicit_root(self):
        self._write_events(self.experience, [{
            "event_id": "EVT-UNSCOPED-EVIDENCE",
            "project_id": "CARD111",
            "type": "test_result",
            "summary": "QR cache recovery verified",
            "status": "verified",
            "evidence": [{"kind": "file", "ref": "test_result.txt"}],
        }])
        result = retrieve_experience_candidates(
            "QR cache recovery", [self.experience], current_project_id="CARD111"
        )
        candidate = result["candidates"][0]
        self.assertEqual(
            candidate["evidence_source_validation"]["status"],
            "NOT_CHECKED_NO_EVIDENCE_ROOT",
        )
        self.assertEqual(candidate["transfer_decision"], "UNASSESSED")

    def test_evidence_path_traversal_is_not_followed_outside_root(self):
        evidence_root = self.root / "evidence-root"
        evidence_root.mkdir()
        (self.root / "outside.txt").write_text("outside evidence", encoding="utf-8")
        self._write_events(self.experience, [{
            "event_id": "EVT-OUTSIDE-EVIDENCE",
            "project_id": "CARD111",
            "type": "test_result",
            "summary": "QR cache recovery verified",
            "status": "verified",
            "evidence": [{"kind": "file", "ref": "../outside.txt"}],
        }])
        result = retrieve_experience_candidates(
            "QR cache recovery", [self.experience],
            current_project_id="CARD111", evidence_root=evidence_root,
        )
        candidate = result["candidates"][0]
        self.assertEqual(
            candidate["evidence_source_validation"]["references"][0]["status"],
            "OUTSIDE_EVIDENCE_ROOT",
        )
        self.assertEqual(
            candidate["evidence_source_validation"]["status"],
            "OUTSIDE_EVIDENCE_ROOT",
        )
        self.assertEqual(
            candidate["candidate_review_gate"],
            "SCOPE_MATCHED_EVIDENCE_SOURCE_OUTSIDE_ROOT_REVIEW_REQUIRED",
        )
        self.assertEqual(candidate["transfer_decision"], "UNASSESSED")
        self.assertFalse(result["writes_performed"])

    def test_short_text_evidence_file_is_readable(self):
        evidence_root = self.root / "evidence-root"
        evidence_root.mkdir()
        (evidence_root / "short.txt").write_text("valid text", encoding="utf-8")
        self._write_events(self.experience, [{
            "event_id": "EVT-SHORT-EVIDENCE",
            "project_id": "CARD111",
            "type": "test_result",
            "summary": "QR cache recovery verified",
            "status": "verified",
            "evidence": [{"kind": "file", "ref": "short.txt"}],
        }])
        result = retrieve_experience_candidates(
            "QR cache recovery", [self.experience],
            current_project_id="CARD111", evidence_root=evidence_root,
        )
        candidate = result["candidates"][0]
        self.assertEqual(
            candidate["evidence_source_validation"]["references"][0]["status"],
            "EXISTS_READABLE",
        )
        self.assertEqual(
            candidate["evidence_source_validation"]["status"],
            "ALL_LOCAL_FILES_READABLE",
        )
        self.assertEqual(candidate["transfer_decision"], "UNASSESSED")

    def test_exact_8192_byte_text_evidence_file_is_readable(self):
        evidence_root = self.root / "evidence-root"
        evidence_root.mkdir()
        payload = b"a" * 8190 + "é".encode("utf-8")
        self.assertEqual(len(payload), 8192)
        (evidence_root / "boundary.txt").write_bytes(payload)
        self._write_events(self.experience, [{
            "event_id": "EVT-8192-EVIDENCE",
            "project_id": "CARD111",
            "type": "test_result",
            "summary": "QR cache recovery verified",
            "status": "verified",
            "evidence": [{"kind": "file", "ref": "boundary.txt"}],
        }])
        result = retrieve_experience_candidates(
            "QR cache recovery", [self.experience],
            current_project_id="CARD111", evidence_root=evidence_root,
        )
        candidate = result["candidates"][0]
        self.assertEqual(
            candidate["evidence_source_validation"]["references"][0]["status"],
            "EXISTS_READABLE",
        )
        self.assertEqual(candidate["transfer_decision"], "UNASSESSED")

    def test_utf8_codepoint_split_at_sample_boundary_is_not_binary(self):
        evidence_root = self.root / "evidence-root"
        evidence_root.mkdir()
        payload = b"a" * 8191 + "é".encode("utf-8")
        self.assertEqual(len(payload), 8193)
        (evidence_root / "split.txt").write_bytes(payload)
        self._write_events(self.experience, [{
            "event_id": "EVT-UTF8-SPLIT-EVIDENCE",
            "project_id": "CARD111",
            "type": "test_result",
            "summary": "QR cache recovery verified",
            "status": "verified",
            "evidence": [{"kind": "file", "ref": "split.txt"}],
        }])
        result = retrieve_experience_candidates(
            "QR cache recovery", [self.experience],
            current_project_id="CARD111", evidence_root=evidence_root,
        )
        candidate = result["candidates"][0]
        self.assertEqual(
            candidate["evidence_source_validation"]["references"][0]["status"],
            "EXISTS_READABLE",
        )
        self.assertEqual(candidate["transfer_decision"], "UNASSESSED")

    def test_disputed_and_conflicting_candidates_are_retained_separately(self):
        self._write_events(self.experience, [
            {
                "event_id": "EVT-EXP-OLD",
                "type": "lesson",
                "summary": "Staging snapshot is safe after crash",
                "status": "reported",
                "lifecycle_status": "disputed",
                "notes": "Conflicts with newer observation",
            },
            {
                "event_id": "EVT-EXP-NEW",
                "type": "observation",
                "summary": "Staging snapshot is unsafe after crash",
                "status": "observed",
                "lifecycle_status": "accepted",
                "relations": [{"type": "contradicts", "event_id": "EVT-EXP-OLD"}],
            },
        ])
        result = retrieve_experience_candidates(
            "staging snapshot crash", [self.experience], limit=10
        )
        self.assertEqual(result["status"], "CANDIDATES_FOUND")
        self.assertEqual({item["event_id"] for item in result["candidates"]},
                         {"EVT-EXP-OLD", "EVT-EXP-NEW"})
        old = next(item for item in result["candidates"] if item["event_id"] == "EVT-EXP-OLD")
        new = next(item for item in result["candidates"] if item["event_id"] == "EVT-EXP-NEW")
        self.assertEqual(old["lifecycle_status"], "disputed")
        self.assertEqual(old["transfer_decision"], "UNASSESSED")
        self.assertTrue(any("EVT-EXP-OLD" in str(rel) for rel in new["relations"]))

    def test_restart_reads_new_checkpoint_instead_of_reusing_old_packet(self):
        first = run_minimal_agent_loop(
            self.task, self.handoff, self.events, "restore staging"
        )
        self.assertEqual(first["context"]["active_goal"], "восстановить staging snapshot")
        self.task.write_text(
            "# TASK_STATE\n"
            "- **Активная задача в текущей сессии:** проверить импорт архива\n"
            "- **Последнее событие:** EVT-CURRENT-1\n",
            encoding="utf-8",
        )
        restarted = run_minimal_agent_loop(
            self.task, self.handoff, self.events, "continue"
        )
        self.assertEqual(restarted["context"]["active_goal"], "проверить импорт архива")
        self.assertEqual(restarted["context"]["source_freshness"]["task_state"], "CURRENT")

    def test_unknown_next_step_stays_unknown_and_blocks_trust_gate(self):
        self.task.write_text(
            "# TASK_STATE\n"
            "- **Активная задача в текущей сессии:** проверить staging snapshot\n"
            "- **Последнее событие:** EVT-CURRENT-1\n",
            encoding="utf-8",
        )
        self.handoff.write_text("# HANDOFF\nNo explicit next step.\n", encoding="utf-8")
        result = run_minimal_agent_loop(
            self.task, self.handoff, self.events, "check staging"
        )
        self.assertEqual(result["context"]["next_step"], "UNKNOWN")
        self.assertEqual(result["trust_gate"]["status"], "REFUSED_UNKNOWN_NEXT_STEP")
        self.assertEqual(result["next_action_policy"], "REVIEW_CANDIDATES_ONLY_NO_PLANNING")

    def test_invalid_event_log_fails_closed_without_partial_candidates(self):
        self.experience.write_text(
            json.dumps({"event_id": "EVT-OK", "summary": "staging snapshot"}) + "\n"
            + "{truncated json\n",
            encoding="utf-8",
        )
        result = retrieve_experience_candidates(
            "staging snapshot", [self.experience]
        )
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["candidates"], [])
        self.assertIn("INVALID_JSONL", result["errors"][0]["error"])
        self.assertFalse(result["writes_performed"])

    def test_missing_experience_source_blocks_retrieval(self):
        result = retrieve_experience_candidates(
            "staging snapshot", [self.root / "missing.jsonl"]
        )
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["candidates"], [])
        self.assertEqual(result["errors"][0]["error"], "MISSING_SOURCE")

    def test_old_packet_is_marked_stale_when_source_changes(self):
        packet = build_session_packet(self.task, self.handoff, self.events)
        self.task.write_text(
            "# TASK_STATE\n"
            "- **Активная задача в текущей сессии:** replaced checkpoint\n",
            encoding="utf-8",
        )
        context = extract_semantic_context(packet)
        self.assertEqual(context["status"], "SOURCE_CHANGED")
        self.assertFalse(context["freshness_verified"])
        self.assertEqual(context["field_status"]["active_goal"], "STALE_SOURCE")


if __name__ == "__main__":
    unittest.main()
