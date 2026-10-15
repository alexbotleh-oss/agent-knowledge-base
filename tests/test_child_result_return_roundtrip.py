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
from context_extractor import extract_semantic_context
from context_trust_gate import authorize_next_step
from restore_session_packet import build_session_packet


class ChildResultReturnRoundTripTests(unittest.TestCase):
    def test_result_ack_and_checkpoint_form_linked_recoverable_chain(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "projects" / "AGENT_MEMORY_SYSTEM"
            project.mkdir(parents=True)
            event_log = project / "events.jsonl"
            task_state = project / "TASK_STATE.md"
            event_log.write_text("", encoding="utf-8")
            task_state.write_text("# Task state\n- **Активная задача в текущей сессии:** проверить результат дочерней ветки\n- **Следующий шаг:** проверить подтверждение владельца\n\nParent checkpoint CKPT-1.\n", encoding="utf-8")
            handoff = project / "HANDOFF.md"
            handoff.write_text("# HANDOFF\n- **Следующий шаг:** проверить подтверждение владельца\n", encoding="utf-8")

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

            task_state.write_text(task_state.read_text(encoding="utf-8") + f"\n- **Последнее событие:** {ack['event_id']}\n", encoding="utf-8")
            packet = build_session_packet(task_state, handoff, event_log)
            verdict = authorize_next_step(extract_semantic_context(packet))
            proposal = {
                "update_id": "UPDATE-1",
                "expected_sha256": sha256_bytes(task_state.read_bytes()),
                "parent_checkpoint_id": "CKPT-1",
                "event_id": ack["event_id"],
                "checkpoint_markdown": "- Child result accepted by owner; parent goal remains open until its remaining criteria are checked.",
            }
            applied = apply_checkpoint(task_state, event_log, proposal, trust_verdict=verdict)
            repeated = apply_checkpoint(task_state, event_log, proposal, trust_verdict=verdict)
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
            task_state.write_text("# Initial\n- **Активная задача в текущей сессии:** проверить устаревшую ревизию\n- **Следующий шаг:** повторно проверить контрольную точку\n- **Последнее событие:** EVT-1\n", encoding="utf-8")
            handoff = project / "HANDOFF.md"
            handoff.write_text("# HANDOFF\n- **Следующий шаг:** повторно проверить контрольную точку\n", encoding="utf-8")
            proposal = {
                "update_id": "UPDATE-2",
                "expected_sha256": sha256_bytes(task_state.read_bytes()),
                "parent_checkpoint_id": "CKPT-2",
                "event_id": "EVT-1",
                "checkpoint_markdown": "- New child result was reviewed.",
            }
            task_state.write_text("# Parent changed while child work was running.\n- **Активная задача в текущей сессии:** проверить устаревшую ревизию\n- **Следующий шаг:** повторно проверить контрольную точку\n- **Последнее событие:** EVT-1\n", encoding="utf-8")
            before = task_state.read_bytes()
            packet = build_session_packet(task_state, handoff, event_log)
            verdict = authorize_next_step(extract_semantic_context(packet))
            stale = apply_checkpoint(task_state, event_log, proposal, trust_verdict=verdict)
            self.assertEqual(stale["status"], "STALE_REVISION")
            self.assertEqual(task_state.read_bytes(), before)

            refreshed = dict(proposal, expected_sha256=sha256_bytes(task_state.read_bytes()))
            refreshed_packet = build_session_packet(task_state, handoff, event_log)
            refreshed_verdict = authorize_next_step(extract_semantic_context(refreshed_packet))
            retried = apply_checkpoint(task_state, event_log, refreshed, trust_verdict=refreshed_verdict)
            self.assertEqual(retried["status"], "APPLIED")
            self.assertIn("Parent changed while child work was running.", task_state.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
