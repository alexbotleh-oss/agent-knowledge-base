import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from check_reuse_policy import evaluate_check_reuse, record_check_result


class CheckReusePolicyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.log = Path(self.tmp.name) / "projects" / "AGENT_MEMORY_SYSTEM" / "events.jsonl"
        self.check = {"type": "RESOLVE_MISSING_EVIDENCE", "target_ids": ["LESSON-1"],
                      "criteria": ["trigger"], "needs": ["verify trigger"]}
        self.sources = {"task_state": "a" * 64, "experience": "b" * 64}
        self.candidates = [{"candidate_type": "lesson", "candidate_id": "LESSON-1",
                            "source_sha256": "b" * 64, "source_path": "lessons.jsonl", "line": 1}]

    def tearDown(self):
        self.tmp.cleanup()

    def test_no_prior_check_requests_run(self):
        result = evaluate_check_reuse(self.log, self.check, self.sources, self.candidates)
        self.assertEqual(result["status"], "RUN_CHECK")
        self.assertEqual(result["action"], "RUN_CHECK")
        self.assertFalse(result["writes_performed"])

    def test_exact_recorded_pass_is_reused_and_replay_is_idempotent(self):
        first = record_check_result(
            self.log, self.check, self.sources, self.candidates,
            result_status="PASS", evidence_refs=["tests/test_trigger.py#case-1"],
            summary="Trigger condition was verified", recorded_by="CI run 123",
        )
        replay = record_check_result(
            self.log, self.check, self.sources, self.candidates,
            result_status="PASS", evidence_refs=["tests/test_trigger.py#case-1"],
            summary="Trigger condition was verified", recorded_by="CI run 123",
        )
        self.assertEqual(first["status"], "RECORDED")
        self.assertEqual(replay["status"], "ALREADY_RECORDED")
        self.assertFalse(replay["writes_performed"])
        reused = evaluate_check_reuse(self.log, self.check, self.sources, self.candidates)
        self.assertEqual(reused["status"], "REUSE_RECORDED_PASS")
        self.assertEqual(reused["action"], "DO_NOT_REPEAT_CHECK")
        self.assertEqual(reused["prior_event_id"], first["event_id"])
        self.assertIn("not independently authenticated", reused["trust_boundary"])
        self.assertEqual(len(self.log.read_text(encoding="utf-8").splitlines()), 1)

    def test_changed_source_hash_forces_recheck(self):
        record_check_result(
            self.log, self.check, self.sources, self.candidates,
            result_status="PASS", evidence_refs=["tests/test_trigger.py#case-1"],
            summary="Trigger condition was verified", recorded_by="CI run 123",
        )
        changed = {**self.sources, "experience": "c" * 64}
        result = evaluate_check_reuse(self.log, self.check, changed, self.candidates)
        self.assertEqual(result["status"], "RECHECK_INPUTS_CHANGED")
        self.assertEqual(result["action"], "RUN_CHECK")

    def test_pass_without_evidence_is_rejected(self):
        result = record_check_result(
            self.log, self.check, self.sources, self.candidates,
            result_status="PASS", evidence_refs=[], summary="No proof",
            recorded_by="agent",
        )
        self.assertEqual(result["status"], "REJECTED")
        self.assertEqual(result["reason"], "PASS_REQUIRES_EVIDENCE_REFS")
        self.assertFalse(self.log.exists())

    def test_nonpass_is_not_reused(self):
        record_check_result(
            self.log, self.check, self.sources, self.candidates,
            result_status="FAIL", evidence_refs=["tests/test_trigger.py#case-1"],
            summary="Trigger check failed", recorded_by="CI run 123",
        )
        result = evaluate_check_reuse(self.log, self.check, self.sources, self.candidates)
        self.assertEqual(result["status"], "RECHECK_PRIOR_RESULT_NOT_REUSABLE")
        self.assertEqual(result["action"], "RUN_CHECK")

    def test_corrupt_journal_fails_closed(self):
        self.log.parent.mkdir(parents=True)
        self.log.write_text("{broken json\n", encoding="utf-8")
        result = evaluate_check_reuse(self.log, self.check, self.sources, self.candidates)
        self.assertEqual(result["status"], "BLOCKED_JOURNAL_INVALID")
        self.assertEqual(result["action"], "STOP_AND_RECONCILE")

    def test_missing_or_malformed_source_hashes_never_allow_reuse(self):
        result = evaluate_check_reuse(self.log, self.check, {"task_state": "UNKNOWN"}, self.candidates)
        self.assertEqual(result["status"], "INSUFFICIENT_INPUT_FINGERPRINT")
        self.assertEqual(result["action"], "RUN_CHECK")


if __name__ == "__main__":
    unittest.main()
