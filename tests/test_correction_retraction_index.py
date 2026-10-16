import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
import canonical_memory_index as indexer


def canon(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")


class CorrectionRetractionIndexTests(unittest.TestCase):
    def test_retract_changes_only_the_index_view(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            relation={"type":"derived_from","target_id":"SRC-RETRACT","basis":"original","confidence":"high","status":"accepted","source_refs":["src"]}
            record={"memory_id":"MEM-RETRACT","record_type":"lesson","title":"test","summary":"test",
                    "evidence_status":"observed","provenance":[{"source_locator":"src"}],"relations":[relation],
                    "revision":{"revision_id":"REV-1","revision_of":None}}
            record_sha=hashlib.sha256(canon(record)).hexdigest()
            source={"registry_schema_version":"semantic-memory-registry-v1","promotion_id":"PROMO-RETRACT",
                    "memory_id":"MEM-RETRACT","revision_id":"REV-1","record_sha256":record_sha,
                    "lifecycle_status":"accepted","record":record,"batch_id":"BATCH-1","artifact_id":"ART-1",
                    "manifest_sha256":"1"*64,"artifact_sha256":"2"*64,"approval_decision_id":"DEC-1",
                    "approval_receipt_sha256":"3"*64,"promoted_at":"2026-10-16T00:00:00Z","previous_revision_id":None}
            correction={"schema_version":"edge-correction-v1","correction_id":"CORR-RETRACT","action":"retract",
                        "status":"accepted","source_memory_id":"MEM-RETRACT","source_revision_id":"REV-1",
                        "source_record_sha256":record_sha,"target_relation_sha256":hashlib.sha256(canon(relation)).hexdigest(),
                        "recorded_at":"2026-10-16T01:00:00Z","rationale":"reviewed correction",
                        "source_refs":["decision"],"decision_id":"DEC-1","decision_source_ref":"user-ref"}
            overlay={"registry_schema_version":"edge-correction-registry-v1","correction_id":"CORR-RETRACT",
                     "correction_sha256":hashlib.sha256(canon(correction)).hexdigest(),"correction":correction,
                     "approval_receipt_sha256":"4"*64,"source_registry_sha256":"5"*64,"registered_at":"2026-10-16T01:01:00Z"}
            payload=indexer.build_index_payload(canon(source)+b"\n",canon(overlay)+b"\n")
            self.assertEqual(payload["coverage"]["correction_overlay_status"],"APPLIED")
            self.assertEqual(payload["records"][0]["relations"],[])
            self.assertNotIn("derived_from",payload["indexes"]["by_relation_type"])
            self.assertEqual(record["relations"],[relation])


if __name__=="__main__": unittest.main()
