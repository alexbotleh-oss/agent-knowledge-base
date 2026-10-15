import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from validate_memory import validate_intake_manifest


class MemoryIntakeContractTests(unittest.TestCase):
    def setUp(self):
        self.fixture = ROOT / "tests/fixtures/memory_intake_batch"
        self.manifest_path = self.fixture / "manifest.json"
        self.manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))

    def test_synthetic_manifest_and_artifact_hash_are_valid(self):
        self.assertEqual(validate_intake_manifest(self.manifest_path, ROOT), [])

    def test_missing_capture_time_remains_unknown_not_invalid(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "records.jsonl").write_text((self.fixture / "records.jsonl").read_text(encoding="utf-8"), encoding="utf-8")
            manifest = dict(self.manifest)
            manifest["source"] = dict(self.manifest["source"])
            manifest["source"].pop("captured_at", None)
            manifest["artifacts"] = [dict(self.manifest["artifacts"][0], path="records.jsonl")]
            path = folder / "manifest.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            self.assertEqual(validate_intake_manifest(path, ROOT), [])

    def test_artifact_tampering_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "records.jsonl").write_text('{"tampered":true}\n', encoding="utf-8")
            manifest = dict(self.manifest)
            manifest["artifacts"] = [dict(self.manifest["artifacts"][0], path="records.jsonl")]
            path = folder / "manifest.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            errors = validate_intake_manifest(path, ROOT)
            self.assertTrue(any("sha256 does not match" in error for error in errors))

    def test_path_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            manifest = dict(self.manifest)
            manifest["artifacts"] = [dict(self.manifest["artifacts"][0], path="../outside.jsonl")]
            path = folder / "manifest.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            errors = validate_intake_manifest(path, ROOT)
            self.assertTrue(any("safe relative path" in error for error in errors))

    def test_accepted_record_requires_explicit_approval_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "records.jsonl").write_text((self.fixture / "records.jsonl").read_text(encoding="utf-8"), encoding="utf-8")
            manifest = dict(self.manifest)
            manifest["artifacts"] = [dict(self.manifest["artifacts"][0],
                path="records.jsonl", lifecycle_status="accepted",
                approval_status="pending", approval_evidence=None)]
            path = folder / "manifest.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            errors = validate_intake_manifest(path, ROOT)
            self.assertTrue(any("accepted records require" in error for error in errors))

    def test_unknown_top_level_fields_are_rejected_not_guessed(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "records.jsonl").write_text((self.fixture / "records.jsonl").read_text(encoding="utf-8"), encoding="utf-8")
            manifest = dict(self.manifest)
            manifest["unexpected_route"] = "arbitrary/path"
            manifest["artifacts"] = [dict(self.manifest["artifacts"][0], path="records.jsonl")]
            path = folder / "manifest.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            errors = validate_intake_manifest(path, ROOT)
            self.assertTrue(any("unknown top-level fields" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
