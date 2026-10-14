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
from restore_session_packet import build_session_packet


class SemanticContextExtractorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.project = Path(self.tmp.name) / "projects" / "TEST_PROJECT"
        self.project.mkdir(parents=True)
        self.task = self.project / "TASK_STATE.md"
        self.handoff = self.project / "HANDOFF.md"
        self.events = self.project / "events.jsonl"
        self.events.write_text(json.dumps({
            "event_id": "EVT-TEST-001",
            "type": "observation",
            "summary": "Test event"
        }) + "\n", encoding="utf-8")
        self.handoff.write_text(
            "# HANDOFF\n"
            "- **Следующий шаг:** проверить сохранённый пакет восстановления\n"
            "## Открытые вопросы\n"
            "- Где хранится подтверждённая ревизия?\n",
            encoding="utf-8",
        )

    def tearDown(self):
        self.tmp.cleanup()

    def _packet(self):
        return build_session_packet(self.task, self.handoff, self.events)

    def test_extracts_explicit_fields_with_provenance_from_current_markdown(self):
        self.task.write_text(
            "# TASK_STATE\n"
            "- **Историческая задача приложения (не активна в этой сессии):** отладить Android-приложение.\n"
            "- **Активная задача в текущей сессии:** перенести опыт в agent-knowledge-base.\n"
            "- **Блокеры / решение пользователя:** не менять main без подтверждения.\n"
            "- **Последнее событие:** EVT-TEST-001\n",
            encoding="utf-8",
        )
        packet = self._packet()
        self.assertEqual(packet["status"], "RESTORED_PACKET")

        context = extract_semantic_context(packet)
        self.assertEqual(context["active_goal"], "перенести опыт в agent-knowledge-base")
        self.assertEqual(context["historical_goal"], "отладить Android-приложение")
        self.assertEqual(context["next_step"], "проверить сохранённый пакет восстановления")
        self.assertEqual(context["open_questions"], ["Где хранится подтверждённая ревизия?"])
        self.assertEqual(context["blockers"], ["не менять main без подтверждения"])
        self.assertEqual(context["last_event"], "EVT-TEST-001")
        self.assertEqual(context["field_status"]["active_goal"], "FOUND")
        self.assertEqual(context["provenance"]["active_goal"]["source"], "TASK_STATE.md")
        self.assertEqual(context["source_freshness"], {
            "task_state": "CURRENT", "handoff": "CURRENT", "events": "CURRENT"
        })
        self.assertFalse(context["writes_performed"])

    def test_real_task_state_format_does_not_invent_next_step_or_questions(self):
        self.task.write_text(
            "# TASK_STATE — sample\n"
            "- **Историческая задача приложения (не активна в этой сессии):** Android debugging.\n"
            "- **Активная задача в текущей сессии:** memory transfer only.\n"
            "- **Осталось:** проверить файлы и CI.\n"
            "- **Последнее событие:** EVT-TEST-001\n",
            encoding="utf-8",
        )
        self.handoff.write_text("# HANDOFF\nNo explicit next step.\n", encoding="utf-8")
        context = extract_semantic_context(self._packet())
        self.assertEqual(context["active_goal"], "memory transfer only")
        self.assertEqual(context["next_step"], "UNKNOWN")
        self.assertEqual(context["open_questions"], [])
        self.assertEqual(context["field_status"]["next_step"], "UNKNOWN")

    def test_detects_source_change_after_packet_was_built(self):
        self.task.write_text(
            "- **Активная задача в текущей сессии:** сохранить точку возврата.\n",
            encoding="utf-8",
        )
        packet = self._packet()
        original_hash = packet["source_hashes"]["task_state_sha256"]
        self.task.write_text(
            "- **Активная задача в текущей сессии:** другая задача.\n",
            encoding="utf-8",
        )

        context = extract_semantic_context(packet)
        self.assertEqual(context["status"], "SOURCE_CHANGED")
        self.assertEqual(context["source_freshness"]["task_state"], "CHANGED")
        self.assertEqual(context["source_hashes"]["task_state"], original_hash)
        self.assertNotEqual(
            context["source_hashes"]["task_state"],
            __import__("hashlib").sha256(self.task.read_bytes()).hexdigest(),
        )

    def test_insufficient_data_returns_unknown_without_guessing(self):
        self.task.write_text("# TASK_STATE\nNo explicit semantic labels.\n", encoding="utf-8")
        self.handoff.write_text("# HANDOFF\nNo explicit next step.\n", encoding="utf-8")
        context = extract_semantic_context(self._packet())
        self.assertEqual(context["active_goal"], "UNKNOWN")
        self.assertEqual(context["historical_goal"], "UNKNOWN")
        self.assertEqual(context["next_step"], "UNKNOWN")
        self.assertEqual(context["open_questions"], [])
        self.assertEqual(context["blockers"], [])
        self.assertEqual(context["last_event"], "UNKNOWN")

    def test_blocked_packet_is_handled_without_exception(self):
        packet = {
            "status": "BLOCKED",
            "reason": "missing canonical source",
            "writes_performed": False,
        }
        context = extract_semantic_context(packet)
        self.assertEqual(context["status"], "BLOCKED")
        self.assertEqual(context["active_goal"], "UNKNOWN")
        self.assertEqual(context["source_hashes"]["task_state"], "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
