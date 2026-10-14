import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from context_extractor import extract_semantic_context
from context_trust_gate import authorize_next_step
from guarded_task_state_update import apply_checkpoint
from restore_session_packet import build_session_packet


class TrustPolicyEnforcedOnWriteTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.project = self.root / "projects" / "TEST_PROJECT"
        self.project.mkdir(parents=True)
        self.task_state = self.project / "TASK_STATE.md"
        self.handoff = self.project / "HANDOFF.md"
        self.events = self.project / "events.jsonl"
        self.events.write_text(
            json.dumps({"event_id": "EVT-TEST-001", "type": "observation", "summary": "test evidence"}) + "\n",
            encoding="utf-8",
        )
        self.handoff.write_text(
            "# HANDOFF\n- **Следующий шаг:** проверить контрольную точку\n",
            encoding="utf-8",
        )
        self.task_state.write_text(
            "# TASK_STATE\n"
            "- **Активная задача в текущей сессии:** проверить политику доверия\n"
            "- **Следующий шаг:** применить контрольную точку после проверки\n"
            "- **Последнее событие:** EVT-TEST-001\n",
            encoding="utf-8",
        )

    def tearDown(self):
        self.tmp.cleanup()

    def _proposal(self):
        return {
            "update_id": "UPDATE-TRUST-001",
            "expected_sha256": hashlib.sha256(self.task_state.read_bytes()).hexdigest(),
            "parent_checkpoint_id": "CKPT-TRUST-001",
            "event_id": "EVT-TEST-001",
            "checkpoint_markdown": "- Integration test checkpoint.",
        }

    def _restore_and_decide(self):
        packet = build_session_packet(self.task_state, self.handoff, self.events)
        context = extract_semantic_context(packet)
        verdict = authorize_next_step(context)
        return packet, context, verdict

    def test_complete_restore_to_trust_gate_to_write_path(self):
        packet, context, verdict = self._restore_and_decide()
        self.assertEqual(packet["status"], "RESTORED_PACKET")
        self.assertTrue(context["freshness_verified"])
        self.assertTrue(context["semantic_context_usable"])
        self.assertTrue(context["event_linkage_complete"])
        self.assertEqual(verdict["status"], "AUTHORIZED_FOR_PLANNING")

        result = apply_checkpoint(
            self.task_state, self.events, self._proposal(), trust_verdict=verdict
        )
        self.assertEqual(result["status"], "APPLIED")
        self.assertTrue(result["writes_performed"])
        self.assertIn("UPDATE-TRUST-001", self.task_state.read_text(encoding="utf-8"))

    def test_changed_source_refuses_write_and_preserves_current_file(self):
        packet = build_session_packet(self.task_state, self.handoff, self.events)
        self.task_state.write_text(
            self.task_state.read_text(encoding="utf-8") + "\nExternal change after packet build.\n",
            encoding="utf-8",
        )
        context = extract_semantic_context(packet)
        verdict = authorize_next_step(context)
        self.assertFalse(context["freshness_verified"])
        self.assertEqual(verdict["status"], "REFUSED_UNVERIFIED_CONTEXT")

        before = self.task_state.read_bytes()
        result = apply_checkpoint(
            self.task_state, self.events, self._proposal(), trust_verdict=verdict
        )
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["reason"], "TrustPolicyViolated")
        self.assertFalse(result["writes_performed"])
        self.assertEqual(before, self.task_state.read_bytes())

    def test_partial_event_history_requires_confirmation_and_blocks_write(self):
        self.task_state.write_text(
            "# TASK_STATE\n"
            "- **Активная задача в текущей сессии:** проверить неполный журнал\n"
            "- **Следующий шаг:** применить контрольную точку после проверки\n"
            "- **Последнее событие:** EVT-MISSING-999\n",
            encoding="utf-8",
        )
        packet, context, verdict = self._restore_and_decide()
        self.assertEqual(packet["status"], "PARTIAL")
        self.assertTrue(context["freshness_verified"])
        self.assertTrue(context["semantic_context_usable"])
        self.assertFalse(context["event_linkage_complete"])
        self.assertEqual(verdict["status"], "PLAN_REQUIRES_CONFIRMATION")

        before = self.task_state.read_bytes()
        result = apply_checkpoint(
            self.task_state, self.events, self._proposal(), trust_verdict=verdict
        )
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["reason"], "TrustPolicyViolated")
        self.assertFalse(result["writes_performed"])
        self.assertEqual(before, self.task_state.read_bytes())

    def test_event_log_change_after_authorization_refuses_write(self):
        _, _, verdict = self._restore_and_decide()
        self.assertEqual(verdict["status"], "AUTHORIZED_FOR_PLANNING")
        # The task-state hash is unchanged; linked event evidence disappears.
        self.events.write_text("", encoding="utf-8")
        before = self.task_state.read_bytes()

        result = apply_checkpoint(
            self.task_state, self.events, self._proposal(), trust_verdict=verdict
        )

        self.assertEqual(result["status"], "REJECTED")
        self.assertFalse(result["writes_performed"])
        self.assertEqual(before, self.task_state.read_bytes())

    def test_unknown_next_step_does_not_authorize_write(self):
        self.task_state.write_text(
            "# TASK_STATE\n"
            "- **Активная задача в текущей сессии:** проверить неизвестный шаг\n"
            "- **Последнее событие:** EVT-TEST-001\n",
            encoding="utf-8",
        )
        self.handoff.write_text("# HANDOFF\n", encoding="utf-8")
        packet = build_session_packet(self.task_state, self.handoff, self.events)
        context = extract_semantic_context(packet)
        verdict = authorize_next_step(context)
        self.assertEqual(context["next_step"], "UNKNOWN")
        self.assertEqual(verdict["status"], "REFUSED_UNKNOWN_NEXT_STEP")

        before = self.task_state.read_bytes()
        result = apply_checkpoint(
            self.task_state, self.events, self._proposal(), trust_verdict=verdict
        )
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["reason"], "TrustPolicyViolated")
        self.assertFalse(result["writes_performed"])
        self.assertEqual(before, self.task_state.read_bytes())


if __name__ == "__main__":
    unittest.main()
