import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from validate_event_journal import validate_event_journal


class ValidateEventJournalTests(unittest.TestCase):
    def test_reports_missing_trusted_order_without_mutating_journal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            journal = root / "events.jsonl"
            order_file = root / "trusted-order.json"
            journal.write_text(
                json.dumps({"event_id": "A", "relations": []}) + "\n" +
                json.dumps({"event_id": "B", "relations": [{"type": "preceded_by", "event_id": "A"}]}) + "\n",
                encoding="utf-8",
            )
            order_file.write_text(json.dumps({"B": 2}), encoding="utf-8")
            before = journal.read_bytes()
            report = validate_event_journal(journal, order_file)
            self.assertEqual(report["status"], "NEEDS_RECONCILIATION")
            self.assertFalse(report["writes_performed"])
            self.assertTrue(any("trusted chronology missing" in error for error in report["errors"]))
            self.assertEqual(journal.read_bytes(), before)

    def test_passes_when_explicit_order_proves_direction(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            journal = root / "events.jsonl"
            order_file = root / "trusted-order.json"
            journal.write_text(
                json.dumps({"event_id": "A", "relations": []}) + "\n" +
                json.dumps({"event_id": "B", "relations": [{"type": "preceded_by", "event_id": "A"}]}) + "\n",
                encoding="utf-8",
            )
            order_file.write_text(json.dumps({"A": 1, "B": 2}), encoding="utf-8")
            report = validate_event_journal(journal, order_file)
            self.assertEqual(report["status"], "PASS")
            self.assertEqual(report["errors"], [])
            self.assertEqual(report["temporal_edge_count"], 1)


if __name__ == "__main__":
    unittest.main()
