import json
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from resumable_chat_import import _commit_batch, connect, import_export, iter_json_array


def sample_conversations(count=5):
    rows = []
    for i in range(count):
        rows.append({
            "id": f"conversation-{i}",
            "title": f"Conversation {i}",
            "create_time": 1700000000 + i,
            "mapping": {
                f"node-{i}-user": {
                    "id": f"node-{i}-user",
                    "parent": None,
                    "children": [f"node-{i}-assistant"],
                    "message": {
                        "id": f"message-{i}-user",
                        "create_time": 1700000000 + i,
                        "author": {"role": "user"},
                        "content": {"content_type": "text", "parts": [f"question {i}"]},
                    },
                },
                f"node-{i}-assistant": {
                    "id": f"node-{i}-assistant",
                    "parent": f"node-{i}-user",
                    "children": [],
                    "message": {
                        "id": f"message-{i}-assistant",
                        "create_time": 1700000001 + i,
                        "author": {"role": "assistant"},
                        "content": {"content_type": "text", "parts": [f"answer {i}"]},
                    },
                },
            },
        })
    return rows


class ResumableChatImportTests(unittest.TestCase):
    def make_source(self, folder, count=5):
        source = folder / "conversations.json"
        source.write_text(json.dumps(sample_conversations(count), ensure_ascii=False), encoding="utf-8")
        return source

    def query_counts(self, out):
        conn = sqlite3.connect(out / "import.sqlite3")
        try:
            records = conn.execute("SELECT COUNT(*), COUNT(DISTINCT source_locator) FROM raw_conversations").fetchone()
            events = conn.execute("SELECT event_type FROM import_events ORDER BY event_id").fetchall()
            payloads = conn.execute("SELECT payload_json FROM raw_conversations ORDER BY source_ordinal").fetchall()
            state = conn.execute("SELECT status,next_ordinal,committed_conversations FROM imports").fetchone()
            return records, [row[0] for row in events], [json.loads(row[0]) for row in payloads], state
        finally:
            conn.close()

    def test_interrupt_and_resume_keeps_all_conversations(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self.make_source(root, 5)
            out = root / "state"
            paused = import_export(source, out, "ARCHIVE-001", batch_size=2, stop_after_batches=1)
            self.assertEqual(paused["status"], "PAUSED")
            self.assertEqual(paused["next_ordinal"], 2)
            self.assertGreater(paused["next_byte_offset"], 0)
            with patch("resumable_chat_import.iter_json_array", wraps=iter_json_array) as parser:
                done = import_export(source, out, "ARCHIVE-001", batch_size=2)
                self.assertEqual(parser.call_args.kwargs["start_offset"], paused["next_byte_offset"])
                self.assertEqual(parser.call_args.kwargs["start_ordinal"], 2)
            self.assertEqual(done["status"], "RAW_COMPLETE")
            self.assertEqual(done["committed_conversations"], 5)
            counts, events, payloads, state = self.query_counts(out)
            self.assertEqual(counts, (5, 5))
            self.assertIn("PAUSED_FOR_TEST", events)
            self.assertEqual([p["id"] for p in payloads], [f"conversation-{i}" for i in range(5)])
            self.assertEqual(state, ("RAW_COMPLETE", 5, 5))


    def test_process_crash_mid_batch_rolls_back_uncommitted_rows_and_resumes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self.make_source(root, 5)
            out = root / "state"
            archive_id = "ARCHIVE-MID-BATCH-CRASH"
            paused = import_export(source, out, archive_id, batch_size=2, stop_after_batches=1)
            self.assertEqual(paused["status"], "PAUSED")
            self.assertEqual(paused["next_ordinal"], 2)

            database = out / "import.sqlite3"
            conn = sqlite3.connect(database)
            try:
                committed_before = conn.execute(
                    """SELECT source_locator,source_conversation_id,source_ordinal,
                              payload_json,payload_sha256,imported_at,source_end_byte_offset
                       FROM raw_conversations WHERE archive_id=? AND source_sha256=?
                       ORDER BY source_ordinal""",
                    (archive_id, paused["source_sha256"]),
                ).fetchall()
                events_before = conn.execute(
                    """SELECT event_id,event_type,ordinal,details_json,occurred_at
                       FROM import_events WHERE archive_id=? AND source_sha256=?
                       ORDER BY event_id""",
                    (archive_id, paused["source_sha256"]),
                ).fetchall()
            finally:
                conn.close()
            self.assertEqual(len(committed_before), 2)

            # The child exits abruptly after SQLite has executed the first
            # raw_conversations INSERT of the next batch, before that batch's
            # transaction can commit its rows and checkpoint.
            crash_script = r'''
import os
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, sys.argv[1])
import resumable_chat_import as importer

real_connect = sqlite3.connect

class CrashAfterFirstRawInsert(sqlite3.Connection):
    def execute(self, sql, parameters=()):
        cursor = super().execute(sql, parameters)
        if sql.lstrip().upper().startswith("INSERT INTO RAW_CONVERSATIONS"):
            os._exit(73)
        return cursor

def crash_connect(database, *args, **kwargs):
    kwargs["factory"] = CrashAfterFirstRawInsert
    return real_connect(database, *args, **kwargs)

sqlite3.connect = crash_connect
importer.import_export(Path(sys.argv[2]), Path(sys.argv[3]), sys.argv[4], batch_size=2)
'''
            crashed = subprocess.run(
                [sys.executable, "-c", crash_script, str(ROOT / "tools"),
                 str(source), str(out), archive_id],
                capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(crashed.returncode, 73, crashed.stderr)

            conn = sqlite3.connect(database)
            try:
                after_crash = conn.execute(
                    """SELECT source_locator,source_conversation_id,source_ordinal,
                              payload_json,payload_sha256,imported_at,source_end_byte_offset
                       FROM raw_conversations WHERE archive_id=? AND source_sha256=?
                       ORDER BY source_ordinal""",
                    (archive_id, paused["source_sha256"]),
                ).fetchall()
                events_after_crash = conn.execute(
                    """SELECT event_id,event_type,ordinal,details_json,occurred_at
                       FROM import_events WHERE archive_id=? AND source_sha256=?
                       ORDER BY event_id""",
                    (archive_id, paused["source_sha256"]),
                ).fetchall()
                checkpoint_after_crash = conn.execute(
                    """SELECT status,next_ordinal,next_byte_offset,last_source_locator,
                              committed_conversations
                       FROM imports WHERE archive_id=? AND source_sha256=?""",
                    (archive_id, paused["source_sha256"]),
                ).fetchone()
            finally:
                conn.close()

            # The already committed prefix and its event history remain exact.
            self.assertEqual(after_crash[:2], committed_before)
            self.assertEqual(events_after_crash[:len(events_before)], events_before)
            # The partial second batch was rolled back; cursor did not advance.
            self.assertEqual(len(after_crash), 2)
            self.assertEqual(checkpoint_after_crash[1], 2)
            self.assertEqual(checkpoint_after_crash[4], 2)

            done = import_export(source, out, archive_id, batch_size=2)
            self.assertEqual(done["status"], "RAW_COMPLETE")
            self.assertEqual(done["committed_conversations"], 5)

            conn = sqlite3.connect(database)
            try:
                final_records = conn.execute(
                    """SELECT source_ordinal,payload_sha256,imported_at
                       FROM raw_conversations WHERE archive_id=? AND source_sha256=?
                       ORDER BY source_ordinal""",
                    (archive_id, paused["source_sha256"]),
                ).fetchall()
                final_events = conn.execute(
                    """SELECT event_type FROM import_events
                       WHERE archive_id=? AND source_sha256=? ORDER BY event_id""",
                    (archive_id, paused["source_sha256"]),
                ).fetchall()
                final_state = conn.execute(
                    """SELECT status,next_ordinal,committed_conversations
                       FROM imports WHERE archive_id=? AND source_sha256=?""",
                    (archive_id, paused["source_sha256"]),
                ).fetchone()
            finally:
                conn.close()

            self.assertEqual([row[0] for row in final_records], list(range(5)))
            self.assertEqual(len({row[0] for row in final_records}), 5)
            self.assertEqual(final_records[:2], [
                (row[2], row[4], row[5]) for row in committed_before
            ])
            self.assertEqual(final_state, ("RAW_COMPLETE", 5, 5))
            self.assertEqual([row[0] for row in final_events].count("RAW_COMPLETE"), 1)

    def test_rerun_is_idempotent_and_preserves_original_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self.make_source(root, 3)
            original = source.read_bytes()
            out = root / "state"
            first = import_export(source, out, "ARCHIVE-002", batch_size=2)
            second = import_export(source, out, "ARCHIVE-002", batch_size=2)
            self.assertEqual(first["source_sha256"], second["source_sha256"])
            self.assertEqual(second["committed_conversations"], 3)
            self.assertEqual(source.read_bytes(), original)
            self.assertEqual(Path(second["snapshot_path"]).read_bytes(), original)
            counts, _, _, _ = self.query_counts(out)
            self.assertEqual(counts, (3, 3))

    def test_zip_input_is_supported_and_nested_message_structure_is_not_summarized(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "export.zip"
            payload = sample_conversations(2)
            with zipfile.ZipFile(source, "w") as archive:
                archive.writestr("account/conversations.json", json.dumps(payload, ensure_ascii=False))
            result = import_export(source, root / "state", "ARCHIVE-003", batch_size=1)
            self.assertEqual(result["status"], "RAW_COMPLETE")
            _, _, staged, _ = self.query_counts(root / "state")
            self.assertEqual(staged[0]["mapping"]["node-0-user"]["message"]["content"]["parts"], ["question 0"])
            self.assertEqual(staged[0]["mapping"]["node-0-user"]["children"], ["node-0-assistant"])

    def test_zip_resume_seeks_within_conversations_member(self):
        with tempfile.TemporaryDirectory() as tmp:            root = Path(tmp)
            source = root / "export.zip"
            rows = sample_conversations(4)
            with zipfile.ZipFile(source, "w") as archive:
                archive.writestr("account/conversations.json", json.dumps(rows, ensure_ascii=False))
            out = root / "state"
            paused = import_export(source, out, "ARCHIVE-ZIP-RESUME", batch_size=1, stop_after_batches=1)
            self.assertEqual(paused["status"], "PAUSED")
            self.assertGreater(paused["next_byte_offset"], 0)
            done = import_export(source, out, "ARCHIVE-ZIP-RESUME", batch_size=1)
            self.assertEqual(done["status"], "RAW_COMPLETE")
            self.assertEqual(done["committed_conversations"], 4)

    def test_replayed_committed_batch_models_lost_ack_without_duplicate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self.make_source(root, 2)
            out = root / "state"
            paused = import_export(source, out, "ARCHIVE-005", batch_size=1, stop_after_batches=1)
            conn = connect(out / "import.sqlite3")
            try:
                record = conn.execute(
                    "SELECT archive_id,source_sha256,source_locator,source_conversation_id,identity_method,source_ordinal,payload_json,payload_sha256,imported_at,source_end_byte_offset FROM raw_conversations ORDER BY source_ordinal LIMIT 1"
                ).fetchone()
                _commit_batch(conn, "ARCHIVE-005", paused["source_sha256"], [record])
                count = conn.execute(
                    "SELECT COUNT(*) FROM raw_conversations WHERE archive_id=? AND source_sha256=?",
                    ("ARCHIVE-005", paused["source_sha256"]),
                ).fetchone()[0]
                self.assertEqual(count, 1)
                cursor = conn.execute(
                    "SELECT next_ordinal FROM imports WHERE archive_id=? AND source_sha256=?",
                    ("ARCHIVE-005", paused["source_sha256"]),
                ).fetchone()[0]
                self.assertEqual(cursor, 1)
            finally:
                conn.close()
            resumed = import_export(source, out, "ARCHIVE-005", batch_size=1)
            self.assertEqual(resumed["status"], "RAW_COMPLETE")
            self.assertEqual(resumed["committed_conversations"], 2)

    def test_duplicate_source_conversation_ids_are_not_silently_dropped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "conversations.json"
            rows = sample_conversations(2)
            rows[1]["id"] = rows[0]["id"]
            source.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
            with self.assertRaises(RuntimeError):
                import_export(source, root / "state", "ARCHIVE-006", batch_size=1)
            conn = sqlite3.connect(root / "state" / "import.sqlite3")
            try:
                state = conn.execute("SELECT status FROM imports").fetchone()[0]
                count = conn.execute("SELECT COUNT(*) FROM raw_conversations").fetchone()[0]
                self.assertEqual(state, "FAILED")
                self.assertEqual(count, 1)
            finally:
                conn.close()

    def test_incremental_decoder_handles_small_chunks_and_unicode(self):
        import io
        rows = [{"id": "один", "title": "Привет 🌍"}, {"id": "two", "title": "second"}]
        stream = io.BytesIO(json.dumps(rows, ensure_ascii=False).encode("utf-8"))
        parsed = list(iter_json_array(stream, chunk_size=5))
        self.assertEqual([ordinal for ordinal, _, _ in parsed], [0, 1])
        self.assertEqual(parsed[0][1]["title"], "Привет 🌍")
        self.assertGreater(parsed[0][2], 0)
        self.assertGreater(parsed[1][2], parsed[0][2])

    def test_invalid_source_is_not_marked_complete(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "bad.json"
            source.write_text('{"not":"an array"}', encoding="utf-8")
            with self.assertRaises(ValueError):
                import_export(source, root / "state", "ARCHIVE-004", batch_size=2)
            conn = sqlite3.connect(root / "state" / "import.sqlite3")
            try:
                state = conn.execute("SELECT status,last_error FROM imports").fetchone()
                self.assertEqual(state[0], "FAILED")
                self.assertTrue(state[1])
            finally:
                conn.close()


    def test_fresh_process_restarts_from_committed_checkpoint_without_rewriting_prefix(self):
        """A new OS process must resume only from the durable checkpoint."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self.make_source(root, 6)
            out = root / "state"
            archive_id = "FRESH-PROCESS-CHECKPOINT-001"

            partial = import_export(
                source, out, archive_id, batch_size=2, stop_after_batches=1
            )
            self.assertEqual(partial["status"], "PAUSED")
            self.assertEqual(partial["next_ordinal"], 2)
            self.assertGreater(partial["next_byte_offset"], 0)
            digest = partial["source_sha256"]
            database = out / "import.sqlite3"

            # Snapshot every committed row field and every event field before
            # the original importer call returns control to a fresh OS process.
            conn = sqlite3.connect(database)
            try:
                checkpoint_before = conn.execute(
                    """SELECT status,next_ordinal,next_byte_offset,last_source_locator,
                              committed_conversations,updated_at,last_error
                       FROM imports WHERE archive_id=? AND source_sha256=?""",
                    (archive_id, digest),
                ).fetchone()
                prefix_before = conn.execute(
                    """SELECT source_locator,source_conversation_id,identity_method,
                              source_ordinal,payload_json,payload_sha256,imported_at,
                              source_end_byte_offset
                       FROM raw_conversations WHERE archive_id=? AND source_sha256=?
                       ORDER BY source_ordinal""",
                    (archive_id, digest),
                ).fetchall()
                events_before = conn.execute(
                    """SELECT event_id,event_type,ordinal,details_json,occurred_at
                       FROM import_events WHERE archive_id=? AND source_sha256=?
                       ORDER BY event_id""",
                    (archive_id, digest),
                ).fetchall()
            finally:
                conn.close()

            self.assertEqual(checkpoint_before[0:5], (
                "PAUSED", 2, partial["next_byte_offset"],
                partial["last_source_locator"], 2,
            ))
            self.assertEqual(len(prefix_before), 2)

            # Invoke the actual CLI in a new interpreter process. It receives
            # no in-memory cursor from the first pass; only source/output/id.
            resumed_process = subprocess.run(
                [
                    sys.executable, str(ROOT / "tools" / "resumable_chat_import.py"),
                    str(source), "--out", str(out), "--archive-id", archive_id,
                    "--batch-size", "2",
                ],
                capture_output=True, text=True, timeout=60,
            )
            self.assertEqual(
                resumed_process.returncode, 0,
                msg=f"stdout={resumed_process.stdout} stderr={resumed_process.stderr}",
            )
            result = json.loads(resumed_process.stdout)
            self.assertEqual(result["run_mode"], "RESUME")
            self.assertEqual(result["status"], "RAW_COMPLETE")
            self.assertEqual(result["source_sha256"], digest)
            self.assertEqual(result["committed_conversations"], 6)
            self.assertEqual(result["next_ordinal"], 6)

            conn = sqlite3.connect(database)
            try:
                prefix_after = conn.execute(
                    """SELECT source_locator,source_conversation_id,identity_method,
                              source_ordinal,payload_json,payload_sha256,imported_at,
                              source_end_byte_offset
                       FROM raw_conversations WHERE archive_id=? AND source_sha256=?
                       ORDER BY source_ordinal LIMIT 2""",
                    (archive_id, digest),
                ).fetchall()
                events_after = conn.execute(
                    """SELECT event_id,event_type,ordinal,details_json,occurred_at
                       FROM import_events WHERE archive_id=? AND source_sha256=?
                       ORDER BY event_id""",
                    (archive_id, digest),
                ).fetchall()
                final_rows = conn.execute(
                    """SELECT source_ordinal,source_conversation_id,payload_sha256
                       FROM raw_conversations WHERE archive_id=? AND source_sha256=?
                       ORDER BY source_ordinal""",
                    (archive_id, digest),
                ).fetchall()
                final_checkpoint = conn.execute(
                    """SELECT status,next_ordinal,next_byte_offset,last_source_locator,
                              committed_conversations
                       FROM imports WHERE archive_id=? AND source_sha256=?""",
                    (archive_id, digest),
                ).fetchone()
            finally:
                conn.close()

            self.assertEqual(prefix_after, prefix_before)
            self.assertEqual(events_after[:len(events_before)], events_before)
            self.assertEqual([row[0] for row in final_rows], list(range(6)))
            self.assertEqual([row[1] for row in final_rows],
                             [f"conversation-{i}" for i in range(6)])
            self.assertEqual(len({row[2] for row in final_rows}), 6)
            self.assertEqual(final_checkpoint, (
                "RAW_COMPLETE", 6, result["next_byte_offset"],
                result["last_source_locator"], 6,
            ))

    def test_explicit_second_pass_resumes_from_last_confirmed_checkpoint(self):
        """A fresh second pass must use the persisted cursor, not agent/chat memory."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self.make_source(root, 6)
            out = root / "state"
            archive_id = "ACCEPTANCE-TWO-PASS-001"

            # Pass 1 is intentionally incomplete: stop only after a durable batch.
            partial = import_export(
                source, out, archive_id, batch_size=2, stop_after_batches=1
            )
            self.assertEqual(partial["status"], "PAUSED")
            self.assertEqual(partial["committed_conversations"], 2)
            self.assertEqual(partial["next_ordinal"], 2)
            self.assertGreater(partial["next_byte_offset"], 0)
            self.assertTrue(partial["last_source_locator"])
            source_digest = partial["source_sha256"]

            # Simulate a new agent/session: reconstruct the continuation point
            # only from durable SQLite state, then invoke the same import identity.
            conn = sqlite3.connect(out / "import.sqlite3")
            try:
                checkpoint = conn.execute(
                    """SELECT source_sha256,status,next_ordinal,next_byte_offset,
                              committed_conversations,last_source_locator
                       FROM imports WHERE archive_id=?""",
                    (archive_id,),
                ).fetchone()
                self.assertEqual(
                    checkpoint,
                    (
                        source_digest, "PAUSED", 2, partial["next_byte_offset"],
                        2, partial["last_source_locator"],
                    ),
                )
            finally:
                conn.close()

            resumed = import_export(source, out, archive_id, batch_size=2)
            self.assertEqual(resumed["status"], "RAW_COMPLETE")
            self.assertEqual(resumed["source_sha256"], source_digest)
            self.assertEqual(resumed["committed_conversations"], 6)
            self.assertEqual(resumed["next_ordinal"], 6)

            conn = sqlite3.connect(out / "import.sqlite3")
            try:
                rows = conn.execute(
                    """SELECT source_ordinal,source_conversation_id,payload_sha256
                       FROM raw_conversations
                       WHERE archive_id=? AND source_sha256=?
                       ORDER BY source_ordinal""",
                    (archive_id, source_digest),
                ).fetchall()
                events = [
                    row[0] for row in conn.execute(
                        """SELECT event_type FROM import_events
                           WHERE archive_id=? AND source_sha256=? ORDER BY event_id""",
                        (archive_id, source_digest),
                    )
                ]
                self.assertEqual([row[0] for row in rows], list(range(6)))
                self.assertEqual(
                    [row[1] for row in rows],
                    [f"conversation-{i}" for i in range(6)],
                )
                self.assertEqual(len({row[2] for row in rows}), 6)
                self.assertIn("PAUSED_FOR_TEST", events)
                self.assertIn("RESUME", events)
                self.assertEqual(
                    conn.execute(
                        """SELECT status,committed_conversations,next_ordinal
                           FROM imports WHERE archive_id=? AND source_sha256=?""",
                        (archive_id, source_digest),
                    ).fetchone(),
                    ("RAW_COMPLETE", 6, 6),
                )
            finally:
                conn.close()


    def test_truncated_source_is_never_marked_complete(self):
        """A partial export is not a paused import and cannot become RAW_COMPLETE."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rows = sample_conversations(2)
            # The first object is complete; the second object is deliberately truncated.
            partial_json = "[" + json.dumps(rows[0], ensure_ascii=False) + ', {"id":"conversation-1","title":'
            source = root / "truncated-conversations.json"
            source.write_text(partial_json, encoding="utf-8")
            out = root / "state"

            with self.assertRaises(ValueError):
                import_export(source, out, "TRUNCATED-EXPORT-001", batch_size=1)

            conn = sqlite3.connect(out / "import.sqlite3")
            try:
                state = conn.execute(
                    "SELECT status,last_error FROM imports WHERE archive_id=?",
                    ("TRUNCATED-EXPORT-001",),
                ).fetchone()
                events = [
                    row[0] for row in conn.execute(
                        "SELECT event_type FROM import_events WHERE archive_id=? ORDER BY event_id",
                        ("TRUNCATED-EXPORT-001",),
                    )
                ]
                rows_saved = conn.execute(
                    "SELECT source_ordinal,source_conversation_id FROM raw_conversations WHERE archive_id=? ORDER BY source_ordinal",
                    ("TRUNCATED-EXPORT-001",),
                ).fetchall()
                self.assertEqual(state[0], "FAILED")
                self.assertTrue(state[1])
                self.assertEqual(rows_saved, [(0, "conversation-0")])
                self.assertIn("FAILED", events)
                self.assertNotIn("RAW_COMPLETE", events)
            finally:
                conn.close()


    def test_first_pass_is_explicit_and_does_not_claim_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self.make_source(root, 3)
            out = root / "state"
            result = import_export(source, out, "INCIDENT-FIRST-PASS-001", batch_size=1)
            self.assertEqual(result["run_mode"], "FIRST_PASS")
            self.assertEqual(result["status"], "RAW_COMPLETE")
            conn = sqlite3.connect(out / "import.sqlite3")
            try:
                events = [
                    row[0] for row in conn.execute(
                        "SELECT event_type FROM import_events ORDER BY event_id"
                    )
                ]
                self.assertIn("FIRST_PASS_STARTED", events)
                self.assertNotIn("RESUME", events)
            finally:
                conn.close()

    def test_completed_exact_source_is_not_reimported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self.make_source(root, 3)
            out = root / "state"
            archive_id = "INCIDENT-COMPLETE-001"
            first = import_export(source, out, archive_id, batch_size=1)
            self.assertEqual(first["run_mode"], "FIRST_PASS")

            conn = sqlite3.connect(out / "import.sqlite3")
            try:
                records_before = conn.execute(
                    """SELECT source_locator,source_conversation_id,payload_sha256,
                              imported_at,source_end_byte_offset
                       FROM raw_conversations
                       WHERE archive_id=? AND source_sha256=?
                       ORDER BY source_ordinal""",
                    (archive_id, first["source_sha256"]),
                ).fetchall()
                events_before = conn.execute(
                    """SELECT event_id,event_type,ordinal,details_json,occurred_at
                       FROM import_events WHERE archive_id=? AND source_sha256=?
                       ORDER BY event_id""",
                    (archive_id, first["source_sha256"]),
                ).fetchall()                state_before = conn.execute(
                    """SELECT status,next_ordinal,next_byte_offset,last_source_locator,
                              committed_conversations,updated_at,last_error
                       FROM imports WHERE archive_id=? AND source_sha256=?""",
                    (archive_id, first["source_sha256"]),
                ).fetchone()
            finally:
                conn.close()

            second = import_export(source, out, archive_id, batch_size=1)
            self.assertEqual(second["run_mode"], "ALREADY_COMPLETE")
            self.assertEqual(second["status"], "RAW_COMPLETE")
            self.assertEqual(second["source_sha256"], first["source_sha256"])

            conn = sqlite3.connect(out / "import.sqlite3")
            try:
                records_after = conn.execute(
                    """SELECT source_locator,source_conversation_id,payload_sha256,
                              imported_at,source_end_byte_offset
                       FROM raw_conversations
                       WHERE archive_id=? AND source_sha256=?
                       ORDER BY source_ordinal""",
                    (archive_id, first["source_sha256"]),
                ).fetchall()
                events_after = conn.execute(
                    """SELECT event_id,event_type,ordinal,details_json,occurred_at
                       FROM import_events WHERE archive_id=? AND source_sha256=?
                       ORDER BY event_id""",
                    (archive_id, first["source_sha256"]),
                ).fetchall()
                state_after = conn.execute(
                    """SELECT status,next_ordinal,next_byte_offset,last_source_locator,
                              committed_conversations,updated_at,last_error
                       FROM imports WHERE archive_id=? AND source_sha256=?""",
                    (archive_id, first["source_sha256"]),
                ).fetchone()
                self.assertEqual(records_after, records_before)
                self.assertEqual(events_after, events_before)
                self.assertEqual(state_after, state_before)
                self.assertEqual(len(records_after), 3)
                self.assertEqual(len({row[0] for row in records_after}), 3)
                self.assertEqual([row[1] for row in events_after].count("FIRST_PASS_STARTED"), 1)
                self.assertEqual([row[1] for row in events_after].count("RAW_COMPLETE"), 1)
            finally:
                conn.close()


    def test_same_source_bytes_with_different_archive_ids_are_independent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self.make_source(root, 3)
            original_bytes = source.read_bytes()
            out = root / "state"

            # Archive A pauses after one committed conversation. Archive B uses
            # the exact same source bytes/digest but must have its own import row,
            # records, events, and checkpoint.
            first_a = import_export(
                source, out, "ARCHIVE-SAME-BYTES-A", batch_size=1,
                stop_after_batches=1,
            )
            self.assertEqual(first_a["status"], "PAUSED")
            self.assertEqual(first_a["next_ordinal"], 1)

            first_b = import_export(
                source, out, "ARCHIVE-SAME-BYTES-B", batch_size=1,
            )
            self.assertEqual(first_b["status"], "RAW_COMPLETE")
            self.assertEqual(first_b["run_mode"], "FIRST_PASS")
            self.assertEqual(first_a["source_sha256"], first_b["source_sha256"])
            self.assertEqual(source.read_bytes(), original_bytes)

            conn = sqlite3.connect(out / "import.sqlite3")
            try:
                import_rows = conn.execute(
                    """SELECT archive_id,source_sha256,status,next_ordinal,
                              committed_conversations,next_byte_offset,last_source_locator
                       FROM imports WHERE source_sha256=?
                       ORDER BY archive_id""",
                    (first_a["source_sha256"],),
                ).fetchall()
                self.assertEqual(len(import_rows), 2)
                by_archive = {row[0]: row[1:] for row in import_rows}
                self.assertEqual(
                    by_archive["ARCHIVE-SAME-BYTES-A"],
                    (first_a["source_sha256"], "PAUSED", 1, 1,
                     first_a["next_byte_offset"], first_a["last_source_locator"]),
                )
                self.assertEqual(
                    by_archive["ARCHIVE-SAME-BYTES-B"],
                    (first_b["source_sha256"], "RAW_COMPLETE", 3, 3,
                     first_b["next_byte_offset"], first_b["last_source_locator"]),
                )

                rows_a = conn.execute(
                    """SELECT source_locator,source_ordinal,payload_sha256
                       FROM raw_conversations WHERE archive_id=? AND source_sha256=?
                       ORDER BY source_ordinal""",
                    ("ARCHIVE-SAME-BYTES-A", first_a["source_sha256"]),
                ).fetchall()
                rows_b = conn.execute(
                    """SELECT source_locator,source_ordinal,payload_sha256
                       FROM raw_conversations WHERE archive_id=? AND source_sha256=?
                       ORDER BY source_ordinal""",
                    ("ARCHIVE-SAME-BYTES-B", first_b["source_sha256"]),
                ).fetchall()
                self.assertEqual([(r[1], r[2]) for r in rows_a], [(0, rows_b[0][2])])
                self.assertEqual([r[1] for r in rows_b], [0, 1, 2])
                self.assertTrue(all(r[0].startswith("ARCHIVE-SAME-BYTES-A/") for r in rows_a))
                self.assertTrue(all(r[0].startswith("ARCHIVE-SAME-BYTES-B/") for r in rows_b))
                self.assertTrue(set(r[0] for r in rows_a).isdisjoint(r[0] for r in rows_b))

                events_a_before_resume = conn.execute(
                    """SELECT event_type,ordinal,details_json
                       FROM import_events WHERE archive_id=? AND source_sha256=?
                       ORDER BY event_id""",
                    ("ARCHIVE-SAME-BYTES-A", first_a["source_sha256"]),
                ).fetchall()
                events_b = conn.execute(
                    """SELECT event_type,ordinal,details_json
                       FROM import_events WHERE archive_id=? AND source_sha256=?
                       ORDER BY event_id""",
                    ("ARCHIVE-SAME-BYTES-B", first_b["source_sha256"]),
                ).fetchall()
                self.assertIn("PAUSED_FOR_TEST", [row[0] for row in events_a_before_resume])
                self.assertIn("RAW_COMPLETE", [row[0] for row in events_b])
                self.assertNotIn("RAW_COMPLETE", [row[0] for row in events_a_before_resume])
                self.assertNotIn("PAUSED_FOR_TEST", [row[0] for row in events_b])
            finally:
                conn.close()

            resumed_a = import_export(source, out, "ARCHIVE-SAME-BYTES-A", batch_size=1)
            self.assertEqual(resumed_a["run_mode"], "RESUME")
            self.assertEqual(resumed_a["status"], "RAW_COMPLETE")
            self.assertEqual(resumed_a["source_sha256"], first_b["source_sha256"])

            conn = sqlite3.connect(out / "import.sqlite3")
            try:
                final_counts = conn.execute(
                    """SELECT archive_id,COUNT(*),COUNT(DISTINCT source_locator),
                              MIN(source_ordinal),MAX(source_ordinal)
                       FROM raw_conversations WHERE source_sha256=?
                       GROUP BY archive_id ORDER BY archive_id""",
                    (first_a["source_sha256"],),
                ).fetchall()
                self.assertEqual(
                    final_counts,
                    [
                        ("ARCHIVE-SAME-BYTES-A", 3, 3, 0, 2),
                        ("ARCHIVE-SAME-BYTES-B", 3, 3, 0, 2),
                    ],
                )
                events_by_archive = {
                    archive_id: [row[0] for row in conn.execute(
                        """SELECT event_type FROM import_events
                           WHERE archive_id=? AND source_sha256=? ORDER BY event_id""",
                        (archive_id, first_a["source_sha256"]),
                    ).fetchall()]
                    for archive_id in ("ARCHIVE-SAME-BYTES-A", "ARCHIVE-SAME-BYTES-B")
                }
                self.assertEqual(events_by_archive["ARCHIVE-SAME-BYTES-A"].count("REGISTERED"), 1)
                self.assertEqual(events_by_archive["ARCHIVE-SAME-BYTES-B"].count("REGISTERED"), 1)
                self.assertIn("RESUME", events_by_archive["ARCHIVE-SAME-BYTES-A"])
                self.assertNotIn("RESUME", events_by_archive["ARCHIVE-SAME-BYTES-B"])
                self.assertIn("RAW_COMPLETE", events_by_archive["ARCHIVE-SAME-BYTES-A"])
                self.assertIn("RAW_COMPLETE", events_by_archive["ARCHIVE-SAME-BYTES-B"])
            finally:
                conn.close()


    def test_same_operation_with_changed_source_is_new_snapshot_not_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self.make_source(root, 2)
            out = root / "state"
            first = import_export(source, out, "INCIDENT-SNAPSHOT-001", batch_size=1)
            original_hash = first["source_sha256"]

            source.write_text(json.dumps(sample_conversations(3), ensure_ascii=False), encoding="utf-8")
            second = import_export(source, out, "INCIDENT-SNAPSHOT-001", batch_size=1)
            self.assertNotEqual(second["source_sha256"], original_hash)
            self.assertEqual(second["run_mode"], "NEW_SNAPSHOT")
            self.assertEqual(second["status"], "RAW_COMPLETE")

            conn = sqlite3.connect(out / "import.sqlite3")
            try:
                rows = conn.execute(
                    "SELECT source_sha256,status FROM imports WHERE archive_id=? ORDER BY source_bytes",
                    ("INCIDENT-SNAPSHOT-001",),
                ).fetchall()
                self.assertEqual(len(rows), 2)
                event_types = [
                    row[0] for row in conn.execute(
                        "SELECT event_type FROM import_events WHERE archive_id=? ORDER BY event_id",
                        ("INCIDENT-SNAPSHOT-001",),
                    )
                ]
                self.assertIn("FIRST_PASS_STARTED", event_types)
                self.assertIn("NEW_SNAPSHOT_STARTED", event_types)
                self.assertNotIn("RESUME", event_types)
            finally:
                conn.close()


    def test_two_concurrent_import_processes_are_serialized(self):
        import subprocess
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self.make_source(root, 8)
            out = root / "state"
            command = [
                sys.executable, str(ROOT / "tools" / "resumable_chat_import.py"),
                str(source), "--out", str(out), "--archive-id", "ARCHIVE-CONCURRENT",
                "--batch-size", "1",
            ]
            processes = [
                subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                for _ in range(2)
            ]
            results = []
            for process in processes:
                stdout, stderr = process.communicate(timeout=60)
                self.assertEqual(process.returncode, 0, msg=f"stdout={stdout} stderr={stderr}")
                results.append(json.loads(stdout))
            self.assertEqual({result["status"] for result in results}, {"RAW_COMPLETE"})
            conn = sqlite3.connect(out / "import.sqlite3")
            try:
                count, distinct_count = conn.execute(
                    "SELECT COUNT(*), COUNT(DISTINCT source_locator) FROM raw_conversations"
                ).fetchone()
                state = conn.execute(
                    "SELECT status,next_ordinal,committed_conversations FROM imports"
                ).fetchone()
                self.assertEqual((count, distinct_count), (8, 8))
                self.assertEqual(state, ("RAW_COMPLETE", 8, 8))
            finally:
                conn.close()


    def test_concurrent_same_source_recovers_after_lock_holder_crashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self.make_source(root, 6)
            out = root / "state"
            archive_id = "ARCHIVE-CONCURRENT-CRASH"
            paused = import_export(source, out, archive_id, batch_size=2, stop_after_batches=1)
            self.assertEqual(paused["status"], "PAUSED")
            database = out / "import.sqlite3"

            conn = sqlite3.connect(database)            try:
                prefix_before = conn.execute(
                    """SELECT source_locator,source_conversation_id,source_ordinal,
                              payload_json,payload_sha256,imported_at,source_end_byte_offset
                       FROM raw_conversations WHERE archive_id=? AND source_sha256=?
                       ORDER BY source_ordinal""",
                    (archive_id, paused["source_sha256"]),
                ).fetchall()
                events_before = conn.execute(
                    """SELECT event_id,event_type,ordinal,details_json,occurred_at
                       FROM import_events WHERE archive_id=? AND source_sha256=?
                       ORDER BY event_id""",
                    (archive_id, paused["source_sha256"]),
                ).fetchall()
            finally:
                conn.close()
            self.assertEqual(len(prefix_before), 2)

            ready = root / "crash-ready"
            release = root / "allow-crash"
            crash_script = r'''
import os
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, sys.argv[1])
import resumable_chat_import as importer

ready = Path(sys.argv[5])
release = Path(sys.argv[6])
real_connect = sqlite3.connect

class HoldThenCrashConnection(sqlite3.Connection):
    def execute(self, sql, parameters=()):
        cursor = super().execute(sql, parameters)
        if sql.lstrip().upper().startswith("INSERT INTO RAW_CONVERSATIONS"):
            ready.write_text("inserted-inside-uncommitted-batch", encoding="utf-8")
            deadline = time.monotonic() + 20
            while not release.exists() and time.monotonic() < deadline:
                time.sleep(0.01)
            os._exit(73)
        return cursor

def crash_connect(database, *args, **kwargs):
    kwargs["factory"] = HoldThenCrashConnection
    return real_connect(database, *args, **kwargs)

sqlite3.connect = crash_connect
importer.import_export(Path(sys.argv[2]), Path(sys.argv[3]), sys.argv[4], batch_size=2)
'''
            crashing = subprocess.Popen(
                [sys.executable, "-c", crash_script, str(ROOT / "tools"),
                 str(source), str(out), archive_id, str(ready), str(release)],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            )
            try:
                deadline = time.monotonic() + 10
                while not ready.exists() and crashing.poll() is None and time.monotonic() < deadline:
                    time.sleep(0.01)
                self.assertTrue(ready.exists(), "crash process did not reach the injected in-transaction point")

                # Start a cooperating importer while the first process still owns
                # the output-directory lock and has an uncommitted row.
                survivor = subprocess.Popen(
                    [sys.executable, str(ROOT / "tools" / "resumable_chat_import.py"),
                     str(source), "--out", str(out), "--archive-id", archive_id,
                     "--batch-size", "2"],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                )
                time.sleep(0.25)
                self.assertIsNone(survivor.poll(), "second importer unexpectedly exited while the lock holder was paused")
            finally:
                release.touch()
            crash_stdout, crash_stderr = crashing.communicate(timeout=30)
            self.assertEqual(crashing.returncode, 73, msg=f"stdout={crash_stdout} stderr={crash_stderr}")
            survivor_stdout, survivor_stderr = survivor.communicate(timeout=60)
            self.assertEqual(survivor.returncode, 0, msg=f"stdout={survivor_stdout} stderr={survivor_stderr}")
            self.assertEqual(json.loads(survivor_stdout)["status"], "RAW_COMPLETE")

            conn = sqlite3.connect(database)
            try:
                recovered_prefix = conn.execute(
                    """SELECT source_locator,source_conversation_id,source_ordinal,
                              payload_json,payload_sha256,imported_at,source_end_byte_offset
                       FROM raw_conversations WHERE archive_id=? AND source_sha256=?
                       ORDER BY source_ordinal""",
                    (archive_id, paused["source_sha256"]),
                ).fetchall()
                recovered_events = conn.execute(
                    """SELECT event_id,event_type,ordinal,details_json,occurred_at
                       FROM import_events WHERE archive_id=? AND source_sha256=?
                       ORDER BY event_id""",
                    (archive_id, paused["source_sha256"]),
                ).fetchall()
                recovered_state = conn.execute(
                    """SELECT status,next_ordinal,committed_conversations
                       FROM imports WHERE archive_id=? AND source_sha256=?""",
                    (archive_id, paused["source_sha256"]),
                ).fetchone()
            finally:
                conn.close()

            self.assertEqual(recovered_prefix[:2], prefix_before)
            self.assertEqual(len(recovered_prefix), 6)
            self.assertEqual([row[2] for row in recovered_prefix], list(range(6)))
            self.assertEqual(recovered_events[:len(events_before)], events_before)
            self.assertEqual(recovered_state, ("RAW_COMPLETE", 6, 6))

            # Same bytes under a different archive_id remain a separate logical source.
            other = import_export(source, out, "ARCHIVE-CONCURRENT-CRASH-OTHER", batch_size=2)
            self.assertEqual(other["status"], "RAW_COMPLETE")
            conn = sqlite3.connect(database)
            try:
                rows_by_archive = conn.execute(
                    """SELECT archive_id,COUNT(*),COUNT(DISTINCT source_locator)
                       FROM raw_conversations WHERE source_sha256=?
                       GROUP BY archive_id ORDER BY archive_id""",
                    (paused["source_sha256"],),
                ).fetchall()
                states_by_archive = conn.execute(
                    """SELECT archive_id,status,next_ordinal,committed_conversations
                       FROM imports WHERE source_sha256=? ORDER BY archive_id""",
                    (paused["source_sha256"],),
                ).fetchall()
            finally:
                conn.close()
            self.assertEqual(rows_by_archive, [
                ("ARCHIVE-CONCURRENT-CRASH", 6, 6),
                ("ARCHIVE-CONCURRENT-CRASH-OTHER", 6, 6),
            ])
            self.assertEqual(states_by_archive, [
                ("ARCHIVE-CONCURRENT-CRASH", "RAW_COMPLETE", 6, 6),
                ("ARCHIVE-CONCURRENT-CRASH-OTHER", "RAW_COMPLETE", 6, 6),
            ])


    def test_stale_replayed_batch_does_not_regress_checkpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self.make_source(root, 4)
            out = root / "state"
            done = import_export(source, out, "ARCHIVE-STALE-REPLAY", batch_size=1)
            conn = connect(out / "import.sqlite3")
            try:
                record = conn.execute(
                    """SELECT archive_id,source_sha256,source_locator,source_conversation_id,
                              identity_method,source_ordinal,payload_json,payload_sha256,
                              imported_at,source_end_byte_offset
                       FROM raw_conversations WHERE source_ordinal=0"""
                ).fetchone()
                before = conn.execute(
                    """SELECT next_ordinal,next_byte_offset,last_source_locator,committed_conversations
                       FROM imports WHERE archive_id=? AND source_sha256=?""",
                    ("ARCHIVE-STALE-REPLAY", done["source_sha256"]),
                ).fetchone()
                _commit_batch(conn, "ARCHIVE-STALE-REPLAY", done["source_sha256"], [record])
                after = conn.execute(
                    """SELECT next_ordinal,next_byte_offset,last_source_locator,committed_conversations
                       FROM imports WHERE archive_id=? AND source_sha256=?""",
                    ("ARCHIVE-STALE-REPLAY", done["source_sha256"]),
                ).fetchone()
                self.assertEqual(after, before)
                self.assertEqual(after[0], 4)
            finally:
                conn.close()


if __name__ == "__main__":
    unittest.main()