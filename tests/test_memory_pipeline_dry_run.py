import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
import memory_pipeline_coordinator as pipeline


class PipelineDryRunTests(unittest.TestCase):
    def test_same_inputs_replay_through_one_hash_chained_run(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); snapshot=root/"snapshot.json"; manifest=root/"manifest.json"; receipt=root/"receipt.json"
            snapshot.write_text(json.dumps({"archive_id":"A1","raw_sha256":"a"*64,"parser_version":"test"}),encoding="utf-8")
            manifest.write_text("{}",encoding="utf-8"); receipt.write_text("{}",encoding="utf-8")
            with mock.patch.object(pipeline,"run_ingestion",return_value={"status":"READY_FOR_SOURCE_REGISTRATION","writes_performed":False}), \
                 mock.patch.object(pipeline,"promote_memory_records",return_value={"status":"DRY_RUN_READY","candidate_count":1,"writes_performed":False}):
                first=pipeline.run_memory_pipeline(snapshot,root/"runs",manifest,receipt,repository="owner/repo",
                    task_state=root/"TASK_STATE.md",handoff=root/"HANDOFF.md",event_log=root/"events.jsonl",
                    source_registry_path=root/"source_records.jsonl",memory_registry_path=root/"memory_records.jsonl",
                    index_root=root/"index",apply=False)
                second=pipeline.run_memory_pipeline(snapshot,root/"runs",manifest,receipt,repository="owner/repo",
                    task_state=root/"TASK_STATE.md",handoff=root/"HANDOFF.md",event_log=root/"events.jsonl",
                    source_registry_path=root/"source_records.jsonl",memory_registry_path=root/"memory_records.jsonl",
                    index_root=root/"index",apply=False)
            self.assertEqual(first["status"],"DRY_RUN_READY")
            self.assertEqual(first["run_id"],second["run_id"])
            events=pipeline._load_ledger(Path(first["ledger_path"]),first["run_id"])
            self.assertEqual(events[-1]["event_type"],"PIPELINE_RESULT")
            self.assertEqual(events[-1]["status"],"DRY_RUN_READY")


if __name__=="__main__": unittest.main()
