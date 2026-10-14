import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from branch_result_registry import publish_result


def sample_result(**overrides):
    value = {
        "child_branch_id": "CHAT-BRANCH-42",
        "parent_checkpoint_id": "CKPT-AGMS-20261014-001",
        "parent_task_id": "TASK-AGENT-MEMORY",
        "result_key": "intake-audit-v1",
        "result_status": "RESULT_REPORTED",
        "summary": "A scoped intake result was produced.",
        "source_refs": ["https://github.com/example/repo/commit/abc123"],
        "reported_at": "2026-10-14T10:00:00Z",
        "evidence_status": "verified",
        "facts": ["Test fixture only."],
        "next_action": "Parent owner reviews before resolving the question.",
    }
    value.update(overrides)
    return value


class BranchResultRegistryTests(unittest.TestCase):
    def test_first_publication_appends_linked_event_without_acknowledging_owner(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            path.write_text('{"event_id":"EXISTING-1","summary":"keep"}\n', encoding="utf-8")
            response = publish_result(path, sample_result())
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(response["status"], "RESULT_REPORTED")
            self.assertTrue(response["writes_performed"])
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["event_id"], "EXISTING-1")
            self.assertEqual(rows[1]["type"], "cross_branch_result")
            self.assertEqual(rows[1]["relations"][0]["checkpoint_id"], "CKPT-AGMS-20261014-001")
            self.assertEqual(rows[1]["branch_return"]["owner_acknowledgement"], "PENDING")

    def test_exact_replay_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            first = publish_result(path, sample_result())
            before = path.read_bytes()
            second = publish_result(path, sample_result())
            self.assertEqual(second["status"], "ALREADY_PUBLISHED")
            self.assertFalse(second["writes_performed"])
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(first["event_id"], second["event_id"])

    def test_same_identity_with_changed_content_is_conflict_not_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            publish_result(path, sample_result())
            before = path.read_bytes()
            response = publish_result(path, sample_result(summary="Changed claim without a new revision key."))
            self.assertEqual(response["status"], "CONFLICT")
            self.assertEqual(path.read_bytes(), before)

    def test_missing_provenance_is_rejected_without_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            response = publish_result(path, sample_result(source_refs=[]))
            self.assertEqual(response["status"], "REJECTED")
            self.assertFalse(path.exists())

    def test_reported_result_cannot_claim_unknown_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            response = publish_result(path, sample_result(evidence_status="unknown"))
            self.assertEqual(response["status"], "REJECTED")
            self.assertTrue(any("requires_non_unknown" in e for e in response["errors"]))
            self.assertFalse(path.exists())

    def test_corrupt_existing_log_is_preserved_and_no_result_is_appended(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            path.write_text('{"event_id":"broken"', encoding="utf-8")
            before = path.read_bytes()
            with self.assertRaises(ValueError):
                publish_result(path, sample_result())
            self.assertEqual(path.read_bytes(), before)

    def test_different_revision_key_can_append_correction_without_erasing_old_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            first = publish_result(path, sample_result())
            second = publish_result(path, sample_result(
                result_key="intake-audit-v2",
                summary="A corrected follow-up result was produced.",
                related_event_ids=[first["event_id"]],
            ))
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(second["status"], "RESULT_REPORTED")
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[1]["related_event_ids"], [first["event_id"]])


    def test_owner_acknowledgement_is_appended_without_editing_child_result_or_task(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            published = publish_result(path, sample_result())
            before = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            from branch_result_registry import acknowledge_result
            ack = acknowledge_result(
                path, published["event_id"], "accepted",
                "user-confirmation:accepted-child-result",
                "2026-10-14T11:00:00Z",
                "Acceptance criteria for this sub-question were reviewed.",
            )
            after = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(ack["status"], "ACKNOWLEDGED")
            self.assertFalse(ack["parent_task_updated"])
            self.assertEqual(len(after), 2)
            self.assertEqual(after[0], before[0])
            self.assertEqual(after[1]["type"], "cross_branch_result_acknowledged")
            self.assertEqual(after[1]["related_event_ids"], [published["event_id"]])
            self.assertEqual(after[1]["outcome"], "accepted")

    def test_acknowledgement_replay_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            published = publish_result(path, sample_result())
            from branch_result_registry import acknowledge_result
            args = (path, published["event_id"], "needs_review", "owner-ref-1", "2026-10-14T11:00:00Z")
            first = acknowledge_result(*args)
            before = path.read_bytes()
            second = acknowledge_result(*args)
            self.assertEqual(first["status"], "ACKNOWLEDGED")
            self.assertEqual(second["status"], "ALREADY_ACKNOWLEDGED")
            self.assertEqual(path.read_bytes(), before)

    def test_acknowledgement_requires_existing_child_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            path.write_text('{"event_id":"OTHER","type":"observation"}\\n', encoding="utf-8")
            from branch_result_registry import acknowledge_result
            response = acknowledge_result(path, "OTHER", "accepted", "owner-ref", "2026-10-14T11:00:00Z")
            self.assertEqual(response["status"], "REJECTED")
            self.assertEqual(path.read_text(encoding="utf-8"), '{"event_id":"OTHER","type":"observation"}\\n')

    def test_acknowledgement_does_not_allow_silent_decision_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            published = publish_result(path, sample_result())
            from branch_result_registry import acknowledge_result
            first = acknowledge_result(path, published["event_id"], "accepted", "owner-ref", "2026-10-14T11:00:00Z")
            before = path.read_bytes()
            second = acknowledge_result(path, published["event_id"], "rejected", "owner-ref", "2026-10-14T11:00:00Z")
            self.assertEqual(first["status"], "ACKNOWLEDGED")
            self.assertEqual(second["status"], "CONFLICT")
            self.assertEqual(path.read_bytes(), before)



if __name__ == "__main__":
    unittest.main()
