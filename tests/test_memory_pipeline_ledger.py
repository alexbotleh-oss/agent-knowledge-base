import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
import memory_pipeline_coordinator as pipeline


class PipelineLedgerTests(unittest.TestCase):
    def test_event_chain_rejects_modified_event(self):
        with tempfile.TemporaryDirectory() as d:
            run_dir=Path(d)
            pipeline._append_event(run_dir,"PIPE-TEST-001","PIPELINE_STARTED","pipeline","RUNNING",{})
            ledger=run_dir/"pipeline_events.jsonl"
            events=pipeline._load_ledger(ledger,"PIPE-TEST-001")
            self.assertEqual(len(events),1)
            row=json.loads(ledger.read_text(encoding="utf-8"))
            row["status"]="CHANGED"
            ledger.write_text(json.dumps(row)+"\n",encoding="utf-8")
            with self.assertRaisesRegex(ValueError,"hash mismatch"):
                pipeline._load_ledger(ledger,"PIPE-TEST-001")

    def test_projection_is_rebuilt_from_hash_chained_events(self):
        with tempfile.TemporaryDirectory() as d:
            run_dir=Path(d)
            pipeline._append_event(run_dir,"PIPE-TEST-002","PIPELINE_STARTED","pipeline","RUNNING",{})
            pipeline._append_event(run_dir,"PIPE-TEST-002","STAGE_RESULT","index","BUILT_PARTIAL",{"generation":"G1"})
            state=json.loads((run_dir/"pipeline_state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["event_count"],2)
            self.assertEqual(state["stages"]["index"]["status"],"BUILT_PARTIAL")
            (run_dir/"pipeline_state.json").write_text("{}",encoding="utf-8")
            events=pipeline._load_ledger(run_dir/"pipeline_events.jsonl","PIPE-TEST-002")
            pipeline._projection(run_dir/"pipeline_state.json",events)
            rebuilt=json.loads((run_dir/"pipeline_state.json").read_text(encoding="utf-8"))
            self.assertEqual(rebuilt["latest_event_sha256"],events[-1]["event_sha256"])


if __name__=="__main__": unittest.main()
