import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
import memory_pipeline_coordinator as pipeline


def canon(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def valid_source_record():
    archive,conversation,node="ARCH-E2E","CONV-E2E","NODE-E2E"
    locator=f"{archive}/{conversation}/{node}"
    return {
        "source_record_id":"SRC-"+sha(locator.encode("utf-8"))[:24],"archive_id":archive,"conversation_id":conversation,
        "source_message_id":"MSG-E2E","source_node_id":node,"source_locator":locator,"parent_node_id":None,
        "child_node_ids":[],"source_time":None,"source_time_unix":None,"role":"user","content_type":"text",
        "text_sha256":"a"*64,"source_snapshot_sha256":"b"*64,"parser_version":"synthetic-e2e",
        "has_attachments":False,"attachment_count":0,"attachment_payloads_inspected":False,
        "batch_id":"BATCH-E2E-001","registered_at":"2026-10-16T00:00:00Z","schema_version":"source-record-v1",
    }


class PipelineRealStageIntegrationTests(unittest.TestCase):
    def test_real_promotion_correction_index_and_restore_stages_compose(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); registry_dir=root/"registry"; registry_dir.mkdir()
            source=valid_source_record()
            source_registry=registry_dir/"source_records.jsonl"
            source_registry.write_bytes(canon(source)+b"\n")
            batch=root/"batch"; batch.mkdir()
            record={
                "memory_id":"MEM-E2E-001","record_type":"lesson","title":"Synthetic end-to-end lesson",
                "summary":"A test-only approved memory record","evidence_status":"observed",
                "lifecycle_status":"candidate","project_ids":["AGENT_MEMORY_SYSTEM"],"task_ids":["TASK-E2E"],
                "context_ids":["CTX-E2E"],"tags":["pipeline","restore"],"relations":[],
                "provenance":[{"source_record_id":source["source_record_id"],"source_locator":source["source_locator"],
                    "archive_id":source["archive_id"],"conversation_id":source["conversation_id"],"content_hash":source["text_sha256"]}],
                "revision":{"revision_id":"REV-E2E-001","revision_of":None,"reason":"synthetic integration fixture"},
            }
            artifact_bytes=canon(record)+b"\n"; artifact=batch/"records.jsonl"; artifact.write_bytes(artifact_bytes)
            manifest_data={
                "schema_version":"1.0","command":"IMPORT_READY","batch_id":"BATCH-E2E-MEMORY-001",
                "created_at":"2026-10-16T00:02:00Z","payload_classification":"sanitized",
                "source":{"source_type":"structured_export","source_id":"ARCH-E2E","project_id":"AGENT_MEMORY_SYSTEM",
                    "conversation_ids":["CONV-E2E"],"source_locator":source["source_locator"],
                    "captured_at":"unknown","scope_status":"PARTIAL","parser_version":"synthetic-e2e"},
                "artifacts":[{"artifact_id":"ART-E2E-001","kind":"memory_records","path":"records.jsonl",
                    "sha256":sha(artifact_bytes),"record_count":1,"lifecycle_status":"accepted",
                    "evidence_status":"observed","approval_status":"user_approved","approval_evidence":"DEC-E2E-001"}],
            }
            manifest_bytes=canon(manifest_data); manifest=batch/"manifest.json"; manifest.write_bytes(manifest_bytes)
            approval={
                "schema_version":"semantic-memory-approval-v1","decision_id":"DEC-E2E-001","decision":"approve",
                "actor_type":"user","actor_ref":"synthetic-test-actor","decided_at":"2026-10-16T00:03:00Z",
                "batch_id":manifest_data["batch_id"],"artifact_id":"ART-E2E-001","manifest_sha256":sha(manifest_bytes),
                "artifact_sha256":sha(artifact_bytes),"decision_source_ref":"fixture:approval-decision",
                "rationale":"Synthetic approval used only by automated integration test.",
            }
            approval_path=batch/"approval.json"; approval_path.write_bytes(canon(approval))
            relation={"type":"derived_from","target_id":source["source_record_id"],"basis":"source message supports the lesson",
                "confidence":"high","status":"accepted","source_refs":[source["source_record_id"]]}
            correction={
                "schema_version":"edge-correction-v1","correction_id":"CORR-E2E-001","action":"add","status":"accepted",
                "source_memory_id":"MEM-E2E-001","source_revision_id":"REV-E2E-001",
                "source_record_sha256":sha(canon(record)),"target_relation_sha256":None,"relation":relation,
                "decision_id":"DEC-CORR-E2E-001","decision_source_ref":"fixture:correction-approval",
                "recorded_at":"2026-10-16T00:04:00Z","rationale":"Synthetic reviewed relation correction",
                "source_refs":[source["source_record_id"]],
            }
            correction_bytes=json.dumps(correction,ensure_ascii=False,sort_keys=True).encode("utf-8")
            correction_path=batch/"correction.json"; correction_path.write_bytes(correction_bytes)
            correction_receipt={
                "schema_version":"edge-correction-approval-v1","decision_id":"DEC-CORR-E2E-001","decision":"approve",
                "actor_type":"user","actor_ref":"synthetic-test-actor","decided_at":"2026-10-16T00:04:30Z",
                "correction_id":"CORR-E2E-001","correction_sha256":sha(correction_bytes),
                "decision_source_ref":"fixture:correction-approval","rationale":"Synthetic approval for integration test.",
            }
            correction_receipt_path=batch/"correction-approval.json"; correction_receipt_path.write_bytes(canon(correction_receipt))
            project=root/"AGENT_MEMORY_SYSTEM"; project.mkdir()
            task=project/"TASK_STATE.md"; task.write_text("Current task: verify the memory pipeline.\n",encoding="utf-8")
            handoff=project/"HANDOFF.md"; handoff.write_text("Resume point: inspect the pipeline result.\n",encoding="utf-8")
            event_log=project/"events.jsonl"; event_log.write_text("",encoding="utf-8")
            code_sha="a"*40
            checkpoint={"branch":"integration/memory-core-clean-20261015","repository_state":{
                "last_verified_code_head":code_sha,"exact_head_ci_run_id":123,"exact_head_ci_conclusion":"success"}}
            (project/"CONTINUITY_CHECKPOINT.json").write_bytes(canon(checkpoint))
            def fake_fetch(url):
                if "/contents/projects/AGENT_MEMORY_SYSTEM/" in url:
                    name=url.split("?",1)[0].rsplit("/",1)[-1]
                    local={"TASK_STATE.md":task,"HANDOFF.md":handoff,"events.jsonl":event_log}.get(name)
                    if local is None: raise AssertionError("unexpected source URL: "+url)
                    raw=local.read_bytes()
                    return {"sha":hashlib.sha1(b"blob "+str(len(raw)).encode("ascii")+bytes([0])+raw).hexdigest()}
                if "/branches/" in url: return {"commit":{"sha":code_sha}}
                if "/actions/runs/123" in url: return {"head_sha":code_sha,"status":"completed","conclusion":"success"}
                if "/compare/" in url: return {"status":"identical","merge_base_commit":{"sha":code_sha},"files":[]}
                raise AssertionError("unexpected API URL: "+url)
            memory_registry=registry_dir/"memory_records.jsonl"
            correction_registry=registry_dir/"edge_corrections.jsonl"
            index_root=registry_dir/"memory_index"
            snapshot=root/"snapshot.json"; snapshot.write_bytes(canon({"archive_id":"ARCH-E2E","raw_sha256":"b"*64,"parser_version":"synthetic-e2e"}))
            real_refresh=pipeline.refresh_canonical_index
            refresh_calls={"count":0}
            def interrupt_after_publish(*args,**kwargs):
                built=real_refresh(*args,**kwargs)
                if refresh_calls["count"]==0:
                    refresh_calls["count"]+=1
                    raise RuntimeError("simulated interruption after index pointer publication")
                return built
            with mock.patch.object(pipeline,"run_ingestion",return_value={"status":"SOURCE_REGISTERED_DOWNSTREAM_PENDING","writes_performed":True}), \
                 mock.patch.object(pipeline,"refresh_canonical_index",side_effect=interrupt_after_publish):
                interrupted=pipeline.run_memory_pipeline(snapshot,root/"runs",manifest,approval_path,
                    repository="owner/repo",task_state=task,handoff=handoff,event_log=event_log,
                    correction_input=correction_path,correction_approval_receipt=correction_receipt_path,
                    source_registry_path=source_registry,memory_registry_path=memory_registry,
                    correction_registry_path=correction_registry,index_root=index_root,apply=True,fetch_json=fake_fetch)
                self.assertEqual(interrupted["status"],"BLOCKED_AT_CANONICAL_INDEX",interrupted)
                first_pointer=json.loads((index_root/"CURRENT.json").read_text(encoding="utf-8"))
                result=pipeline.run_memory_pipeline(snapshot,root/"runs",manifest,approval_path,
                    repository="owner/repo",task_state=task,handoff=handoff,event_log=event_log,
                    correction_input=correction_path,correction_approval_receipt=correction_receipt_path,
                    source_registry_path=source_registry,memory_registry_path=memory_registry,
                    correction_registry_path=correction_registry,index_root=index_root,apply=True,fetch_json=fake_fetch)
            self.assertEqual(result["status"],"PIPELINE_COMPLETE_WITH_PARTIAL_MEMORY",result)
            self.assertEqual(result["run_id"],interrupted["run_id"])
            self.assertEqual(result["stages"]["provenance_validation"],"RESOLVED")
            self.assertEqual(result["stages"]["semantic_promotion"],"ALREADY_PROMOTED")
            self.assertEqual(result["stages"]["edge_correction"],"ALREADY_REGISTERED")
            self.assertEqual(result["stages"]["canonical_index"],"BUILT_PARTIAL")
            self.assertEqual(result["stages"]["session_restore"],"RESTORED_PACKET_WITH_PARTIAL_MEMORY")
            restored=result["restore"]
            self.assertEqual(restored["semantic_memory_status"],"PARTIAL")
            index=json.loads((index_root/"CURRENT.json").read_text(encoding="utf-8"))
            generation=json.loads((index_root/index["generation_file"]).read_text(encoding="utf-8"))
            self.assertEqual(first_pointer["generation_id"],index["generation_id"])
            self.assertEqual(generation["coverage"]["correction_overlay_status"],"APPLIED")
            self.assertEqual(len(memory_registry.read_text(encoding="utf-8").splitlines()),1)
            self.assertEqual(len(correction_registry.read_text(encoding="utf-8").splitlines()),1)
            packet_event=pipeline._load_ledger(Path(result["ledger_path"]),result["run_id"])
            self.assertEqual(packet_event[-1]["event_type"],"PIPELINE_RESULT")
            self.assertEqual(sum(1 for event in packet_event if event["event_type"]=="PIPELINE_RESULT"),2)
            self.assertTrue(result["canonical_writes_performed"])


if __name__=="__main__": unittest.main()
