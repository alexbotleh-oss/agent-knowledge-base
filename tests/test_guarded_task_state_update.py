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
        self.task_state.write_text(
            "# Task state — TASK-TEST\n"
            "- **Активная задача в текущей сессии:** проверка записи контрольной точки\n"
            "- **Следующий шаг:** применить подтверждённую контрольную точку\n"
            "- **Последнее событие:** EVT-TEST-001\n"
            "\nOriginal checkpoint.\n",
            encoding="utf-8",
        )
        (self.project / "HANDOFF.md").write_text(
            "# HANDOFF\n- **Следующий шаг:** проверить запись контрольной точки\n",
            encoding="utf-8",
        )
        event_dir = self.root / "projects" / "AGENT_MEMORY_SYSTEM"
        event_dir.mkdir(parents=True)
        self.event_log = event_dir / "events.jsonl"
        result_event = {
            "event_id": "EVT-TEST-RESULT",
            "project_id": "AGENT_MEMORY_SYSTEM",
            "type": "cross_branch_result",
            "branch_return": {
                "parent_checkpoint_id": "CKPT-TEST-001",
                "parent_task_id": "TASK-TEST",
                "owner_acknowledgement": "PENDING",
            },
        }
        acknowledgement_event = {
            "event_id": "EVT-TEST-001",
            "project_id": "AGENT_MEMORY_SYSTEM",
            "type": "cross_branch_result_acknowledged",
            "outcome": "accepted",
            "related_event_ids": ["EVT-TEST-RESULT"],
            "acknowledgement": {
                "result_event_id": "EVT-TEST-RESULT",
                "decision": "accepted",
                "parent_checkpoint_id": "CKPT-TEST-001",
            },
            "relations": [
                {"type": "acknowledges_result", "event_id": "EVT-TEST-RESULT"},
                {"type": "reports_to_checkpoint", "checkpoint_id": "CKPT-TEST-001"},
                {"type": "belongs_to_task", "task_id": "TASK-TEST"},
            ],
        }
        self.event_log.write_text(
            json.dumps(result_event) + "\n" + json.dumps(acknowledgement_event) + "\n",
            encoding="utf-8",
        )
        self.proposal = {
            "update_id": "UPDATE-TEST-001",
            "expected_sha256": sha256_bytes(self.task_state.read_bytes()),
            "parent_checkpoint_id": "CKPT-TEST-001",
            "event_id": "EVT-TEST-001",
            "checkpoint_markdown": "- Verified child result received; parent acceptance criteria still require review.",
        }

    def tearDown(self):
        self.tmp.cleanup()

    def test_unacknowledged_child_result_cannot_update_task_state(self):
        proposal = dict(self.proposal, event_id="EVT-TEST-RESULT")
        before = self.task_state.read_bytes()
        result = apply_checkpoint(
            self.task_state, self.event_log, proposal,
            trust_verdict={"status": "AUTHORIZED_FOR_PLANNING"},
        )
        self.assertEqual(result["status"], "REJECTED")
        self.assertIn("must be acknowledged", result["errors"][0])
        self.assertEqual(self.task_state.read_bytes(), before)

    def test_wrong_parent_checkpoint_blocks_accepted_cross_project_result(self):
        proposal = dict(self.proposal, parent_checkpoint_id="CKPT-WRONG")
        before = self.task_state.read_bytes()
        result = apply_checkpoint(
            self.task_state, self.event_log, proposal,
            trust_verdict={"status": "AUTHORIZED_FOR_PLANNING"},
        )
        self.assertEqual(result["status"], "REJECTED")
        self.assertIn("checkpoint", result["errors"][0])
        self.assertEqual(self.task_state.read_bytes(), before)

    def test_appends_linked_checkpoint_without_removing_history(self):
        result = apply_checkpoint(self.task_state, self.event_log, self.proposal, trust_verdict={"status": "AUTHORIZED_FOR_PLANNING"})
        text = self.task_state.read_text(encoding="utf-8")
        self.assertEqual(result["status"], "APPLIED_CHECKPOINT_PENDING")
        self.assertFalse(result["paired_checkpoint_confirmed"])
        self.assertEqual(result["checkpoint"]["reason"], "TARGET_PROJECT_EVENT_LOG_MISSING")
        self.assertIn("Original checkpoint.", text)
        self.assertIn("UPDATE-TEST-001", text)
        self.assertIn("EVT-TEST-001", text)
        self.assertEqual(result["new_sha256"], sha256_bytes(self.task_state.read_bytes()))

    def test_exact_replay_is_idempotent(self):
        first = apply_checkpoint(self.task_state, self.event_log, self.proposal, trust_verdict={"status": "AUTHORIZED_FOR_PLANNING"})
        before = self.task_state.read_bytes()
        second = apply_checkpoint(self.task_state, self.event_log, self.proposal, trust_verdict={"status": "AUTHORIZED_FOR_PLANNING"})
        self.assertEqual(first["status"], "APPLIED_CHECKPOINT_PENDING")
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
        second = apply_checkpoint(self.task_state, self.event_log, changed, trust_verdict={"status": "AUTHORIZED_FOR_PLANNING"})
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



    def test_same_project_update_captures_paired_checkpoint_automatically(self):
        local_event_log = self.project / "events.jsonl"
        local_event = {
            "event_id": "EVT-LOCAL-001",
            "project_id": "TEST_PROJECT",
            "type": "verification",
            "summary": "Local evidence for paired checkpoint test",
        }
        local_event_log.write_text(json.dumps(local_event) + "\n", encoding="utf-8")
        proposal = dict(self.proposal, event_id="EVT-LOCAL-001")
        result = apply_checkpoint(
            self.task_state, local_event_log, proposal,
            trust_verdict={"status": "AUTHORIZED_FOR_PLANNING"},
        )
        self.assertEqual(result["status"], "APPLIED")
        self.assertTrue(result["paired_checkpoint_confirmed"])
        self.assertIn(result["checkpoint"]["status"], {"CAPTURED", "ALREADY_CAPTURED"})
        from continuity_checkpoint_bundle import verify
        verified = verify(self.project)
        self.assertEqual(verified["status"], "CURRENT")
        self.assertEqual(verified["checkpoint_id"], result["checkpoint"]["checkpoint_id"])

    def test_cross_project_evidence_reports_checkpoint_boundary_explicitly(self):
        result = apply_checkpoint(
            self.task_state, self.event_log, self.proposal,
            trust_verdict={"status": "AUTHORIZED_FOR_PLANNING"},
        )
        self.assertEqual(result["status"], "APPLIED_CHECKPOINT_PENDING")
        self.assertFalse(result["paired_checkpoint_confirmed"])
        self.assertEqual(result["checkpoint"]["reason"], "TARGET_PROJECT_EVENT_LOG_MISSING")
        self.assertTrue(result["writes_performed"])

if __name__ == "__main__":
    unittest.main()
