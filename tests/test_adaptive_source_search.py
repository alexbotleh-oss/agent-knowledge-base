import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from adaptive_source_search import build_plan, execute_search


class AdaptiveSourceSearchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.good = self.root / "good"
        self.unknown = self.root / "unknown"
        self.emergency = self.root / "emergency"
        for path in (self.good, self.unknown, self.emergency):
            (path / "expected").mkdir(parents=True)

    def request(self, **extra):
        result = {
            "identity": "SRC-ADAPTIVE-20261017",
            "source_type": "structured_export",
            "format": "json",
            "project_id": "AGENT_MEMORY_SYSTEM",
            "size_bytes": 5000,
            "required_capabilities": ["source_records"],
        }
        result.update(extra)
        return result

    def sources(self):
        return [
            {
                "source_id": "small-incompatible", "root": str(self.emergency),
                "source_types": ["structured_export"], "formats": ["json"],
                "project_ids": ["AGENT_MEMORY_SYSTEM"], "max_item_size_bytes": 1000,
                "capabilities": ["source_records"], "priority": 0,
            },
            {
                "source_id": "unknown-profile", "root": str(self.unknown),
                "priority": 0,
            },
            {
                "source_id": "compatible", "root": str(self.good),
                "source_types": ["structured_export"], "formats": ["json"],
                "project_ids": ["AGENT_MEMORY_SYSTEM"], "max_item_size_bytes": 10000,
                "min_item_size_bytes": 0, "capabilities": ["source_records"], "priority": 5,
            },
        ]

    def test_known_fit_precedes_unknown_and_conflicting_sources(self):
        plan = build_plan(self.sources(), self.request())
        self.assertEqual(plan["status"], "PLAN_READY")
        self.assertEqual(
            [item["source_id"] for item in plan["tiers"][0]["sources"]],
            ["compatible"],
        )
        self.assertEqual(
            [item["source_id"] for item in plan["tiers"][1]["sources"]],
            ["unknown-profile"],
        )
        self.assertEqual(
            [item["source_id"] for item in plan["tiers"][2]["sources"]],
            ["small-incompatible"],
        )

    def test_unknown_metadata_is_fallback_not_exclusion(self):
        plan = build_plan(self.sources(), self.request())
        all_sources = [source["source_id"] for tier in plan["tiers"] for source in tier["sources"]]
        self.assertEqual(set(all_sources), {"compatible", "unknown-profile", "small-incompatible"})

    def test_verified_match_stops_before_emergency_tier(self):
        (self.good / "expected" / "record.json").write_text(
            json.dumps({"source_record_id": "SRC-ADAPTIVE-20261017"}),
            encoding="utf-8",
        )
        plan = build_plan(self.sources(), self.request())
        result = execute_search(plan, self.request(), "expected")
        self.assertEqual(result["status"], "VERIFIED_MATCH_FOUND")
        self.assertEqual(result["matched_source_id"], "compatible")
        self.assertEqual(result["unsearched_tiers"], ["fallback", "emergency"])
        self.assertEqual(len(result["searches"]), 1)
        self.assertFalse(result["writes_performed"])

    def test_unverified_candidate_does_not_stop_fallback(self):
        (self.good / "expected" / "note.md").write_text(
            "A note mentions SRC-ADAPTIVE-20261017 in passing.",
            encoding="utf-8",
        )
        (self.unknown / "expected" / "actual.json").write_text(
            json.dumps({"source_record_id": "SRC-ADAPTIVE-20261017"}),
            encoding="utf-8",
        )
        plan = build_plan(self.sources(), self.request())
        result = execute_search(plan, self.request(), "expected")
        self.assertEqual(result["status"], "VERIFIED_MATCH_FOUND")
        self.assertEqual(result["matched_source_id"], "unknown-profile")
        self.assertEqual([item["tier"] for item in result["searches"]], ["preferred", "fallback"])
        self.assertFalse(result["writes_performed"])

    def test_no_match_expands_to_emergency_source(self):
        plan = build_plan(self.sources(), self.request(identity="SRC-NOT-PRESENT"))
        result = execute_search(plan, self.request(identity="SRC-NOT-PRESENT"), "expected")
        self.assertEqual(result["status"], "NO_MATCH_IN_CONFIGURED_SOURCES")
        self.assertEqual([item["tier"] for item in result["searches"]], [
            "preferred", "fallback", "emergency"
        ])

    def test_bad_size_is_rejected(self):
        plan = build_plan(self.sources(), self.request(size_bytes=-1))
        self.assertEqual(plan["status"], "INVALID_INPUT")


if __name__ == "__main__":
    unittest.main()
