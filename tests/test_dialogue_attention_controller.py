import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import dialogue_attention_controller as controller


class DialogueAttentionControllerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.log = Path(self.tmp.name) / "projects" / "AGENT_MEMORY_SYSTEM" / "events.jsonl"

    def tearDown(self):
        self.tmp.cleanup()

    def turn(self, turn_id, text, **kwargs):
        defaults = {
            "event_log": self.log, "turn_id": turn_id, "text": text,
            "active_task_id": "TASK-PARENT", "active_checkpoint_id": "CKPT-PARENT",
        }
        defaults.update(kwargs)
        return controller.process_turn(**defaults)

    def test_classifies_common_russian_turns_conservatively(self):
        self.assertEqual(controller.classify_turn("Продолжай работу")["classification"], "CONTINUATION")
        self.assertEqual(controller.classify_turn("Кстати, проверь отдельный вопрос")["classification"], "SIDE_BRANCH")
        self.assertEqual(controller.classify_turn("Запомни эту идею")["classification"], "DEFERRED_IDEA")
        self.assertEqual(controller.classify_turn("Сначала делаем импорт")["classification"], "PRIORITY_CHANGE")
        self.assertEqual(controller.classify_turn("Посмотри на это")["classification"], "AMBIGUOUS")

    def test_side_branch_persists_parent_and_restores_after_restart(self):
        result = self.turn("T-SIDE-1", "Кстати, проверь отдельный вопрос",
                           child_task_id="TASK-SIDE", child_checkpoint_id="CKPT-SIDE")
        self.assertEqual(result["status"], "BRANCH_OPENED")
        restored = controller.inspect(self.log)
        self.assertEqual(restored["active"]["task_id"], "TASK-SIDE")
        self.assertEqual(restored["return_stack"][0]["parent"]["task_id"], "TASK-PARENT")
        self.assertEqual(restored["return_stack"][0]["parent"]["checkpoint_id"], "CKPT-PARENT")
        returned = controller._return_to_parent_unchecked(self.log, turn_id="T-RETURN-1", parent_task_id="TASK-PARENT")
        self.assertEqual(returned["status"], "RETURNED")
        restored_again = controller.inspect(self.log)
        self.assertEqual(restored_again["active"]["task_id"], "TASK-PARENT")
        self.assertEqual(restored_again["open_branch_count"], 0)

    def test_return_replay_is_idempotent_and_does_not_pop_another_frame(self):
        self.turn("T-SIDE-1", "Кстати, проверь отдельный вопрос",
                  child_task_id="TASK-SIDE", child_checkpoint_id="CKPT-SIDE")
        first = controller._return_to_parent_unchecked(
            self.log, turn_id="T-RETURN-1", parent_task_id="TASK-PARENT"
        )
        second = controller._return_to_parent_unchecked(
            self.log, turn_id="T-RETURN-1", parent_task_id="TASK-PARENT"
        )
        self.assertEqual(first["status"], "RETURNED")
        self.assertEqual(second["status"], "ALREADY_RETURNED")
        self.assertFalse(second["writes_performed"])
        self.assertEqual(second["active"]["task_id"], "TASK-PARENT")
        self.assertEqual(len([
            event for event in controller.read_events(self.log)
            if event.get("type") == "attention_returned"
        ]), 1)

    def test_stack_is_reconstructed_in_a_fresh_process(self):
        self.turn("T-SIDE-1", "Кстати, проверь отдельный вопрос",
                  child_task_id="TASK-SIDE", child_checkpoint_id="CKPT-SIDE")
        script = ROOT / "tools" / "dialogue_attention_controller.py"
        completed = subprocess.run(
            [sys.executable, str(script), str(self.log), "inspect"],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        state = json.loads(completed.stdout)
        self.assertEqual(state["active"]["task_id"], "TASK-SIDE")
        self.assertEqual(state["return_stack"][0]["parent"]["task_id"], "TASK-PARENT")
        self.assertEqual(state["open_branch_count"], 1)

    def test_nested_branches_return_lifo(self):
        self.turn("T-SIDE-1", "Кстати, проверь отдельный вопрос",
                  child_task_id="TASK-SIDE", child_checkpoint_id="CKPT-SIDE")
        nested = self.turn("T-SIDE-2", "Кстати, отдельный вопрос",
                           active_task_id="TASK-SIDE", active_checkpoint_id="CKPT-SIDE",
                           child_task_id="TASK-NESTED", child_checkpoint_id="CKPT-NESTED")
        self.assertEqual(nested["status"], "BRANCH_OPENED")
        wrong = controller._return_to_parent_unchecked(self.log, turn_id="T-WRONG-RETURN", parent_task_id="TASK-PARENT")
        self.assertEqual(wrong["status"], "PARENT_MISMATCH")
        first = controller._return_to_parent_unchecked(self.log, turn_id="T-RETURN-NESTED", parent_task_id="TASK-SIDE")
        self.assertEqual(first["active"]["task_id"], "TASK-SIDE")
        second = controller._return_to_parent_unchecked(self.log, turn_id="T-RETURN-PARENT", parent_task_id="TASK-PARENT")
        self.assertEqual(second["active"]["task_id"], "TASK-PARENT")
        self.assertEqual(controller.inspect(self.log)["open_branch_count"], 0)

    def test_repeated_turn_is_idempotent(self):
        first = self.turn("T-REPLAY-1", "Продолжай работу")
        second = self.turn("T-REPLAY-1", "Продолжай работу")
        self.assertEqual(first["event_id"], second["event_id"])
        self.assertEqual(len(controller.read_events(self.log)), 1)

    def test_return_language_requires_unified_cycle_guard(self):
        self.turn("T-SIDE-1", "Кстати, проверь отдельный вопрос",
                  child_task_id="TASK-SIDE", child_checkpoint_id="CKPT-SIDE")
        result = self.turn("T-RETURN-1", "Вернись к основной задаче",
                           active_task_id="TASK-SIDE", active_checkpoint_id="CKPT-SIDE")
        self.assertEqual(result["status"], "BLOCKED_GUARD_REQUIRED")
        self.assertTrue(result["writes_performed"])  # intent classification is persisted
        self.assertEqual(len([
            event for event in controller.read_events(self.log)
            if event.get("type") == "attention_returned"
        ]), 0)
        self.assertEqual(controller.inspect(self.log)["open_branch_count"], 1)

    def test_deferred_idea_is_recorded_without_switching_or_stack_push(self):
        result = self.turn("T-IDEA-1", "Запомни эту идею")
        self.assertEqual(result["classification"], "DEFERRED_IDEA")
        state = controller.inspect(self.log)
        self.assertEqual(state["open_branch_count"], 0)
        self.assertEqual(state["active"]["task_id"], "TASK-PARENT")
        self.assertEqual(len(state["deferred_ideas"]), 1)
        self.assertEqual(state["deferred_ideas"][0]["return_condition"],
                         "user explicitly selects this idea for execution")

    def test_switch_requires_explicit_child_context(self):
        result = self.turn("T-SIDE-1", "Кстати, отдельный вопрос")
        self.assertEqual(result["status"], "NEEDS_CHILD_CONTEXT")
        self.assertFalse(self.log.exists())

    def test_ambiguous_turn_is_recorded_as_unknown_not_guessed(self):
        result = self.turn("T-AMB-1", "Посмотри на это")
        self.assertEqual(result["classification"], "AMBIGUOUS")
        self.assertTrue(result["suggestion"]["needs_confirmation"])
        event = controller.read_events(self.log)[0]
        self.assertEqual(event["status"], "unknown")

    def test_bad_journal_fails_closed(self):
        self.log.parent.mkdir(parents=True)
        self.log.write_text("{broken json\n", encoding="utf-8")
        before = self.log.read_bytes()
        with self.assertRaisesRegex(ValueError, "corrupt canonical event log"):
            controller.inspect(self.log)
        self.assertEqual(self.log.read_bytes(), before)

    def test_malformed_branch_frame_fails_closed_without_key_error(self):
        self.log.parent.mkdir(parents=True)
        event = {
            "event_id": "EVT-MALFORMED-BRANCH",
            "type": "attention_branch_opened",
            "attention": {
                "parent": {"task_id": "TASK-PARENT", "checkpoint_id": "CKPT-PARENT"},
                "child": {"task_id": "TASK-SIDE", "checkpoint_id": "CKPT-SIDE"},
                "classification": "SIDE_BRANCH",
                "turn_id": "T-MALFORMED",
            },
        }
        self.log.write_text(json.dumps(event) + "\n", encoding="utf-8")
        before = self.log.read_bytes()
        with self.assertRaisesRegex(ValueError, "required identifiers missing"):
            controller.inspect(self.log)
        self.assertEqual(self.log.read_bytes(), before)

    def test_public_return_fails_closed_without_unified_guard(self):
        self.turn("T-SIDE-GUARD", "Кстати, проверь отдельный вопрос",
                  child_task_id="TASK-SIDE", child_checkpoint_id="CKPT-SIDE")
        before = self.log.read_bytes()
        result = controller.return_to_parent(
            self.log, turn_id="T-UNGUARDED", parent_task_id="TASK-PARENT"
        )
        self.assertEqual(result["status"], "BLOCKED_GUARD_REQUIRED")
        self.assertFalse(result["writes_performed"])
        self.assertEqual(self.log.read_bytes(), before)

    def test_public_return_rejects_incomplete_guard(self):
        result = controller.return_to_parent(
            self.log, turn_id="T-BAD-GUARD", parent_task_id="TASK-PARENT",
            authorization={"reconciliation_status": "CONSISTENT", "child_result_status": "MISSING"},
        )
        self.assertEqual(result["status"], "BLOCKED_CHILD_RESULT")
        self.assertFalse(result["writes_performed"])

    def test_public_return_never_accepts_ready_shaped_guard(self):
        self.turn("T-SIDE-READY-GUARD", "Кстати, проверь отдельный вопрос",
                  child_task_id="TASK-SIDE", child_checkpoint_id="CKPT-SIDE")
        before = self.log.read_bytes()
        result = controller.return_to_parent(
            self.log, turn_id="T-READY-GUARD", parent_task_id="TASK-PARENT",
            authorization={"reconciliation_status": "CONSISTENT", "child_result_status": "READY"},
        )
        self.assertEqual(result["status"], "BLOCKED_GUARD_REQUIRED")
        self.assertFalse(result["writes_performed"])
        self.assertEqual(self.log.read_bytes(), before)
        self.assertEqual(controller.inspect(self.log)["open_branch_count"], 1)

    def test_return_without_parent_does_not_write(self):
        result = controller._return_to_parent_unchecked(self.log, turn_id="T-RETURN", parent_task_id="TASK-PARENT")
        self.assertEqual(result["status"], "NO_PARENT")
        self.assertFalse(self.log.exists())


if __name__ == "__main__":
    unittest.main()
