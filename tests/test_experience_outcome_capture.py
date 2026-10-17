import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from experience_outcome_capture import capture_verified_experience_candidate
from minimal_agent_loop import run_minimal_agent_loop


class ExperienceOutcomeCaptureTests(unittest.TestCase):
    def _capture(self, root, event_log, evidence_file, marker="TEST_RESULT=PASS"):
        return capture_verified_experience_candidate(
            event_log,
            evidence_root=root,
            project_id="TEST",
            task_id="TASK-001",
            request_summary="service worker cache restore",
            action_taken="Changed the cache key after reproducing stale restore",
            acceptance_criterion="The latest app shell is restored after reload",
            expected_evidence_marker=marker,
            evidence_file=evidence_file,
            observed_outcome="Acceptance check output contains TEST_RESULT=PASS",
            related_event_ids=["EVT-REPRO-001"],
        )

    def test_capture_requires_acceptance_marker_in_real_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            evidence = root / "artifacts" / "check-output.txt"
            evidence.parent.mkdir(parents=True)
            evidence.write_text("TEST_RESULT=FAIL\n", encoding="utf-8")
            event_log = root / "projects" / "TEST" / "events.jsonl"

            result = self._capture(root, event_log, evidence)

            self.assertEqual(result["status"], "BLOCKED_ACCEPTANCE_MARKER_NOT_FOUND")
            self.assertFalse(result["writes_performed"])
            self.assertFalse(event_log.exists())

    def test_verified_outcome_persists_and_changes_next_task_route(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            project = root / "projects" / "TEST"
            project.mkdir(parents=True)
            task_state = project / "TASK_STATE.md"
            handoff = project / "HANDOFF.md"
            event_log = project / "events.jsonl"
            evidence = root / "artifacts" / "check-output.txt"
            evidence.parent.mkdir(parents=True)
            evidence.write_text(
                "RUN_ID=run-17\nACCEPTANCE_CHECK=latest app shell restored after reload\nTEST_RESULT=PASS\n",
                encoding="utf-8",
            )
            task_state.write_text(
                "# TASK_STATE\n- **Активная задача в текущей сессии:** service worker cache restore\n",
                encoding="utf-8",
            )
            handoff.write_text(
                "# HANDOFF\n- **Следующий шаг:** inspect service worker cache restore\n",
                encoding="utf-8",
            )

            captured = self._capture(root, event_log, evidence)
            self.assertEqual(captured["status"], "CAPTURED_CANDIDATE")
            self.assertFalse(captured["semantic_memory_promoted"])
            self.assertTrue(captured["writes_performed"])

            replay = self._capture(root, event_log, evidence)
            self.assertEqual(replay["status"], "ALREADY_CAPTURED")
            self.assertFalse(replay["writes_performed"])
            self.assertEqual(len(event_log.read_text(encoding="utf-8").splitlines()), 1)

            # A fresh invocation reloads the persisted log, retrieves the exact
            # captured event, and changes the next route from ordinary execution
            # to candidate review. Events are history, not accepted rules.
            result = run_minimal_agent_loop(
                task_state,
                handoff,
                event_log,
                "service worker cache restore",
                experience_logs=[event_log],
                lesson_logs=[],
                current_project_id="TEST",
                evidence_root=root,
            )
            candidate_ids = {
                item.get("event_id")
                for item in result["retrieval"].get("candidates", [])
            }
            self.assertIn(captured["event_id"], candidate_ids)
            self.assertEqual(
                result["adaptive_task_flow"]["mode"],
                "REVIEW_EXPERIENCE_CANDIDATES",
            )
            self.assertFalse(result["execution_performed"])
            self.assertFalse(result["writes_performed"])


if __name__ == "__main__":
    unittest.main()
