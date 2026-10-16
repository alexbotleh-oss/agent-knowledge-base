import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from restore_session_packet import build_session_packet, sha256_file


class RestoreSessionPacketTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.project = self.root / "projects" / "TEST_PROJECT"
        self.project.mkdir(parents=True)
        self.task = self.project / "TASK_STATE.md"
        self.handoff = self.project / "HANDOFF.md"
        self.events = self.project / "events.jsonl"
        self.task.write_text(
            "# TASK_STATE\n- Goal: preserve memory continuity.\n"
            "## Active checkpoint — test\n- Next step: restore source-backed state.\n"
            "- Evidence: EVT-TEST-001\n",
            encoding="utf-8",
        )
        self.handoff.write_text(
            "# HANDOFF\n## Checkpoint test\n- Continue from EVT-TEST-001.\n",
            encoding="utf-8",
        )
        self.events.write_text(json.dumps({
            "event_id": "EVT-TEST-001",
            "type": "observation",
            "status": "verified",
            "summary": "A source-backed test event.",
        }) + "\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_restores_hashes_latest_excerpts_and_linked_events_without_writes(self):
        before = (self.task.read_bytes(), self.handoff.read_bytes(), self.events.read_bytes())
        packet = build_session_packet(self.task, self.handoff, self.events)
        self.assertEqual(packet["status"], "RESTORED_PACKET")
        self.assertEqual(packet["source_hashes"]["task_state_sha256"], sha256_file(self.task))
        self.assertIn("Goal: preserve memory continuity", packet["task_state_header"])
        self.assertIn("Next step: restore source-backed state", packet["latest_task_state_excerpt"])
        self.assertEqual([e["event_id"] for e in packet["linked_events"]], ["EVT-TEST-001"])
        self.assertFalse(packet["writes_performed"])
        self.assertEqual(before, (self.task.read_bytes(), self.handoff.read_bytes(), self.events.read_bytes()))

    def test_task_state_and_handoff_from_different_projects_are_blocked(self):
        other_project = self.root / "projects" / "OTHER_PROJECT"
        other_project.mkdir(parents=True)
        other_handoff = other_project / "HANDOFF.md"
        other_handoff.write_text(
            "# HANDOFF\n- **Следующий шаг:** unrelated project step\n",
            encoding="utf-8",
        )
        packet = build_session_packet(self.task, other_handoff, self.events)
        self.assertEqual(packet["status"], "BLOCKED")
        self.assertIn("same project directory", packet["reason"])
        self.assertFalse(packet["writes_performed"])

    def test_duplicate_event_ids_block_ambiguous_source_linkage(self):
        self.events.write_text(
            json.dumps({"event_id": "EVT-TEST-001", "summary": "first"}) + "\n"
            + json.dumps({"event_id": "EVT-TEST-001", "summary": "different second record"}) + "\n",
            encoding="utf-8",
        )
        packet = build_session_packet(self.task, self.handoff, self.events)
        self.assertEqual(packet["status"], "BLOCKED")
        self.assertEqual(packet["duplicate_event_ids"], ["EVT-TEST-001"])
        self.assertFalse(packet["writes_performed"])

    def test_missing_referenced_event_yields_partial_not_false_success(self):
        self.events.write_text("", encoding="utf-8")
        packet = build_session_packet(self.task, self.handoff, self.events)
        self.assertEqual(packet["status"], "PARTIAL")
        self.assertIn("EVT-TEST-001", packet["missing_event_refs"])

    def test_restores_transitive_event_references_in_journal_order(self):
        acknowledgement = {
            "event_id": "EVT-TEST-002",
            "type": "cross_branch_result_acknowledged",
            "related_event_ids": ["EVT-TEST-001"],
            "relations": [{"type": "acknowledges_result", "event_id": "EVT-TEST-001"}],
            "acknowledgement": {"result_event_id": "EVT-TEST-001"},
        }
        self.task.write_text(
            "# TASK_STATE\n- Goal: preserve memory continuity.\n"
            "## Active checkpoint — test\n- Next step: restore source-backed state.\n"
            "- Evidence: EVT-TEST-002\n",
            encoding="utf-8",
        )
        self.handoff.write_text(
            "# HANDOFF\n## Checkpoint test\n- Continue from EVT-TEST-002.\n",
            encoding="utf-8",
        )
        self.events.write_text(
            json.dumps({
                "event_id": "EVT-TEST-001",
                "type": "cross_branch_result",
                "summary": "Original child result.",
            }) + "\n"
            + json.dumps(acknowledgement) + "\n",
            encoding="utf-8",
        )

        packet = build_session_packet(self.task, self.handoff, self.events)

        self.assertEqual(packet["status"], "RESTORED_PACKET")
        self.assertEqual(
            [event["event_id"] for event in packet["linked_events"]],
            ["EVT-TEST-001", "EVT-TEST-002"],
        )
        self.assertEqual(packet["missing_event_refs"], [])

    def test_missing_transitive_event_reference_yields_partial(self):
        self.task.write_text(
            "# TASK_STATE\n- Goal: preserve memory continuity.\n"
            "## Active checkpoint — test\n- Next step: restore source-backed state.\n"
            "- Evidence: EVT-TEST-002\n",
            encoding="utf-8",
        )
        self.handoff.write_text(
            "# HANDOFF\n## Checkpoint test\n- Continue from EVT-TEST-002.\n",
            encoding="utf-8",
        )
        self.events.write_text(json.dumps({
            "event_id": "EVT-TEST-002",
            "type": "cross_branch_result_acknowledged",
            "related_event_ids": ["EVT-TEST-MISSING"],
            "relations": [{"type": "acknowledges_result", "event_id": "EVT-TEST-MISSING"}],
            "acknowledgement": {"result_event_id": "EVT-TEST-MISSING"},
        }) + "\n", encoding="utf-8")

        packet = build_session_packet(self.task, self.handoff, self.events)

        self.assertEqual(packet["status"], "PARTIAL")
        self.assertEqual(packet["missing_event_refs"], ["EVT-TEST-MISSING"])
        self.assertEqual([event["event_id"] for event in packet["linked_events"]], ["EVT-TEST-002"])

    def test_missing_canonical_file_yields_blocked(self):
        packet = build_session_packet(self.task, self.handoff, self.root / "missing.jsonl")
        self.assertEqual(packet["status"], "BLOCKED")
        self.assertFalse(packet["writes_performed"])

    def test_corrupt_event_log_yields_blocked(self):
        self.events.write_text("{broken json\n", encoding="utf-8")
        packet = build_session_packet(self.task, self.handoff, self.events)
        self.assertEqual(packet["status"], "BLOCKED")

    def test_packet_excerpt_respects_max_chars_when_no_checkpoint_heading(self):
        self.task.write_text("x" * 500, encoding="utf-8")
        self.handoff.write_text("y" * 500, encoding="utf-8")
        self.events.write_text("", encoding="utf-8")
        packet = build_session_packet(self.task, self.handoff, self.events, max_chars=100)
        self.assertLessEqual(len(packet["latest_task_state_excerpt"]), 100)
        self.assertLessEqual(len(packet["latest_handoff_excerpt"]), 100)


    def test_revision_evidence_distinguishes_recorded_current_and_historical_state(self):
        checkpoint = {
            "repository_state": {
                "last_verified_code_head": "a" * 40,
                "exact_head_ci_run_id": 12345,
                "exact_head_ci_conclusion": "success",
            },
            "historical_repository_state": {
                "last_verified_code_head": "b" * 40,
                "exact_head_ci_run_id": 12300,
            },
            "revision_semantics": {"metadata_revision": "commit containing metadata"},
        }
        (self.project / "CONTINUITY_CHECKPOINT.json").write_text(
            json.dumps(checkpoint), encoding="utf-8"
        )
        from restore_session_packet import load_revision_evidence

        recorded = load_revision_evidence(self.project)
        self.assertEqual(recorded["status"], "RECORDED_EVIDENCE_ONLY")
        self.assertEqual(recorded["recorded_code_head"], "a" * 40)
        self.assertEqual(
            recorded["historical_repository_state"]["last_verified_code_head"],
            "b" * 40,
        )

        matching = load_revision_evidence(
            self.project, observed_code_head="a" * 40, observed_ci_run_id="12345"
        )
        self.assertEqual(matching["status"], "OBSERVED_CODE_AND_CI_MATCH")

        mismatch = load_revision_evidence(
            self.project, observed_code_head="c" * 40, observed_ci_run_id="12345"
        )
        self.assertEqual(mismatch["status"], "OBSERVED_CODE_HEAD_MISMATCH")
        self.assertFalse(mismatch["writes_performed"])

    def test_revision_evidence_missing_checkpoint_is_explicitly_unavailable(self):
        from restore_session_packet import load_revision_evidence

        evidence = load_revision_evidence(self.project)
        self.assertEqual(evidence["status"], "UNAVAILABLE")
        self.assertFalse(evidence["writes_performed"])

    def test_restore_packet_exposes_revision_evidence_without_blocking_task_restore(self):
        (self.project / "CONTINUITY_CHECKPOINT.json").write_text(json.dumps({
            "repository_state": {
                "last_verified_code_head": "a" * 40,
                "exact_head_ci_run_id": 12345,
                "exact_head_ci_conclusion": "success",
            },
            "historical_repository_state": {
                "last_verified_code_head": "b" * 40,
                "exact_head_ci_run_id": 12300,
            },
        }), encoding="utf-8")
        packet = build_session_packet(
            self.task, self.handoff, self.events, observed_code_head="c" * 40
        )
        self.assertEqual(packet["status"], "RESTORED_PACKET")
        self.assertEqual(
            packet["repository_revision_evidence"]["status"],
            "OBSERVED_CODE_HEAD_MISMATCH",
        )


if __name__ == "__main__":
    unittest.main()
