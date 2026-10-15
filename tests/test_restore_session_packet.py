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
            "# HANDOFF\\n- **Следующий шаг:** unrelated project step\\n",
            encoding="utf-8",
        )
        packet = build_session_packet(self.task, other_handoff, self.events)
        self.assertEqual(packet["status"], "BLOCKED")
        self.assertIn("same project directory", packet["reason"])
        self.assertFalse(packet["writes_performed"])

    def test_duplicate_event_ids_block_ambiguous_source_linkage(self):
        self.events.write_text(
            json.dumps({"event_id": "EVT-TEST-001", "summary": "first"}) + "\\n"
            + json.dumps({"event_id": "EVT-TEST-001", "summary": "different second record"}) + "\\n",
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


if __name__ == "__main__":
    unittest.main()
