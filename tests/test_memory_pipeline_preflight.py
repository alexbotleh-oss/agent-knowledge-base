import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
import memory_pipeline_coordinator as pipeline


class PipelinePreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.snapshot=self.root/"snapshot.json"; self.manifest=self.root/"manifest.json"; self.receipt=self.root/"receipt.json"
        self.snapshot.write_text(json.dumps({"archive_id":"A1","raw_sha256":"a"*64,"parser_version":"test"}),encoding="utf-8")
        self.manifest.write_text("{}",encoding="utf-8"); self.receipt.write_text("{}",encoding="utf-8")

    def call_pipeline(self,**kwargs):
        defaults={"repository":"owner/repo","task_state":self.root/"TASK_STATE.md","handoff":self.root/"HANDOFF.md",
                  "event_log":self.root/"events.jsonl","source_registry_path":self.root/"source_records.jsonl",
                  "memory_registry_path":self.root/"memory_records.jsonl","index_root":self.root/"index","apply":True}
        defaults.update(kwargs)
        return pipeline.run_memory_pipeline(self.snapshot,self.root/"runs",self.manifest,self.receipt,**defaults)

    def test_missing_restore_inputs_block_before_source_ingestion(self):
        with mock.patch.object(pipeline,"run_ingestion") as ingestion:
            result=self.call_pipeline()
        self.assertEqual(result["status"],"BLOCKED_AT_PREFLIGHT")
        ingestion.assert_not_called()
        self.assertTrue(Path(result["ledger_path"]).is_file())

    def test_invalid_semantic_approval_blocks_before_source_ingestion(self):
        for name in ("TASK_STATE.md","HANDOFF.md","events.jsonl"):
            (self.root/name).write_text("fixture",encoding="utf-8")
        with mock.patch.object(pipeline,"promote_memory_records",return_value={"status":"REJECTED","error":"bad receipt","writes_performed":False}), \
             mock.patch.object(pipeline,"run_ingestion") as ingestion:
            result=self.call_pipeline()
        self.assertEqual(result["status"],"BLOCKED_AT_PREFLIGHT")
        ingestion.assert_not_called()


if __name__=="__main__": unittest.main()
