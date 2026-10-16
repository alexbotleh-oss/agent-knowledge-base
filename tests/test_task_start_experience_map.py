import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from dialogue_attention_controller import process_turn
from task_start_experience_map import build_task_start_experience_map


class TaskStartExperienceMapTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.project = self.root / "projects" / "TEST"
        self.project.mkdir(parents=True)
        self.task = self.project / "TASK_STATE.md"
        self.handoff = self.project / "HANDOFF.md"
        self.events = self.project / "events.jsonl"
        self.experience = self.root / "shared-events.jsonl"
        self.attention = self.root / "projects" / "AGENT_MEMORY_SYSTEM" / "events.jsonl"
        self.task.write_text(
            "# TASK_STATE — TASK-PARENT\n"
            "project_id: TEST\n"
            "- **Активная задача в текущей сессии:** Investigate cache recovery\n"
            "- **Последнее событие:** EVT-CURRENT-1\n",
            encoding="utf-8",
        )
        self.handoff.write_text(
            "# HANDOFF\n"
            "project_id: TEST\n"
            "- **Следующий шаг:** Compare prior successful and failed attempts\n",
            encoding="utf-8",
        )
        self._write(self.events, [{
            "event_id": "EVT-CURRENT-1", "project_id": "TEST", "type": "checkpoint",
            "summary": "Current task checkpoint for cache recovery", "status": "verified",
        }])
        self._write(self.experience, [{
            "event_id": "EVT-EXP-1", "project_id": "TEST", "type": "test_result",
            "summary": "Cache recovery succeeded after restoring the prior index pointer",
            "status": "observed", "action_taken": "Restored prior index pointer",
            "outcome": "Cache recovery succeeded", "hypotheses": ["pointer was stale"],
            "evidence": [{"kind": "test", "ref": "tests/test_cache.py"}],
        }])

    def tearDown(self):
        self.tmp.cleanup()

    @staticmethod
    def _write(path, events):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in events), encoding="utf-8")

    def test_composes_restore_attention_and_experience_with_provenance(self):
        branch = process_turn(
            self.attention, turn_id="T-SIDE-1", text="Кстати, отдельный вопрос",
            active_task_id="TASK-PARENT", active_checkpoint_id="CKPT-PARENT",
            child_task_id="TASK-SIDE", child_checkpoint_id="CKPT-SIDE",
        )
        self.assertEqual(branch["status"], "BRANCH_OPENED")
        result = build_task_start_experience_map(
            self.task, self.handoff, self.events, "cache recovery index pointer",
            experience_logs=[self.experience], attention_log=self.attention,
            active_task_id="TASK-PARENT", active_checkpoint_id="CKPT-PARENT",
            current_project_id="TEST",
        )
        self.assertEqual(result["status"], "READY_FOR_REVIEW", json.dumps({"task_restore": result["task_restore"], "experience_map": result["experience_map"], "attention": result["attention"]}, ensure_ascii=False))
        self.assertEqual(result["task_restore"]["status"], "RESTORED_PACKET")
        self.assertEqual(result["attention"]["open_branch_count"], 1)
        self.assertEqual(result["attention"]["return_stack"][0]["parent"]["task_id"], "TASK-PARENT")
        self.assertEqual(result["attention"]["return_stack"][0]["child"]["task_id"], "TASK-SIDE")
        self.assertEqual(result["attention"]["alignment_with_task_state"], "BRANCH_ACTIVE_TASK_DIFFERS_FROM_TASK_STATE")
        candidate = result["experience_map"]["groups"]["current_project_scope"][0]
        self.assertEqual(candidate["event_id"], "EVT-EXP-1")
        self.assertEqual(candidate["source_record_status"], "HASH_AND_EVENT_ID_MATCH")
        self.assertEqual(candidate["experience_details"]["action_taken"], "Restored prior index pointer")
        self.assertEqual(candidate["transfer_decision"], "UNASSESSED")
        self.assertFalse(result["decision_policy"]["planning_authorized"])
        self.assertFalse(result["writes_performed"])
        self.assertFalse(result["execution_performed"])

    def test_no_attention_journal_is_reported_without_inventing_a_branch(self):
        result = build_task_start_experience_map(
            self.task, self.handoff, self.events, "cache recovery",
            experience_logs=[self.experience], attention_log=self.attention,
            active_task_id="TASK-PARENT", active_checkpoint_id="CKPT-PARENT",
            current_project_id="TEST",
        )
        self.assertEqual(result["attention"]["open_branch_count"], 0)
        self.assertEqual(result["attention"]["alignment_with_task_state"], "NO_PERSISTED_ATTENTION_STATE")
        self.assertEqual(result["experience_map"]["candidate_count"], 1)


if __name__ == "__main__":
    unittest.main()
