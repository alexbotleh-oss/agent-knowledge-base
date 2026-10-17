import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import dialogue_window as memory


def msg(sequence, role, conversation, turn, text, *, project="PROJECT-A",
        message_id=None, event_id=None, attachments=None):
    return {
        "schema": memory.SCHEMA,
        "event_id": event_id or f"E-{sequence}",
        "message_id": message_id or f"M-{sequence}",
        "sequence": sequence,
        "conversation_id": conversation,
        "turn_id": turn,
        "project_id": project,
        "role": role,
        "text": text,
        "source_time": None,
        "attachments": attachments or [],
    }


def pair(sequence, conversation, turn, *, project="PROJECT-A"):
    return [
        msg(sequence, "user", conversation, turn, f"user {turn}", project=project),
        msg(sequence + 1, "assistant", conversation, turn, f"assistant {turn}", project=project),
    ]


class DialogueWindowTests(unittest.TestCase):
    def test_rollover_keeps_last_five_pairs_and_reports_older_source_retained(self):
        events = []
        for i in range(6):
            events.extend(pair(i * 2 + 1, "chat-A", f"T{i}"))
        packet = memory.build_windows(events, "chat-A")
        self.assertEqual([p["turn_id"] for p in packet["global_recent_pairs"]],
                         ["T1", "T2", "T3", "T4", "T5"])
        self.assertEqual(packet["evicted_from_windows_but_retained_in_source"], 1)
        self.assertEqual(packet["source_event_count"], 12)

    def test_global_and_current_chat_windows_are_independent(self):
        events = pair(1, "chat-A", "A1") + pair(3, "chat-B", "B1") + pair(5, "chat-A", "A2")
        packet = memory.build_windows(events, "chat-A")
        self.assertEqual([p["turn_id"] for p in packet["global_recent_pairs"]], ["A1", "B1", "A2"])
        self.assertEqual([p["turn_id"] for p in packet["current_chat_recent_pairs"]], ["A1", "A2"])
        self.assertTrue(all(p["conversation_id"] == "chat-A"
                            for p in packet["current_chat_recent_pairs"]))

    def test_incomplete_user_turn_survives_as_pending_not_fake_complete_pair(self):
        events = pair(1, "chat-A", "T1")
        events.append(msg(3, "user", "chat-B", "T2", "unfinished", attachments=[{
            "attachment_id": "ATT-7", "library_ref": "project-library://ATT-7",
            "access_status": "UNKNOWN"
        }]))
        packet = memory.build_windows(events, "chat-B")
        self.assertEqual(len(packet["global_recent_pairs"]), 1)
        self.assertEqual(packet["status"], "PARTIAL")
        self.assertEqual(packet["current_chat_pending_turns"][0]["turn_id"], "T2")
        self.assertEqual(packet["current_chat_pending_turns"][0]["present_message"]["attachments"][0]["library_ref"],
                         "project-library://ATT-7")

    def test_attachment_payload_is_rejected_and_only_library_reference_is_kept(self):
        events = pair(1, "chat-A", "T1")
        events[0]["attachments"] = [{
            "attachment_id": "ATT-1", "library_ref": "library://ATT-1",
            "payload": "file bytes should never be copied here"
        }]
        with self.assertRaisesRegex(ValueError, "payload is forbidden"):
            memory.build_windows(events, "chat-A")

    def test_conflicting_duplicate_message_id_fails_closed(self):
        events = pair(1, "chat-A", "T1")
        duplicate = dict(events[0], event_id="E-duplicate", sequence=3, text="tampered")
        events.append(duplicate)
        with self.assertRaisesRegex(ValueError, "message_id collision"):
            memory.build_windows(events, "chat-A")

    def test_same_turn_cannot_cross_project_boundary(self):
        events = pair(1, "chat-A", "T1", project="PROJECT-A")
        events[1]["project_id"] = "PROJECT-B"
        with self.assertRaisesRegex(ValueError, "project boundary conflict"):
            memory.build_windows(events, "chat-A")

    def test_self_check_detects_wrong_chat_in_current_window(self):
        packet = memory.build_windows(pair(1, "chat-A", "T1"), "chat-A")
        packet["current_chat_recent_pairs"][0]["conversation_id"] = "chat-B"
        result = memory.verify_windows(packet, "chat-A")
        self.assertEqual(result["status"], "BLOCKED")
        self.assertTrue(any("another conversation" in e for e in result["errors"]))

    def test_exact_event_replay_is_idempotent_but_changed_event_id_is_conflict(self):
        events = pair(1, "chat-A", "T1")
        replayed = events + [dict(events[0])]
        packet = memory.build_windows(replayed, "chat-A")
        self.assertEqual(packet["source_event_count"], 2)
        changed = dict(events[0], text="changed")
        with self.assertRaisesRegex(ValueError, "event_id collision"):
            memory.build_windows(events + [changed], "chat-A")


if __name__ == "__main__":
    unittest.main()
