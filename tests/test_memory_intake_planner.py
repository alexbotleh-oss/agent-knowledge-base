import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from plan_memory_intake import build_route_plan


class MemoryIntakePlannerTests(unittest.TestCase):
    def setUp(self):
        self.fixture = ROOT / "tests/fixtures/memory_intake_batch"
        self.manifest_path = self.fixture / "manifest.json"
        self.manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))

    def test_candidate_event_is_routed_to_candidate_view_without_writes(self):
        plan = build_route_plan(self.manifest_path)
        self.assertEqual(plan["status"], "DRY_RUN_READY")
        self.assertFalse(plan["writes_performed"])
        self.assertEqual(len(plan["routes"]), 1)
        self.assertEqual(plan["routes"][0]["logical_view"], "candidate_memory_view")
        self.assertEqual(plan["routes"][0]["planned_operation"], "stage_candidate_record")
        self.assertFalse(plan["routes"][0]["writes_performed"])

    def test_approved_record_routes_by_status_not_arbitrary_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            shutil.copyfile(self.fixture / "records.jsonl", folder / "records.jsonl")
            manifest = dict(self.manifest)
            manifest["artifacts"] = [dict(self.manifest["artifacts"][0],
                path="records.jsonl", lifecycle_status="accepted",
                approval_status="user_approved",
                approval_evidence="explicit approval reference")]
            path = folder / "manifest.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            plan = build_route_plan(path)
            self.assertEqual(plan["status"], "DRY_RUN_READY")
            self.assertEqual(plan["routes"][0]["logical_view"], "accepted_memory_view")
            self.assertFalse(plan["writes_performed"])

    def test_invalid_hash_rejects_entire_batch_with_no_routes(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            shutil.copyfile(self.fixture / "records.jsonl", folder / "records.jsonl")
            manifest = dict(self.manifest)
            manifest["artifacts"] = [dict(self.manifest["artifacts"][0],
                path="records.jsonl", sha256="0" * 64)]
            path = folder / "manifest.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            plan = build_route_plan(path)
            self.assertEqual(plan["status"], "REJECTED")
            self.assertEqual(plan["routes"], [])
            self.assertFalse(plan["writes_performed"])

    def test_unmapped_artifact_is_quarantined_not_guessed(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            shutil.copyfile(self.fixture / "records.jsonl", folder / "records.jsonl")
            manifest = dict(self.manifest)
            manifest["artifacts"] = [dict(self.manifest["artifacts"][0],
                path="records.jsonl", kind="other")]
            path = folder / "manifest.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            plan = build_route_plan(path)
            self.assertEqual(plan["routes"][0]["logical_view"], "quarantine_unmapped")
            self.assertEqual(plan["routes"][0]["planned_operation"], "quarantine_for_manual_mapping")


if __name__ == "__main__":
    unittest.main()
