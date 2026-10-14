# tests/test_real_api_integration.py
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

test_dir = Path(__file__).resolve().parent
tools_dir = test_dir.parent / "tools"
if str(tools_dir) not in sys.path:
    sys.path.insert(0, str(tools_dir))

from branch_result_registry import publish_result, acknowledge_result
from guarded_task_state_update import apply_checkpoint
from reconcile_branch_returns import build_report


class TestRealApiIntegration(unittest.TestCase):
    """Integration contracts for the real result, acknowledgement, and checkpoint APIs."""

    def _publish_result(self, event_log_path: str, parent_checkpoint_id: str) -> str:
        payload = {
            "child_branch_id": "branch-side-001",
            "parent_task_id": "task-main-123",
            "parent_checkpoint_id": parent_checkpoint_id,
            "result_status": "RESULT_REPORTED",
            "evidence_status": "verified",
            "summary": "Archive reconciled",
            "source_refs": ["commit-abc123"],
            "reported_at": "2026-10-15T10:00:00Z",
            "result_key": "key-side-001",
        }
        result = publish_result(event_log_path, payload)
        self.assertIsNotNone(result)
        self.assertEqual(result.get("status"), "RESULT_REPORTED")
        return result["event_id"]

    def _acknowledge_result(
        self, event_log_path: str, result_event_id: str, owner_ref: str
    ) -> str:
        acknowledgement = acknowledge_result(
            event_log_path,
            result_event_id=result_event_id,
            decision="accepted",
            owner_ref=owner_ref,
            acknowledged_at="2026-10-15T10:05:00Z",
        )
        self.assertIsNotNone(acknowledgement)
        self.assertEqual(acknowledgement.get("status"), "ACKNOWLEDGED")
        return acknowledgement["event_id"]

    def _project_files(self, tmp_dir: str):
        project_dir = Path(tmp_dir) / "projects" / "project-test-001"
        project_dir.mkdir(parents=True, exist_ok=True)
        event_log = project_dir / "events.jsonl"
        event_log.write_text("", encoding="utf-8")
        task_state = project_dir / "TASK_STATE.md"
        task_state.write_text("", encoding="utf-8")
        return event_log, task_state

    def test_publish_and_idempotency(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            event_log, _ = self._project_files(tmp_dir)
            parent_checkpoint_id = "root-cp-000"

            self._publish_result(str(event_log), parent_checkpoint_id)

            payload = {
                "child_branch_id": "branch-side-001",
                "parent_task_id": "task-main-123",
                "parent_checkpoint_id": parent_checkpoint_id,
                "result_status": "RESULT_REPORTED",
                "evidence_status": "verified",
                "summary": "Archive reconciled",
                "source_refs": ["commit-abc123"],
                "reported_at": "2026-10-15T10:00:00Z",
                "result_key": "key-side-001",
            }
            repeated = publish_result(str(event_log), payload)
            self.assertEqual(repeated.get("status"), "ALREADY_PUBLISHED")

    def test_acknowledge_and_idempotency(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            event_log, _ = self._project_files(tmp_dir)
            pub_event_id = self._publish_result(str(event_log), "root-cp-000")
            owner_ref = "owner-abc"

            self._acknowledge_result(str(event_log), pub_event_id, owner_ref)

            repeated = acknowledge_result(
                str(event_log),
                result_event_id=pub_event_id,
                decision="accepted",
                owner_ref=owner_ref,
                acknowledged_at="2026-10-15T10:05:00Z",
            )
            self.assertEqual(repeated.get("status"), "ALREADY_ACKNOWLEDGED")

    def test_apply_checkpoint_success_and_conflict_by_update_id(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            event_log, task_state = self._project_files(tmp_dir)
            parent_checkpoint_id = "root-cp-000"
            pub_event_id = self._publish_result(str(event_log), parent_checkpoint_id)
            ack_event_id = self._acknowledge_result(
                str(event_log), pub_event_id, "owner-abc"
            )

            state_content = (
                "# Task: build_core_lite\n"
                "parent_task_id: task-main-123\n"
                "next_step: compile_core\n"
            )
            task_state.write_text(state_content, encoding="utf-8")
            expected_sha256 = hashlib.sha256(state_content.encode("utf-8")).hexdigest()
            proposal = {
                "update_id": "upd-001",
                "expected_sha256": expected_sha256,
                "parent_checkpoint_id": parent_checkpoint_id,
                "event_id": ack_event_id,
                "checkpoint_markdown": state_content,
            }

            applied = apply_checkpoint(str(task_state), str(event_log), proposal)
            self.assertEqual(applied.get("status"), "APPLIED")

            repeated = apply_checkpoint(str(task_state), str(event_log), proposal)
            self.assertEqual(repeated.get("status"), "ALREADY_APPLIED")

            diff_content = state_content.replace("compile_core", "build_docs")
            conflict_proposal = {
                "update_id": "upd-001",
                "expected_sha256": hashlib.sha256(
                    diff_content.encode("utf-8")
                ).hexdigest(),
                "parent_checkpoint_id": parent_checkpoint_id,
                "event_id": ack_event_id,
                "checkpoint_markdown": diff_content,
            }
            conflict = apply_checkpoint(
                str(task_state), str(event_log), conflict_proposal
            )
            self.assertEqual(conflict.get("status"), "CONFLICT")

    def test_stale_revision_when_file_changed_before_apply(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            event_log, task_state = self._project_files(tmp_dir)
            parent_checkpoint_id = "root-cp-000"
            pub_event_id = self._publish_result(str(event_log), parent_checkpoint_id)
            ack_event_id = self._acknowledge_result(
                str(event_log), pub_event_id, "owner-abc"
            )

            original_content = (
                "# Task: build_core_lite\n"
                "parent_task_id: task-main-123\n"
                "next_step: compile_core\n"
            )
            task_state.write_text(original_content, encoding="utf-8")
            expected_sha256 = hashlib.sha256(
                original_content.encode("utf-8")
            ).hexdigest()
            proposal = {
                "update_id": "upd-stale-001",
                "expected_sha256": expected_sha256,
                "parent_checkpoint_id": parent_checkpoint_id,
                "event_id": ack_event_id,
                "checkpoint_markdown": original_content,
            }

            modified_content = original_content.replace("compile_core", "build_docs")
            task_state.write_text(modified_content, encoding="utf-8")
            bytes_before_apply = task_state.read_bytes()

            stale = apply_checkpoint(str(task_state), str(event_log), proposal)
            self.assertEqual(stale.get("status"), "STALE_REVISION")
            self.assertEqual(task_state.read_bytes(), bytes_before_apply)

    def test_detect_specific_unresolved_transition(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            event_log, task_state = self._project_files(tmp_dir)
            pub_event_id = self._publish_result(str(event_log), "root-cp-000")
            self._acknowledge_result(str(event_log), pub_event_id, "owner-abc")

            report = build_report(str(event_log), [str(task_state)])
            self.assertIsInstance(report, dict)
            self.assertTrue(
                any(
                    issue.get("kind") == "accepted_ack_without_task_checkpoint"
                    for issue in report.get("issues", [])
                ),
                "Expected accepted_ack_without_task_checkpoint for an accepted "
                "result without a task checkpoint.",
            )

    def test_persisted_state_can_be_read_again(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            event_log, task_state = self._project_files(tmp_dir)
            parent_checkpoint_id = "root-cp-000"
            pub_event_id = self._publish_result(str(event_log), parent_checkpoint_id)
            ack_event_id = self._acknowledge_result(
                str(event_log), pub_event_id, "owner-abc"
            )

            state_content = (
                "# Task: build_core_lite\n"
                "parent_task_id: task-main-123\n"
                "next_step: compile_core\n"
            )
            task_state.write_text(state_content, encoding="utf-8")
            proposal = {
                "update_id": "upd-persisted-001",
                "expected_sha256": hashlib.sha256(
                    state_content.encode("utf-8")
                ).hexdigest(),
                "parent_checkpoint_id": parent_checkpoint_id,
                "event_id": ack_event_id,
                "checkpoint_markdown": state_content,
            }

            applied = apply_checkpoint(str(task_state), str(event_log), proposal)
            self.assertEqual(applied.get("status"), "APPLIED")

            report_after_reread = build_report(str(event_log), [str(task_state)])
            self.assertIsInstance(report_after_reread, dict)
            self.assertEqual(report_after_reread.get("issues"), [])
