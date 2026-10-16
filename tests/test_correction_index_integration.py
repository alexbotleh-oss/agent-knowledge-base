import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
import canonical_memory_index as indexer


def canon(x):
    return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")


class CorrectionIndexTests(unittest.TestCase):
    def test_accepted_add_is_applied_only_to_derived_index(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); registry=root/"memory_records.jsonl"; overlays=root/"edge_corrections.jsonl"
            relation={"type":"derived_from","target_id":"SRC-1","basis":"original","confidence":"high","status":"accepted","source_refs":["src"]}
            record={"memory_id":"MEM-1","record_type":"lesson","title":"t","summary":"s","evidence_status":"observed",
                    "provenance":[{"source_locator":"src"}],"relations":[relation],
                    "revision":{"revision_id":"REV-1","revision_of":None}}
            rh=hashlib.sha256(canon(record)).hexdigest()
            envelope={"registry_schema_version":"semantic-memory-registry-v1","promotion_id":"PROMO-1",
                "memory_id":"MEM-1","revision_id":"REV-1","record_sha256":rh,"lifecycle_status":"accepted","record":record,
                "batch_id":"BATCH-1","artifact_id":"ART-1","manifest_sha256":"1"*64,"artifact_sha256":"2"*64,
                "approval_decision_id":"DEC-1","approval_receipt_sha256":"3"*64,"promoted_at":"2026-10-16T00:00:00Z","previous_revision_id":None}
            registry.write_bytes(canon(envelope)+b"\n")
            relation2={"type":"supports","target_id":"MEM-2","basis":"reviewed","confidence":"medium","status":"accepted","source_refs":["decision"]}
            correction={"schema_version":"edge-correction-v1","correction_id":"CORR-1","action":"add","status":"accepted",
                "source_memory_id":"MEM-1","source_revision_id":"REV-1","source_record_sha256":rh,"target_relation_sha256":None,
                "relation":relation2,"decision_id":"DEC-1","decision_source_ref":"user-ref","recorded_at":"2026-10-16T01:00:00Z",
                "rationale":"test","source_refs":["decision"]}
            correction_envelope={"registry_schema_version":"edge-correction-registry-v1","correction_id":"CORR-1",
                "correction_sha256":hashlib.sha256(canon(correction)).hexdigest(),"correction":correction,
                "approval_receipt_sha256":"4"*64,"source_registry_sha256":"5"*64,"registered_at":"2026-10-16T01:01:00Z"}
            overlays.write_bytes(canon(correction_envelope)+b"\n")
            payload=indexer.build_index_payload(registry.read_bytes(),overlays.read_bytes())
            self.assertEqual(payload["coverage"]["correction_overlay_status"],"APPLIED")
            self.assertIn(relation2,payload["records"][0]["relations"])
            self.assertIn("MEM-2",payload["indexes"]["by_relation_target"])
            self.assertEqual(json.loads(registry.read_text())["record"]["relations"],[relation])


if __name__=="__main__": unittest.main()
