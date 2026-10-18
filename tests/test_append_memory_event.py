import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from append_memory_event import append_event_record


class AppendMemoryEventTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.journal = self.root / "events.jsonl"
        self.order = {"A": 1, "B": 2, "C": 3}

    def write_rows(self, rows):
        self.journal.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")

    def test_rejects_wrong_direction_without_changing_journal(self):
        rows = [
            {"event_id": "A", "relations": []},
            {"event_id": "B", "relations": [{"type": "preceded_by", "event_id": "A"}]},
        ]
        self.write_rows(rows)
        before = self.journal.read_bytes()
        bad = {"event_id": "C", "relations": [{"type": "followed_by", "event_id": "A"}]}
        with self.assertRaisesRegex(ValueError, "Temporal relation validation failed"):
            append_event_record(self.journal, bad, self.order)
        self.assertEqual(self.journal.read_bytes(), before)

    def test_appends_valid_event_after_full_graph_validation(self):
        rows = [
            {"event_id": "A", "relations": []},
            {"event_id": "B", "relations": [{"type": "preceded_by", "event_id": "A"}]},
        ]
        self.write_rows(rows)
        new = {"event_id": "C", "relations": [{"type": "preceded_by", "event_id": "B"}], "summary": "valid"}
        result = append_event_record(self.journal, new, self.order)
        self.assertEqual(result["status"], "APPENDED")
        self.assertEqual([row["event_id"] for row in [json.loads(line) for line in self.journal.read_text().splitlines()]], ["A", "B", "C"])
        self.assertEqual(json.loads(self.journal.read_text().splitlines()[-1]), new)

    def test_duplicate_event_id_is_rejected(self):
        self.write_rows([{"event_id": "A", "relations": []}])
        before = self.journal.read_bytes()
        with self.assertRaisesRegex(ValueError, "event_id already exists"):
            append_event_record(self.journal, {"event_id": "A", "relations": []}, self.order)
        self.assertEqual(self.journal.read_bytes(), before)

    def test_correction_overlay_is_applied_before_validating_old_edge(self):
        old_edge = {"type": "followed_by", "event_id": "A", "basis": "verified ancestry"}
        corrected = {"type": "preceded_by", "event_id": "A", "basis": "verified ancestry"}
        rows = [
            {"event_id": "A", "relations": []},
            {"event_id": "B", "relations": [old_edge]},
            {
                "event_id": "C",
                "relations": [{"type": "preceded_by", "event_id": "B"}],
                "edge_corrections": [{
                    "record_id": "B", "field": "relations",
                    "old_relation": old_edge, "corrected_relation": corrected,
                }],
            },
        ]
        # Historical source row stays incorrect; the append-only overlay supplies the correction.
        self.write_rows(rows[:2])
        result = append_event_record(self.journal, rows[2], self.order)
        self.assertEqual(result["status"], "APPENDED")
        stored = [json.loads(line) for line in self.journal.read_text().splitlines()]
        self.assertEqual(stored[1]["relations"], [old_edge])
        self.assertEqual(stored[2]["edge_corrections"][0]["corrected_relation"], corrected)

    def test_missing_trusted_order_fails_closed(self):
        self.write_rows([{"event_id": "A", "relations": []}])
        before = self.journal.read_bytes()
        with self.assertRaisesRegex(ValueError, "trusted chronology missing"):
            append_event_record(self.journal, {"event_id": "B", "relations": [{"type": "preceded_by", "event_id": "A"}]}, {})
        self.assertEqual(self.journal.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
