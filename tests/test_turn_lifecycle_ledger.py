import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import turn_lifecycle_ledger as ledger


class TurnLifecycleLedgerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.path = self.root / "private" / "turns.jsonl"

    def tearDown(self):
        self.tmp.cleanup()

    def receive(self, turn_id="T-001", text="продолжай дальше"):
        return ledger.record(
            self.path, "TURN_RECEIVED", turn_id,
            task_id="TASK-1", user_text=text, user_text_sha256=ledger.digest(text),
            previous_checkpoint="CKPT-001",
        )

    def test_exact_input_and_checkpoint_survive_restart_inspection(self):
        self.receive()
        result = ledger.inspect(self.path)
        self.assertEqual(result["incomplete_turn_ids"], ["T-001"])
        turn = result["turns"][0]
        self.assertEqual(turn["exact_user_text"], "продолжай дальше")
        self.assertEqual(turn["previous_checkpoint"], "CKPT-001")
        self.assertEqual(turn["state"], "AWAITING_START")

    def test_interrupted_work_without_report_is_detected(self):
        self.receive()
        ledger.record(self.path, "WORK_STARTED", "T-001")
        ledger.record(self.path, "PROGRESS", "T-001", detail="wrote candidate file")
        turn = ledger.inspect(self.path)["turns"][0]
        self.assertEqual(turn["state"], "IN_PROGRESS")
        self.assertEqual(turn["progress"], ["wrote candidate file"])
        self.assertIn("T-001", ledger.inspect(self.path)["incomplete_turn_ids"])

    def test_prepared_report_is_not_mistaken_for_delivered_report(self):
        self.receive()
        ledger.record(self.path, "WORK_STARTED", "T-001")
        ledger.record(self.path, "REPORT_PREPARED", "T-001", report={"path": "report.md", "sha256": "abc"})
        turn = ledger.inspect(self.path)["turns"][0]
        self.assertEqual(turn["state"], "REPORT_PREPARED_UNCONFIRMED")
        self.assertIn("T-001", ledger.inspect(self.path)["incomplete_turn_ids"])

    def test_delivery_ack_closes_turn(self):
        self.receive()
        ledger.record(self.path, "WORK_STARTED", "T-001")
        ledger.record(self.path, "RESPONSE_SUBMITTED", "T-001", submission={"reference": "host-ref"})
        ledger.record(self.path, "DELIVERY_ACKNOWLEDGED", "T-001", delivery={"reference": "ack-ref"})
        result = ledger.inspect(self.path)
        self.assertEqual(result["turns"][0]["state"], "CLOSED_DELIVERED")
        self.assertEqual(result["incomplete_turn_ids"], [])

    def test_receive_replay_is_idempotent_and_changed_text_conflicts(self):
        first = self.receive()
        replay = self.receive()
        self.assertEqual(first["status"], "APPENDED")
        self.assertEqual(replay["status"], "ALREADY_REGISTERED")
        with self.assertRaisesRegex(ValueError, "collision"):
            self.receive(text="другая команда")

    def test_lifecycle_event_replay_is_idempotent_after_lost_acknowledgement(self):
        self.receive()
        first = ledger.record(self.path, "WORK_STARTED", "T-001")
        replay = ledger.record(self.path, "WORK_STARTED", "T-001")
        self.assertEqual(first["status"], "APPENDED")
        self.assertEqual(replay["status"], "ALREADY_RECORDED")
        self.assertEqual(len(ledger.read_events(self.path)), 2)

    def test_receipt_replay_with_changed_checkpoint_conflicts(self):
        self.receive()
        with self.assertRaisesRegex(ValueError, "collision"):
            ledger.record(
                self.path, "TURN_RECEIVED", "T-001",
                task_id="TASK-1", user_text="продолжай дальше",
                user_text_sha256=ledger.digest("продолжай дальше"),
                previous_checkpoint="CKPT-STALE",
            )

    def test_event_for_unknown_turn_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "unknown turn_id"):
            ledger.record(self.path, "WORK_STARTED", "missing")

    def test_terminal_turn_rejects_late_events(self):
        self.receive()
        ledger.record(self.path, "TURN_FAILED", "T-001", detail="interrupted")
        with self.assertRaisesRegex(ValueError, "terminal"):
            ledger.record(self.path, "WORK_STARTED", "T-001")

    def test_corrupt_journal_fails_closed(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text('{"schema":"bad"}\n', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "invalid ledger event"):
            ledger.inspect(self.path)

    def test_artifact_scan_finds_empty_and_partial_files_but_marks_unknown_owner(self):
        empty = self.root / "workspace" / "empty.txt"
        partial = self.root / "workspace" / "draft.md.partial"
        empty.parent.mkdir()
        empty.write_bytes(b"")
        partial.write_text("half written", encoding="utf-8")
        findings = ledger.scan_artifacts([empty.parent])
        by_path = {Path(item["path"]).name: item for item in findings}
        self.assertIn("empty.txt", by_path)
        self.assertIn("draft.md.partial", by_path)
        self.assertEqual(by_path["empty.txt"]["ownership"], "UNKNOWN_REQUIRES_CORRELATION")
        self.assertIn("empty_file", by_path["empty.txt"]["signals"])


if __name__ == "__main__":
    unittest.main()
