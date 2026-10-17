import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from verified_task_executor import run_reviewed_action


class VerifiedTaskExecutorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.project = self.root / "projects" / "TEST"
        self.project.mkdir(parents=True)
        self.task_state = self.project / "TASK_STATE.md"
        self.handoff = self.project / "HANDOFF.md"
        self.event_log = self.project / "events.jsonl"
        self.experience_log = self.root / "shared-experience.jsonl"
        self.task_state.write_text(
            "# TASK_STATE\n"
            "- **Активная задача в текущей сессии:** service worker cache restore\n"
            "- **Последнее событие:** EVT-CURRENT-001\n",
            encoding="utf-8",
        )
        self.handoff.write_text(
            "# HANDOFF\n- **Следующий шаг:** inspect service worker cache restore\n",
            encoding="utf-8",
        )
        self.event_log.write_text(json.dumps({
            "event_id": "EVT-CURRENT-001",
            "project_id": "TEST",
            "type": "checkpoint",
            "summary": "Current service worker cache restore checkpoint",
            "status": "observed",
        }) + "\n", encoding="utf-8")
        self.experience_log.write_text(json.dumps({
            "event_id": "EVT-EXP-001",
            "project_id": "TEST",
            "type": "test_result",
            "summary": "Service worker cache restore regression fixed by changing cache key",
            "status": "observed",
            "facts": ["A stale cache key restored an outdated app shell"],
            "action_taken": "Change cache key and reload",
            "outcome": "Fresh app shell restored after reload",
            "evidence": [{"kind": "file", "ref": "tests/test_service_worker.py"}],
        }) + "\n", encoding="utf-8")
        (self.root / "tests").mkdir()
        (self.root / "artifacts").mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def _run(self, *, execute, checks=None, argv=None, event_id="EVT-EXP-001"):
        return run_reviewed_action(
            workspace_root=self.root,
            task_state=self.task_state,
            handoff=self.handoff,
            event_log=self.event_log,
            experience_logs=[self.experience_log],
            request="service worker cache restore",
            project_id="TEST",
            task_id="TASK-RESTORE-001",
            reviewed_experience_event_id=event_id,
            action_rationale="Prior experience identified stale cache-key reuse; run the focused reproduction and verify the generated artifact.",
            action_argv=argv or [
                sys.executable,
                "-c",
                "from pathlib import Path; import json; p=Path('artifacts/result.json'); p.parent.mkdir(exist_ok=True); p.write_text(json.dumps({'status':'PASS','cache_key':'v52'}), encoding='utf-8')",
            ],
            action_cwd=self.root,
            acceptance_criterion="The fresh app-shell check reports PASS and a new cache key",
            acceptance_checks=checks or [
                {"type": "command_exit_code", "expected": 0},
                {"type": "json_field_equals", "path": "artifacts/result.json", "field": "status", "expected": "PASS"},
                {"type": "json_field_equals", "path": "artifacts/result.json", "field": "cache_key", "expected": "v52"},
            ],
            evidence_report=Path("artifacts/task-run-evidence.json"),
            observed_outcome="Independent artifact checks passed after the reviewed action",
            execute=execute,
            timeout_seconds=10,
        )

    def test_dry_run_retrieves_experience_but_does_not_execute_or_write(self):
        result = self._run(execute=False)
        self.assertEqual(result["status"], "PLAN_READY_REQUIRES_EXPLICIT_EXECUTE")
        self.assertEqual(result["retrieved_event_id"], "EVT-EXP-001")
        self.assertFalse(result["execution_performed"])
        self.assertFalse(result["writes_performed"])
        self.assertFalse((self.root / "artifacts" / "result.json").exists())

    def test_reviewed_experience_guides_action_and_independent_checks_gate_capture(self):
        result = self._run(execute=True)
        self.assertEqual(result["status"], "VERIFIED_ACTION_AND_CAPTURED")
        self.assertEqual(result["retrieved_experience_event_id"], "EVT-EXP-001")
        self.assertEqual(result["verification_status"], "PASS")
        self.assertTrue(all(check["passed"] for check in result["acceptance_checks"]))
        self.assertEqual(result["capture"]["status"], "CAPTURED_CANDIDATE")
        self.assertFalse(result["semantic_memory_promoted"])
        report = (self.root / "artifacts" / "task-run-evidence.json").read_text(encoding="utf-8")
        self.assertIn("VERIFICATION_STATUS=PASS", report)
        records = [json.loads(line) for line in self.event_log.read_text(encoding="utf-8").splitlines()]
        captured = next(item for item in records if item["event_id"] == result["capture"]["event_id"])
        self.assertIn("EVT-EXP-001", captured["related_event_ids"])
        self.assertEqual(captured["status"], "observed")

    def test_failed_independent_check_does_not_capture_outcome(self):
        result = self._run(
            execute=True,
            checks=[
                {"type": "command_exit_code", "expected": 0},
                {"type": "json_field_equals", "path": "artifacts/result.json", "field": "status", "expected": "FAIL"},
            ],
        )
        self.assertEqual(result["status"], "ACTION_OR_ACCEPTANCE_CHECK_FAILED")
        self.assertEqual(result["verification_status"], "FAIL")
        self.assertFalse(any(
            json.loads(line).get("type") == "test"
            for line in self.event_log.read_text(encoding="utf-8").splitlines()
        ))

    def test_unretrieved_experience_blocks_action(self):
        result = self._run(execute=True, event_id="EVT-DOES-NOT-EXIST")
        self.assertIn(result["status"], {"BLOCKED_EXPERIENCE_NOT_RETRIEVED", "BLOCKED_EXPERIENCE_SCOPE_MISMATCH"})
        self.assertFalse(result.get("execution_performed", False))
        self.assertFalse((self.root / "artifacts" / "result.json").exists())

    def test_memory_checkpoint_mutation_during_action_blocks_capture(self):
        script = (
            "from pathlib import Path; "
            "Path('projects/TEST/TASK_STATE.md').write_text('tampered', encoding='utf-8'); "
            "Path('artifacts/result.json').write_text('{\"status\":\"PASS\"}', encoding='utf-8')"
        )
        result = self._run(execute=True, argv=[sys.executable, "-c", script])
        self.assertEqual(result["status"], "ACTION_OR_ACCEPTANCE_CHECK_FAILED")
        self.assertEqual(result["verification_status"], "FAIL")
        self.assertFalse(any(
            json.loads(line).get("type") == "test"
            for line in self.event_log.read_text(encoding="utf-8").splitlines()
        ))


if __name__ == "__main__":
    unittest.main()
