"""Tests for the UMC-03 applicability evaluator and its integration in the minimal loop.

Lesson records here are FIXTURES. Passing these tests shows that the mechanism
behaves as specified; it is not evidence that any real repository lesson
(including the existing scope: global records) is applicable to anything.
"""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from applicability_evaluator import evaluate_applicability
from minimal_agent_loop import extract_explicit_experience_markers, retrieve_lesson_candidates, retrieve_lesson_candidates_structured, run_minimal_agent_loop

PROJECT = "TEST"
FULL = ("problem_similarity", "trigger", "applicability", "evidence_support", "circumstances_unchanged")


def lesson_candidate(lesson_id, **overrides):
    candidate = {
        "candidate_type": "lesson", "lesson_id": lesson_id, "status": "validated",
        "scope": "project", "project_id": PROJECT,
        "candidate_review_gate": "SCOPE_MATCHED_LESSON_REQUIRES_REVIEW",
        "supersedes": [],
    }
    candidate.update(overrides)
    return candidate


def judge(candidate_id, criterion, result, judged_by="user", basis="basis://check-1", **extra):
    item = {
        "candidate_id": candidate_id, "candidate_type": "lesson", "criterion": criterion,
        "result": result, "judged_by": judged_by, "basis_ref": basis,
    }
    item.update(extra)
    return item


def full_judgments(candidate_id, judged_by="user"):
    items = [judge(candidate_id, name, "MATCH", judged_by) for name in FULL]
    items.append(judge(candidate_id, "exceptions", "NOT_TRIGGERED", judged_by))
    return items


def outcome_of(report, candidate_id):
    for item in report["assessments"]:
        if item["candidate_id"] == candidate_id:
            return item["outcome"]
    return None


