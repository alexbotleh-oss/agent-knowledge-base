import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from adaptive_task_flow import route_after_attempt, select_initial_route
from minimal_agent_loop import run_minimal_agent_loop


class AdaptiveTaskFlowTests(unittest.TestCase):
    def test_completed_search_without_experience_selects_standard_execution(self):
        route = select_initial_route(
            experience_status="NO_MATCHES",
            lesson_status="NO_MATCHES",
            semantic_memory_status="NO_MATCHES",
        )
        self.assertEqual(route["mode"], "STANDARD_EXECUTION_AFTER_EXPERIENCE_REVIEW")
        self.assertTrue(route["experience_search"]["absence_proven"])
        self.assertFalse(route["external_search_required_now"])

    def test_unavailable_memory_is_not_misreported_as_no_experience(self):
        route = select_initial_route(
            experience_status="NO_MATCHES",
            lesson_status="NO_MATCHES",
            semantic_memory_status="UNAVAILABLE",
        )
        self.assertEqual(route["mode"], "STANDARD_EXECUTION_AFTER_EXPERIENCE_REVIEW")
        self.assertFalse(route["experience_search"]["absence_proven"])
        self.assertTrue(route["experience_search"]["search_incomplete"])
        self.assertIn("not proof that no experience exists", route["reason"])

    def test_applicable_experience_is_selected_before_standard_execution(self):
        route = select_initial_route(
            experience_status="CANDIDATES_FOUND",
            lesson_status="CANDIDATES_FOUND",
            applicable_experience_count=1,
            candidate_count=2,
        )
        self.assertEqual(route["mode"], "APPLY_RELEVANT_EXPERIENCE")

    def test_unresolved_candidate_requires_review(self):
        route = select_initial_route(
            experience_status="CANDIDATES_FOUND",
            lesson_status="CANDIDATES_FOUND",
            unresolved_candidate_count=1,
            candidate_count=1,
        )
        self.assertEqual(route["mode"], "REVIEW_EXPERIENCE_CANDIDATES")

    def test_known_prior_failure_escalates_before_another_attempt(self):
        route = select_initial_route(
            experience_status="NO_MATCHES",
            lesson_status="NO_MATCHES",
            prior_failed_attempts=2,
        )
        self.assertEqual(route["mode"], "DEEP_ANALYSIS_BEFORE_RETRY")
        self.assertTrue(route["external_search_required_now"])

    def test_repeated_related_corrections_escalate_without_manual_failure_count(self):
        from adaptive_task_flow import count_related_corrections
        candidates = [
            {"event_id": "EVT-CORR-1", "event_type": "correction", "project_scope_match": "MATCH",
             "matched_terms": ["cache", "index", "restore"]},
            {"event_id": "EVT-CORR-2", "event_type": "correction", "project_scope_match": "MATCH",
             "matched_terms": ["cache", "index", "restore"]},
            {"event_id": "EVT-OTHER", "event_type": "correction", "project_scope_match": "MISMATCH",
             "matched_terms": ["cache", "index", "restore"]},
            {"event_id": "EVT-DUP", "event_type": "correction", "project_scope_match": "MATCH",
             "matched_terms": ["cache"]},
        ]
        count = count_related_corrections(candidates, current_project_id="TEST")
        self.assertEqual(count, 2)
        route = select_initial_route(
            experience_status="CANDIDATES_FOUND",
            lesson_status="NO_MATCHES",
            candidate_count=2,
            prior_correction_count=count,
        )
        self.assertEqual(route["mode"], "DEEP_ANALYSIS_BEFORE_RETRY")
        self.assertTrue(route["external_search_required_now"])
        self.assertEqual(route["prior_correction_count"], 2)

    def test_high_risk_task_escalates_even_without_prior_failure(self):
        route = select_initial_route(
            experience_status="NO_MATCHES",
            lesson_status="NO_MATCHES",
            risk_level="high",
        )
        self.assertEqual(route["mode"], "DEEP_ANALYSIS_BEFORE_EXECUTION")

    def test_failed_attempt_requires_deep_analysis_and_external_search(self):
        route = route_after_attempt("FAIL")
        self.assertEqual(route["mode"], "DEEP_ANALYSIS_EXTERNAL_SEARCH")
        self.assertTrue(route["external_search_required_now"])
        self.assertFalse(route["execution_performed"])

    def test_unverified_success_is_not_captured_as_lesson(self):
        route = route_after_attempt("SUCCESS")
        self.assertEqual(route["mode"], "VERIFY_RESULT")

    def test_verified_success_routes_to_experience_capture(self):
        route = route_after_attempt("VERIFIED_SUCCESS")
        self.assertEqual(route["mode"], "CAPTURE_CONFIRMED_EXPERIENCE")

    def test_actual_minimal_loop_exposes_experience_first_route(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            project = root / "projects" / "TEST"
            project.mkdir(parents=True)
            task = project / "TASK_STATE.md"
            handoff = project / "HANDOFF.md"
            events = project / "events.jsonl"
            task.write_text("# TASK_STATE\n- **Активная задача в текущей сессии:** staging snapshot\n", encoding="utf-8")
            handoff.write_text("# HANDOFF\n- **Следующий шаг:** inspect staging\n", encoding="utf-8")
            events.write_text(
                '{"event_id":"EVT-CORR-1","type":"correction","project_id":"TEST","summary":"cache recovery index pointer correction","status":"verified"}\\n'
                '{"event_id":"EVT-CORR-2","type":"correction","project_id":"TEST","summary":"cache recovery index pointer correction retry","status":"verified"}\\n',
                encoding="utf-8",
            )
            result = run_minimal_agent_loop(
                task, handoff, events, "cache recovery index pointer",
                experience_logs=[events], lesson_logs=[], current_project_id="TEST",
            )
            self.assertIn("adaptive_task_flow", result)
            self.assertEqual(result["adaptive_task_flow"]["mode"], "DEEP_ANALYSIS_BEFORE_RETRY")
            self.assertEqual(result["adaptive_task_flow"]["prior_correction_count"], 2)
            self.assertFalse(result["execution_performed"])


if __name__ == "__main__":
    unittest.main()
