import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from branch_result_registry import acknowledge_result, publish_result
from reconcile_branch_returns import build_report


class ReconcileBranchReturnsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.project = self.root / "projects" / "AGENT_MEMORY_SYSTEM"
        self.project.mkdir(parents=True)
        self.event_log = self.project / "events.jsonl"
        self.task_state = self.project / "TASK_STATE.md"
        self.event_log.write_text("", encoding="utf-8")
        self.task_state.write_text("# Current state\n", encoding="utf-8")
        self.result = {
            "child_branch_id": "CHILD-RECON-1",
            "parent_checkpoint_id": "CKPT-RECON-1",
            "parent_task_id": "TASK-RECON-1",
            "result_key": "recon-v1",
            "result_status": "RESULT_REPORTED",
            "summary": "Reconciliation fixture result.",
            "source_refs": ["evidence://recon/1"],
            "reported_at": "2026-10-14T13:00:00Z",
            "evidence_status": "verified",
        }
        self.published = publish_result(self.event_log, self.result)

    def tearDown(self):
        self.tmp.cleanup()

    def test_reports_missing_acknowledgement_without_writing(self):
        before_events = self.event_log.read_bytes()
        before_state = self.task_state.read_bytes()
        report = build_report(self.event_log, [self.task_state])
        self.assertEqual(report["status"], "RECONCILIATION_REQUIRED")
        self.assertEqual(report["issues"][0]["kind"], "missing_owner_acknowledgement")
        self.assertFalse(report["writes_performed"])
        self.assertEqual(self.event_log.read_bytes(), before_events)
        self.assertEqual(self.task_state.read_bytes(), before_state)

    def test_reports_accepted_ack_without_task_checkpoint(self):
        ack = acknowledge_result(
            self.event_log, self.published["event_id"], "accepted",
            "owner-confirmation://recon", "2026-10-14T13:05:00Z",
        )
        self.assertEqual(ack["status"], "ACKNOWLEDGED")
        report = build_report(self.event_log, [self.task_state])
        self.assertTrue(any(i["kind"] == "accepted_ack_without_task_checkpoint" for i in report["issues"]))

    def test_consistent_when_ack_event_is_linked_from_task_state(self):
        ack = acknowledge_result(
            self.event_log, self.published["event_id"], "accepted",
            "owner-confirmation://recon", "2026-10-14T13:05:00Z",
        )
        self.task_state.write_text("# Current state\n\nAcknowledgement: " + ack["event_id"] + "\n", encoding="utf-8")
        report = build_report(self.event_log, [self.task_state])
        self.assertEqual(report["status"], "CONSISTENT")
        self.assertEqual(report["issues"], [])

    def test_malformed_event_log_is_rejected_read_only(self):
        self.event_log.write_text("{broken json\n", encoding="utf-8")
        before = self.event_log.read_bytes()
        report = build_report(self.event_log, [self.task_state])
        self.assertEqual(report["status"], "REJECTED")
        self.assertEqual(self.event_log.read_bytes(), before)

    def test_missing_task_state_is_rejected(self):
        report = build_report(self.event_log, [self.project / "missing-TASK_STATE.md"])
        self.assertEqual(report["status"], "REJECTED")


if __name__ == "__main__":
    unittest.main()
