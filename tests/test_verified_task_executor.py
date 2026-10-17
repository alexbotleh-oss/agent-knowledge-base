import json
import sys
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from verified_task_executor import run_reviewed_action
from minimal_agent_loop import run_minimal_agent_loop


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
            "type": "regression",
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

    def _run(self, *, execute, checks=None, argv=None, event_id="EVT-EXP-001", risk_level="normal", prior_failed_attempts=0):
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
            risk_level=risk_level,
            prior_failed_attempts=prior_failed_attempts,
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

    def test_success_candidate_is_retrieved_in_next_task_start_cycle(self):
        first_run = self._run(execute=True)
        self.assertEqual(first_run["status"], "VERIFIED_ACTION_AND_CAPTURED")
        captured_id = first_run["capture"]["event_id"]

        # Start a fresh task cycle using only the persisted logs, not the prior
        # in-memory result. This is the critical persistence -> retrieval check.
        next_start = run_minimal_agent_loop(
            self.task_state,
            self.handoff,
            self.event_log,
            "service worker cache restore",
            experience_logs=[self.experience_log, self.event_log],
            current_project_id="TEST",
            evidence_root=self.root,
        )
        retrieved = next_start.get("retrieval", {}).get("candidates", [])
        retrieved_by_id = {item.get("event_id"): item for item in retrieved}
        self.assertIn(captured_id, retrieved_by_id)
        self.assertIn("Verified outcome candidate", retrieved_by_id[captured_id].get("summary", ""))

        persisted = next(
            json.loads(line)
            for line in self.event_log.read_text(encoding="utf-8").splitlines()
            if json.loads(line).get("event_id") == captured_id
        )
        self.assertEqual(persisted["type"], "test")
        self.assertIn("EVT-EXP-001", persisted["related_event_ids"])
        self.assertFalse(first_run["semantic_memory_promoted"])

    def test_real_agent_memory_event_drives_isolated_controlled_action(self):
        # Use a real, already-recorded AGENT_MEMORY_SYSTEM event as the
        # retrieved source, while isolating all writes in a temporary workspace.
        source_events = ROOT / "projects" / "AGENT_MEMORY_SYSTEM" / "events.jsonl"
        source_records = [
            json.loads(line)
            for line in source_events.read_text(encoding="utf-8").splitlines()
        ]
        source_event_id = "EVT-AGMS-20261017-004"
        source_event = next(item for item in source_records if item.get("event_id") == source_event_id)
        self.assertEqual(source_event["project_id"], "AGENT_MEMORY_SYSTEM")

        workspace = self.root / "real-source-run"
        project = workspace / "projects" / "AGENT_MEMORY_SYSTEM"
        project.mkdir(parents=True)
        (workspace / "artifacts").mkdir()
        task_state = project / "TASK_STATE.md"
        handoff = project / "HANDOFF.md"
        event_log = project / "events.jsonl"
        experience_log = workspace / "experience" / "events.jsonl"
        experience_log.parent.mkdir(parents=True)
        experience_log.write_bytes(source_events.read_bytes())
        task_state.write_text(
            "# TASK_STATE\n"
            "- **Активная задача в текущей сессии:** task-start cluster verification\n"
            "- **Последнее событие:** EVT-AGMS-CURRENT-001\n",
            encoding="utf-8",
        )
        handoff.write_text(
            "# HANDOFF\n- **Следующий шаг:** verify task-start artifact using retrieved experience\n",
            encoding="utf-8",
        )
        event_log.write_text(json.dumps({
            "event_id": "EVT-AGMS-CURRENT-001",
            "project_id": "AGENT_MEMORY_SYSTEM",
            "type": "checkpoint",
            "summary": "Current task-start cluster verification checkpoint",
            "status": "observed",
        }) + "\n", encoding="utf-8")

        artifact_script = (
            "from pathlib import Path; import json; "
            "Path('artifacts/real-source-check.json').write_text("
            "json.dumps({'status':'PASS','basis_event_id':'EVT-AGMS-20261017-004'}), "
            "encoding='utf-8')"
        )
        action_spec = workspace / "action-spec.json"
        action_spec.write_text(json.dumps({
            "argv": [sys.executable, "-c", artifact_script],
            "cwd": ".",
            "acceptance_criterion": "The artifact passes and records the exact reviewed source event",
            "acceptance_checks": [
                {"type": "command_exit_code", "expected": 0},
                {"type": "json_field_equals", "path": "artifacts/real-source-check.json", "field": "status", "expected": "PASS"},
                {"type": "json_field_equals", "path": "artifacts/real-source-check.json", "field": "basis_event_id", "expected": source_event_id},
            ],
            "evidence_report": "artifacts/real-source-evidence.json",
            "observed_outcome": "Controlled artifact verification passed using a real AGENT_MEMORY_SYSTEM source event",
        }), encoding="utf-8")
        completed = subprocess.run(
            [
                sys.executable,
                str(ROOT / "tools" / "verified_task_executor.py"),
                "--workspace-root", str(workspace),
                "--task-state", "projects/AGENT_MEMORY_SYSTEM/TASK_STATE.md",
                "--handoff", "projects/AGENT_MEMORY_SYSTEM/HANDOFF.md",
                "--event-log", "projects/AGENT_MEMORY_SYSTEM/events.jsonl",
                "--experience-log", "experience/events.jsonl",
                "--request", "task-start cluster verified restore candidates",
                "--project-id", "AGENT_MEMORY_SYSTEM",
                "--task-id", "TASK-REAL-SOURCE-SMOKE-001",
                "--reviewed-experience-event-id", source_event_id,
                "--action-rationale", "Prior experience integrated task-start cluster and verified restore; run focused artifact verification.",
                "--action-spec", str(action_spec),
                "--risk-level", "low",
                "--timeout-seconds", "10",
                "--execute",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr + "\\n" + completed.stdout)
        result = json.loads(completed.stdout)
        self.assertEqual(result["status"], "VERIFIED_ACTION_AND_CAPTURED", result)
        self.assertEqual(result["retrieved_experience_event_id"], source_event_id)
        self.assertTrue(all(check["passed"] for check in result["acceptance_checks"]))
        artifact = json.loads((workspace / "artifacts" / "real-source-check.json").read_text(encoding="utf-8"))
        self.assertEqual(artifact["basis_event_id"], source_event_id)
        captured_records = [
            json.loads(line)
            for line in event_log.read_text(encoding="utf-8").splitlines()
        ]
        captured_event = next(
            item for item in captured_records
            if item.get("event_id") == result["capture"]["event_id"]
        )
        self.assertIn(source_event_id, captured_event["related_event_ids"])
        self.assertEqual(captured_event["status"], "observed")
        # The real source log is copied for retrieval and remains byte-identical.
        self.assertEqual(experience_log.read_bytes(), source_events.read_bytes())
        self.assertFalse(result["semantic_memory_promoted"])

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
        self.assertEqual(result["failure_event"]["status"], "FAILURE_EVENT_RECORDED")
        events = [json.loads(line) for line in self.event_log.read_text(encoding="utf-8").splitlines()]
        failure = next(item for item in events if item.get("type") == "failed_attempt")
        self.assertIn("EVT-EXP-001", failure["related_event_ids"])
        self.assertEqual(failure["status"], "observed")
        self.assertFalse(any(item.get("type") == "test" for item in events))
        next_start = run_minimal_agent_loop(
            self.task_state,
            self.handoff,
            self.event_log,
            "service worker cache restore",
            experience_logs=[self.experience_log, self.event_log],
            current_project_id="TEST",
            evidence_root=self.root,
        )
        failed_ids = {
            item.get("event_id")
            for item in next_start.get("retrieval", {}).get("candidates", [])
        }
        self.assertIn(result["failure_event"]["event_id"], failed_ids)
        self.assertEqual(
            next_start["adaptive_task_flow"]["mode"],
            "DEEP_ANALYSIS_BEFORE_RETRY",
        )

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

    def test_action_without_traceable_link_to_retrieved_experience_is_blocked(self):
        result = run_reviewed_action(
            workspace_root=self.root,
            task_state=self.task_state,
            handoff=self.handoff,
            event_log=self.event_log,
            experience_logs=[self.experience_log],
            request="service worker cache restore",
            project_id="TEST",
            task_id="TASK-RESTORE-002",
            reviewed_experience_event_id="EVT-EXP-001",
            action_rationale="Run an unrelated database cleanup and inspect the customer table",
            action_argv=[sys.executable, "-c", "from pathlib import Path; Path('artifacts/should-not-exist').write_text('x')"],
            action_cwd=self.root,
            acceptance_criterion="A generated artifact exists",
            acceptance_checks=[
                {"type": "command_exit_code", "expected": 0},
                {"type": "file_contains", "path": "artifacts/should-not-exist", "expected": "x"},
            ],
            evidence_report=Path("artifacts/task-run-evidence.json"),
            observed_outcome="test",
            execute=True,
            timeout_seconds=10,
        )
        self.assertEqual(result["status"], "BLOCKED_EXPERIENCE_NOT_LINKED_TO_ACTION")
        self.assertFalse(result["execution_performed"] if "execution_performed" in result else False)
        self.assertFalse((self.root / "artifacts" / "should-not-exist").exists())

    def test_high_risk_route_blocks_action_even_when_execute_flag_is_set(self):
        result = self._run(
            execute=True,
            risk_level="critical",
            argv=[
                sys.executable,
                "-c",
                "from pathlib import Path; Path('artifacts/should-not-exist').write_text('x')",
            ],
        )
        self.assertEqual(result["status"], "BLOCKED_ROUTE_REQUIRES_DEEPER_ANALYSIS")
        self.assertFalse(result["execution_performed"])
        self.assertFalse((self.root / "artifacts" / "should-not-exist").exists())


if __name__ == "__main__":
    unittest.main()
