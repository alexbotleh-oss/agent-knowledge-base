# tests/test_real_api_integration.py
import hashlib
import json
import os
import subprocess
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
from context_extractor import extract_semantic_context
from context_trust_gate import authorize_next_step
from restore_session_packet import build_session_packet
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
        handoff = project_dir / "HANDOFF.md"
        handoff.write_text("- **Следующий шаг:** compile_core\n", encoding="utf-8")
        return event_log, task_state

    def _trust_verdict(self, task_state: Path, event_log: Path) -> dict:
        packet = build_session_packet(task_state, task_state.with_name("HANDOFF.md"), event_log)
        context = extract_semantic_context(packet)
        return authorize_next_step(context)

    def _state_content(self, ack_event_id: str) -> str:
        return (
            "# Task: build_core_lite\n"
            "- **Активная задача в текущей сессии:** восстановить состояние проекта\n"
            "- **Следующий шаг:** compile_core\n"
            f"- **Последнее событие:** {ack_event_id}\n"
            "parent_task_id: task-main-123\n"
        )

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

            state_content = self._state_content(ack_event_id)
            task_state.write_text(state_content, encoding="utf-8")
            expected_sha256 = hashlib.sha256(state_content.encode("utf-8")).hexdigest()
            proposal = {
                "update_id": "upd-001",
                "expected_sha256": expected_sha256,
                "parent_checkpoint_id": parent_checkpoint_id,
                "event_id": ack_event_id,
                "checkpoint_markdown": state_content,
            }

            verdict = self._trust_verdict(task_state, event_log)
            self.assertEqual(verdict.get("status"), "AUTHORIZED_FOR_PLANNING")
            applied = apply_checkpoint(str(task_state), str(event_log), proposal, trust_verdict=verdict)
            self.assertEqual(applied.get("status"), "APPLIED")

            repeated = apply_checkpoint(str(task_state), str(event_log), proposal, trust_verdict=verdict)
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
                str(task_state), str(event_log), conflict_proposal, trust_verdict=verdict
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

            original_content = self._state_content(ack_event_id)
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

            verdict = self._trust_verdict(task_state, event_log)
            modified_content = original_content.replace("compile_core", "build_docs")
            task_state.write_text(modified_content, encoding="utf-8")
            bytes_before_apply = task_state.read_bytes()

            stale = apply_checkpoint(str(task_state), str(event_log), proposal, trust_verdict=verdict)
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

            state_content = self._state_content(ack_event_id)
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

            verdict = self._trust_verdict(task_state, event_log)
            self.assertEqual(verdict.get("status"), "AUTHORIZED_FOR_PLANNING")
            applied = apply_checkpoint(str(task_state), str(event_log), proposal, trust_verdict=verdict)
            self.assertEqual(applied.get("status"), "APPLIED")

            report_after_reread = build_report(str(event_log), [str(task_state)])
            self.assertIsInstance(report_after_reread, dict)
            self.assertEqual(report_after_reread.get("issues"), [])


    def test_fresh_process_restores_semantics_from_persisted_files(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            event_log, task_state = self._project_files(tmp_dir)
            handoff = task_state.with_name("HANDOFF.md")
            event = {
                "event_id": "EVT-RESTART-001",
                "type": "checkpoint",
                "summary": "Persisted recovery fixture",
            }
            event_log.write_text(json.dumps(event) + "\n", encoding="utf-8")
            task_state.write_text(
                "# TASK_STATE\n"
                "- **Активная задача в текущей сессии:** проверить восстановление после рестарта\n"
                "- **Следующий шаг:** проверить новый процесс\n"
                "- **Последнее событие:** EVT-RESTART-001\n",
                encoding="utf-8",
            )
            handoff.write_text(
                "# HANDOFF\n- **Следующий шаг:** fallback шаг не должен переопределить TASK_STATE\n",
                encoding="utf-8",
            )
            script = (
                "import json, sys; "
                "from pathlib import Path; "
                "from restore_session_packet import build_session_packet; "
                "from context_extractor import extract_semantic_context; "
                "p=build_session_packet(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])); "
                "c=extract_semantic_context(p); "
                "print(json.dumps({'packet_status':p['status'],'active_goal':c['active_goal'],"
                "'next_step':c['next_step'],'event_linkage_complete':c['event_linkage_complete'],"
                "'freshness_verified':c['freshness_verified']}))"
            )
            env = os.environ.copy()
            env["PYTHONPATH"] = str(tools_dir) + os.pathsep + env.get("PYTHONPATH", "")
            completed = subprocess.run(
                [sys.executable, "-c", script, str(task_state), str(handoff), str(event_log)],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            restored = json.loads(completed.stdout)
            self.assertEqual(restored["packet_status"], "RESTORED_PACKET")
            self.assertEqual(restored["active_goal"], "проверить восстановление после рестарта")
            self.assertEqual(restored["next_step"], "проверить новый процесс")
            self.assertTrue(restored["event_linkage_complete"])
            self.assertTrue(restored["freshness_verified"])


    def test_end_to_end_cycle_is_resumable_and_restores_persisted_evidence(self):
        """Exercise publish -> acknowledgement -> guarded update -> fresh-process restore.

        Repeated calls model a restart at durable boundaries: each stage must either
        apply once or return its idempotent replay status without changing bytes.
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            event_log, task_state = self._project_files(tmp_dir)
            handoff = task_state.with_name("HANDOFF.md")
            parent_checkpoint_id = "root-cp-e2e-001"

            # Stage 1: child result is durably published; interruption before ack is safe.
            result_event_id = self._publish_result(str(event_log), parent_checkpoint_id)
            published_bytes = event_log.read_bytes()
            replay_payload = {
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
            replayed_result = publish_result(str(event_log), replay_payload)
            self.assertEqual(replayed_result["status"], "ALREADY_PUBLISHED")
            self.assertEqual(event_log.read_bytes(), published_bytes)

            # Stage 2: owner decision is a separate durable event, never an in-place edit.
            ack_event_id = self._acknowledge_result(
                str(event_log), result_event_id, "owner-e2e-001"
            )
            acknowledged_bytes = event_log.read_bytes()
            replayed_ack = acknowledge_result(
                str(event_log), result_event_id=result_event_id,
                decision="accepted", owner_ref="owner-e2e-001",
                acknowledged_at="2026-10-15T10:05:00Z",
            )
            self.assertEqual(replayed_ack["status"], "ALREADY_ACKNOWLEDGED")
            self.assertEqual(event_log.read_bytes(), acknowledged_bytes)

            # An interruption here must remain visible as an unresolved transition.
            pending_report = build_report(str(event_log), [str(task_state)])
            self.assertTrue(any(
                issue.get("kind") == "accepted_ack_without_task_checkpoint"
                for issue in pending_report.get("issues", [])
            ))

            # Stage 3: guarded update consumes the accepted ack and preserves old state.
            state_content = self._state_content(ack_event_id)
            task_state.write_text(state_content, encoding="utf-8")
            original_bytes = task_state.read_bytes()
            proposal = {
                "update_id": "upd-e2e-001",
                "expected_sha256": hashlib.sha256(original_bytes).hexdigest(),
                "parent_checkpoint_id": parent_checkpoint_id,
                "event_id": ack_event_id,
                "checkpoint_markdown": "- Resumed from accepted child result; source linkage retained.",
            }
            verdict = self._trust_verdict(task_state, event_log)
            self.assertEqual(verdict.get("status"), "AUTHORIZED_FOR_PLANNING")
            applied = apply_checkpoint(task_state, event_log, proposal, trust_verdict=verdict)
            self.assertEqual(applied.get("status"), "APPLIED")
            after_apply = task_state.read_bytes()
            self.assertIn(b"Original", after_apply)
            self.assertIn(ack_event_id.encode("utf-8"), after_apply)

            # Simulated restart/replay after the state write must not append twice.
            replayed_update = apply_checkpoint(task_state, event_log, proposal, trust_verdict=verdict)
            self.assertEqual(replayed_update.get("status"), "ALREADY_APPLIED")
            self.assertEqual(task_state.read_bytes(), after_apply)

            # Stage 4: a new interpreter reconstructs the packet only from persisted files.
            script = (
                "import json, sys; from pathlib import Path; "
                "from restore_session_packet import build_session_packet; "
                "p=build_session_packet(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])); "
                "print(json.dumps({'status':p['status'], 'linked_ids':[e['event_id'] for e in p['linked_events']], "
                "'missing':p['missing_event_refs'], 'hashes':p['source_hashes'], 'writes':p['writes_performed']}))"
            )
            env = os.environ.copy()
            env["PYTHONPATH"] = str(tools_dir) + os.pathsep + env.get("PYTHONPATH", "")
            completed = subprocess.run(
                [sys.executable, "-c", script, str(task_state), str(handoff), str(event_log)],
                check=True, capture_output=True, text=True, env=env,
            )
            restored = json.loads(completed.stdout)
            self.assertEqual(restored["status"], "RESTORED_PACKET")
            self.assertEqual(restored["missing"], [])
            self.assertIn(ack_event_id, restored["linked_ids"])
            self.assertFalse(restored["writes"])
            self.assertEqual(
                restored["hashes"]["task_state_sha256"],
                hashlib.sha256(after_apply).hexdigest(),
            )
            rows = [json.loads(line) for line in event_log.read_text(encoding="utf-8").splitlines()]
            self.assertIn(result_event_id, {row["event_id"] for row in rows})
            ack_row = next(row for row in rows if row["event_id"] == ack_event_id)
            self.assertIn(result_event_id, ack_row["related_event_ids"])

            final_report = build_report(str(event_log), [str(task_state)])
            self.assertEqual(final_report.get("issues"), [])
