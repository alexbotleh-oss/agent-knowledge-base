"""Crash-injection tests for the guarded checkpoint writer.

These POSIX subprocess tests kill the writer at controlled points around os.replace.
They verify file atomicity and make stale-lock/temp-file behaviour explicit; they do
not claim automatic crash recovery.
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

from context_extractor import extract_semantic_context
from context_trust_gate import authorize_next_step
from restore_session_packet import build_session_packet


class CheckpointCrashInjectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.project = self.root / "projects" / "CRASH_TEST"
        self.project.mkdir(parents=True)
        self.task = self.project / "TASK_STATE.md"
        self.handoff = self.project / "HANDOFF.md"
        self.events = self.project / "events.jsonl"
        self.original = (
            "# TASK_STATE\n"
            "- **Активная задача в текущей сессии:** проверить аварийное завершение\n"
            "- **Следующий шаг:** применить контрольную точку\n"
            "- **Последнее событие:** EVT-CRASH-001\n"
        ).encode("utf-8")
        self.task.write_bytes(self.original)
        self.handoff.write_text("# HANDOFF\n- **Следующий шаг:** применить контрольную точку\n", encoding="utf-8")
        self.events.write_text(json.dumps({
            "event_id": "EVT-CRASH-001", "type": "observation", "summary": "crash fixture"
        }) + "\n", encoding="utf-8")
        packet = build_session_packet(self.task, self.handoff, self.events)
        context = extract_semantic_context(packet)
        self.verdict = authorize_next_step(context)
        self.assertEqual(self.verdict["status"], "AUTHORIZED_FOR_PLANNING")
        self.proposal = {
            "update_id": "UPDATE-CRASH-001",
            "expected_sha256": hashlib.sha256(self.original).hexdigest(),
            "parent_checkpoint_id": "CKPT-CRASH-001",
            "event_id": "EVT-CRASH-001",
            "checkpoint_markdown": "- Crash injection checkpoint.",
        }

    def tearDown(self):
        self.tmp.cleanup()

    def _run_until_replace_hook(self, mode):
        signal = self.root / "HOOK_REACHED"
        worker = r'''
import json, os, sys, time
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import guarded_task_state_update as module
task, events = Path(sys.argv[2]), Path(sys.argv[3])
proposal, verdict = json.loads(sys.argv[4]), json.loads(sys.argv[5])
signal, mode = Path(sys.argv[6]), sys.argv[7]
real_replace = os.replace
def hooked_replace(src, dst):
    if mode == "before":
        signal.write_text("ready", encoding="utf-8")
        time.sleep(60)
        return real_replace(src, dst)
    result = real_replace(src, dst)
    signal.write_text("ready", encoding="utf-8")
    time.sleep(60)
    return result
module.os.replace = hooked_replace
print(json.dumps(module.apply_checkpoint(task, events, proposal, trust_verdict=verdict)), flush=True)
'''
        command = [
            sys.executable, "-c", worker, str(TOOLS), str(self.task), str(self.events),
            json.dumps(self.proposal), json.dumps(self.verdict), str(signal), mode,
        ]
        proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        deadline = time.monotonic() + 10
        while not signal.exists() and time.monotonic() < deadline:
            if proc.poll() is not None:
                out, err = proc.communicate()
                self.fail(f"worker exited before crash hook; rc={proc.returncode}; stdout={out}; stderr={err}")
            time.sleep(0.01)
        if not signal.exists():
            proc.kill()
            proc.communicate(timeout=5)
            self.fail("worker did not reach os.replace crash hook")
        proc.kill()
        proc.communicate(timeout=5)
        self.assertIsNotNone(proc.returncode)
        self.assertEqual(proc.returncode, -9, "expected SIGKILL on the Ubuntu CI runner")

    def _locks(self):
        return (
            self.events.with_name(self.events.name + ".lock"),
            self.task.with_name(self.task.name + ".lock"),
        )

    def test_kill_before_atomic_replace_preserves_old_state_and_leaves_recovery_markers(self):
        self._run_until_replace_hook("before")
        self.assertEqual(self.task.read_bytes(), self.original)
        for lock in self._locks():
            self.assertTrue(lock.exists(), f"expected stale lock to remain: {lock.name}")
        # The killed process cannot run its finally block: a prepared temp file may remain.
        self.assertTrue(list(self.project.glob(".task-state-*.tmp")))
        # Recovery is explicit, after verifying the subprocess is dead.
        for lock in self._locks():
            lock.unlink()
        result = self._apply_retry()
        self.assertEqual(result["status"], "APPLIED")
        self.assertIn(b"Crash injection checkpoint", self.task.read_bytes())

    def test_kill_after_atomic_replace_leaves_complete_new_state_and_stale_locks(self):
        self._run_until_replace_hook("after")
        state = self.task.read_bytes()
        self.assertNotEqual(state, self.original)
        self.assertTrue(state.startswith(self.original))
        self.assertIn(b"Crash injection checkpoint", state)
        for lock in self._locks():
            self.assertTrue(lock.exists(), f"expected stale lock to remain: {lock.name}")
        # Idempotency is checked before lock acquisition, so replay recognizes the committed update.
        from guarded_task_state_update import apply_checkpoint
        replay = apply_checkpoint(self.task, self.events, self.proposal, trust_verdict=self.verdict)
        self.assertEqual(replay["status"], "ALREADY_APPLIED")
        # Do not silently reap stale locks in production code; test cleanup follows dead-process verification.
        for lock in self._locks():
            lock.unlink()

    def _apply_retry(self):
        from guarded_task_state_update import apply_checkpoint
        return apply_checkpoint(self.task, self.events, self.proposal, trust_verdict=self.verdict)


if __name__ == "__main__":
    unittest.main()
