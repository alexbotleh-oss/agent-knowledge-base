import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from agent_memory_cycle import run_cycle
from branch_result_registry import publish_result, acknowledge_result
from dialogue_attention_controller import process_turn
from check_reuse_policy import record_check_result


class AgentMemoryCycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.project = self.root / "projects" / "TEST"
        self.project.mkdir(parents=True)
        self.task = self.project / "TASK_STATE.md"
        self.handoff = self.project / "HANDOFF.md"
        self.project_events = self.project / "events.jsonl"
        self.experience = self.root / "shared-events.jsonl"
        self.attention = self.root / "projects" / "AGENT_MEMORY_SYSTEM" / "events.jsonl"
        self.task.write_text(
            "# TASK_STATE — TASK-PARENT\nproject_id: TEST\n"
            "- **Активная задача в текущей сессии:** Investigate cache recovery\n"
            "- **Последнее событие:** EVT-CURRENT-1\n",
            encoding="utf-8",
        )
        self.handoff.write_text(
            "# HANDOFF\nproject_id: TEST\n"
            "- **Следующий шаг:** Compare prior successful and failed attempts\n",
            encoding="utf-8",
        )
        self._write(self.project_events, [{
            "event_id": "EVT-CURRENT-1", "project_id": "TEST", "type": "checkpoint",
            "summary": "Current task checkpoint for cache recovery", "status": "verified",
        }])
        self._write(self.experience, [{
            "event_id": "EVT-EXP-1", "project_id": "TEST", "type": "test_result",
            "summary": "Cache recovery succeeded after restoring the prior index pointer",
            "status": "observed", "action_taken": "Restored prior index pointer",
            "outcome": "Cache recovery succeeded",
            "evidence": [{"kind": "test", "ref": "tests/test_cache.py"}],
        }])

    def tearDown(self):
        self.tmp.cleanup()

    @staticmethod
    def _write(path, events):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in events), encoding="utf-8")

    def test_single_entrypoint_reconciles_child_result_returns_and_reuses_check(self):
        opened = process_turn(
            self.attention, turn_id="T-CYCLE-SIDE", text="Кстати, проверь отдельный вопрос",
            active_task_id="TASK-PARENT", active_checkpoint_id="CKPT-PARENT",
            child_task_id="TASK-SIDE", child_checkpoint_id="CKPT-SIDE",
        )
        self.assertEqual(opened["status"], "BRANCH_OPENED")
        published = publish_result(self.attention, {
            "child_branch_id": opened["branch_id"],
            "parent_checkpoint_id": "CKPT-PARENT", "parent_task_id": "TASK-PARENT",
            "result_key": "cache-check-v1", "result_status": "RESULT_REPORTED",
            "summary": "Cache recovery check completed in the side branch.",
            "source_refs": ["tests/test_cache.py#case-1"],
            "reported_at": "2026-10-16T12:00:00Z", "evidence_status": "verified",
        })
        self.assertEqual(published["status"], "RESULT_REPORTED")
        ack = acknowledge_result(
            self.attention, published["event_id"], "accepted",
            "owner-confirmation://cycle-test", "2026-10-16T12:01:00Z",
        )
        self.assertEqual(ack["status"], "ACKNOWLEDGED")
        with self.task.open("a", encoding="utf-8") as stream:
            stream.write(
                "\n## Checkpoint update UPDATE-CYCLE-1\n"
                "- Parent checkpoint: `CKPT-PARENT`\n"
                f"- Supporting event: `{ack['event_id']}`\n"
                "Child result reviewed; parent acceptance criteria reconciled.\n"
            )

        before = run_cycle(
            self.task, self.handoff, self.project_events, self.attention,
            "cache recovery index pointer", experience_logs=[self.experience],
            active_task_id="TASK-SIDE", active_checkpoint_id="CKPT-SIDE",
            current_project_id="TEST",
        )
        policy = before["check_reuse"]
        self.assertEqual(policy["status"], "RUN_CHECK")
        recorded = record_check_result(
            self.attention, policy["check_spec"], policy["source_hashes"],
            policy["candidate_fingerprints"], result_status="PASS",
            evidence_refs=["tests/test_cache.py#case-1"],
            summary="Discriminating check passed after reviewing the branch result.",
            recorded_by="synthetic-agent-memory-cycle-test",
        )
        self.assertEqual(recorded["status"], "RECORDED")

        after = run_cycle(
            self.task, self.handoff, self.project_events, self.attention,
            "cache recovery index pointer", experience_logs=[self.experience],
            active_task_id="TASK-SIDE", active_checkpoint_id="CKPT-SIDE",
            current_project_id="TEST", return_turn_id="T-CYCLE-RETURN",
            parent_task_id="TASK-PARENT",
        )
        self.assertEqual(after["status"], "READY")
        self.assertEqual(after["branch_reconciliation"]["status"], "CONSISTENT")
        self.assertEqual(after["parent_return"]["status"], "RETURNED")
        self.assertEqual(after["attention"]["active"]["task_id"], "TASK-PARENT")
        self.assertEqual(after["check_reuse"]["status"], "REUSE_RECORDED_PASS")
        self.assertEqual(after["check_reuse"]["action"], "DO_NOT_REPEAT_CHECK")
        self.assertFalse(after["task_start"]["decision_policy"]["repeat_check"])
        self.assertFalse(after["task_start"]["decision_policy"]["planning_authorized"])
        self.assertTrue(after["writes_performed"])

    def test_cycle_replay_of_same_return_turn_is_idempotent(self):
        opened = process_turn(
            self.attention, turn_id="T-CYCLE-REPLAY-SIDE", text="Кстати, отдельный вопрос",
            active_task_id="TASK-PARENT", active_checkpoint_id="CKPT-PARENT",
            child_task_id="TASK-SIDE", child_checkpoint_id="CKPT-SIDE",
        )
        published = publish_result(self.attention, {
            "child_branch_id": opened["branch_id"],
            "parent_checkpoint_id": "CKPT-PARENT", "parent_task_id": "TASK-PARENT",
            "result_key": "replay-check-v1", "result_status": "RESULT_REPORTED",
            "summary": "Replay test result.", "source_refs": ["tests/test_replay.py#case"],
            "reported_at": "2026-10-16T12:00:00Z", "evidence_status": "verified",
        })
        ack = acknowledge_result(
            self.attention, published["event_id"], "accepted",
            "owner-confirmation://replay-test", "2026-10-16T12:01:00Z",
        )
        with self.task.open("a", encoding="utf-8") as stream:
            stream.write(
                "\n## Checkpoint update UPDATE-REPLAY-1\n"
                "- Parent checkpoint: `CKPT-PARENT`\n"
                f"- Supporting event: `{ack['event_id']}`\n"
            )
        first = run_cycle(
            self.task, self.handoff, self.project_events, self.attention,
            "cache recovery index pointer", experience_logs=[self.experience],
            active_task_id="TASK-SIDE", active_checkpoint_id="CKPT-SIDE",
            current_project_id="TEST", return_turn_id="T-CYCLE-RETURN-REPLAY",
            parent_task_id="TASK-PARENT",
        )
        self.assertEqual(first["parent_return"]["status"], "RETURNED")
        before = self.attention.read_bytes()
        second = run_cycle(
            self.task, self.handoff, self.project_events, self.attention,
            "cache recovery index pointer", experience_logs=[self.experience],
            active_task_id="TASK-PARENT", active_checkpoint_id="CKPT-PARENT",
            current_project_id="TEST", return_turn_id="T-CYCLE-RETURN-REPLAY",
            parent_task_id="TASK-PARENT",
        )
        self.assertEqual(second["status"], "READY")
        self.assertEqual(second["parent_return"]["status"], "ALREADY_RETURNED")
        self.assertFalse(second["parent_return"]["writes_performed"])
        self.assertEqual(self.attention.read_bytes(), before)

    def test_return_is_blocked_when_child_result_is_not_acknowledged(self):
        opened = process_turn(
            self.attention, turn_id="T-CYCLE-SIDE-2", text="Кстати, отдельный вопрос",
            active_task_id="TASK-PARENT", active_checkpoint_id="CKPT-PARENT",
            child_task_id="TASK-SIDE", child_checkpoint_id="CKPT-SIDE",
        )
        self.assertEqual(opened["status"], "BRANCH_OPENED")
        result = run_cycle(
            self.task, self.handoff, self.project_events, self.attention,
            "cache recovery index pointer", experience_logs=[self.experience],
            active_task_id="TASK-SIDE", active_checkpoint_id="CKPT-SIDE",
            current_project_id="TEST", return_turn_id="T-BLOCKED-RETURN",
            parent_task_id="TASK-PARENT",
        )
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["parent_return"]["status"], "BLOCKED_CHILD_RESULT_MISSING")
        self.assertFalse(result["writes_performed"])
        self.assertEqual(result["attention"]["active"]["task_id"], "TASK-SIDE")


if __name__ == "__main__":
    unittest.main()
