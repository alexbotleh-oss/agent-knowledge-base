import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from relocation_aware_discovery import discover


class RelocationAwareDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "expected").mkdir()
        (self.root / "archive").mkdir()

    def test_finds_stable_identity_elsewhere_when_expected_path_is_empty(self):
        (self.root / "archive" / "history.md").write_text(
            "Earlier checkpoint references EVT-AGMS-20261017-004 and preserves provenance.",
            encoding="utf-8",
        )
        result = discover(
            "expected/TASK_STATE.md", [self.root],
            identity="EVT-AGMS-20261017-004",
        )
        self.assertEqual(result["status"], "FOUND_ELSEWHERE_IDENTITY_MATCH")
        self.assertFalse(result["expected_path_exists"])
        self.assertEqual(result["candidates"][0]["relative_path"], "archive/history.md")
        self.assertFalse(result["writes_performed"])

    def test_exact_hash_is_stronger_than_query_candidate(self):
        data = b"the source record"
        (self.root / "archive" / "source.txt").write_bytes(data)
        result = discover(
            "expected/source.txt", [self.root],
            expected_sha256=hashlib.sha256(data).hexdigest(),
        )
        self.assertEqual(result["status"], "FOUND_ELSEWHERE_IDENTITY_MATCH")
        self.assertIn("EXACT_SHA256", result["candidates"][0]["evidence"])

    def test_query_only_is_not_identity_verification(self):
        (self.root / "archive" / "notes.md").write_text("Memory recovery and provenance.", encoding="utf-8")
        result = discover("expected/missing.md", [self.root], query="MEMORY   recovery")
        self.assertEqual(result["status"], "CANDIDATES_UNVERIFIED")
        self.assertFalse(result["candidates"][0]["identity_verified"])

    def test_complete_no_match_is_scoped_not_global_absence(self):
        (self.root / "archive" / "notes.md").write_text("Other content.", encoding="utf-8")
        result = discover("expected/missing.md", [self.root], identity="MEM-DOES-NOT-EXIST")
        self.assertEqual(result["status"], "NOT_FOUND_WITHIN_SEARCH_SCOPE")
        self.assertIn("configured scope", result["interpretation"])

    def test_file_limit_marks_search_incomplete(self):
        (self.root / "archive" / "one.md").write_text("one", encoding="utf-8")
        (self.root / "archive" / "two.md").write_text("two", encoding="utf-8")
        result = discover("expected/missing.md", [self.root], identity="ABSENT-ID", max_files=1)
        self.assertEqual(result["status"], "SEARCH_INCOMPLETE")
        self.assertEqual(result["coverage_status"], "PARTIAL")

    def test_invalid_hash_is_rejected(self):
        result = discover("expected/missing.md", [self.root], expected_sha256="not-a-hash")
        self.assertEqual(result["status"], "INVALID_INPUT")


if __name__ == "__main__":
    unittest.main()
