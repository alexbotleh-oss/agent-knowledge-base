import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
import memory_pipeline_coordinator as pipeline


class PipelineApplySequenceTests(unittest.TestCase):
    def test_stages_are_composed_in_order_and_restore_coverage_is_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            snapshot=root/"snapshot.json"; snapshot.write_text('{"archive_id":"A1"}',encoding="utf-8")
            manifest=root/"manifest.json"; manifest.write_text("{}",encoding="utf-8")
            receipt=root/"receipt.json"; receipt.write_text("{}",encoding="utf-8")
            for name in ("TASK_STATE.md","HANDOFF.md","events.jsonl"):
                (root/name).write_text("fixture",encoding="utf-8")
            promotion_results=[
                {"status":"DRY_RUN_READY","writes_performed":False},
                {"status":"PROMOTED","batch_id":"B1","promoted_count":1,"writes_performed":True},
            ]
            restore_packet={"status":"RESTORED_PACKET_WITH_PARTIAL_MEMORY",
                "semantic_memory":{"status":"PARTIAL","coverage_status":"PARTIAL","index_generation_id":"GEN-1","returned_count":1},
                "repository_revision_evidence":{"status":"REMOTE_VERIFIED_EXACT_CODE_HEAD"}}
            with mock.patch.object(pipeline,"promote_memory_records",side_effect=promotion_results) as promote, \
                 mock.patch.object(pipeline,"run_ingestion",return_value={"status":"SOURCE_REGISTERED_DOWNSTREAM_PENDING","writes_performed":True}), \
                 mock.patch.object(pipeline,"validate_provenance_links",return_value={"status":"RESOLVED","resolved_refs":1}), \
                 mock.patch.object(pipeline,"refresh_canonical_index",return_value={"status":"BUILT_PARTIAL","generation_id":"GEN-1","records_indexed":1,"writes_performed":True}), \
                 mock.patch.object(pipeline,"build_memory_aware_packet",return_value=restore_packet):
                result=pipeline.run_memory_pipeline(snapshot,root/"runs",manifest,receipt,repository="owner/repo",
                    task_state=root/"TASK_STATE.md",handoff=root/"HANDOFF.md",event_log=root/"events.jsonl",
                    source_registry_path=root/"source_records.jsonl",memory_registry_path=root/"memory_records.jsonl",
                    index_root=root/"index",apply=True)
            self.assertEqual(result["status"],"PIPELINE_COMPLETE_WITH_PARTIAL_MEMORY")
            self.assertTrue(result["canonical_writes_performed"])
            self.assertEqual(result["stages"]["source_ingestion"],"SOURCE_REGISTERED_DOWNSTREAM_PENDING")
            self.assertEqual(result["stages"]["semantic_promotion"],"PROMOTED")
            self.assertEqual(result["stages"]["canonical_index"],"BUILT_PARTIAL")
            self.assertEqual(result["stages"]["session_restore"],"RESTORED_PACKET_WITH_PARTIAL_MEMORY")
            self.assertEqual(promote.call_count,2)
            events=pipeline._load_ledger(Path(result["ledger_path"]),result["run_id"])
            self.assertEqual(events[-1]["event_type"],"PIPELINE_RESULT")


if __name__=="__main__": unittest.main()
