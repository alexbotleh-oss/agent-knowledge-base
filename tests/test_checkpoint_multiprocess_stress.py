"""Independent-process contention test for the guarded checkpoint writer.

The test checks the invariant, not a throughput target: N independent workers share
one expected TASK_STATE revision, and at most one may commit. Losing workers must
report a documented no-write status; the test does not claim that load testing alone
proves race freedom for writers outside the shared lock protocol.
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


class CheckpointMultiprocessStressTests(unittest.TestCase):
    def test_many_independent_writers_apply_at_most_once(self):
        workers = int(os.environ.get("CHECKPOINT_STRESS_WORKERS", "32"))
        self.assertGreaterEqual(workers, 2)
        self.assertLessEqual(workers, 100, "keep CI stress bounded")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "projects" / "STRESS_TEST"
            project.mkdir(parents=True)
            task = project / "TASK_STATE.md"
            handoff = project / "HANDOFF.md"
            events = project / "events.jsonl"
            task.write_text(
                "# TASK_STATE\n"
                "- **Активная задача в текущей сессии:** проверить конкуренцию процессов\n"
                "- **Следующий шаг:** применить одну контрольную точку\n"
                "- **Последнее событие:** EVT-STRESS-001\n",
                encoding="utf-8",
            )
            handoff.write_text(
                "# HANDOFF\n- **Следующий шаг:** применить одну контрольную точку\n",
                encoding="utf-8",
            )
            events.write_text(
                json.dumps({
                    "event_id": "EVT-STRESS-001",
                    "type": "observation",
                    "summary": "multiprocess stress evidence",
                }) + "\n",
                encoding="utf-8",
            )
            packet = build_session_packet(task, handoff, events)
            verdict = authorize_next_step(extract_semantic_context(packet))
            self.assertEqual(verdict["status"], "AUTHORIZED_FOR_PLANNING")

            expected_hash = hashlib.sha256(task.read_bytes()).hexdigest()
            start = root / "START"
            worker_code = r'''
import json, sys, time
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from guarded_task_state_update import apply_checkpoint
task, events = Path(sys.argv[2]), Path(sys.argv[3])
update_id, expected_hash = sys.argv[4], sys.argv[5]
verdict = json.loads(sys.argv[6])
start = Path(sys.argv[7])
deadline = time.monotonic() + 15
while not start.exists():
    if time.monotonic() >= deadline:
        print(json.dumps({"status": "WORKER_TIMEOUT", "writes_performed": False}))
        raise SystemExit(2)
    time.sleep(0.002)
proposal = {
    "update_id": update_id,
    "expected_sha256": expected_hash,
    "parent_checkpoint_id": "CKPT-STRESS-001",
    "event_id": "EVT-STRESS-001",
    "checkpoint_markdown": "- Multiprocess stress checkpoint " + update_id + ".",
}
print(json.dumps(apply_checkpoint(task, events, proposal, trust_verdict=verdict)), flush=True)
'''
            processes = []
            for i in range(workers):
                command = [
                    sys.executable, "-c", worker_code, str(TOOLS), str(task), str(events),
                    f"UPDATE-STRESS-{i:03d}", expected_hash, json.dumps(verdict), str(start),
                ]
                processes.append(subprocess.Popen(
                    command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
                ))

            # Release all already-started independent processes together.
            start.write_text("go", encoding="utf-8")
            results = []
            for index, proc in enumerate(processes):
                try:
                    stdout, stderr = proc.communicate(timeout=25)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    stdout, stderr = proc.communicate()
                    self.fail(f"worker {index} timed out; stdout={stdout}; stderr={stderr}")
                self.assertEqual(proc.returncode, 0, f"worker {index} failed: {stderr}; stdout={stdout}")
                try:
                    results.append(json.loads(stdout.strip().splitlines()[-1]))
                except (json.JSONDecodeError, IndexError):
                    self.fail(f"worker {index} returned invalid JSON: {stdout!r}; stderr={stderr}")

            statuses = [result.get("status") for result in results]
            self.assertEqual(
                statuses.count("APPLIED"), 1,
                f"expected exactly one APPLIED among {workers} workers; statuses={statuses}",
            )
            allowed_losers = {"LOCKED", "STALE_REVISION"}
            unexpected = [status for status in statuses if status != "APPLIED" and status not in allowed_losers]
            self.assertEqual(unexpected, [], f"unexpected losing-worker statuses: {statuses}")
            self.assertEqual(sum(bool(result.get("writes_performed")) for result in results), 1)

            final_state = task.read_text(encoding="utf-8")
            self.assertEqual(final_state.count("<!-- guarded-task-update:"), 1)
            self.assertEqual(len(list(project.glob("*.lock"))), 0, "successful workers should release locks")


if __name__ == "__main__":
    unittest.main()
