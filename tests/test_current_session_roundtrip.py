"""Round-trip regression test based on the visible current-session timeline.

This is a reconstructed/redacted fixture, NOT a native export of the live chat.
It tests whether the importer preserves ordering, parent/child links, roles,
message IDs, and raw payload fields without semantic rewriting.
"""
import hashlib
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from resumable_chat_import import import_export


def visible_session_fixture():
    # Short, non-verbatim summaries avoid copying the private conversation into
    # the repository while preserving the specific chronology under test.
    summaries = [
        ("u-1", "user", "Defer repository visibility change; continue current task."),
        ("a-1", "assistant", "Confirm deferral and return to memory-intake pipeline."),
        ("a-2", "assistant", "Inspect repository state and identify compatibility gaps."),
        ("u-2", "user", "Ask whether the agent records its own history and request a round-trip test."),
        ("a-3", "assistant", "Clarify that checkpoints were manually written, not automatically recorded."),
        ("a-4", "assistant", "Begin self-history audit; distinguish native export from reconstructed fixture."),
    ]
    mapping = {}
    previous = None
    ids = [item[0] for item in summaries]
    for index, (message_id, role, text) in enumerate(summaries):
        node_id = f"node-{message_id}"
        parent = f"node-{previous}" if previous else None
        child = f"node-{ids[index + 1]}" if index + 1 < len(ids) else None
        mapping[node_id] = {
            "id": node_id,
            "parent": parent,
            "children": [child] if child else [],
            "message": {
                "id": message_id,
                "author": {"role": role},
                "content": {"content_type": "text", "parts": [text]},
            },
        }
        previous = message_id
    return {
        "id": "self-history-roundtrip-fixture-2026-10-14",
        "title": "Current-session self-history round-trip (redacted fixture)",
        "mapping": mapping,
        "metadata": {
            "source_fidelity": "reconstructed_visible_timeline",
            "native_live_chat_export_available": False,
            "timestamps": "unknown_not_invented",
        },
    }


class CurrentSessionRoundTripTests(unittest.TestCase):
    def test_visible_session_fixture_round_trips_without_losing_order_or_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "conversations.json"
            original = [visible_session_fixture()]
            source.write_text(json.dumps(original, ensure_ascii=False), encoding="utf-8")

            out = root / "state"
            first = import_export(source, out, "SELF-HISTORY-2026-10-14", batch_size=1)
            self.assertEqual(first["status"], "RAW_COMPLETE")
            self.assertEqual(first["committed_conversations"], 1)

            conn = sqlite3.connect(out / "import.sqlite3")
            try:
                row = conn.execute(
                    "SELECT source_ordinal,payload_json,payload_sha256 FROM raw_conversations ORDER BY source_ordinal"
                ).fetchone()
                self.assertIsNotNone(row)
                ordinal, payload_json, payload_hash = row
                restored = json.loads(payload_json)
                self.assertEqual(ordinal, 0)
                self.assertEqual(restored, original[0])
                self.assertEqual(
                    payload_hash,
                    hashlib.sha256(payload_json.encode("utf-8")).hexdigest(),
                )

                mapping = restored["mapping"]
                ordered_ids = [
                    mapping[f"node-{mid}"]["message"]["id"]
                    for mid, _, _ in [
                        ("u-1", "user", ""),
                        ("a-1", "assistant", ""),
                        ("a-2", "assistant", ""),
                        ("u-2", "user", ""),
                        ("a-3", "assistant", ""),
                        ("a-4", "assistant", ""),
                    ]
                ]
                self.assertEqual(ordered_ids, ["u-1", "a-1", "a-2", "u-2", "a-3", "a-4"])
                self.assertEqual(mapping["node-a-2"]["parent"], "node-a-1")
                self.assertEqual(mapping["node-u-2"]["parent"], "node-a-2")
                self.assertEqual(mapping["node-a-3"]["parent"], "node-u-2")
                self.assertEqual(mapping["node-u-2"]["message"]["author"]["role"], "user")
                self.assertEqual(mapping["node-a-3"]["message"]["author"]["role"], "assistant")
                self.assertEqual(restored["metadata"]["timestamps"], "unknown_not_invented")
            finally:
                conn.close()

            # Replay must not duplicate the conversation or alter the snapshot.
            second = import_export(source, out, "SELF-HISTORY-2026-10-14", batch_size=1)
            self.assertEqual(second["status"], "RAW_COMPLETE")
            conn = sqlite3.connect(out / "import.sqlite3")
            try:
                count = conn.execute("SELECT COUNT(*) FROM raw_conversations").fetchone()[0]
                self.assertEqual(count, 1)
            finally:
                conn.close()


if __name__ == "__main__":
    unittest.main()
