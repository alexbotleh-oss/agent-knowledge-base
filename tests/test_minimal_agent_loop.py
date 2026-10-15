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
        self.assertFalse(result["writes_performed"])
        self.assertFalse(result["execution_performed"])

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
        self.assertEqual(result["next_action_policy"], "REVIEW_CONTEXT_AND_CANDIDATES")

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