class EvaluatorUnitTests(unittest.TestCase):
    def test_user_assertions_with_basis_do_not_prove_applicability(self):
        report = evaluate_applicability([lesson_candidate("L-1")], full_judgments("L-1"))
        self.assertEqual(outcome_of(report, "L-1"), "INSUFFICIENT_DATA")
        self.assertEqual(report["usable_as_rationale"], [])
        self.assertTrue(any(
            c.get("claims_for_review") for a in report["assessments"]
            for c in a["criteria"].values()
        ))
        self.assertFalse(report["grants_planning_permission"])
        self.assertFalse(report["writes_performed"])

    def test_trusted_verifier_enables_positive_applicability_with_bound_receipts(self):
        candidate = lesson_candidate("L-VERIFIED", status="validated")
        judgments = full_judgments("L-VERIFIED", judged_by="agent")
        def verifier(candidate_arg, judgment):
            # Test double for an independently trusted verifier.
            return {
                "verified": True,
                "candidate_id": candidate_arg["lesson_id"],
                "candidate_type": "lesson",
                "criterion": judgment["criterion"],
                "result": judgment["result"],
                "basis_ref": judgment["basis_ref"],
                "verifier_id": "test-independent-verifier",
                "source_sha256": "a" * 64,
            }
        report = evaluate_applicability([candidate], judgments, verifier=verifier)
        self.assertEqual(outcome_of(report, "L-VERIFIED"), "APPLICABLE")
        self.assertEqual([item["candidate_id"] for item in report["usable_as_rationale"]], ["L-VERIFIED"])
        self.assertEqual(report["assessments"][0]["criteria"]["trigger"]["judged_by"], "rule")
        self.assertEqual(report["assessments"][0]["criteria"]["trigger"]["asserted_by"], "agent")
        self.assertTrue(report["assessments"][0]["criteria"]["trigger"]["verification"]["source_sha256"])
        self.assertFalse(report["grants_planning_permission"])

    def test_verifier_receipt_cannot_be_replayed_for_another_result_or_candidate(self):
        candidate = lesson_candidate("L-VERIFIED", status="validated")
        judgments = full_judgments("L-VERIFIED")
        def wrong_binding(candidate_arg, judgment):
            return {
                "verified": True, "candidate_id": "OTHER", "candidate_type": "lesson",
                "criterion": judgment["criterion"], "result": judgment["result"],
                "basis_ref": judgment["basis_ref"], "verifier_id": "test-verifier",
                "source_sha256": "b" * 64,
            }
        report = evaluate_applicability([candidate], judgments, verifier=wrong_binding)
        self.assertEqual(outcome_of(report, "L-VERIFIED"), "INSUFFICIENT_DATA")
        self.assertEqual(report["usable_as_rationale"], [])

    def test_rule_label_and_nonempty_basis_cannot_self_certify(self):
        report = evaluate_applicability(
            [lesson_candidate("L-1")], full_judgments("L-1", judged_by="rule")
        )
        self.assertEqual(outcome_of(report, "L-1"), "INSUFFICIENT_DATA")
        self.assertEqual(report["usable_as_rationale"], [])

    def test_no_judgments_means_insufficient_data_with_named_needs(self):
        report = evaluate_applicability([lesson_candidate("L-1")])
        self.assertEqual(outcome_of(report, "L-1"), "INSUFFICIENT_DATA")
        self.assertEqual(report["usable_as_rationale"], [])
        needs = report["needs"][0]["needs"]
        self.assertTrue(any("exceptions" in item for item in needs))
        self.assertEqual(report["restrictive_policy"], "ASK_OR_SEARCH_MORE")

    def test_permissive_judgment_without_basis_is_ignored(self):
        judgments = full_judgments("L-1")
        judgments[0] = judge("L-1", "problem_similarity", "MATCH", basis="")
        report = evaluate_applicability([lesson_candidate("L-1")], judgments)
        self.assertEqual(outcome_of(report, "L-1"), "INSUFFICIENT_DATA")

    def test_restrictive_judgment_is_honoured_even_without_basis(self):
        judgments = full_judgments("L-1") + [judge("L-1", "exceptions", "TRIGGERED", "agent", basis="")]
        report = evaluate_applicability([lesson_candidate("L-1")], judgments)
        self.assertEqual(outcome_of(report, "L-1"), "NOT_APPLICABLE")
        self.assertEqual(report["usable_as_rationale"], [])
        self.assertEqual(report["excluded"][0]["reason"], "EXCEPTION_HOLDS")

    def test_agent_judged_criteria_remain_unverified(self):
        report = evaluate_applicability([lesson_candidate("L-1")], full_judgments("L-1", "agent"))
        self.assertEqual(outcome_of(report, "L-1"), "INSUFFICIENT_DATA")
        self.assertEqual(report["usable_as_rationale"], [])

    def test_user_judgment_outranks_agent_judgment_on_same_criterion(self):
        judgments = full_judgments("L-1", "agent") + full_judgments("L-1", "user")
        report = evaluate_applicability([lesson_candidate("L-1")], judgments)
        self.assertEqual(outcome_of(report, "L-1"), "INSUFFICIENT_DATA")

    def test_candidate_status_never_reaches_plain_applicable(self):
        report = evaluate_applicability(
            [lesson_candidate("L-1", status="candidate")], full_judgments("L-1")
        )
        self.assertEqual(outcome_of(report, "L-1"), "INSUFFICIENT_DATA")
        self.assertEqual(report["usable_as_rationale"], [])

    def test_explicit_difference_gives_adaptation_with_note(self):
        judgments = [j for j in full_judgments("L-1") if j["criterion"] != "circumstances_unchanged"]
        judgments.append(judge("L-1", "circumstances_unchanged", "MISMATCH",
                               adaptation_note="library version differs"))
        report = evaluate_applicability([lesson_candidate("L-1")], judgments)
        self.assertEqual(outcome_of(report, "L-1"), "INSUFFICIENT_DATA")
        self.assertEqual(report["usable_as_rationale"], [])

    def test_violated_condition_without_adaptation_note_is_not_applicable(self):
        judgments = [j for j in full_judgments("L-1") if j["criterion"] != "trigger"]
        judgments.append(judge("L-1", "trigger", "MISMATCH"))
        report = evaluate_applicability([lesson_candidate("L-1")], judgments)
        self.assertEqual(outcome_of(report, "L-1"), "NOT_APPLICABLE")

    def test_global_and_out_of_project_candidates_are_not_evaluated(self):
        candidates = [
            lesson_candidate("G-1", scope="global", project_id="global",
                             candidate_review_gate="OUT_OF_PROJECT_SCOPE"),
            lesson_candidate("G-2", scope="global"),
            lesson_candidate("O-1", project_id="OTHER", candidate_review_gate="OUT_OF_PROJECT_SCOPE"),
        ]
        report = evaluate_applicability(candidates, full_judgments("G-1") + full_judgments("G-2"))
        self.assertEqual(report["assessments"], [])
        self.assertEqual({item["candidate_id"] for item in report["not_evaluated"]}, {"G-1", "G-2", "O-1"})
        self.assertEqual(report["excluded"], [])
        self.assertIsNone(report["restrictive_policy"])

    def test_unknown_project_scope_is_insufficient_data(self):
        report = evaluate_applicability(
            [lesson_candidate("L-1", candidate_review_gate="PROJECT_SCOPE_UNKNOWN")],
            full_judgments("L-1"),
        )
        self.assertEqual(outcome_of(report, "L-1"), "INSUFFICIENT_DATA")

    def test_blocked_evidence_route_is_insufficient_data(self):
        report = evaluate_applicability(
            [lesson_candidate("L-1", candidate_review_gate="SCOPE_MATCHED_EVIDENCE_SOURCE_UNAVAILABLE_BLOCKED")],
            full_judgments("L-1"),
        )
        self.assertEqual(outcome_of(report, "L-1"), "INSUFFICIENT_DATA")

    def test_event_is_history_never_applicable_and_does_not_drive_policy(self):
        event = {
            "candidate_type": "event", "event_id": "EVT-1", "status": "verified",
            "candidate_review_gate": "SCOPE_MATCHED_VERIFIED_LABEL_WITH_REFS_REVIEW_REQUIRED",
        }
        judgments = [dict(j, candidate_id="EVT-1", candidate_type="event") for j in full_judgments("x")]
        report = evaluate_applicability([event], judgments)
        self.assertEqual(outcome_of(report, "EVT-1"), "INSUFFICIENT_DATA")
        self.assertTrue(report["needs"][0]["informational"])
        self.assertIsNone(report["restrictive_policy"])

    def test_retired_lessons_are_excluded_with_replacement_when_known(self):
        old = lesson_candidate("L-OLD", status="superseded")
        deprecated = lesson_candidate("L-DEP", status="deprecated")
        new = lesson_candidate("L-NEW", supersedes=["L-OLD"])
        report = evaluate_applicability([old, deprecated, new], full_judgments("L-NEW"))
        by_id = {item["candidate_id"]: item for item in report["excluded"]}
        self.assertEqual(by_id["L-OLD"]["reason"], "superseded")
        self.assertEqual(by_id["L-OLD"]["replacement"], "L-NEW")
        self.assertEqual(by_id["L-DEP"]["replacement"], "UNKNOWN")
        self.assertEqual(outcome_of(report, "L-NEW"), "INSUFFICIENT_DATA")

    def test_disputed_lesson_requires_dispute_resolution(self):
        report = evaluate_applicability([lesson_candidate("L-1", status="disputed")], full_judgments("L-1"))
        self.assertEqual(outcome_of(report, "L-1"), "INSUFFICIENT_DATA")
        self.assertIn("resolve dispute", report["needs"][0]["needs"][0])

    def test_unknown_status_is_reported_not_guessed(self):
        for status in ("accepted", "weird", None):
            with self.subTest(status=status):
                report = evaluate_applicability([lesson_candidate("L-1", status=status)], full_judgments("L-1"))
                self.assertEqual(outcome_of(report, "L-1"), "INSUFFICIENT_DATA")
                self.assertEqual(report["assessments"][0]["reason"], "STATUS_SEMANTICS_UNDEFINED")

    def test_declared_conflict_blocks_both_candidates(self):
        judgments = full_judgments("L-A") + full_judgments("L-B") + [
            judge("L-A", "compatibility", "CONFLICT", with_candidate_id="L-B"),
        ]
        report = evaluate_applicability([lesson_candidate("L-A"), lesson_candidate("L-B")], judgments)
        self.assertEqual(outcome_of(report, "L-A"), "CONFLICT")
        self.assertEqual(outcome_of(report, "L-B"), "CONFLICT")
        self.assertEqual(report["usable_as_rationale"], [])
        self.assertEqual(len(report["blocked_dependent_decisions"]), 2)
        self.assertEqual(report["restrictive_policy"], "STOP_RESOLVE_CONFLICT")

    def test_triggered_exception_takes_precedence_over_declared_conflict(self):
        judgments = full_judgments("L-A") + full_judgments("L-B") + [
            judge("L-A", "exceptions", "TRIGGERED"),
            judge("L-B", "compatibility", "CONFLICT", with_candidate_id="L-A"),
        ]
        report = evaluate_applicability([lesson_candidate("L-A"), lesson_candidate("L-B")], judgments)
        self.assertEqual(outcome_of(report, "L-A"), "NOT_APPLICABLE")
        self.assertEqual(outcome_of(report, "L-B"), "CONFLICT")

    def test_malformed_judgments_are_reported_and_never_grant_applicability(self):
        judgments = [
            "not an object",
            judge("L-1", "no_such_criterion", "MATCH"),
            judge("L-1", "trigger", "MATCH", judged_by="oracle"),
            judge("L-1", "exceptions", "MATCH"),
            judge("L-1", "compatibility", "CONFLICT"),
            judge("GHOST", "trigger", "MATCH"),
        ]
        report = evaluate_applicability([lesson_candidate("L-1")], judgments)
        issues = {item["issue"] for item in report["judgment_issues"]}
        self.assertTrue({"NOT_AN_OBJECT", "UNKNOWN_CRITERION", "INVALID_JUDGED_BY",
                         "INVALID_RESULT_FOR_CRITERION", "CONFLICT_WITHOUT_with_candidate_id",
                         "JUDGMENT_FOR_UNKNOWN_CANDIDATE"} <= issues)
        self.assertEqual(outcome_of(report, "L-1"), "INSUFFICIENT_DATA")

    def test_evaluator_does_not_mutate_inputs(self):
        candidates = [lesson_candidate("L-1")]
        judgments = full_judgments("L-1")
        before = json.dumps([candidates, judgments], sort_keys=True)
        evaluate_applicability(candidates, judgments)
        self.assertEqual(json.dumps([candidates, judgments], sort_keys=True), before)


class LoopIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        project = self.root / "projects" / PROJECT
        project.mkdir(parents=True)
        self.task = project / "TASK_STATE.md"
        self.handoff = project / "HANDOFF.md"
        self.events = project / "events.jsonl"
        self.lessons = self.root / "lessons.jsonl"
        self.events.write_text(json.dumps({
            "event_id": "EVT-CURRENT-1", "project_id": PROJECT, "type": "checkpoint",
            "summary": "Current task checkpoint", "status": "verified", "lifecycle_status": "accepted",
        }) + "\n", encoding="utf-8")
        self.task.write_text(
            "# TASK_STATE\n"
            "- **Активная задача в текущей сессии:** восстановить staging snapshot\n"
            "- **Следующий шаг:** проверить staging snapshot\n"
            "- **Последнее событие:** EVT-CURRENT-1\n", encoding="utf-8")
        self.handoff.write_text(
            "# HANDOFF\n- **Следующий шаг:** проверить staging snapshot\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def _lesson(self, lesson_id, **overrides):
        record = {
            "lesson_id": lesson_id, "scope": "project", "project_id": PROJECT,
            "title": "Verify staging snapshot after restore", "status": "validated",
            "trigger": "restoring a staging snapshot", "observed_problem": "staging snapshot restore reported success without data check",
            "prevention_rule": "compare restored data with the snapshot", "applicability": ["staging snapshot restore"],
            "exceptions": ["snapshot is empty by design"], "evidence_refs": ["projects/TEST/events.jsonl:EVT-CURRENT-1"],
            "supersedes": [],
            "markers": {
                "problem_types": ["snapshot_restore"],
                "tools": ["Python", "SQLite"],
                "languages": ["Python"],
                "environments": ["GitHub Actions"],
            },
        }
        record.update(overrides)
        return record

    def _write_lessons(self, records):
        self.lessons.write_text(
            "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in records), encoding="utf-8")

    def _run(self, judgments=None, **kwargs):
        return run_minimal_agent_loop(
            self.task, self.handoff, self.events, "Investigate staging snapshot restore",
            lesson_logs=[self.lessons], judgments=judgments, **kwargs)

    @staticmethod
    def _sha(path):
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()

    def _assert_planning_still_blocked(self, result):
        self.assertEqual(result["checkpoint_currentness_gate"]["status"], "BLOCKED_CURRENTNESS_UNVERIFIED")
        self.assertFalse(result["checkpoint_currentness_gate"]["authorized_for_planning"])
        self.assertFalse(result["applicability"]["grants_planning_permission"])
        self.assertIn(result["next_action_policy"], {
            "REVIEW_CANDIDATES_ONLY_NO_PLANNING", "ASK_OR_SEARCH_MORE",
            "STOP_RESOLVE_CONFLICT", "STOP_AND_RECONCILE_SOURCES",
        })
        self.assertFalse(result["writes_performed"])

    def test_t1_unverified_assertions_do_not_enter_rationale(self):
        self._write_lessons([self._lesson("L-1")])
        lesson_hash = self._sha(self.lessons)
        result = self._run(full_judgments("L-1"), current_project_id=PROJECT)
        self.assertEqual(result["lesson_retrieval"]["status"], "CANDIDATES_FOUND")
        applicability = result["applicability"]
        self.assertEqual(outcome_of(applicability, "L-1"), "INSUFFICIENT_DATA")
        self.assertEqual([u["candidate_id"] for u in applicability["usable_as_rationale"]], [])
        self._assert_planning_still_blocked(result)
        self.assertEqual(result["next_action_policy"], "ASK_OR_SEARCH_MORE")
        self.assertEqual(self._sha(self.lessons), lesson_hash)

        # Same record, same lexical score, one changed judgment: the outcome changes.
        changed = [j for j in full_judgments("L-1") if j["criterion"] != "circumstances_unchanged"]
        changed.append(judge("L-1", "circumstances_unchanged", "MISMATCH"))
        second = self._run(changed, current_project_id=PROJECT)
        self.assertEqual(
            second["lesson_retrieval"]["candidates"][0]["score"],
            result["lesson_retrieval"]["candidates"][0]["score"],
        )
        self.assertEqual(outcome_of(second["applicability"], "L-1"), "NOT_APPLICABLE")
        self.assertEqual(second["applicability"]["usable_as_rationale"], [])

    def test_verified_lesson_can_enter_rationale_but_never_unblocks_planning(self):
        self._write_lessons([self._lesson("L-VERIFIED", status="validated")])
        def verifier(candidate, judgment):
            return {
                "verified": True,
                "candidate_id": candidate["lesson_id"],
                "candidate_type": "lesson",
                "criterion": judgment["criterion"],
                "result": judgment["result"],
                "basis_ref": judgment["basis_ref"],
                "verifier_id": "test-independent-verifier",
                "source_sha256": "c" * 64,
            }
        result = self._run(
            full_judgments("L-VERIFIED", judged_by="agent"),
            current_project_id=PROJECT,
            current_markers={"problem_types": ["snapshot_restore"], "tools": ["Python"]},
            judgment_verifier=verifier,
        )
        self.assertEqual(outcome_of(result["applicability"], "L-VERIFIED"), "APPLICABLE")
        self.assertEqual(result["applicability"]["usable_as_rationale"][0]["candidate_id"], "L-VERIFIED")
        self.assertEqual(result["next_action_policy"], "REVIEW_CANDIDATES_ONLY_NO_PLANNING")
        self.assertEqual(result["lesson_search_stages"][0]["stage"], "S1_STRUCTURED")
        self.assertTrue(result["lesson_search_stages"][0]["verified_applicable_found"])
        self.assertEqual(result["lesson_search_stages"][1]["status"], "SKIPPED_SUFFICIENT_S1")
        self._assert_planning_still_blocked(result)

    def test_task_state_markers_are_read_only_from_explicit_json_block(self):
        fence = chr(96) * 3
        self.task.write_text(
            "# TASK_STATE\n- active goal: restore snapshot\n"
            + fence + "experience-markers\n"
            + '{"problem_types":["snapshot_restore"],"tools":["Python"]}\n'
            + fence + "\n",
            encoding="utf-8",
        )
        markers, source = extract_explicit_experience_markers(self.task)
        self.assertEqual(source, "TASK_STATE_EXPLICIT_BLOCK")
        self.assertEqual(markers["problem_types"], ["snapshot_restore"])
        self.assertEqual(markers["tools"], ["Python"])

    def test_task_state_marker_reader_does_not_infer_from_prose_or_accept_malformed_json(self):
        self.task.write_text("# TASK_STATE\n- Python snapshot restore\n", encoding="utf-8")
        markers, source = extract_explicit_experience_markers(self.task)
        self.assertIsNone(markers)
        self.assertEqual(source, "NOT_DECLARED")
        fence = chr(96) * 3
        self.task.write_text(
            "# TASK_STATE\n" + fence + "experience-markers\nnot-json\n" + fence + "\n",
            encoding="utf-8",
        )
        markers, source = extract_explicit_experience_markers(self.task)
        self.assertIsNone(markers)
        self.assertEqual(source, "INVALID_TASK_STATE_MARKERS_BLOCK")

    def test_s1_structured_markers_are_exact_and_project_scoped(self):
        self._write_lessons([
            self._lesson("L-S1"),
            self._lesson("L-OTHER", project_id="OTHER"),
            self._lesson("L-NO-MATCH", markers={"tools": ["Rust"], "languages": ["Rust"], "problem_types": ["compiler"]}),
            self._lesson("L-GLOBAL", scope="global", project_id="global"),
        ])
        result = retrieve_lesson_candidates_structured(
            {"problem_types": ["snapshot_restore"], "tools": ["Python"]},
            [self.lessons], current_project_id=PROJECT,
        )
        self.assertEqual(result["status"], "CANDIDATES_FOUND")
        self.assertEqual([c["lesson_id"] for c in result["candidates"]], ["L-S1"])
        self.assertIn("problem_types", result["candidates"][0]["matching_marker_dimensions"])
        self.assertEqual(result["candidates"][0]["project_scope_match"], "MATCH")
        self.assertGreaterEqual(result["out_of_scope_count"], 2)

    def test_s1_and_s2_candidates_are_deduplicated_and_both_retained(self):
        self._write_lessons([
            self._lesson("L-S1"),
            self._lesson("L-S2", markers={"problem_types": ["other_problem"], "tools": ["Rust"]}),
        ])
        result = self._run(
            None, current_project_id=PROJECT,
            current_markers={"problem_types": ["snapshot_restore"]},
        )
        self.assertEqual(result["lesson_search_stages"][0]["stage"], "S1_STRUCTURED")
        self.assertEqual(result["lesson_search_stages"][0]["candidate_count"], 1)
        self.assertEqual(result["lesson_search_stages"][1]["stage"], "S2_LEXICAL")
        self.assertEqual(result["lesson_search_stages"][1]["candidate_count"], 2)
        self.assertEqual(
            {item["lesson_id"] for item in result["lesson_retrieval"]["candidates"]},
            {"L-S1", "L-S2"},
        )
        self.assertEqual(result["lesson_retrieval"]["candidate_count_combined"], 2)
        self.assertIn(str(self.lessons), result["lesson_search_stages"][0]["source_hashes"])

    def test_s2_lexical_fallback_runs_when_s1_has_no_verified_applicable_lesson(self):
        self._write_lessons([self._lesson("L-1")])
        result = self._run(None, current_project_id=PROJECT,
                           current_markers={"problem_types": ["different_problem"]})
        self.assertEqual(result["lesson_search_stages"][0]["status"], "NO_MATCHES")
        self.assertEqual(result["lesson_search_stages"][1]["stage"], "S2_LEXICAL")
        self.assertEqual(result["lesson_search_stages"][1]["status"], "CANDIDATES_FOUND")
        self.assertEqual([c["lesson_id"] for c in result["lesson_retrieval"]["candidates"]], ["L-1"])
        self.assertEqual(outcome_of(result["applicability"], "L-1"), "INSUFFICIENT_DATA")

    def test_s1_without_markers_falls_back_to_s2(self):
        self._write_lessons([self._lesson("L-1")])
        result = self._run(None, current_project_id=PROJECT)
        self.assertEqual(result["lesson_search_stages"][0]["status"], "NO_MARKERS")
        self.assertEqual(result["lesson_search_stages"][1]["status"], "CANDIDATES_FOUND")
        self.assertEqual(result["lesson_retrieval"]["candidates"][0]["retrieval_stage"], "S2_LEXICAL")

    def test_t1b_global_lesson_is_reported_not_evaluated_and_left_unchanged(self):
        self._write_lessons([self._lesson("G-1", scope="global", project_id="global")])
        lesson_hash = self._sha(self.lessons)
        result = self._run(full_judgments("G-1"), current_project_id=PROJECT)
        applicability = result["applicability"]
        self.assertEqual(applicability["assessments"], [])
        self.assertEqual(applicability["not_evaluated"][0]["candidate_id"], "G-1")
        self.assertEqual(applicability["not_evaluated"][0]["scope"], "global")
        self.assertEqual(applicability["usable_as_rationale"], [])
        self.assertEqual(applicability["excluded"], [])
        self.assertEqual(self._sha(self.lessons), lesson_hash)

    def test_t1c_lesson_statuses_follow_spec(self):
        self._write_lessons([
            self._lesson("L-OLD", status="superseded"),
            self._lesson("L-DISPUTED", status="disputed"),
            self._lesson("L-CAND", status="candidate"),
            self._lesson("L-ODD", status="accepted"),
            self._lesson("L-NEW", supersedes=["L-OLD"]),
        ])
        judgments = []
        for lid in ("L-CAND", "L-ODD", "L-NEW", "L-DISPUTED"):
            judgments += full_judgments(lid)
        result = self._run(judgments, current_project_id=PROJECT)
        applicability = result["applicability"]
        self.assertEqual(outcome_of(applicability, "L-CAND"), "INSUFFICIENT_DATA")
        self.assertEqual(outcome_of(applicability, "L-DISPUTED"), "INSUFFICIENT_DATA")
        self.assertEqual(outcome_of(applicability, "L-ODD"), "INSUFFICIENT_DATA")
        self.assertEqual(outcome_of(applicability, "L-NEW"), "INSUFFICIENT_DATA")
        retired = {item["candidate_id"]: item for item in applicability["excluded"]}
        self.assertEqual(retired["L-OLD"]["replacement"], "L-NEW")
        # A disputed lesson carries only `status`; it must not be missed for lacking lifecycle_status.
        self.assertNotIn("lifecycle_status", self._lesson("L-DISPUTED"))

    def test_t2_triggered_exception_excludes_lesson_despite_everything_else(self):
        self._write_lessons([self._lesson("L-1", status="validated")])
        judgments = full_judgments("L-1") + [judge("L-1", "exceptions", "TRIGGERED")]
        result = self._run(judgments, current_project_id=PROJECT)
        applicability = result["applicability"]
        self.assertEqual(outcome_of(applicability, "L-1"), "NOT_APPLICABLE")
        self.assertEqual(applicability["usable_as_rationale"], [])
        self.assertEqual(applicability["excluded"][0]["reason"], "EXCEPTION_HOLDS")
        self.assertEqual(result["lesson_retrieval"]["candidates"][0]["score"] > 0, True)

    def test_t3a_insufficient_data_asks_for_more_and_does_not_use_the_lesson(self):
        self._write_lessons([self._lesson("L-1")])
        result = self._run(None, current_project_id=PROJECT)
        applicability = result["applicability"]
        self.assertEqual(outcome_of(applicability, "L-1"), "INSUFFICIENT_DATA")
        self.assertEqual(applicability["usable_as_rationale"], [])
        self.assertTrue(applicability["needs"][0]["needs"])
        self.assertEqual(result["next_action_policy"], "ASK_OR_SEARCH_MORE")
        self._assert_planning_still_blocked(result)

    def test_t3b_conflict_stops_dependent_decision(self):
        self._write_lessons([self._lesson("L-A"), self._lesson("L-B", title="Skip staging snapshot verification")])
        judgments = full_judgments("L-A") + full_judgments("L-B") + [
            judge("L-A", "compatibility", "CONFLICT", with_candidate_id="L-B"),
        ]
        result = self._run(judgments, current_project_id=PROJECT)
        applicability = result["applicability"]
        self.assertEqual(outcome_of(applicability, "L-A"), "CONFLICT")
        self.assertEqual(outcome_of(applicability, "L-B"), "CONFLICT")
        self.assertEqual(applicability["usable_as_rationale"], [])
        self.assertTrue(applicability["blocked_dependent_decisions"])
        self.assertEqual(result["next_action_policy"], "STOP_RESOLVE_CONFLICT")
        self._assert_planning_still_blocked(result)

    def test_t4_unverified_lesson_cannot_unblock_planning_or_untrusted_context(self):
        self._write_lessons([self._lesson("L-1")])
        ok = self._run(full_judgments("L-1"), current_project_id=PROJECT)
        self.assertEqual(outcome_of(ok["applicability"], "L-1"), "INSUFFICIENT_DATA")
        self._assert_planning_still_blocked(ok)

        # Context without a next step is not trusted; the evaluator must not change that.
        self.task.write_text(
            "# TASK_STATE\n- **Активная задача в текущей сессии:** восстановить staging snapshot\n"
            "- **Последнее событие:** EVT-CURRENT-1\n", encoding="utf-8")
        self.handoff.write_text("# HANDOFF\n", encoding="utf-8")
        untrusted = self._run(full_judgments("L-1"), current_project_id=PROJECT)
        self.assertEqual(untrusted["trust_gate"]["status"], "REFUSED_UNKNOWN_NEXT_STEP")
        self.assertEqual(outcome_of(untrusted["applicability"], "L-1"), "INSUFFICIENT_DATA")
        self.assertNotEqual(untrusted["trust_gate"]["status"], "AUTHORIZED_FOR_PLANNING")
        self._assert_planning_still_blocked(untrusted)

        # Blocked sources keep the stricter base policy; the evaluator cannot relax it.
        self.events.write_text("{broken\n", encoding="utf-8")
        blocked = self._run(full_judgments("L-1"), current_project_id=PROJECT)
        self.assertEqual(blocked["status"], "CONTEXT_OR_RETRIEVAL_BLOCKED")
        self.assertEqual(blocked["next_action_policy"], "STOP_AND_RECONCILE_SOURCES")
        self._assert_planning_still_blocked(blocked)

    def test_scope_unknown_without_explicit_project_is_insufficient_not_evaluated_as_match(self):
        # task_state under projects/TEST/ infers the project, so pass a mismatching one explicitly.
        self._write_lessons([self._lesson("L-1")])
        result = self._run(full_judgments("L-1"), current_project_id="OTHER")
        applicability = result["applicability"]
        self.assertEqual(applicability["assessments"], [])
        self.assertEqual(applicability["not_evaluated"][0]["candidate_id"], "L-1")

    def test_invalid_lesson_file_fails_closed(self):
        self.lessons.write_text("{not json}\n", encoding="utf-8")
        result = self._run(None, current_project_id=PROJECT)
        self.assertEqual(result["lesson_retrieval"]["status"], "BLOCKED")
        self.assertEqual(result["status"], "CONTEXT_OR_RETRIEVAL_BLOCKED")
        self.assertEqual(result["lesson_retrieval"]["candidates"], [])

    def test_lesson_without_id_fails_closed_and_missing_file_blocks(self):
        self.lessons.write_text(json.dumps({"title": "no id"}) + "\n", encoding="utf-8")
        self.assertEqual(retrieve_lesson_candidates("staging snapshot", [self.lessons])["status"], "BLOCKED")
        missing = retrieve_lesson_candidates("staging snapshot", [self.root / "absent.jsonl"])
        self.assertEqual(missing["status"], "BLOCKED")

    def test_malformed_evidence_refs_are_flagged_not_reinterpreted(self):
        self._write_lessons([self._lesson("L-1", evidence_refs="['free text note']")])
        result = retrieve_lesson_candidates("staging snapshot", [self.lessons], current_project_id=PROJECT)
        candidate = result["candidates"][0]
        self.assertTrue(candidate["evidence_refs_malformed"])
        self.assertEqual(candidate["evidence_refs"], [])
        self.assertEqual(candidate["transfer_decision"], "UNASSESSED")

    def test_event_candidates_keep_working_and_are_history_only(self):
        experience = self.root / "shared-events.jsonl"
        experience.write_text(json.dumps({
            "event_id": "EVT-EXP-1", "project_id": PROJECT, "type": "test_result",
            "summary": "Staging snapshot restore succeeded", "status": "verified",
        }) + "\n", encoding="utf-8")
        result = run_minimal_agent_loop(
            self.task, self.handoff, self.events, "Investigate staging snapshot restore",
            [experience], current_project_id=PROJECT)
        self.assertEqual(result["retrieval"]["candidates"][0]["candidate_type"], "event")
        self.assertEqual(result["lesson_retrieval"]["status"], "NOT_REQUESTED")
        self.assertEqual(outcome_of(result["applicability"], "EVT-EXP-1"), "INSUFFICIENT_DATA")
        self.assertEqual(result["applicability"]["usable_as_rationale"], [])
        self.assertEqual(result["next_action_policy"], "REVIEW_CANDIDATES_ONLY_NO_PLANNING")


if __name__ == "__main__":
    unittest.main()
