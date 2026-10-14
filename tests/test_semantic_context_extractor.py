import json
import subprocess
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
        self.assertTrue(context["freshness_verified"])
        self.assertTrue(context["semantic_context_usable"])
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
        self.assertEqual(context["field_status"]["active_goal"], "STALE_SOURCE")
        self.assertFalse(context["freshness_verified"])
        self.assertFalse(context["semantic_context_usable"])
        self.assertEqual(context["source_hashes"]["task_state"], original_hash)
        self.assertNotEqual(
            context["source_hashes"]["task_state"],
            __import__("hashlib").sha256(self.task.read_bytes()).hexdigest(),
        )

    def test_task_state_next_step_takes_precedence_over_handoff(self):
        self.task.write_text(
            "- **Активная задача в текущей сессии:** сессионная задача.\n"
            "- **Следующий шаг:** сначала проверить TASK_STATE.\n",
            encoding="utf-8",
        )
        self.handoff.write_text(
            "# HANDOFF\n"
            "- **Следующий шаг:** продолжить общую задачу проекта.\n",
            encoding="utf-8",
        )
        context = extract_semantic_context(self._packet())
        self.assertEqual(context["next_step"], "сначала проверить TASK_STATE")
        self.assertEqual(context["provenance"]["next_step"]["source"], "TASK_STATE.md")

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

    def test_missing_source_disables_freshness_and_usability(self):
        self.task.write_text(
            "- **Активная задача в текущей сессии:** сохранить контрольную точку.\n",
            encoding="utf-8",
        )
        packet = self._packet()
        self.handoff.unlink()
        context = extract_semantic_context(packet)
        self.assertEqual(context["status"], "SOURCE_MISSING")
        self.assertEqual(context["source_freshness"]["handoff"], "MISSING")
        self.assertFalse(context["freshness_verified"])
        self.assertFalse(context["semantic_context_usable"])

    def test_partial_packet_separates_semantic_freshness_from_event_completeness(self):
        self.task.write_text(
            "- **Активная задача в текущей сессии:** проверить неполный журнал.\n"
            "- **Последнее событие:** EVT-MISSING-999\n",
            encoding="utf-8",
        )
        packet = self._packet()
        self.assertEqual(packet["status"], "PARTIAL")
        context = extract_semantic_context(packet)
        self.assertTrue(context["freshness_verified"])
        self.assertTrue(context["semantic_context_usable"])
        self.assertFalse(context["event_linkage_complete"])
        self.assertEqual(context["active_goal"], "проверить неполный журнал")

    def test_verify_sources_false_never_claims_verified_freshness(self):
        self.task.write_text(
            "- **Активная задача в текущей сессии:** проверить без хеш-проверки.\n",
            encoding="utf-8",
        )
        context = extract_semantic_context(self._packet(), verify_sources=False)
        self.assertFalse(context["freshness_verified"])
        self.assertFalse(context["semantic_context_usable"])
        self.assertFalse(context["event_linkage_complete"])

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
        self.assertFalse(context["freshness_verified"])
        self.assertFalse(context["semantic_context_usable"])


    def test_real_recipe_manager_sources_keep_session_and_project_scopes_distinct(self):
        task = ROOT / "projects" / "RECIPE_MANAGER" / "TASK_STATE.md"
        handoff = ROOT / "projects" / "RECIPE_MANAGER" / "HANDOFF.md"
        events = ROOT / "projects" / "RECIPE_MANAGER" / "events.jsonl"
        packet = build_session_packet(task, handoff, events)
        context = extract_semantic_context(packet)
        self.assertEqual(
            context["active_goal"],
            "перенести доступный опыт текущего чата в `agent-knowledge-base`, проверить дубликаты и оформить отдельный PR. Не выполнять отладку, не изменять код/БД приложения и не собирать APK",
        )
        self.assertEqual(context["historical_goal"], "отладить Android-приложение; улучшения интерфейса отложить до завершения отладки")
        # The handoff's project-level Android goal must not become this session's goal.
        self.assertNotIn("отладку Android", context["active_goal"])
        # No explicit session next-step label exists in TASK_STATE; don't infer one
        # from the handoff's differently named prose heading.
        self.assertEqual(context["next_step"], "UNKNOWN")
        self.assertEqual(context["provenance"]["active_goal"]["source"], "TASK_STATE.md")

    def test_semantic_context_restores_in_fresh_process_from_persisted_sources(self):
        self.task.write_text(
            "# TASK_STATE\n"
            "- **Активная задача в текущей сессии:** проверить восстановление после перезапуска.\n"
            "- **Последнее событие:** EVT-TEST-001\n",
            encoding="utf-8",
        )
        self.handoff.write_text(
            "# HANDOFF\n"
            "- **Следующий шаг:** проверить результат восстановления.\n",
            encoding="utf-8",
        )
        script = (
            "import json, sys; "
            "from pathlib import Path; "
            "sys.path.insert(0, sys.argv[1]); "
            "from restore_session_packet import build_session_packet; "
            "from context_extractor import extract_semantic_context; "
            "packet = build_session_packet(Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])); "
            "print(json.dumps(extract_semantic_context(packet), ensure_ascii=False))"
        )
        completed = subprocess.run(
            [
                sys.executable, "-c", script, str(TOOLS),
                str(self.task), str(self.handoff), str(self.events),
            ],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        context = json.loads(completed.stdout)
        self.assertEqual(context["status"], "RESTORED_PACKET")
        self.assertEqual(
            context["active_goal"],
            "проверить восстановление после перезапуска",
        )
        self.assertEqual(context["next_step"], "проверить результат восстановления")
        self.assertEqual(context["source_freshness"]["task_state"], "CURRENT")
        self.assertFalse(context["writes_performed"])


if __name__ == "__main__":
    unittest.main()
