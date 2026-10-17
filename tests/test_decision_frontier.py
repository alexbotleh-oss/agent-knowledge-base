"""Tests for the read-only decision frontier reducer."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from decision_frontier import reduce_decision_frontier


class DecisionFrontierTests(unittest.TestCase):
    def test_separates_keep_exclude_hold_and_out_of_scope_with_provenance(self):
        candidates = [
            {"candidate_type": "lesson", "lesson_id": "L-KEEP", "project_id": "P",
             "source": {"path": "lessons.jsonl", "line": 1}, "retrieval_stage": "S1_STRUCTURED"},
            {"candidate_type": "lesson", "lesson_id": "L-EXCLUDE", "project_id": "P",
             "source": {"path": "lessons.jsonl", "line": 2}},
            {"candidate_type": "lesson", "lesson_id": "L-HOLD", "project_id": "P",
             "source": {"path": "lessons.jsonl", "line": 3}},
            {"candidate_type": "lesson", "lesson_id": "L-OTHER", "project_id": "OTHER",
             "source": {"path": "global.jsonl", "line": 4}},
        ]
        report = {
            "assessments": [
                {"candidate_id": "L-KEEP", "candidate_type": "lesson", "outcome": "APPLICABLE",
                 "reason": "ALL_CRITERIA_JUDGED_WITH_BASIS", "criteria": {}, "needs": [],
                 "adaptation_notes": [], "caps": []},
                {"candidate_id": "L-EXCLUDE", "candidate_type": "lesson", "outcome": "NOT_APPLICABLE",
                 "reason": "EXCEPTION_HOLDS", "criteria": {}, "needs": []},
                {"candidate_id": "L-HOLD", "candidate_type": "lesson", "outcome": "INSUFFICIENT_DATA",
                 "reason": "CRITERIA_UNDETERMINED",
                 "criteria": {"trigger": {"result": "UNKNOWN"}}, "needs": ["verify trigger"]},
            ],
            "usable_as_rationale": [{"candidate_id": "L-KEEP", "candidate_type": "lesson", "outcome": "APPLICABLE"}],
            "excluded": [{"candidate_id": "L-EXCLUDE", "candidate_type": "lesson", "reason": "EXCEPTION_HOLDS"}],
            "not_evaluated": [{"candidate_id": "L-OTHER", "candidate_type": "lesson",
                               "reason": "OUT_OF_CURRENT_SEARCH_SCOPE"}],
            "needs": [{"candidate_id": "L-HOLD", "candidate_type": "lesson", "needs": ["verify trigger"]}],
            "blocked_dependent_decisions": [],
        }
        frontier = reduce_decision_frontier(candidates, report, retrieval_status="CANDIDATES_FOUND")
        classes = {item["candidate_id"]: item["classification"] for item in frontier["directions"]}
        self.assertEqual(classes, {
            "L-KEEP": "KEEP_FOR_RATIONALE_REVIEW",
            "L-EXCLUDE": "EXCLUDE",
            "L-HOLD": "HOLD",
            "L-OTHER": "OUT_OF_SCOPE",
        })
        self.assertEqual(frontier["next_discriminating_check"]["type"], "RESOLVE_MISSING_EVIDENCE")
        keep = next(item for item in frontier["directions"] if item["candidate_id"] == "L-KEEP")
        self.assertEqual(keep["source"]["line"], 1)
        self.assertFalse(frontier["grants_planning_permission"])
        self.assertFalse(frontier["writes_performed"])

    def test_conflict_takes_priority_and_keeps_both_directions(self):
        candidates = [
            {"candidate_type": "lesson", "lesson_id": "L-A", "source": {"path": "a.jsonl"}},
            {"candidate_type": "lesson", "lesson_id": "L-B", "source": {"path": "b.jsonl"}},
        ]
        report = {
            "assessments": [
                {"candidate_id": "L-A", "candidate_type": "lesson", "outcome": "CONFLICT",
                 "reason": "DECLARED_INCOMPATIBLE_RECOMMENDATION", "conflicts_with": ["L-B"]},
                {"candidate_id": "L-B", "candidate_type": "lesson", "outcome": "CONFLICT",
                 "reason": "DECLARED_INCOMPATIBLE_RECOMMENDATION", "conflicts_with": ["L-A"]},
            ],
            "usable_as_rationale": [], "excluded": [], "not_evaluated": [], "needs": [],
            "blocked_dependent_decisions": [
                {"candidate_id": "L-A", "candidate_type": "lesson", "conflicts_with": ["L-B"]},
                {"candidate_id": "L-B", "candidate_type": "lesson", "conflicts_with": ["L-A"]},
            ],
        }
        frontier = reduce_decision_frontier(candidates, report)
        self.assertEqual(frontier["summary"]["conflicts"], 2)
        self.assertEqual(frontier["next_discriminating_check"]["type"], "RECONCILE_CONFLICT")
        self.assertEqual(frontier["next_discriminating_check"]["target_ids"], ["L-A", "L-B"])

    def test_duplicate_candidate_ids_preserve_both_sources_and_block_keep(self):
        candidates = [
            {"candidate_type": "event", "event_id": "EVT-DUP-1", "project_id": "P",
             "source": {"path": "project-a/events.jsonl", "line": 3}, "retrieval_stage": "EVENT_LEXICAL"},
            {"candidate_type": "event", "event_id": "EVT-DUP-1", "project_id": "P",
             "source": {"path": "project-b/events.jsonl", "line": 9}, "retrieval_stage": "EVENT_LEXICAL"},
        ]
        report = {
            "assessments": [{"candidate_id": "EVT-DUP-1", "candidate_type": "event",
                             "outcome": "APPLICABLE", "reason": "synthetic positive label"}],
            "usable_as_rationale": [{"candidate_id": "EVT-DUP-1", "candidate_type": "event"}],
            "excluded": [], "not_evaluated": [], "needs": [], "blocked_dependent_decisions": [],
        }
        frontier = reduce_decision_frontier(candidates, report)
        duplicates = [row for row in frontier["directions"] if row["candidate_id"] == "EVT-DUP-1"]
        self.assertEqual(len(duplicates), 2)
        self.assertEqual({row["classification"] for row in duplicates}, {"HOLD"})
        self.assertEqual(
            {row["source"]["path"] for row in duplicates},
            {"project-a/events.jsonl", "project-b/events.jsonl"},
        )
        self.assertTrue(all(row["duplicate_candidate_id"] for row in duplicates))
        self.assertEqual(frontier["summary"]["duplicate_candidate_keys"], 1)
        self.assertEqual(frontier["next_discriminating_check"]["type"], "RESOLVE_DUPLICATE_CANDIDATE_ID")
        self.assertFalse(frontier["grants_planning_permission"])

    def test_no_candidates_requests_retrieval_input_review(self):
        frontier = reduce_decision_frontier([], {}, retrieval_status="NO_MATCHES")
        self.assertEqual(frontier["status"], "NO_CANDIDATES")
        self.assertEqual(frontier["next_discriminating_check"]["type"], "IMPROVE_RETRIEVAL_INPUTS")
        self.assertFalse(frontier["execution_performed"])

    def test_outcome_label_alone_never_allows_keep(self):
        candidate = {"candidate_type": "lesson", "lesson_id": "L-1"}
        report = {
            "assessments": [{"candidate_id": "L-1", "candidate_type": "lesson",
                             "outcome": "APPLICABLE", "reason": "label only"}],
            "usable_as_rationale": [], "excluded": [], "not_evaluated": [], "needs": [],
            "blocked_dependent_decisions": [],
        }
        frontier = reduce_decision_frontier([candidate], report)
        self.assertEqual(frontier["directions"][0]["classification"], "HOLD")
        self.assertEqual(frontier["directions"][0]["reason"], "label only")


if __name__ == "__main__":
    unittest.main()
