import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from audit_memory_architecture import build_audit


class MemoryArchitectureAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "tools").mkdir()
        (self.root / "core").mkdir()
        (self.root / "registry").mkdir()
        (self.root / "registry" / "records.jsonl").write_text("", encoding="utf-8")
        (self.root / "tools" / "reader.py").write_text(
            "def read():\\n    return True\\n", encoding="utf-8"
        )
        (self.root / "tools" / "writer.py").write_text(
            "from reader import read\\n"
            "from pathlib import Path\\n"
            "ROOT = Path(__file__).resolve().parents[1]\\n"
            "DEFAULT_REGISTRY = ROOT / 'registry' / 'records.jsonl'\\n"
            "if __name__ == '__main__':\\n"
            "    print(read())\\n",
            encoding="utf-8",
        )

    def test_builds_direct_import_graph_and_detects_storage_path(self):
        report = build_audit(self.root, expected_paths=("core/agent_bootstrap.md",))
        self.assertEqual(report["status"], "COMPLETE_SCAN")
        self.assertIn(
            {"from": "writer", "to": "reader", "type": "imports"},
            report["dependency_edges"],
        )
        registry = [
            item for item in report["storage_paths"]
            if item["owner"] == "tools/writer.py" and item["constant"] == "DEFAULT_REGISTRY"
        ]
        self.assertEqual(len(registry), 1)
        self.assertEqual(registry[0]["path"], "registry/records.jsonl")
        self.assertTrue(registry[0]["exists_in_current_checkout"])

    def test_expected_missing_location_is_reported_not_assumed_globally_absent(self):
        report = build_audit(self.root, expected_paths=("core/agent_bootstrap.md",))
        self.assertEqual(report["expected_locations"][0]["status"], "EXPECTED_BUT_ABSENT")
        self.assertIn(
            "Runtime data files may be absent from Git while existing in another runtime or branch.",
            report["limitations"],
        )

    def test_parse_error_marks_scan_partial(self):
        (self.root / "tools" / "broken.py").write_text("def broken(:\\n", encoding="utf-8")
        report = build_audit(self.root)
        self.assertEqual(report["status"], "PARTIAL_SCAN")
        broken = next(item for item in report["components"] if item["path"] == "tools/broken.py")
        self.assertEqual(broken["parse_status"], "ERROR")

    def test_invalid_root_is_reported(self):
        report = build_audit(self.root / "does-not-exist")
        self.assertEqual(report["status"], "INVALID_ROOT")
        self.assertFalse(report["writes_performed"])


if __name__ == "__main__":
    unittest.main()
