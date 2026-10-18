import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from temporal_memory_model import (
    assertions_as_of,
    compare_snapshots,
    downstream_impact,
    validate_assertion,
    validate_snapshot,
    validate_temporal_relations,
)


def snapshot(snapshot_id, captured_at, count, **overrides):
    row = {
        "snapshot_id": snapshot_id,
        "captured_at": captured_at,
        "scope_id": "all-chat-exports-v1",
        "counting_unit": "conversation_object",
        "inclusion_rules_id": "include-available-conversation-objects-v1",
        "exclusion_rules_id": "exclude-non-conversation-assets-v1",
        "coverage_status": "PARTIAL",
        "counts": {"conversations": count, "message_ids": 10034},
    }
    row.update(overrides)
    return row


def assertion(assertion_id, claim, recorded_at, lifecycle_status="accepted"):
    return {
        "assertion_id": assertion_id,
        "claim": claim,
        "recorded_at": recorded_at,
        "evidence_status": "reported",
        "lifecycle_status": lifecycle_status,
        "source_refs": ["snapshot:archive-2026-10-07"],
    }


class TemporalMemoryModelTests(unittest.TestCase):
    def test_same_scope_count_delta_is_not_called_corruption(self):
        before = snapshot("archive-2026-10-07", "2026-10-07T15:00:00Z", 37)
        later = snapshot("merged-memory-2026-10-13", "2026-10-13T12:00:00Z", 74)
        result = compare_snapshots(before, later)
        self.assertEqual(result["status"], "comparable")
        self.assertEqual(result["deltas"]["conversations"], 37)
        self.assertIn("cause is undetermined", result["interpretation"])

    def test_37_vs_74_fixture_keeps_unknown_snapshot_unresolved(self):
        fixture_path = ROOT / "tests" / "fixtures" / "temporal_snapshots_37_vs_74.json"
        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        left, right = fixture["snapshots"]
        result = compare_snapshots(left, right)
        self.assertEqual(result["status"], fixture["expected_interpretation"]["status"])
        self.assertIsNone(right["captured_at"])
        self.assertIn("scope_id", result["mismatched_dimensions"])
        self.assertIn("counting_unit", result["mismatched_dimensions"])
        self.assertIn("37 missing conversations", fixture["expected_interpretation"]["must_not_conclude"][-1])

    def test_different_counting_unit_is_not_comparable(self):
        before = snapshot("a", "2026-10-07T15:00:00Z", 37)
        later = snapshot("b", "2026-10-13T12:00:00Z", 74, counting_unit="merged_memory_record")
        result = compare_snapshots(before, later)
        self.assertEqual(result["status"], "not_comparable")
        self.assertIn("counting_unit", result["mismatched_dimensions"])

    def test_missing_snapshot_scope_is_invalid_not_guessed(self):
        row = snapshot("a", "2026-10-07T15:00:00Z", 37)
        del row["scope_id"]
        self.assertIn("missing:scope_id", validate_snapshot(row))

    def test_as_of_view_preserves_old_assertion_without_future_revision(self):
        old = assertion("A1", "archive contains 37 conversations", "2026-10-07T16:00:00Z")
        later = assertion("A2", "merged memory mentions 74 conversations", "2026-10-13T12:00:00Z")
        rows = assertions_as_of([old, later], "2026-10-10T00:00:00Z")
        self.assertEqual([row["assertion_id"] for row in rows], ["A1"])
        self.assertEqual(len([old, later]), 2)

    def test_superseded_assertion_is_not_current_but_remains_stored(self):
        old = assertion("A1", "earlier interpretation", "2026-10-07T16:00:00Z", "superseded")
        new = assertion("A2", "revised interpretation", "2026-10-13T12:00:00Z")
        rows = assertions_as_of([old, new], "2026-10-14T00:00:00Z")
        self.assertEqual([row["assertion_id"] for row in rows], ["A2"])
        self.assertEqual(old["claim"], "earlier interpretation")

    def test_downstream_impact_is_transitive_and_cycle_safe(self):
        edges = [
            {"source_id": "A", "target_id": "B", "type": "derived_from"},
            {"source_id": "B", "target_id": "C", "type": "supports"},
            {"source_id": "C", "target_id": "A", "type": "summarizes"},
            {"source_id": "X", "target_id": "Y", "type": "same_incident_candidate"},
        ]
        self.assertEqual(downstream_impact("A", edges), ["B", "C"])

    def test_assertion_requires_provenance_and_timezone(self):
        row = assertion("A1", "claim", "2026-10-07T16:00:00")
        errors = validate_assertion(row)
        self.assertTrue(any("must include a timezone" in error for error in errors))
        self.assertIn("source_refs must be a non-empty list", validate_assertion({**row, "recorded_at": "2026-10-07T16:00:00Z", "source_refs": []}))


    def test_temporal_relation_validator_flags_wrong_direction_from_trusted_order(self):
        records = [
            {"event_id": "EVT-AGMS-20261018-001", "relations": []},
            {
                "event_id": "EVT-AGMS-20261018-002",
                "relations": [{
                    "type": "followed_by",
                    "event_id": "EVT-AGMS-20261018-001",
                    "basis": "commit ancestry",
                }],
            },
        ]
        errors = validate_temporal_relations(
            records,
            {"EVT-AGMS-20261018-001": 1, "EVT-AGMS-20261018-002": 2},
        )
        self.assertEqual(len(errors), 1)
        self.assertIn("followed_by points to non-later event EVT-AGMS-20261018-001", errors[0])

    def test_temporal_relation_correction_overlay_repairs_direction_without_mutating_source(self):
        old_edge = {
            "type": "followed_by",
            "event_id": "EVT-AGMS-20261018-001",
            "basis": "git commit ancestry; earlier date",
        }
        corrected_edge = {
            "type": "preceded_by",
            "event_id": "EVT-AGMS-20261018-001",
            "basis": "git commit ancestry; earlier date",
        }
        records = [
            {"event_id": "EVT-AGMS-20261018-001", "relations": []},
            {"event_id": "EVT-AGMS-20261018-002", "relations": [old_edge]},
            {
                "event_id": "EVT-AGMS-20261018-003",
                "relations": [{
                    "type": "preceded_by",
                    "event_id": "EVT-AGMS-20261018-002",
                    "basis": "git commit ancestry",
                }],
                "edge_corrections": [{
                    "record_id": "EVT-AGMS-20261018-002",
                    "field": "relations",
                    "old_relation": old_edge,
                    "corrected_relation": corrected_edge,
                }],
            },
        ]
        errors = validate_temporal_relations(
            records,
            {
                "EVT-AGMS-20261018-001": 1,
                "EVT-AGMS-20261018-002": 2,
                "EVT-AGMS-20261018-003": 3,
            },
        )
        self.assertEqual(errors, [])
        # Validation applies overlays to an in-memory projection only.
        self.assertEqual(records[1]["relations"], [old_edge])
        self.assertEqual(records[2]["edge_corrections"][0]["corrected_relation"], corrected_edge)

    def test_temporal_relation_validator_does_not_guess_missing_order(self):
        records = [
            {"event_id": "A", "relations": []},
            {"event_id": "B", "relations": [{"type": "preceded_by", "event_id": "A"}]},
        ]
        errors = validate_temporal_relations(records, {"B": 2})
        self.assertTrue(any("trusted chronology missing" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
