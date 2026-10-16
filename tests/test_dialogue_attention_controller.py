import json
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
        returned = controller.return_to_parent(self.log, turn_id="T-RETURN-1", parent_task_id="TASK-PARENT")
        self.assertEqual(returned["status"], "RETURNED")
        restored_again = controller.inspect(self.log)
        self.assertEqual(restored_again["active"]["task_id"], "TASK-PARENT")
        self.assertEqual(restored_again["open_branch_count"], 0)

    def test_nested_branches_return_lifo(self):
        self.turn("T-SIDE-1", "Кстати, проверь отдельный вопрос",
                  child_task_id="TASK-SIDE", child_checkpoint_id="CKPT-SIDE")
        nested = self.turn("T-SIDE-2", "Кстати, отдельный вопрос",
                           active_task_id="TASK-SIDE", active_checkpoint_id="CKPT-SIDE",
                           child_task_id="TASK-NESTED", child_checkpoint_id="CKPT-NESTED")
        self.assertEqual(nested["status"], "BRANCH_OPENED")
        wrong = controller.return_to_parent(self.log, turn_id="T-WRONG-RETURN", parent_task_id="TASK-PARENT")
        self.assertEqual(wrong["status"], "PARENT_MISMATCH")
        first = controller.return_to_parent(self.log, turn_id="T-RETURN-NESTED", parent_task_id="TASK-SIDE")
        self.assertEqual(first["active"]["task_id"], "TASK-SIDE")
        second = controller.return_to_parent(self.log, turn_id="T-RETURN-PARENT", parent_task_id="TASK-PARENT")
        self.assertEqual(second["active"]["task_id"], "TASK-PARENT")
        self.assertEqual(controller.inspect(self.log)["open_branch_count"], 0)

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

    def test_return_without_parent_does_not_write(self):
        result = controller.return_to_parent(self.log, turn_id="T-RETURN", parent_task_id="TASK-PARENT")
        self.assertEqual(result["status"], "NO_PARENT")
        self.assertFalse(self.log.exists())


if __name__ == "__main__":
    unittest.main()
