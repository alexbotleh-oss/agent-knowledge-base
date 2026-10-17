"""Integration tests for the local child-result -> owner acknowledgement -> task checkpoint path."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from branch_result_registry import acknowledge_result, publish_result
from guarded_task_state_update import apply_checkpoint, sha256_bytes


class ChildResultReturnRoundTripTests(unittest.TestCase):
    def test_result_ack_and_checkpoint_form_linked_recoverable_chain(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "projects" / "AGENT_MEMORY_SYSTEM"
            project.mkdir(parents=True)
            event_log = project / "events.jsonl"
            task_state = project / "TASK_STATE.md"
            event_log.write_text("", encoding="utf-8")
            task_state.write_text("# Task state\n\nParent checkpoint CKPT-1.\n", encoding="utf-8")

            result_payload = {
                "child_branch_id": "CHILD-1",
                "parent_checkpoint_id": "CKPT-1",
                "parent_task_id": "TASK-1",
                "result_key": "result-v1",
                "result_status": "RESULT_REPORTED",
                "summary": "Child branch produced a result for the parent question.",
                "source_refs": ["evidence://child/result-1"],
                "reported_at": "2026-10-14T12:00:00Z",
                "evidence_status": "verified",
            }
            first = publish_result(event_log, result_payload)
            # Model a lost acknowledgement: replaying the same result must not duplicate it.
            replay = publish_result(event_log, result_payload)
            self.assertEqual(first["status"], "RESULT_REPORTED")
            self.assertEqual(replay["status"], "ALREADY_PUBLISHED")

            ack = acknowledge_result(
                event_log, first["event_id"], "accepted",
                "owner-confirmation://decision-1", "2026-10-14T12:05:00Z",
            )
            self.assertEqual(ack["status"], "ACKNOWLEDGED")

            proposal = {
                "update_id": "UPDATE-1",
                "expected_sha256": sha256_bytes(task_state.read_bytes()),
                "parent_checkpoint_id": "CKPT-1",
                "event_id": ack["event_id"],
                "checkpoint_markdown": "- Child result accepted by owner; parent goal remains open until its remaining criteria are checked.",
            }
            applied = apply_checkpoint(task_state, event_log, proposal)
            repeated = apply_checkpoint(task_state, event_log, proposal)
            rows = [json.loads(line) for line in event_log.read_text(encoding="utf-8").splitlines()]
            state_text = task_state.read_text(encoding="utf-8")

            self.assertEqual(applied["status"], "APPLIED")
            self.assertEqual(repeated["status"], "ALREADY_APPLIED")
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[1]["related_event_ids"], [first["event_id"]])
            self.assertIn(ack["event_id"], state_text)
            self.assertIn("Parent checkpoint CKPT-1.", state_text)
            self.assertIn("parent goal remains open", state_text)

    def test_intervening_parent_change_blocks_stale_projection_and_can_be_replanned(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "projects" / "TEST_PROJECT"
            project.mkdir(parents=True)
            event_log = project / "events.jsonl"
            task_state = project / "TASK_STATE.md"
            event_log.write_text(json.dumps({"event_id": "EVT-1", "type": "cross_branch_result"}) + "\n", encoding="utf-8")
            task_state.write_text("# Initial\n", encoding="utf-8")
            proposal = {
                "update_id": "UPDATE-2",
                "expected_sha256": sha256_bytes(task_state.read_bytes()),
                "parent_checkpoint_id": "CKPT-2",
                "event_id": "EVT-1",
                "checkpoint_markdown": "- New child result was reviewed.",
            }
            task_state.write_text("# Parent changed while child work was running.\n", encoding="utf-8")
            before = task_state.read_bytes()
            stale = apply_checkpoint(task_state, event_log, proposal)
            self.assertEqual(stale["status"], "STALE_REVISION")
            self.assertEqual(task_state.read_bytes(), before)

            refreshed = dict(proposal, expected_sha256=sha256_bytes(task_state.read_bytes()))
            retried = apply_checkpoint(task_state, event_log, refreshed)
            self.assertEqual(retried["status"], "APPLIED")
            self.assertIn("Parent changed while child work was running.", task_state.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
