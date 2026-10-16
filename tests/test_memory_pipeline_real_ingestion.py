import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
TOOLS=ROOT/"tools"
sys.path.insert(0,str(TOOLS))
from archive_registry_staging import build as build_staging
from source_ingestion_runner import run_ingestion, _load_events


class RealSourceIngestionIntegrationTests(unittest.TestCase):
    def test_coordinator_uses_real_runner_and_registers_synthetic_archive(self):
        import memory_pipeline_coordinator as pipeline
        from unittest import mock
        import hashlib

        def canon(x):
            return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()

        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            archive=root/"conversations.json"
            archive.write_text(json.dumps([{
                "id":"CONV-REAL-1",
                "mapping":{"NODE-REAL-1":{"parent":None,"children":[],"message":{
                    "id":"MSG-REAL-1","create_time":1790000000,"author":{"role":"user"},
                    "content":{"content_type":"text","parts":["synthetic pipeline source text"]},"metadata":{}}}}
            }]),encoding="utf-8")
            staging=root/"staging"
            build_staging(archive,staging,"ARCH-REAL-INGEST-1")
            snapshot=staging/"archive_snapshot.json"
            source_registry=root/"registry"/"source_records.jsonl"
            source_registry.parent.mkdir()
            dry=run_ingestion(snapshot,root/"preflight-runs",intake_root=root/"preflight-intake",
                              registry_path=root/"preflight-registry"/"source_records.jsonl",apply=False)
            self.assertEqual(dry["status"],"READY_FOR_SOURCE_REGISTRATION",dry)
            source_batch=Path(dry["run_dir"]).parent.parent/"preflight-intake"
            # The adapter's batch is deterministically named; read the generated intake manifest.
            manifest_path=Path(dry["run_dir"]).parent.parent/"preflight-intake"/Path(dry["run_dir"]).name/"manifest.json"
            if not manifest_path.is_file():
                candidates=list((root/"preflight-intake").glob("*/manifest.json"))
                self.assertEqual(len(candidates),1,candidates)
                manifest_path=candidates[0]
            intake=json.loads(manifest_path.read_text(encoding="utf-8"))
            artifact=intake["artifacts"][0]
            staged_rows=(manifest_path.parent/artifact["path"]).read_text(encoding="utf-8").splitlines()
            source=json.loads(staged_rows[0])
            record={"memory_id":"MEM-REAL-INGEST-1","record_type":"lesson","title":"Synthetic integration",
                "summary":"Record tied to the real source-ingestion runner","evidence_status":"observed",
                "lifecycle_status":"candidate","project_ids":["AGENT_MEMORY_SYSTEM"],"task_ids":["TASK-REAL"],
                "context_ids":["CTX-REAL"],"tags":["pipeline"],"relations":[],
                "provenance":[{"source_record_id":source["source_record_id"],"source_locator":source["source_locator"],
                    "archive_id":source["archive_id"],"conversation_id":source["conversation_id"],
                    "content_hash":source["text_sha256"]}],
                "revision":{"revision_id":"REV-REAL-1","revision_of":None,"reason":"synthetic real-runner integration"}}
            batch=root/"semantic-batch"; batch.mkdir()
            record_bytes=canon(record)+b"\n"; (batch/"records.jsonl").write_bytes(record_bytes)
            manifest_data={"schema_version":"1.0","command":"IMPORT_READY","batch_id":"BATCH-REAL-MEM-1",
                "created_at":"2026-10-16T00:00:00Z","payload_classification":"sanitized",
                "source":{"source_type":"structured_export","source_id":"ARCH-REAL-INGEST-1","project_id":"AGENT_MEMORY_SYSTEM",
                    "conversation_ids":[source["conversation_id"]],"source_locator":source["source_locator"],
                    "captured_at":"unknown","scope_status":"PARTIAL","parser_version":"synthetic"},
                "artifacts":[{"artifact_id":"ART-REAL-1","kind":"memory_records","path":"records.jsonl",
                    "sha256":hashlib.sha256(record_bytes).hexdigest(),"record_count":1,"lifecycle_status":"accepted",
                    "evidence_status":"observed","approval_status":"user_approved","approval_evidence":"DEC-REAL-1"}]}
            manifest_bytes=canon(manifest_data); manifest=batch/"manifest.json"; manifest.write_bytes(manifest_bytes)
            receipt=batch/"approval.json"; receipt.write_bytes(canon({"schema_version":"semantic-memory-approval-v1",
                "decision_id":"DEC-REAL-1","decision":"approve","actor_type":"user","actor_ref":"synthetic-test",
                "decided_at":"2026-10-16T00:01:00Z","batch_id":manifest_data["batch_id"],"artifact_id":"ART-REAL-1",
                "manifest_sha256":hashlib.sha256(manifest_bytes).hexdigest(),
                "artifact_sha256":hashlib.sha256(record_bytes).hexdigest(),"decision_source_ref":"fixture:approval",
                "rationale":"Synthetic integration test only"}))
            project=root/"project"; project.mkdir()
            task=project/"TASK_STATE.md"; task.write_text("test",encoding="utf-8")
            handoff=project/"HANDOFF.md"; handoff.write_text("test",encoding="utf-8")
            events=project/"events.jsonl"; events.write_text("",encoding="utf-8")
            code_sha="a"*40
            (project/"CONTINUITY_CHECKPOINT.json").write_bytes(canon({"branch":"integration/memory-core-clean-20261015",
                "repository_state":{"last_verified_code_head":code_sha,"exact_head_ci_run_id":7,"exact_head_ci_conclusion":"success"}}))
            def fake_fetch(url):
                if "/branches/" in url:return {"commit":{"sha":code_sha}}
                if "/actions/runs/7" in url:return {"head_sha":code_sha,"status":"completed","conclusion":"success"}
                if "/compare/" in url:return {"status":"identical","merge_base_commit":{"sha":code_sha},"files":[]}
                raise AssertionError(url)
            memory_registry=root/"registry"/"memory_records.jsonl"; index_root=root/"registry"/"index"
            result=pipeline.run_memory_pipeline(snapshot,root/"pipeline-runs",manifest,receipt,repository="owner/repo",
                task_state=task,handoff=handoff,event_log=events,source_registry_path=source_registry,
                memory_registry_path=memory_registry,index_root=index_root,apply=True,fetch_json=fake_fetch)
            self.assertEqual(result["status"],"PIPELINE_COMPLETE_WITH_PARTIAL_MEMORY",result)
            self.assertEqual(result["stages"]["source_ingestion"],"SOURCE_REGISTERED_DOWNSTREAM_PENDING")
            self.assertEqual(result["stages"]["provenance_validation"],"RESOLVED")
            self.assertEqual(result["stages"]["semantic_promotion"],"PROMOTED")
            self.assertEqual(result["stages"]["canonical_index"],"BUILT_PARTIAL")
            self.assertEqual(result["stages"]["session_restore"],"RESTORED_PACKET_WITH_PARTIAL_MEMORY_NO_MATCH")
            self.assertEqual(result["restore"]["semantic_memory_status"],"PARTIAL_NO_MATCH")
            self.assertEqual(result["restore"]["repository_revision_evidence"]["status"],"REMOTE_VERIFIED_EXACT_CODE_HEAD")
            self.assertEqual(result["restore"]["returned_count"],0)
            rows=source_registry.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(rows),1)
            self.assertEqual(json.loads(rows[0])["source_record_id"],source["source_record_id"])
            self.assertEqual(len(memory_registry.read_text(encoding="utf-8").splitlines()),1)
            ingestion_events=list((root/"pipeline-runs"/"source_ingestion").glob("*/run_events.jsonl"))
            self.assertEqual(len(ingestion_events),1)
            self.assertEqual(_load_events(ingestion_events[0])[-1]["status"],"SOURCE_REGISTERED_DOWNSTREAM_PENDING")


if __name__=="__main__":unittest.main()
