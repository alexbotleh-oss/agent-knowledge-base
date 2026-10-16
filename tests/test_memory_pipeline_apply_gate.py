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


def canon(x):
    return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")


class PipelineApplyGateTests(unittest.TestCase):
    def test_unresolved_provenance_prevents_promotion_stage(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); snap=root/"snapshot.json"; snap.write_bytes(canon({"archive_id":"A1","raw_sha256":"a"*64,"parser_version":"test"}))
            records=root/"records.jsonl"
            record={"memory_id":"MEM-1","record_type":"lesson","title":"x","summary":"x","evidence_status":"observed",
                    "provenance":[{"source_locator":"missing-locator"}],"revision":{"revision_id":"REV-1","revision_of":None}}
            raw=canon(record)+b"\n"; records.write_bytes(raw)
            manifest_data={"schema_version":"1.0","command":"IMPORT_READY","batch_id":"BATCH-PIPE-1",
                "created_at":"2026-10-16T00:00:00Z","payload_classification":"sanitized",
                "source":{"source_type":"chat_summary","source_id":"SRC-1","project_id":"TEST","conversation_ids":["C1"],
                    "source_locator":"fixture:source","captured_at":"unknown","scope_status":"PARTIAL"},
                "artifacts":[{"artifact_id":"ART-1","kind":"memory_records","path":"records.jsonl",
                    "sha256":hashlib.sha256(raw).hexdigest(),"record_count":1,"lifecycle_status":"accepted",
                    "evidence_status":"observed","approval_status":"user_approved","approval_evidence":"DEC-1"}]}
            manifest=root/"manifest.json"; manifest.write_bytes(canon(manifest_data))
            receipt=root/"receipt.json"; receipt.write_text("{}",encoding="utf-8")
            source=root/"source_records.jsonl"
            source.write_bytes(canon({"source_record_id":"SRC-000000000000000000000001","source_locator":"other",
                "source_node_id":"N1","source_message_id":"M1","archive_id":"A1","conversation_id":"C1","text_sha256":"b"*64})+b"\n")
            task=root/"TASK_STATE.md"; task.write_text("task",encoding="utf-8")
            handoff=root/"HANDOFF.md"; handoff.write_text("handoff",encoding="utf-8")
            events=root/"events.jsonl"; events.write_text("{}",encoding="utf-8")
            with mock.patch.object(pipeline,"promote_memory_records",return_value={"status":"DRY_RUN_READY","writes_performed":False}) as promote, \
                 mock.patch.object(pipeline,"run_ingestion",return_value={"status":"SOURCE_REGISTERED_DOWNSTREAM_PENDING","writes_performed":True}):
                result=pipeline.run_memory_pipeline(snap,root/"runs",manifest,receipt,repository="owner/repo",
                    task_state=task,handoff=handoff,event_log=events,source_registry_path=source,
                    memory_registry_path=root/"memory_records.jsonl",index_root=root/"index",apply=True)
            self.assertEqual(result["status"],"BLOCKED_AT_PROVENANCE_VALIDATION")
            self.assertEqual(promote.call_count,1)
            self.assertFalse((root/"index"/"CURRENT.json").exists())


if __name__=="__main__": unittest.main()
