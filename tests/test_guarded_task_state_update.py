import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from guarded_task_state_update import apply_checkpoint, sha256_bytes


class GuardedTaskStateUpdateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.project = self.root / "projects" / "TEST_PROJECT"
        self.project.mkdir(parents=True)
        self.task_state = self.project / "TASK_STATE.md"
        self.task_state.write_text("# Task state\n\nOriginal checkpoint.\n", encoding="utf-8")
        event_dir = self.root / "projects" / "AGENT_MEMORY_SYSTEM"
        event_dir.mkdir(parents=True)
        self.event_log = event_dir / "events.jsonl"
        self.event_log.write_text(json.dumps({"event_id": "EVT-TEST-001", "type": "cross_branch_result"}) + "\n", encoding="utf-8")
        self.proposal = {
            "update_id": "UPDATE-TEST-001",
            "expected_sha256": sha256_bytes(self.task_state.read_bytes()),
            "parent_checkpoint_id": "CKPT-TEST-001",
            "event_id": "EVT-TEST-001",
            "checkpoint_markdown": "- Verified child result received; parent acceptance criteria still require review.",
        }

    def tearDown(self):
        self.tmp.cleanup()

    def test_appends_linked_checkpoint_without_removing_history(self):
        result = apply_checkpoint(self.task_state, self.event_log, self.proposal, trust_verdict={"status": "AUTHORIZED_FOR_PLANNING"})
        text = self.task_state.read_text(encoding="utf-8")
        self.assertEqual(result["status"], "APPLIED")
        self.assertIn("Original checkpoint.", text)
        self.assertIn("UPDATE-TEST-001", text)
        self.assertIn("EVT-TEST-001", text)
        self.assertEqual(result["new_sha256"], sha256_bytes(self.task_state.read_bytes()))

    def test_exact_replay_is_idempotent(self):
        first = apply_checkpoint(self.task_state, self.event_log, self.proposal, trust_verdict={"status": "AUTHORIZED_FOR_PLANNING"})
        before = self.task_state.read_bytes()
        second = apply_checkpoint(self.task_state, self.event_log, self.proposal, trust_verdict={"status": "AUTHORIZED_FOR_PLANNING"})
        self.assertEqual(first["status"], "APPLIED")
        self.assertEqual(second["status"], "ALREADY_APPLIED")
        self.assertEqual(before, self.task_state.read_bytes())

    def test_stale_expected_revision_refuses_to_write(self):
        self.task_state.write_text("# Newer state\n", encoding="utf-8")
        before = self.task_state.read_bytes()
        result = apply_checkpoint(self.task_state, self.event_log, self.proposal, trust_verdict={"status": "AUTHORIZED_FOR_PLANNING"})
        self.assertEqual(result["status"], "STALE_REVISION")
        self.assertEqual(before, self.task_state.read_bytes())

    def test_missing_supporting_event_refuses_to_write(self):
        proposal = dict(self.proposal, event_id="EVT-NOT-FOUND")
        before = self.task_state.read_bytes()
        result = apply_checkpoint(self.task_state, self.event_log, proposal, trust_verdict={"status": "AUTHORIZED_FOR_PLANNING"})
        self.assertEqual(result["status"], "REJECTED")
        self.assertEqual(before, self.task_state.read_bytes())

    def test_existing_lock_fails_closed(self):
        lock = self.task_state.with_name(self.task_state.name + ".lock")
        lock.write_text("active writer", encoding="utf-8")
        before = self.task_state.read_bytes()
        result = apply_checkpoint(self.task_state, self.event_log, self.proposal, trust_verdict={"status": "AUTHORIZED_FOR_PLANNING"})
        self.assertEqual(result["status"], "LOCKED")
        self.assertEqual(before, self.task_state.read_bytes())
        self.assertTrue(lock.exists())

    def test_malformed_event_log_refuses_to_write(self):
        self.event_log.write_text("{bad json}\n", encoding="utf-8")
        before = self.task_state.read_bytes()
        result = apply_checkpoint(self.task_state, self.event_log, self.proposal, trust_verdict={"status": "AUTHORIZED_FOR_PLANNING"})
        self.assertEqual(result["status"], "REJECTED")
        self.assertEqual(before, self.task_state.read_bytes())

    def test_duplicate_update_id_with_changed_payload_is_conflict(self):
        first = apply_checkpoint(self.task_state, self.event_log, self.proposal, trust_verdict={"status": "AUTHORIZED_FOR_PLANNING"})
        before = self.task_state.read_bytes()
        changed = dict(self.proposal, checkpoint_markdown="- Different content under same update ID.")
        second = apply_checkpoint(self.task_state, self.event_log, changed)
        self.assertEqual(first["status"], "APPLIED")
        self.assertEqual(second["status"], "CONFLICT")
        self.assertEqual(before, self.task_state.read_bytes())


    def test_arbitrary_target_path_is_rejected(self):
        arbitrary = self.project / "notes.md"
        arbitrary.write_text("do not mutate", encoding="utf-8")
        before = arbitrary.read_bytes()
        result = apply_checkpoint(arbitrary, self.event_log, self.proposal, trust_verdict={"status": "AUTHORIZED_FOR_PLANNING"})
        self.assertEqual(result["status"], "REJECTED")
        self.assertEqual(before, arbitrary.read_bytes())



    def test_missing_trust_verdict_blocks_write_without_mutation(self):
        before = self.task_state.read_bytes()
        result = apply_checkpoint(self.task_state, self.event_log, self.proposal)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["reason"], "TrustPolicyViolated")
        self.assertEqual(result["trust_status"], "MISSING_TRUST_VERDICT")
        self.assertFalse(result["writes_performed"])
        self.assertEqual(before, self.task_state.read_bytes())

    def test_non_authorizing_trust_verdict_blocks_write_without_mutation(self):
        before = self.task_state.read_bytes()
        result = apply_checkpoint(
            self.task_state, self.event_log, self.proposal,
            trust_verdict={"status": "PLAN_REQUIRES_CONFIRMATION"},
        )
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["reason"], "TrustPolicyViolated")
        self.assertEqual(result["trust_status"], "PLAN_REQUIRES_CONFIRMATION")
        self.assertFalse(result["writes_performed"])
        self.assertEqual(before, self.task_state.read_bytes())


if __name__ == "__main__":
    unittest.main()
