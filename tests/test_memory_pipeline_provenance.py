import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
import memory_pipeline_coordinator as pipeline


def canon(x):
    return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")


class ProvenanceGateTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name); self.folder=self.root/"input"; self.folder.mkdir()

    def make_inputs(self,locator="loc-1",source_rows=None,content_hash="a"*64):
        record={"memory_id":"MEM-PIPE-001","record_type":"lesson","title":"Fixture","summary":"Synthetic",
                "evidence_status":"observed","provenance":[{"source_locator":locator,"archive_id":"ARCH-1","conversation_id":"CONV-1","content_hash":content_hash}],
                "revision":{"revision_id":"REV-001","revision_of":None}}
        raw=canon(record)+b"\n"; (self.folder/"records.jsonl").write_bytes(raw)
        manifest={"schema_version":"1.0","command":"IMPORT_READY","batch_id":"BATCH-PIPE-001",
            "created_at":"2026-10-16T00:00:00Z","payload_classification":"sanitized",
            "source":{"source_type":"chat_summary","source_id":"PIPE-SOURCE","project_id":"TEST_PROJECT",
                "conversation_ids":["CONV-1"],"source_locator":"fixture:archive","captured_at":"unknown","scope_status":"PARTIAL"},
            "artifacts":[{"artifact_id":"ART-PIPE-001","kind":"memory_records","path":"records.jsonl",
                "sha256":hashlib.sha256(raw).hexdigest(),"record_count":1,"lifecycle_status":"accepted",
                "evidence_status":"observed","approval_status":"user_approved","approval_evidence":"DEC-PIPE-001"}]}
        mp=self.folder/"manifest.json"; mp.write_bytes(canon(manifest))
        rows=source_rows or [{"source_record_id":"SRC-000000000000000000000001","source_locator":"loc-1",
            "source_node_id":"NODE-1","source_message_id":"MSG-1","archive_id":"ARCH-1","conversation_id":"CONV-1","text_sha256":"a"*64}]
        sp=self.folder/"source_records.jsonl"; sp.write_bytes(b"".join(canon(x)+b"\n" for x in rows))
        return mp,sp

    def test_exact_source_locator_and_hash_resolve(self):
        manifest,source=self.make_inputs()
        result=pipeline.validate_provenance_links(manifest,source)
        self.assertEqual(result["status"],"RESOLVED")
        self.assertEqual(result["resolved_refs"],1)

    def test_ambiguous_source_locator_blocks(self):
        second={"source_record_id":"SRC-000000000000000000000002","source_locator":"loc-1",
            "source_node_id":"NODE-2","source_message_id":"MSG-2","archive_id":"ARCH-1","conversation_id":"CONV-1","text_sha256":"a"*64}
        manifest,source=self.make_inputs(source_rows=[
            {"source_record_id":"SRC-000000000000000000000001","source_locator":"loc-1","source_node_id":"NODE-1",
             "source_message_id":"MSG-1","archive_id":"ARCH-1","conversation_id":"CONV-1","text_sha256":"a"*64},second])
        result=pipeline.validate_provenance_links(manifest,source)
        self.assertEqual(result["status"],"BLOCKED")
        self.assertEqual(len(result["ambiguous_refs"]),1)

    def test_missing_source_blocks(self):
        manifest,source=self.make_inputs(locator="missing-locator")
        result=pipeline.validate_provenance_links(manifest,source)
        self.assertEqual(result["status"],"BLOCKED")
        self.assertEqual(len(result["missing_refs"]),1)


if __name__=="__main__": unittest.main()
