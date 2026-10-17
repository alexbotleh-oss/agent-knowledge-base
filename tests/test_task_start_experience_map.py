import base64
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from dialogue_attention_controller import process_turn
from agent_memory_cycle import run_cycle
from branch_result_registry import publish_result, acknowledge_result
from reconcile_branch_returns import build_report as build_branch_return_report
from check_reuse_policy import record_check_result
from trusted_receipt_verifier import canonical_receipt_payload
import task_start_experience_map as task_start_module
from task_start_experience_map import build_task_start_experience_map


class TaskStartExperienceMapTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self._old_env = {key: os.environ.get(key) for key in ("AGMS_TRUSTED_KEYRING_PATH", "AGMS_TRUSTED_KEYRING_SHA256")}
        self.private_key = self.root / "test-private.pem"
        self.public_key = self.root / "test-public.pem"
        subprocess.run(["openssl", "genpkey", "-algorithm", "ED25519", "-out", str(self.private_key)], check=True, capture_output=True)
        subprocess.run(["openssl", "pkey", "-in", str(self.private_key), "-pubout", "-out", str(self.public_key)], check=True, capture_output=True)
        self.keyring = self.root / "trusted-keyring.json"
        self.keyring.write_text(json.dumps({"schema_version": "1.0", "keys": [{
            "key_id": "test-key-1", "issuer_id": "test-signer", "algorithm": "Ed25519", "status": "ACTIVE",
            "allowed_receipt_types": ["applicability_judgment", "check_result", "owner_acknowledgement"],
            "public_key_pem": self.public_key.read_text(encoding="utf-8"),
        }]}, sort_keys=True), encoding="utf-8")
        os.environ["AGMS_TRUSTED_KEYRING_PATH"] = str(self.keyring)
        os.environ["AGMS_TRUSTED_KEYRING_SHA256"] = hashlib.sha256(self.keyring.read_bytes()).hexdigest()
        self.project = self.root / "projects" / "TEST"
        self.project.mkdir(parents=True)
        self.task = self.project / "TASK_STATE.md"
        self.handoff = self.project / "HANDOFF.md"
        self.events = self.project / "events.jsonl"
        self.experience = self.root / "shared-events.jsonl"
        self.experience2 = self.root / "shared-events-duplicate.jsonl"
        self.lessons = self.root / "lessons.jsonl"
        self.attention = self.root / "projects" / "AGENT_MEMORY_SYSTEM" / "events.jsonl"
        self.task.write_text(
            "# TASK_STATE — TASK-PARENT\n"
            "project_id: TEST\n"
            "- **Активная задача в текущей сессии:** Investigate cache recovery\n"
            "- **Последнее событие:** EVT-CURRENT-1\n",
            encoding="utf-8",
        )
        self.handoff.write_text(
            "# HANDOFF\n"
            "project_id: TEST\n"
            "- **Следующий шаг:** Compare prior successful and failed attempts\n",
            encoding="utf-8",
        )
        self._write(self.events, [{
            "event_id": "EVT-CURRENT-1", "project_id": "TEST", "type": "checkpoint",
            "summary": "Current task checkpoint for cache recovery", "status": "verified",
        }])
        self._write(self.experience, [{
            "event_id": "EVT-EXP-1", "project_id": "TEST", "type": "test_result",
            "summary": "Cache recovery succeeded after restoring the prior index pointer",
            "status": "observed", "action_taken": "Restored prior index pointer",
            "outcome": "Cache recovery succeeded", "hypotheses": ["pointer was stale"],
            "evidence": [{"kind": "test", "ref": "tests/test_cache.py"}],
        }])

    def tearDown(self):
        for key, value in self._old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.tmp.cleanup()

    @staticmethod
    def _write(path, events):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in events), encoding="utf-8")

    def _signed_owner_receipt(self, result_event_id, decision, owner_ref):
        events = [json.loads(line) for line in self.attention.read_text(encoding="utf-8").splitlines() if line.strip()]
        target = next(event for event in events if event.get("event_id") == result_event_id)
        branch = target["branch_return"]
        receipt = {
            "schema_version": "1.0", "receipt_id": "RECEIPT-OWNER-INTEGRATED",
            "receipt_type": "owner_acknowledgement", "issuer_id": "test-signer", "key_id": "test-key-1",
            "issued_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "claim": {"result_event_id": result_event_id, "child_branch_id": branch["child_branch_id"],
                      "parent_task_id": branch["parent_task_id"], "parent_checkpoint_id": branch["parent_checkpoint_id"],
                      "decision": decision, "owner_ref": owner_ref},
        }
        payload_path = self.root / "owner-payload.json"
        signature_path = self.root / "owner-signature.bin"
        payload_path.write_bytes(canonical_receipt_payload(receipt))
        subprocess.run(["openssl", "pkeyutl", "-sign", "-inkey", str(self.private_key), "-rawin",
                        "-in", str(payload_path), "-out", str(signature_path)], check=True, capture_output=True)
        receipt["signature"] = {"algorithm": "Ed25519", "value": base64.b64encode(signature_path.read_bytes()).decode("ascii")}
        return receipt

    def test_composes_restore_attention_and_experience_with_provenance(self):
        branch = process_turn(
            self.attention, turn_id="T-SIDE-1", text="Кстати, отдельный вопрос",
            active_task_id="TASK-PARENT", active_checkpoint_id="CKPT-PARENT",
            child_task_id="TASK-SIDE", child_checkpoint_id="CKPT-SIDE",
        )
        self.assertEqual(branch["status"], "BRANCH_OPENED")
        result = build_task_start_experience_map(
            self.task, self.handoff, self.events, "cache recovery index pointer",
            experience_logs=[self.experience], attention_log=self.attention,
            active_task_id="TASK-PARENT", active_checkpoint_id="CKPT-PARENT",
            current_project_id="TEST",
        )
        self.assertEqual(result["status"], "READY_FOR_REVIEW", json.dumps({"task_restore": result["task_restore"], "experience_map": result["experience_map"], "attention": result["attention"]}, ensure_ascii=False))
        self.assertEqual(result["task_restore"]["status"], "RESTORED_PACKET")
        self.assertEqual(result["attention"]["open_branch_count"], 1)
        self.assertEqual(result["attention"]["return_stack"][0]["parent"]["task_id"], "TASK-PARENT")
        self.assertEqual(result["attention"]["return_stack"][0]["child"]["task_id"], "TASK-SIDE")
        self.assertEqual(result["attention"]["alignment_with_task_state"], "BRANCH_ACTIVE_TASK_DIFFERS_FROM_TASK_STATE")
        candidate = result["experience_map"]["groups"]["current_project_scope"][0]
        self.assertEqual(candidate["event_id"], "EVT-EXP-1")
        self.assertEqual(candidate["source_record_status"], "HASH_AND_EVENT_ID_MATCH")
        self.assertEqual(candidate["experience_details"]["action_taken"], "Restored prior index pointer")
        self.assertEqual(candidate["transfer_decision"], "UNASSESSED")
        self.assertFalse(result["decision_policy"]["planning_authorized"])
        self.assertFalse(result["writes_performed"])
        self.assertFalse(result["execution_performed"])

    def test_staged_s1_s2_and_frontier_are_connected_to_task_start(self):
        self.task.write_text(
            self.task.read_text(encoding="utf-8")
            + "\n\n```experience-markers\n"
            + json.dumps({
                "problem_types": ["cache-recovery"],
                "tools": ["Python"],
                "languages": ["Python"],
                "environments": ["GitHub Actions"],
            }) + "\n```\n",
            encoding="utf-8",
        )
        self._write(self.lessons, [{
            "lesson_id": "LESSON-CACHE-1", "scope": "project", "project_id": "TEST",
            "title": "Cache recovery after stale index pointer",
            "status": "candidate",
            "trigger": "cache recovery and index pointer mismatch",
            "observed_problem": "cache recovery",
            "applicability": ["same project and matching tool context"],
            "exceptions": [],
            "prevention_rule": "verify the index pointer before retrying",
            "markers": {
                "problem_types": ["cache-recovery"], "tools": ["Python"],
                "languages": ["Python"], "environments": ["GitHub Actions"],
            },
            "evidence_refs": [{"kind": "test", "ref": "tests/test_cache.py"}],
        }])
        result = build_task_start_experience_map(
            self.task, self.handoff, self.events, "cache recovery index pointer",
            experience_logs=[self.experience], lesson_logs=[self.lessons],
            attention_log=self.attention, active_task_id="TASK-PARENT",
            active_checkpoint_id="CKPT-PARENT", current_project_id="TEST",
        )
        self.assertEqual(result["status"], "READY_FOR_REVIEW")
        stages = result["experience_map"]["lesson_search_stages"]
        self.assertEqual([stage["stage"] for stage in stages], ["S1_STRUCTURED", "S2_LEXICAL"])
        self.assertEqual(stages[0]["status"], "CANDIDATES_FOUND")
        self.assertEqual(stages[1]["status"], "CANDIDATES_FOUND")
        self.assertEqual(result["experience_map"]["current_markers_source"], "TASK_STATE_EXPLICIT_BLOCK")
        frontier = result["experience_map"]["decision_frontier"]
        lesson_direction = next(
            row for row in frontier["directions"] if row["candidate_id"] == "LESSON-CACHE-1"
        )
        self.assertEqual(lesson_direction["classification"], "HOLD")
        self.assertEqual(lesson_direction["candidate_type"], "lesson")
        self.assertFalse(frontier["grants_planning_permission"])
        self.assertFalse(result["decision_policy"]["planning_authorized"])
        self.assertFalse(result["writes_performed"])

    def test_source_mutation_after_retrieval_blocks_candidate_expansion(self):
        real_loop = task_start_module.run_minimal_agent_loop

        def mutate_after_retrieval(*args, **kwargs):
            result = real_loop(*args, **kwargs)
            self.experience.write_text(
                json.dumps({
                    "event_id": "EVT-EXP-1", "project_id": "TEST", "type": "test_result",
                    "summary": "Changed after retrieval; this must not be trusted",
                    "status": "observed",
                }) + "\n",
                encoding="utf-8",
            )
            return result

        with patch("task_start_experience_map.run_minimal_agent_loop", side_effect=mutate_after_retrieval):
            result = build_task_start_experience_map(
                self.task, self.handoff, self.events, "cache recovery index pointer",
                experience_logs=[self.experience], attention_log=self.attention,
                active_task_id="TASK-PARENT", active_checkpoint_id="CKPT-PARENT",
                current_project_id="TEST",
            )
        candidate = result["experience_map"]["groups"]["current_project_scope"][0]
        self.assertEqual(candidate["source_record_status"], "SOURCE_CHANGED_AFTER_RETRIEVAL")
        self.assertNotIn("experience_details", candidate)
        self.assertFalse(result["writes_performed"])

    def test_duplicate_event_ids_from_two_logs_hold_both_provenance_paths(self):
        self._write(self.experience2, [{
            "event_id": "EVT-EXP-1", "project_id": "TEST", "type": "test_result",
            "summary": "Cache recovery failed after a different index repair",
            "status": "observed", "action_taken": "Rebuilt index pointer",
            "outcome": "Recovery failed",
        }])
        result = build_task_start_experience_map(
            self.task, self.handoff, self.events, "cache recovery index pointer",
            experience_logs=[self.experience, self.experience2], attention_log=self.attention,
            active_task_id="TASK-PARENT", active_checkpoint_id="CKPT-PARENT",
            current_project_id="TEST",
        )
        frontier = result["experience_map"]["decision_frontier"]
        self.assertEqual(frontier["summary"]["duplicate_candidate_keys"], 1)
        self.assertEqual(
            frontier["next_discriminating_check"]["type"],
            "RESOLVE_DUPLICATE_CANDIDATE_ID",
        )
        rows = [row for row in frontier["directions"] if row["candidate_id"] == "EVT-EXP-1"]
        self.assertEqual(len(rows), 2)
        self.assertEqual({row["classification"] for row in rows}, {"HOLD"})
        self.assertEqual(
            {row["source"]["path"] for row in rows},
            {str(self.experience), str(self.experience2)},
        )
        self.assertFalse(result["decision_policy"]["planning_authorized"])

    def test_cross_project_and_global_lessons_remain_out_of_scope(self):
        self.task.write_text(
            self.task.read_text(encoding="utf-8")
            + "\n\n```experience-markers\n"
            + json.dumps({"problem_types": ["cache-recovery"], "tools": ["Python"],
                          "languages": ["Python"], "environments": ["GitHub Actions"]})
            + "\n```\n",
            encoding="utf-8",
        )
        common = {
            "status": "validated", "trigger": "cache recovery index pointer",
            "observed_problem": "cache recovery index pointer", "applicability": ["cache recovery"],
            "exceptions": [], "evidence_refs": [],
            "markers": {"problem_types": ["cache-recovery"], "tools": ["Python"],
                        "languages": ["Python"], "environments": ["GitHub Actions"]},
        }
        self._write(self.lessons, [
            {"lesson_id": "LESSON-CURRENT", "scope": "project", "project_id": "TEST",
             "title": "Cache recovery index pointer current project", **common},
            {"lesson_id": "LESSON-OTHER", "scope": "project", "project_id": "OTHER",
             "title": "Cache recovery index pointer other project", **common},
            {"lesson_id": "LESSON-GLOBAL", "scope": "global", "project_id": "global",
             "title": "Cache recovery index pointer global lesson", **common},
        ])
        result = build_task_start_experience_map(
            self.task, self.handoff, self.events, "cache recovery index pointer",
            experience_logs=[self.experience], lesson_logs=[self.lessons],
            attention_log=self.attention, active_task_id="TASK-PARENT",
            active_checkpoint_id="CKPT-PARENT", current_project_id="TEST",
        )
        frontier = result["experience_map"]["decision_frontier"]
        by_id = {row["candidate_id"]: row["classification"] for row in frontier["directions"]}
        self.assertEqual(by_id["LESSON-CURRENT"], "HOLD")
        self.assertEqual(by_id["LESSON-OTHER"], "OUT_OF_SCOPE")
        self.assertEqual(by_id["LESSON-GLOBAL"], "OUT_OF_SCOPE")
        self.assertNotIn("LESSON-OTHER", [row["candidate_id"] for row in result["experience_map"]["review_directions_by_classification"]["KEEP_FOR_RATIONALE_REVIEW"]])
        self.assertFalse(result["decision_policy"]["planning_authorized"])

    def test_conflicting_lessons_surface_conflict_through_task_start(self):
        self.task.write_text(
            self.task.read_text(encoding="utf-8")
            + "\n\n```experience-markers\n"
            + json.dumps({"problem_types": ["cache-recovery"], "tools": ["Python"]})
            + "\n```\n",
            encoding="utf-8",
        )
        common = {
            "scope": "project", "project_id": "TEST", "status": "validated",
            "trigger": "cache recovery index pointer", "observed_problem": "cache recovery",
            "applicability": ["cache recovery"], "exceptions": [],
            "markers": {"problem_types": ["cache-recovery"], "tools": ["Python"]},
            "evidence_refs": [{"kind": "test", "ref": "tests/test_cache.py"}],
        }
        self._write(self.lessons, [
            {"lesson_id": "LESSON-A", "title": "Cache recovery use prior index pointer", **common},
            {"lesson_id": "LESSON-B", "title": "Cache recovery rebuild index pointer", **common},
        ])
        judgments = [
            {"candidate_id": "LESSON-A", "candidate_type": "lesson", "criterion": "compatibility",
             "result": "CONFLICT", "judged_by": "user", "basis_ref": "tests/test_cache.py#case-a",
             "with_candidate_id": "LESSON-B"},
            {"candidate_id": "LESSON-B", "candidate_type": "lesson", "criterion": "compatibility",
             "result": "CONFLICT", "judged_by": "user", "basis_ref": "tests/test_cache.py#case-b",
             "with_candidate_id": "LESSON-A"},
        ]
        result = build_task_start_experience_map(
            self.task, self.handoff, self.events, "cache recovery index pointer",
            experience_logs=[self.experience], lesson_logs=[self.lessons], judgments=judgments,
            attention_log=self.attention, active_task_id="TASK-PARENT",
            active_checkpoint_id="CKPT-PARENT", current_project_id="TEST",
        )
        frontier = result["experience_map"]["decision_frontier"]
        self.assertEqual(frontier["summary"]["conflicts"], 2)
        self.assertEqual(frontier["next_discriminating_check"]["type"], "RECONCILE_CONFLICT")
        conflicts = [row["candidate_id"] for row in frontier["directions"] if row["classification"] == "CONFLICT"]
        self.assertEqual(set(conflicts), {"LESSON-A", "LESSON-B"})
        self.assertFalse(result["decision_policy"]["planning_authorized"])

    def test_task_start_surfaces_untrusted_prior_pass_without_skipping_check(self):
        result = build_task_start_experience_map(
            self.task, self.handoff, self.events, "cache recovery index pointer",
            experience_logs=[self.experience], attention_log=self.attention,
            active_task_id="TASK-PARENT", active_checkpoint_id="CKPT-PARENT",
            current_project_id="TEST",
        )
        policy = result["experience_map"]["check_reuse_policy"]
        self.assertEqual(policy["status"], "RUN_CHECK")
        from check_reuse_policy import record_check_result
        recorded = record_check_result(
            self.attention,
            policy["check_spec"],
            policy["source_hashes"],
            policy["candidate_fingerprints"],
            result_status="PASS",
            evidence_refs=["tests/test_task_start_experience_map.py#case"],
            summary="The requested discriminating check was run and passed",
            recorded_by="synthetic-test-run",
        )
        self.assertEqual(recorded["status"], "RECORDED")
        # Irrelevant checkpoint metadata and unrelated events should not invalidate
        # a check whose semantic context, candidate records and check spec are unchanged.
        self.handoff.write_text(
            self.handoff.read_text(encoding="utf-8") + "\nUnrelated checkpoint note changed.\n",
            encoding="utf-8",
        )
        self._write(self.events, [
            {"event_id": "EVT-CURRENT-1", "project_id": "TEST", "type": "checkpoint",
             "summary": "Current task checkpoint for cache recovery", "status": "verified"},
            {"event_id": "EVT-UNRELATED-1", "project_id": "TEST", "type": "note",
             "summary": "Unrelated formatting check completed", "status": "observed"},
        ])
        replay = build_task_start_experience_map(
            self.task, self.handoff, self.events, "cache recovery index pointer",
            experience_logs=[self.experience], attention_log=self.attention,
            active_task_id="TASK-PARENT", active_checkpoint_id="CKPT-PARENT",
            current_project_id="TEST",
        )
        reuse = replay["experience_map"]["check_reuse_policy"]
        self.assertEqual(reuse["status"], "REUSE_RECORDED_PASS_UNTRUSTED")
        self.assertEqual(reuse["action"], "REVIEW_PRIOR_RESULT")
        self.assertTrue(replay["decision_policy"]["repeat_check"])
        self.assertFalse(replay["decision_policy"]["planning_authorized"])

    def test_lesson_source_mutation_blocks_frontier_and_check_reuse(self):
        self.task.write_text(
            self.task.read_text(encoding="utf-8")
            + "\n\n```experience-markers\n"
            + json.dumps({"problem_types": ["cache-recovery"], "tools": ["Python"]})
            + "\n```\n",
            encoding="utf-8",
        )
        self._write(self.lessons, [{
            "lesson_id": "LESSON-MUTATE", "scope": "project", "project_id": "TEST",
            "title": "Cache recovery index pointer", "status": "candidate",
            "trigger": "cache recovery index pointer", "observed_problem": "cache recovery",
            "applicability": ["cache recovery"], "exceptions": [],
            "markers": {"problem_types": ["cache-recovery"], "tools": ["Python"]},
            "evidence_refs": [],
        }])
        real_loop = task_start_module.run_minimal_agent_loop

        def mutate_after_retrieval(*args, **kwargs):
            result = real_loop(*args, **kwargs)
            self.lessons.write_text(
                json.dumps({
                    "lesson_id": "LESSON-MUTATE", "scope": "project", "project_id": "TEST",
                    "title": "Changed after retrieval", "status": "candidate",
                    "trigger": "changed content",
                }) + "\n",
                encoding="utf-8",
            )
            return result

        with patch("task_start_experience_map.run_minimal_agent_loop", side_effect=mutate_after_retrieval):
            result = build_task_start_experience_map(
                self.task, self.handoff, self.events, "cache recovery index pointer",
                experience_logs=[self.experience], lesson_logs=[self.lessons],
                attention_log=self.attention, active_task_id="TASK-PARENT",
                active_checkpoint_id="CKPT-PARENT", current_project_id="TEST",
            )
        stale = [item for item in result["experience_map"]["stale_sources"]
                 if item["candidate_id"] == "LESSON-MUTATE"]
        self.assertEqual(len(stale), 1)
        self.assertEqual(stale[0]["source_record_status"], "SOURCE_CHANGED_AFTER_RETRIEVAL")
        direction = next(row for row in result["experience_map"]["decision_frontier"]["directions"]
                         if row["candidate_id"] == "LESSON-MUTATE")
        self.assertEqual(direction["classification"], "HOLD")
        self.assertEqual(direction["source_record_status"], "SOURCE_CHANGED_AFTER_RETRIEVAL")
        self.assertEqual(result["experience_map"]["check_reuse_policy"]["status"], "BLOCKED_SOURCE_NOT_CURRENT")
        self.assertEqual(result["status"], "PARTIAL_SOURCE_PROVENANCE_STALE")
        self.assertFalse(result["decision_policy"]["planning_authorized"])

    def test_untrusted_pass_does_not_suppress_check_after_child_result_ack_and_return(self):
        opened = process_turn(
            self.attention, turn_id="T-INTEGRATED-SIDE", text="Кстати, проверь отдельный вопрос",
            active_task_id="TASK-PARENT", active_checkpoint_id="CKPT-PARENT",
            child_task_id="TASK-SIDE", child_checkpoint_id="CKPT-SIDE",
        )
        self.assertEqual(opened["status"], "BRANCH_OPENED")

        published = publish_result(self.attention, {
            "child_branch_id": opened["branch_id"],
            "parent_checkpoint_id": "CKPT-PARENT",
            "parent_task_id": "TASK-PARENT",
            "result_key": "cache-recovery-check-v1",
            "result_status": "RESULT_REPORTED",
            "summary": "Cache recovery check completed in the side branch.",
            "source_refs": ["tests/test_cache_recovery.py#case-1"],
            "reported_at": "2026-10-16T12:00:00Z",
            "evidence_status": "verified",
        })
        self.assertEqual(published["status"], "RESULT_REPORTED")
        acknowledged = acknowledge_result(
            self.attention, published["event_id"], "accepted",
            "owner-confirmation://integrated-test", "2026-10-16T12:01:00Z",
            signed_receipt=self._signed_owner_receipt(
                published["event_id"], "accepted", "owner-confirmation://integrated-test"),
        )
        self.assertEqual(acknowledged["status"], "ACKNOWLEDGED")

        with self.task.open("a", encoding="utf-8") as stream:
            stream.write(
                "\n## Checkpoint update UPDATE-INTEGRATED-1\n"
                "- Parent checkpoint: `CKPT-PARENT`\n"
                f"- Supporting event: `{acknowledged['event_id']}`\n"
                "Child result reviewed; parent acceptance criteria reconciled.\n"
            )
        reconciled = build_branch_return_report(self.attention, [self.task])
        self.assertEqual(reconciled["status"], "CONSISTENT")
        self.assertEqual(reconciled["issues"], [])

        request = "cache recovery index pointer"
        before_return = build_task_start_experience_map(
            self.task, self.handoff, self.events, request,
            experience_logs=[self.events, self.experience],
            attention_log=self.attention, active_task_id="TASK-PARENT",
            active_checkpoint_id="CKPT-PARENT", current_project_id="TEST",
        )
        policy = before_return["experience_map"]["check_reuse_policy"]
        self.assertEqual(policy["status"], "RUN_CHECK")
        recorded = record_check_result(
            self.attention, policy["check_spec"], policy["source_hashes"],
            policy["candidate_fingerprints"], result_status="PASS",
            evidence_refs=["tests/test_cache_recovery.py#case-1"],
            summary="The discriminating check passed after parent reconciliation.",
            recorded_by="synthetic-integration-test",
        )
        self.assertEqual(recorded["status"], "RECORDED")

        cycle = run_cycle(
            self.task, self.handoff, self.events, self.attention, request,
            experience_logs=[self.events, self.experience],
            active_task_id="TASK-PARENT", active_checkpoint_id="CKPT-PARENT",
            current_project_id="TEST", task_state_paths=[self.task],
            return_turn_id="T-INTEGRATED-RETURN", parent_task_id="TASK-PARENT",
        )
        self.assertEqual(cycle["status"], "READY", json.dumps(cycle["parent_return"], ensure_ascii=False))
        self.assertEqual(cycle["parent_return"]["status"], "RETURNED")
        after_return = build_task_start_experience_map(
            self.task, self.handoff, self.events, request,
            experience_logs=[self.events, self.experience],
            attention_log=self.attention, active_task_id="TASK-PARENT",
            active_checkpoint_id="CKPT-PARENT", current_project_id="TEST",
        )
        reuse = after_return["experience_map"]["check_reuse_policy"]
        self.assertEqual(reuse["status"], "REUSE_RECORDED_PASS_UNTRUSTED")
        self.assertEqual(reuse["action"], "REVIEW_PRIOR_RESULT")
        self.assertTrue(after_return["decision_policy"]["repeat_check"])
        self.assertFalse(after_return["decision_policy"]["planning_authorized"])
        self.assertEqual(len([
            event for event in json.loads("[" + ",".join(
                self.attention.read_text(encoding="utf-8").splitlines()
            ) + "]") if event.get("type") == "verification_check_completed"
        ]), 1)

    def test_task_id_is_recovered_from_canonical_task_state_heading(self):
        self.assertEqual(task_start_module._infer_task_id(self.task), "TASK-PARENT")

    def test_no_attention_journal_is_reported_without_inventing_a_branch(self):
        result = build_task_start_experience_map(
            self.task, self.handoff, self.events, "cache recovery",
            experience_logs=[self.experience], attention_log=self.attention,
            active_task_id="TASK-PARENT", active_checkpoint_id="CKPT-PARENT",
            current_project_id="TEST",
        )
        self.assertEqual(result["attention"]["open_branch_count"], 0)
        self.assertEqual(result["attention"]["alignment_with_task_state"], "NO_PERSISTED_ATTENTION_STATE")
        self.assertEqual(result["experience_map"]["candidate_count"], 1)


if __name__ == "__main__":
    unittest.main()
