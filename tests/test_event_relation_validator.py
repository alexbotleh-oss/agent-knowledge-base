import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from event_relation_validator import audit_event_log, validate_event_append


def event(event_id, relation=None, event_time="2026-10-17", precision="day"):
    return {
        "event_id": event_id,
        "event_time": event_time,
        "time_precision": precision,
        "relations": [relation] if relation else [],
    }


def correction_event():
    targets = [
        ("EVT-AGMS-20261016-003", "EVT-AGMS-20261016-002", "implementation following pipeline audit"),
        ("EVT-AGMS-20261016-004", "EVT-AGMS-20261016-003", "index and restore layers build on semantic promotion"),
        ("EVT-AGMS-20261016-005", "EVT-AGMS-20261016-004", "exact-head validation after semantic-memory restore integration"),
        ("EVT-AGMS-20261016-006", "EVT-AGMS-20261016-005", "correction overlay implementation after index/restore integration"),
        ("EVT-AGMS-20261016-007", "EVT-AGMS-20261016-006", "chronological append after latest recorded event; supersedes stale open-item status without deleting history"),
        ("EVT-AGMS-20261016-008", "EVT-AGMS-20261016-007", "subsequent checkpoint reconciliation preserves event chronology"),
    ]
    return {
        "event_id": "EVT-AGMS-20261017-007",
        "event_time": "2026-10-17",
        "time_precision": "day",
        "relations": [{
            "type": "preceded_by",
            "event_id": "EVT-AGMS-20261017-005",
            "basis": "append-only correction follows remote source discovery integration",
        }],
        "edge_corrections": [{
            "record_id": record_id,
            "field": "relations",
            "old_relation": {"type": "followed_by", "event_id": target_id, "basis": basis},
            "corrected_relation": {"type": "preceded_by", "event_id": target_id, "basis": basis},
        } for record_id, target_id, basis in targets],
    }


class EventRelationValidatorTests(unittest.TestCase):
    def test_followed_by_to_an_earlier_same_day_event_is_rejected(self):
        prior = event("EVT-1")
        candidate = event("EVT-2", {"type": "followed_by", "event_id": "EVT-1", "basis": "append order"})
        result = validate_event_append(candidate, [prior])
        self.assertEqual(result["status"], "REJECTED")
        self.assertEqual(result["issues"][0]["code"], "TEMPORAL_DIRECTION_CONTRADICTS_APPEND_ORDER")

    def test_preceded_by_to_an_earlier_event_is_accepted(self):
        prior = event("EVT-1")
        candidate = event("EVT-2", {"type": "preceded_by", "event_id": "EVT-1", "basis": "append order"})
        self.assertEqual(validate_event_append(candidate, [prior])["status"], "PASS")

    def test_explicit_timestamps_allow_a_historical_backfill(self):
        target = event("EVT-LATER", event_time="2026-10-18T10:00:00Z", precision="timestamp")
        backfilled = event(
            "EVT-BACKFILLED",
            {"type": "followed_by", "event_id": "EVT-LATER", "basis": "source timestamp"},
            event_time="2026-10-17T10:00:00Z", precision="timestamp",
        )
        self.assertEqual(validate_event_append(backfilled, [target])["status"], "PASS")

    def test_missing_temporal_target_requires_review_not_global_absence(self):
        candidate = event("EVT-2", {"type": "preceded_by", "event_id": "EVT-UNKNOWN", "basis": "unknown"})
        result = validate_event_append(candidate, [event("EVT-1")])
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertEqual(result["issues"][0]["code"], "TEMPORAL_TARGET_NOT_FOUND_IN_CURRENT_LOG")

    def test_correction_overlay_repairs_existing_relation_without_rewriting_event(self):
        prior = event("EVT-1")
        bad = event("EVT-2", {"type": "followed_by", "event_id": "EVT-1", "basis": "same-day append"})
        correction = {
            **event("EVT-3", {"type": "preceded_by", "event_id": "EVT-2", "basis": "correction chronology"}),
            "edge_corrections": [{
                "record_id": "EVT-2", "field": "relations",
                "old_relation": {"type": "followed_by", "event_id": "EVT-1"},
                "corrected_relation": {"type": "preceded_by", "event_id": "EVT-1"},
            }],
        }
        result = audit_event_log([prior, bad, correction])
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(bad["relations"][0]["type"], "followed_by")

    def test_current_event_log_passes_after_append_only_correction_overlay(self):
        event_log = ROOT / "projects" / "AGENT_MEMORY_SYSTEM" / "events.jsonl"
        existing = [
            json.loads(line) for line in event_log.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        result = audit_event_log(existing)
        self.assertEqual(result["status"], "PASS", json.dumps(result, ensure_ascii=False, indent=2))
        self.assertEqual(result["issue_count"], 0)

    def test_appending_duplicate_correction_event_is_rejected(self):
        event_log = ROOT / "projects" / "AGENT_MEMORY_SYSTEM" / "events.jsonl"
        existing = [
            json.loads(line) for line in event_log.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        result = validate_event_append(correction_event(), existing)
        self.assertEqual(result["status"], "REJECTED")
        self.assertEqual(result["issues"][0]["code"], "DUPLICATE_EVENT_ID")

    def test_duplicate_event_id_is_rejected(self):
        prior = event("EVT-1")
        result = validate_event_append(event("EVT-1"), [prior])
        self.assertEqual(result["status"], "REJECTED")
        self.assertEqual(result["issues"][0]["code"], "DUPLICATE_EVENT_ID")


if __name__ == "__main__":
    unittest.main()
