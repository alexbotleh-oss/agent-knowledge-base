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


def source_row(archive="ARCH-1",conversation="CONV-1",node="NODE-1",text_hash="a"*64):
    locator=f"{archive}/{conversation}/{node}"
    return {
        "source_record_id":"SRC-"+hashlib.sha256(locator.encode("utf-8")).hexdigest()[:24],
        "archive_id":archive,"conversation_id":conversation,"source_message_id":"MSG-1","source_node_id":node,
        "source_locator":locator,"parent_node_id":None,"child_node_ids":[],"source_time":None,"source_time_unix":None,
        "role":"user","content_type":"text","text_sha256":text_hash,"source_snapshot_sha256":"b"*64,
        "parser_version":"test-parser","has_attachments":False,"attachment_count":0,
        "attachment_payloads_inspected":False,"batch_id":"BATCH-TEST-001","registered_at":"2026-10-16T00:00:00Z",
        "schema_version":"source-record-v1",
    }


class ProvenanceGateTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name); self.folder=self.root/"input"; self.folder.mkdir()

    def make_inputs(self,provenance=None,source_rows=None):
        default_source=source_row()
        if provenance is None:
            provenance=[{"source_locator":default_source["source_locator"],"archive_id":"ARCH-1",
                         "conversation_id":"CONV-1","content_hash":"a"*64}]
        record={"memory_id":"MEM-PIPE-001","record_type":"lesson","title":"Fixture","summary":"Synthetic",
                "evidence_status":"observed","provenance":provenance,
                "revision":{"revision_id":"REV-001","revision_of":None}}
        raw=canon(record)+b"\n"; (self.folder/"records.jsonl").write_bytes(raw)
        manifest_data={"schema_version":"1.0","command":"IMPORT_READY","batch_id":"BATCH-PIPE-001",
            "created_at":"2026-10-16T00:00:00Z","payload_classification":"sanitized",
            "source":{"source_type":"chat_summary","source_id":"PIPE-SOURCE","project_id":"TEST_PROJECT",
                "conversation_ids":["CONV-1"],"source_locator":"fixture:archive","captured_at":"unknown","scope_status":"PARTIAL"},
            "artifacts":[{"artifact_id":"ART-PIPE-001","kind":"memory_records","path":"records.jsonl",
                "sha256":hashlib.sha256(raw).hexdigest(),"record_count":1,"lifecycle_status":"accepted",
                "evidence_status":"observed","approval_status":"user_approved","approval_evidence":"DEC-PIPE-001"}]}
        mp=self.folder/"manifest.json"; mp.write_bytes(canon(manifest_data))
        rows=source_rows or [default_source]
        sp=self.folder/"source_records.jsonl"; sp.write_bytes(b"".join(canon(x)+b"\n" for x in rows))
        return mp,sp

    def test_exact_source_locator_and_hash_resolve(self):
        manifest,source=self.make_inputs()
        result=pipeline.validate_provenance_links(manifest,source)
        self.assertEqual(result["status"],"RESOLVED")
        self.assertEqual(result["resolved_refs"],1)

    def test_ambiguous_node_id_blocks(self):
        manifest,source=self.make_inputs(provenance=[{"source_node_id":"NODE-1"}],
            source_rows=[source_row("ARCH-1","CONV-1","NODE-1"),source_row("ARCH-2","CONV-2","NODE-1")])
        result=pipeline.validate_provenance_links(manifest,source)
        self.assertEqual(result["status"],"BLOCKED")
        self.assertEqual(len(result["ambiguous_refs"]),1)

    def test_missing_source_blocks(self):
        manifest,source=self.make_inputs(provenance=[{"source_locator":"ARCH-1/CONV-1/NODE-MISSING"}])
        result=pipeline.validate_provenance_links(manifest,source)
        self.assertEqual(result["status"],"BLOCKED")
        self.assertEqual(len(result["missing_refs"]),1)

    def test_content_hash_mismatch_blocks(self):
        source=source_row()
        manifest,path=self.make_inputs(provenance=[{"source_locator":source["source_locator"],"content_hash":"c"*64}],source_rows=[source])
        result=pipeline.validate_provenance_links(manifest,path)
        self.assertEqual(result["status"],"BLOCKED")
        self.assertIn("content_hash",result["missing_refs"][0]["reason"])


if __name__=="__main__": unittest.main()
