import hashlib
import json
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
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

    def test_handoff_change_after_authorization_refuses_write(self):
        # HANDOFF supplies the next step because TASK_STATE intentionally omits it.
        self.task_state.write_text(
            "# TASK_STATE\n"
            "- **Активная задача в текущей сессии:** проверить изменение HANDOFF\n"
            "- **Последнее событие:** EVT-TEST-001\n",
            encoding="utf-8",
        )
        _, context, verdict = self._restore_and_decide()
        self.assertEqual(context["next_step"], "проверить контрольную точку")
        self.assertEqual(verdict["status"], "AUTHORIZED_FOR_PLANNING")

        # The proposal and TASK_STATE revision remain unchanged; only HANDOFF changes.
        self.handoff.write_text("# HANDOFF\n", encoding="utf-8")
        before = self.task_state.read_bytes()
        result = apply_checkpoint(
            self.task_state, self.events, self._proposal(), trust_verdict=verdict
        )

        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["trust_status"], "REFUSED_UNKNOWN_NEXT_STEP")
        self.assertFalse(result["writes_performed"])
        self.assertEqual(before, self.task_state.read_bytes())

    def test_independent_processes_cannot_both_apply_same_revision(self):
        _, _, verdict = self._restore_and_decide()
        expected_hash = hashlib.sha256(self.task_state.read_bytes()).hexdigest()
        go_file = self.root / "GO"
        worker = r'''
import json, sys, time
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from guarded_task_state_update import apply_checkpoint
task_state, events = Path(sys.argv[2]), Path(sys.argv[3])
proposal = {
    "update_id": sys.argv[4],
    "expected_sha256": sys.argv[5],
    "parent_checkpoint_id": "CKPT-MP",
    "event_id": "EVT-TEST-001",
    "checkpoint_markdown": "- Independent process checkpoint.",
}
verdict = json.loads(sys.argv[6])
go_file = Path(sys.argv[7])
deadline = time.monotonic() + 10
while not go_file.exists():
    if time.monotonic() > deadline:
        raise SystemExit("start barrier timed out")
    time.sleep(0.005)
print(json.dumps(apply_checkpoint(task_state, events, proposal, trust_verdict=verdict)))
\''' 
        import os
        import subprocess

        command_args = [
            sys.executable, "-c", worker, str(ROOT / "tools"),
            str(self.task_state), str(self.events), "UPDATE-PROCESS-A",
            expected_hash, json.dumps(verdict), str(go_file),
        ]
        command_args_b = list(command_args)
        command_args_b[command_args_b.index("UPDATE-PROCESS-A")] = "UPDATE-PROCESS-B"
        first = subprocess.Popen(command_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        second = subprocess.Popen(command_args_b, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        go_file.write_text("go", encoding="utf-8")
        out_a, err_a = first.communicate(timeout=15)
        out_b, err_b = second.communicate(timeout=15)
        self.assertEqual(first.returncode, 0, err_a)
        self.assertEqual(second.returncode, 0, err_b)
        results = [json.loads(out_a), json.loads(out_b)]
        statuses = [item["status"] for item in results]
        self.assertEqual(statuses.count("APPLIED"), 1, statuses)
        self.assertEqual(sum(status in {"LOCKED", "STALE_REVISION"} for status in statuses), 1, statuses)
        state = self.task_state.read_text(encoding="utf-8")
        self.assertEqual(
            sum(marker in state for marker in (
                "guarded-task-update:UPDATE-PROCESS-A",
                "guarded-task-update:UPDATE-PROCESS-B",
            )),
            1,
        )
        self.assertFalse(self.events.with_name(self.events.name + ".lock").exists())
        self.assertFalse(self.task_state.with_name(self.task_state.name + ".lock").exists())

    def test_concurrent_checkpoint_writers_cannot_both_apply_same_revision(self):
        _, _, verdict = self._restore_and_decide()
        base_hash = hashlib.sha256(self.task_state.read_bytes()).hexdigest()
        barrier = Barrier(2)

        def attempt(update_id):
            proposal = self._proposal()
            proposal["update_id"] = update_id
            proposal["expected_sha256"] = base_hash
            barrier.wait(timeout=5)
            return apply_checkpoint(
                self.task_state, self.events, proposal, trust_verdict=verdict
            )

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [
                pool.submit(attempt, "UPDATE-CONCURRENT-A"),
                pool.submit(attempt, "UPDATE-CONCURRENT-B"),
            ]
            results = [future.result(timeout=10) for future in futures]

        statuses = [result["status"] for result in results]
        self.assertEqual(statuses.count("APPLIED"), 1, statuses)
        self.assertEqual(sum(status in {"LOCKED", "STALE_REVISION"} for status in statuses), 1, statuses)
        state = self.task_state.read_text(encoding="utf-8")
        self.assertEqual(
            sum(marker in state for marker in (
                "guarded-task-update:UPDATE-CONCURRENT-A",
                "guarded-task-update:UPDATE-CONCURRENT-B",
            )),
            1,
        )

    def test_journal_lock_contention_refuses_checkpoint_write(self):
        _, _, verdict = self._restore_and_decide()
        proposal = self._proposal()
        before = self.task_state.read_bytes()
        journal_lock = self.events.with_name(self.events.name + ".lock")
        journal_lock.write_text('{"pid": 999999, "started_at": "test"}', encoding="utf-8")

        result = apply_checkpoint(
            self.task_state, self.events, proposal, trust_verdict=verdict
        )

        self.assertEqual(result["status"], "LOCKED")
        self.assertFalse(result["writes_performed"])
        self.assertEqual(before, self.task_state.read_bytes())
        self.assertTrue(journal_lock.exists())

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
