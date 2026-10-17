"""Synthetic acceptance path: resumable raw import through approved memory restore."""
import hashlib
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

from resumable_chat_import import import_export
from archive_registry_staging import build as build_staging
from adapt_archive_staging_to_intake import adapt_archive_staging_to_intake
from memory_aware_session_restore import retrieve_approved_memory


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


class ResumableImportToMemoryPipelineTests(unittest.TestCase):
    def test_import_snapshot_provenance_approval_index_and_restore(self):
        import memory_pipeline_coordinator as pipeline

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "export.zip"
            conversations = [{
                "id": "CONV-E2E-001",
                "title": "Synthetic E2E fixture",
                "mapping": {
                    "NODE-E2E-USER": {
                        "parent": None, "children": ["NODE-E2E-ASSISTANT"],
                        "message": {
                            "id": "MSG-E2E-USER", "create_time": 1790000000,
                            "author": {"role": "user"},
                            "content": {"content_type": "text", "parts": ["synthetic source fact"]},
                            "metadata": {"attachments": [{
                                "id": "ATTACHMENT-E2E-001",
                                "name": "synthetic-attachment.pdf",
                            }]},
                        },
                    },
                    "NODE-E2E-ASSISTANT": {
                        "parent": "NODE-E2E-USER", "children": ["NODE-E2E-A-FOLLOWUP"],
                        "message": {
                            "id": "MSG-E2E-ASSISTANT", "create_time": 1790000001,
                            "author": {"role": "assistant"},
                            "content": {"content_type": "text", "parts": ["synthetic response"]},
                            "metadata": {},
                        },
                    },
                    # This node sorts lexically before NODE-E2E-ASSISTANT but
                    # appears after it in the export and has the same timestamp.
                    "NODE-E2E-A-FOLLOWUP": {
                        "parent": "NODE-E2E-ASSISTANT", "children": [],
                        "message": {
                            "id": "MSG-E2E-FOLLOWUP", "create_time": 1790000001,
                            "author": {"role": "assistant"},
                            "content": {"content_type": "text", "parts": ["synthetic followup"]},
                            "metadata": {},
                        },
                    },
                },
            }]
            with zipfile.ZipFile(source, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("conversations.json", json.dumps(conversations, ensure_ascii=False))
                archive.writestr("files/synthetic-attachment.pdf", b"%PDF-1.4\nsynthetic test payload\n%%EOF")
            source_bytes = source.read_bytes()
            import_root = root / "resumable-import"

            # Exercise an actual checkpoint/resume, not only a clean first pass.
            paused = import_export(source, import_root, "ARCHIVE-E2E-001", batch_size=1, stop_after_batches=1)
            self.assertEqual(paused["status"], "PAUSED")
            self.assertEqual(paused["committed_conversations"], 1)
            imported = import_export(source, import_root, "ARCHIVE-E2E-001", batch_size=1)
            self.assertEqual(imported["status"], "RAW_COMPLETE")
            self.assertEqual(imported["committed_conversations"], 1)
            self.assertEqual(imported["source_sha256"], hashlib.sha256(source_bytes).hexdigest())

            snapshot_file = Path(imported["snapshot_path"])
            self.assertEqual(snapshot_file.read_bytes(), source_bytes)
            db = __import__("sqlite3").connect(imported["database_path"])
            try:
                rows = db.execute(
                    "SELECT source_ordinal,payload_json,payload_sha256 FROM raw_conversations "
                    "WHERE archive_id=? AND source_sha256=? ORDER BY source_ordinal",
                    ("ARCHIVE-E2E-001", imported["source_sha256"]),
                ).fetchall()
                self.assertEqual([r[0] for r in rows], [0])
                self.assertEqual([hashlib.sha256(r[1].encode("utf-8")).hexdigest() for r in rows], [r[2] for r in rows])
                self.assertEqual(json.loads(rows[0][1]), conversations[0])
            finally:
                db.close()

            staging_root = root / "staging"
            staged = build_staging(snapshot_file, staging_root, "ARCHIVE-E2E-001")
            self.assertEqual(staged["raw_sha256"], imported["source_sha256"])
            self.assertEqual(staged["coverage"]["status"], "partial")
            self.assertEqual(staged["coverage"]["records_with_attachment_markers"], 1)
            snapshot_manifest = staging_root / "archive_snapshot.json"
            source_registry = root / "registry" / "source_records.jsonl"
            memory_registry = root / "registry" / "memory_records.jsonl"
            index_root = root / "registry" / "index"

            # Bind the semantic candidate to a staged source row; no source text is
            # copied into the canonical source registry.
            adapted = adapt_archive_staging_to_intake(snapshot_manifest, root / "intake")
            intake_manifest = json.loads(Path(adapted["manifest_path"]).read_text(encoding="utf-8"))
            intake_artifact = intake_manifest["artifacts"][0]
            intake_rows_path = Path(adapted["manifest_path"]).parent / intake_artifact["path"]
            intake_rows = [
                json.loads(line)
                for line in intake_rows_path.read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual(len(intake_rows), 3)
            self.assertEqual(
                [row["source_node_id"] for row in intake_rows],
                ["NODE-E2E-USER", "NODE-E2E-ASSISTANT", "NODE-E2E-A-FOLLOWUP"],
            )
            self.assertEqual(
                [row["source_time_unix"] for row in intake_rows],
                [1790000000, 1790000001, 1790000001],
            )
            self.assertIsNone(intake_rows[0]["parent_node_id"])
            self.assertEqual(intake_rows[0]["child_node_ids"], ["NODE-E2E-ASSISTANT"])
            self.assertTrue(intake_rows[0]["has_attachments"])
            self.assertFalse(intake_rows[0]["attachment_payloads_inspected"])
            self.assertEqual(intake_rows[1]["parent_node_id"], "NODE-E2E-USER")
            self.assertEqual(intake_rows[1]["child_node_ids"], ["NODE-E2E-A-FOLLOWUP"])
            self.assertEqual(intake_rows[2]["parent_node_id"], "NODE-E2E-ASSISTANT")
            self.assertEqual(intake_rows[2]["child_node_ids"], [])
            source_row = intake_rows[0]
            memory_record = {
                "memory_id": "MEM-E2E-001", "record_type": "lesson",
                "title": "Synthetic E2E memory",
                "summary": "Synthetic candidate linked to the imported source",
                "evidence_status": "observed", "lifecycle_status": "candidate",
                "project_ids": ["AGENT_MEMORY_SYSTEM"], "task_ids": ["TASK-E2E"],
                "context_ids": ["CTX-E2E"], "tags": ["e2e"], "relations": [],
                "provenance": [{
                    "source_record_id": source_row["source_record_id"],
                    "source_locator": source_row["source_locator"],
                    "archive_id": source_row["archive_id"],
                    "conversation_id": source_row["conversation_id"],
                    "content_hash": source_row["text_sha256"],
                }],
                "revision": {
                    "revision_id": "REV-E2E-001", "revision_of": None,
                    "reason": "synthetic end-to-end acceptance test",
                },
            }
            batch = root / "semantic-batch"
            batch.mkdir()
            record_bytes = canonical(memory_record) + b"\n"
            (batch / "records.jsonl").write_bytes(record_bytes)
            manifest_data = {
                "schema_version": "1.0", "command": "IMPORT_READY",
                "batch_id": "BATCH-E2E-001", "created_at": "2026-10-17T00:00:00Z",
                "payload_classification": "sanitized",
                "source": {
                    "source_type": "structured_export", "source_id": "ARCHIVE-E2E-001",
                    "project_id": "AGENT_MEMORY_SYSTEM",
                    "conversation_ids": [source_row["conversation_id"]],
                    "source_locator": source_row["source_locator"],
                    "captured_at": "unknown", "scope_status": "PARTIAL",
                    "parser_version": "synthetic-e2e",
                },
                "artifacts": [{
                    "artifact_id": "ART-E2E-001", "kind": "memory_records",
                    "path": "records.jsonl", "sha256": hashlib.sha256(record_bytes).hexdigest(),
                    "record_count": 1, "lifecycle_status": "accepted",
                    "evidence_status": "observed", "approval_status": "user_approved",
                    "approval_evidence": "DEC-E2E-001",
                }],
            }
            manifest_bytes = canonical(manifest_data)
            manifest_path = batch / "manifest.json"
            manifest_path.write_bytes(manifest_bytes)
            approval = batch / "approval.json"
            approval.write_bytes(canonical({
                "schema_version": "semantic-memory-approval-v1",
                "decision_id": "DEC-E2E-001", "decision": "approve",
                "actor_type": "user", "actor_ref": "synthetic-test",
                "decided_at": "2026-10-17T00:01:00Z",
                "batch_id": manifest_data["batch_id"], "artifact_id": "ART-E2E-001",
                "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
                "artifact_sha256": hashlib.sha256(record_bytes).hexdigest(),
                "decision_source_ref": "fixture:synthetic-approval",
                "rationale": "Synthetic acceptance fixture only",
            }))

            project = root / "AGENT_MEMORY_SYSTEM"
            project.mkdir()
            task_state = project / "TASK_STATE.md"
            task_state.write_text("synthetic test state", encoding="utf-8")
            handoff = project / "HANDOFF.md"
            handoff.write_text("synthetic test handoff", encoding="utf-8")
            event_log = project / "events.jsonl"
            event_log.write_text("", encoding="utf-8")
            code_sha = "a" * 40
            (project / "CONTINUITY_CHECKPOINT.json").write_bytes(canonical({
                "branch": "integration/memory-core-clean-20261015",
                "repository_state": {
                    "last_verified_code_head": code_sha,
                    "exact_head_ci_run_id": 7,
                    "exact_head_ci_conclusion": "success",
                },
            }))

            def fake_fetch(url):
                if "/branches/" in url:
                    return {"commit": {"sha": code_sha}}
                if "/actions/runs/7" in url:
                    return {"head_sha": code_sha, "status": "completed", "conclusion": "success"}
                if "/compare/" in url:
                    return {"status": "identical", "merge_base_commit": {"sha": code_sha}, "files": []}
                raise AssertionError(url)

            result = pipeline.run_memory_pipeline(
                snapshot_manifest, root / "pipeline-runs", manifest_path, approval,
                repository="owner/repo", task_state=task_state, handoff=handoff,
                event_log=event_log, source_registry_path=source_registry,
                memory_registry_path=memory_registry, index_root=index_root,
                apply=True, fetch_json=fake_fetch,
            )
            self.assertEqual(result["stages"]["source_ingestion"], "SOURCE_REGISTERED_DOWNSTREAM_PENDING", result)
            self.assertEqual(result["stages"]["provenance_validation"], "RESOLVED", result)
            self.assertEqual(result["stages"]["semantic_promotion"], "PROMOTED", result)
            self.assertEqual(result["stages"]["canonical_index"], "BUILT_PARTIAL", result)
            self.assertEqual(result["stages"]["session_restore"], "RESTORED_PACKET_WITH_PARTIAL_MEMORY", result)
            self.assertEqual(result["restore"]["task_restore_status"], "RESTORED_PACKET")

            restored = retrieve_approved_memory(
                "AGENT_MEMORY_SYSTEM", task_id="TASK-E2E", context_id="CTX-E2E",
                query="Synthetic candidate linked to the imported source",
                registry_path=memory_registry, index_root=index_root,
            )
            self.assertEqual(restored["returned_count"], 1, restored)
            self.assertEqual(restored["records"][0]["memory_id"], "MEM-E2E-001")
            self.assertEqual(restored["records"][0]["revision_id"], "REV-E2E-001")
            self.assertTrue(restored["records"][0]["provenance"])
            source_rows = [json.loads(line) for line in source_registry.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(source_rows), 3)  # three message nodes
            self.assertEqual(
                [row["source_node_id"] for row in source_rows],
                ["NODE-E2E-USER", "NODE-E2E-ASSISTANT", "NODE-E2E-A-FOLLOWUP"],
            )
            self.assertEqual(
                [row["source_time_unix"] for row in source_rows],
                [1790000000, 1790000001, 1790000001],
            )
            self.assertIsNone(source_rows[0]["parent_node_id"])
            self.assertEqual(source_rows[0]["child_node_ids"], ["NODE-E2E-ASSISTANT"])
            self.assertTrue(source_rows[0]["has_attachments"])
            self.assertFalse(source_rows[0]["attachment_payloads_inspected"])
            self.assertEqual(source_rows[1]["parent_node_id"], "NODE-E2E-USER")
            self.assertEqual(source_rows[1]["child_node_ids"], ["NODE-E2E-A-FOLLOWUP"])
            self.assertEqual(source_rows[2]["parent_node_id"], "NODE-E2E-ASSISTANT")
            self.assertEqual(source_rows[2]["child_node_ids"], [])
            for source_row in source_rows:
                self.assertNotIn("text", source_row)
                self.assertEqual(source_row["source_snapshot_sha256"], imported["source_sha256"])


if __name__ == "__main__":
    unittest.main()
