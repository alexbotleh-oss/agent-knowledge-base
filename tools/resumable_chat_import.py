#!/usr/bin/env python3
"""Resumable, local-first ingestion of ChatGPT conversation exports.

The immutable source snapshot is retained separately. Conversation payloads are
staged as opaque JSON; this importer does not summarize, normalize, or merge them.
Only Python's standard library is required.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import BinaryIO, Iterator, Any

PARSER_VERSION = "resumable-chat-import-v1"
SCHEMA_VERSION = 1


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def immutable_snapshot(source: Path, output: Path) -> tuple[Path, str, int]:
    digest = sha256_file(source)
    size = source.stat().st_size
    snapshots = output / "snapshots"
    snapshots.mkdir(parents=True, exist_ok=True)
    suffix = source.suffix.lower() or ".bin"
    target = snapshots / f"{digest}{suffix}"
    if target.exists():
        if target.stat().st_size != size or sha256_file(target) != digest:
            raise RuntimeError(f"Existing snapshot failed integrity check: {target}")
    else:
        fd, temporary_name = tempfile.mkstemp(prefix=".snapshot-", dir=snapshots)
        os.close(fd)
        temporary = Path(temporary_name)
        try:
            shutil.copyfile(source, temporary)
            if temporary.stat().st_size != size or sha256_file(temporary) != digest:
                raise RuntimeError("Source changed while snapshot was being copied")
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)
    return target, digest, size


def iter_json_array(stream: BinaryIO, chunk_size: int = 65536, *, start_offset: int = 0, start_ordinal: int = 0) -> Iterator[tuple[int, dict[str, Any], int]]:
    """Yield (zero-based ordinal, object, byte offset after object) from a top-level JSON array.

    Uses incremental decoding so the full export is not loaded into RAM. A
    single conversation object is decoded at a time. The immutable source file
    is the byte-exact record of the original export.
    """
    import codecs

    decoder = json.JSONDecoder()
    utf8 = codecs.getincrementaldecoder("utf-8")()
    buffer = ""
    pos = 0
    eof = False
    base_byte_offset = start_offset
    if start_offset:
        stream.seek(start_offset)

    def refill() -> None:
        nonlocal buffer, pos, eof, base_byte_offset
        if pos:
            base_byte_offset += len(buffer[:pos].encode("utf-8"))
            buffer = buffer[pos:]
            pos = 0
        raw = stream.read(chunk_size)
        if raw:
            buffer += utf8.decode(raw, final=False)
        else:
            if not eof:
                buffer += utf8.decode(b"", final=True)
            eof = True

    def whitespace() -> None:
        nonlocal pos
        while True:
            while pos < len(buffer) and buffer[pos].isspace():
                pos += 1
            if pos < len(buffer) or eof:
                return
            refill()

    if start_offset:
        ordinal = start_ordinal
        expect_value = False  # Cursor points immediately after the last committed object.
    else:
        whitespace()
        while not buffer and not eof:
            refill()
            whitespace()
        if pos >= len(buffer) or buffer[pos] != "[":
            raise ValueError("Export root must be a JSON array")
        pos += 1
        ordinal = 0
        expect_value = True
    while True:
        whitespace()
        if pos >= len(buffer):
            if eof:
                raise ValueError("Unexpected end of file inside JSON array")
            refill()
            continue
        if buffer[pos] == "]":
            pos += 1
            whitespace()
            if pos < len(buffer) or not eof:
                while not eof:
                    refill()
                    whitespace()
                if pos < len(buffer):
                    raise ValueError("Unexpected data after JSON array")
            return
        if not expect_value:
            if buffer[pos] != ",":
                raise ValueError(f"Expected ',' between array items near item {ordinal}")
            pos += 1
            whitespace()
            if pos < len(buffer) and buffer[pos] == "]":
                raise ValueError("Trailing comma in JSON array")
        while True:
            try:
                item, end = decoder.raw_decode(buffer, pos)
                break
            except json.JSONDecodeError:
                if eof:
                    raise ValueError(f"Invalid or truncated JSON near item {ordinal}")
                refill()
        if not isinstance(item, dict):
            raise ValueError(f"Conversation at ordinal {ordinal} is not a JSON object")
        end_byte_offset = base_byte_offset + len(buffer[:end].encode("utf-8"))
        yield ordinal, item, end_byte_offset
        ordinal += 1
        pos = end
        expect_value = False


def conversation_id(item: dict[str, Any], ordinal: int) -> tuple[str, str]:
    value = item.get("id") or item.get("conversation_id")
    if value is not None and str(value).strip():
        return str(value), "source_id"
    # Fallback is explicitly scoped to this immutable snapshot and ordinal.
    canonical = json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"ordinal-{ordinal}-{hashlib.sha256(canonical.encode('utf-8')).hexdigest()[:16]}", "snapshot_ordinal_fallback"


def open_conversation_stream(snapshot: Path):
    if snapshot.suffix.lower() == ".zip":
        archive = zipfile.ZipFile(snapshot, "r")
        names = [name for name in archive.namelist() if Path(name).name == "conversations.json"]
        if len(names) != 1:
            archive.close()
            raise ValueError(f"Expected exactly one conversations.json in ZIP; found {len(names)}")
        return archive, archive.open(names[0], "r")
    return None, snapshot.open("rb")


def connect(database: Path) -> sqlite3.Connection:
    database.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(database, timeout=30)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=FULL")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS imports (
            archive_id TEXT NOT NULL,
            source_sha256 TEXT NOT NULL,
            snapshot_path TEXT NOT NULL,
            source_bytes INTEGER NOT NULL,
            parser_version TEXT NOT NULL,
            schema_version INTEGER NOT NULL,
            status TEXT NOT NULL,
            next_ordinal INTEGER NOT NULL DEFAULT 0,
            committed_conversations INTEGER NOT NULL DEFAULT 0,
            last_error TEXT,
            updated_at TEXT NOT NULL,
            next_byte_offset INTEGER NOT NULL DEFAULT 0,
            last_source_locator TEXT,
            PRIMARY KEY (archive_id, source_sha256)
        );
        CREATE TABLE IF NOT EXISTS raw_conversations (
            archive_id TEXT NOT NULL,
            source_sha256 TEXT NOT NULL,
            source_locator TEXT NOT NULL,
            source_conversation_id TEXT NOT NULL,
            identity_method TEXT NOT NULL,
            source_ordinal INTEGER NOT NULL,
            payload_json TEXT NOT NULL,
            payload_sha256 TEXT NOT NULL,
            imported_at TEXT NOT NULL,
            source_end_byte_offset INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (archive_id, source_sha256, source_locator),
            UNIQUE (archive_id, source_sha256, source_ordinal),
            FOREIGN KEY (archive_id, source_sha256)
              REFERENCES imports(archive_id, source_sha256)
        );
        CREATE TABLE IF NOT EXISTS import_events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            archive_id TEXT NOT NULL,
            source_sha256 TEXT NOT NULL,
            event_type TEXT NOT NULL,
            ordinal INTEGER,
            details_json TEXT NOT NULL,
            occurred_at TEXT NOT NULL
        );
    """)
    # Additive migrations keep an existing prototype database resumable.
    for table, column, declaration in (
        ("imports", "next_byte_offset", "INTEGER NOT NULL DEFAULT 0"),
        ("imports", "last_source_locator", "TEXT"),
        ("raw_conversations", "source_end_byte_offset", "INTEGER NOT NULL DEFAULT 0"),
    ):
        existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
        if column not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {declaration}")
    return conn


def add_event(conn: sqlite3.Connection, archive_id: str, digest: str,
              event_type: str, ordinal: int | None, details: dict[str, Any]) -> None:
    conn.execute(
        "INSERT INTO import_events(archive_id,source_sha256,event_type,ordinal,details_json,occurred_at) VALUES(?,?,?,?,?,?)",
        (archive_id, digest, event_type, ordinal, json.dumps(details, ensure_ascii=False, sort_keys=True), utc_now()),
    )


def _import_export_unlocked(source: Path, output: Path, archive_id: str, batch_size: int = 100,
                            stop_after_batches: int | None = None) -> dict[str, Any]:
    if batch_size < 1:
        raise ValueError("batch_size must be at least 1")
    source = source.resolve()
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    snapshot, digest, byte_size = immutable_snapshot(source, output)
    db_path = output / "import.sqlite3"
    conn = connect(db_path)
    try:
        row = conn.execute(
            "SELECT status,next_ordinal,committed_conversations,parser_version,next_byte_offset FROM imports WHERE archive_id=? AND source_sha256=?",
            (archive_id, digest),
        ).fetchone()
        if row and row[3] != PARSER_VERSION:
            raise RuntimeError("Parser version changed; explicit migration is required")
        if row is None:
            prior_sources = conn.execute(
                "SELECT source_sha256,status FROM imports WHERE archive_id=? ORDER BY updated_at",
                (archive_id,),
            ).fetchall()
            run_mode = "NEW_SNAPSHOT" if prior_sources else "FIRST_PASS"
            with conn:
                conn.execute(
                    "INSERT INTO imports(archive_id,source_sha256,snapshot_path,source_bytes,parser_version,schema_version,status,next_ordinal,committed_conversations,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                    (archive_id, digest, str(snapshot), byte_size, PARSER_VERSION, SCHEMA_VERSION, "REGISTERED", 0, 0, utc_now()),
                )
                add_event(conn, archive_id, digest, "REGISTERED", None, {
                    "snapshot_path": str(snapshot), "bytes": byte_size, "run_mode": run_mode,
                    "prior_source_hashes": [item[0] for item in prior_sources],
                })
            next_ordinal = committed = next_byte_offset = 0
        else:
            prior_status = str(row[0])
            next_ordinal, committed, next_byte_offset = int(row[1]), int(row[2]), int(row[4])
            if prior_status == "RAW_COMPLETE":
                # Exact same archive ID + immutable source hash: nothing to ingest again.
                return _status(conn, archive_id, digest, db_path, run_mode="ALREADY_COMPLETE")
            run_mode = "RESUME" if next_ordinal > 0 and next_byte_offset > 0 else "RETRY_FROM_START"

        with conn:
            conn.execute("UPDATE imports SET status='STAGING',last_error=NULL,updated_at=? WHERE archive_id=? AND source_sha256=?",
                         (utc_now(), archive_id, digest))
            event_type = {
                "FIRST_PASS": "FIRST_PASS_STARTED",
                "NEW_SNAPSHOT": "NEW_SNAPSHOT_STARTED",
                "RESUME": "RESUME",
                "RETRY_FROM_START": "RETRY_FROM_START",
            }[run_mode]
            add_event(conn, archive_id, digest, event_type, next_ordinal,
                      {"run_mode": run_mode, "prior_status": row[0] if row else "NEW",
                       "next_ordinal": next_ordinal, "next_byte_offset": next_byte_offset,
                       "parser_version": PARSER_VERSION})

        archive = None
        batch: list[tuple] = []
        batches_this_run = 0
        seen_count = next_ordinal if next_byte_offset else 0
        try:
            archive, stream = open_conversation_stream(snapshot)
            with stream:
                parser_offset = next_byte_offset
                parser_ordinal = next_ordinal if next_byte_offset else 0
                for ordinal, conversation, end_byte_offset in iter_json_array(
                    stream, start_offset=parser_offset, start_ordinal=parser_ordinal
                ):
                    seen_count = ordinal + 1
                    if not next_byte_offset and ordinal < next_ordinal:
                        continue
                    cid, identity_method = conversation_id(conversation, ordinal)
                    locator = f"{archive_id}/{digest}/{cid}" if identity_method == "source_id" else f"{archive_id}/{digest}/{cid}"
                    payload = json.dumps(conversation, ensure_ascii=False, separators=(",", ":"))
                    payload_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
                    batch.append((archive_id, digest, locator, cid, identity_method, ordinal, payload, payload_hash, utc_now(), end_byte_offset))
                    if len(batch) >= batch_size:
                        committed += _commit_batch(conn, archive_id, digest, batch)
                        next_ordinal = ordinal + 1
                        next_byte_offset = end_byte_offset
                        batch = []
                        batches_this_run += 1
                        if stop_after_batches is not None and batches_this_run >= stop_after_batches:
                            with conn:
                                conn.execute("UPDATE imports SET status='PAUSED',updated_at=? WHERE archive_id=? AND source_sha256=?",
                                             (utc_now(), archive_id, digest))
                                add_event(conn, archive_id, digest, "PAUSED_FOR_TEST", next_ordinal,
                                          {"committed_conversations": committed, "next_ordinal": next_ordinal, "next_byte_offset": next_byte_offset})
                            return _status(conn, archive_id, digest, db_path, run_mode=run_mode)
                if batch:
                    committed += _commit_batch(conn, archive_id, digest, batch)
                    next_ordinal = batch[-1][5] + 1
                    next_byte_offset = batch[-1][9]
                    batches_this_run += 1
            total = conn.execute("SELECT COUNT(*) FROM raw_conversations WHERE archive_id=? AND source_sha256=?",
                                 (archive_id, digest)).fetchone()[0]
            if total != seen_count:
                raise RuntimeError(f"Staging count mismatch: staged={total}, source={seen_count}")
            with conn:
                conn.execute("UPDATE imports SET status='RAW_COMPLETE',next_ordinal=?,next_byte_offset=?,committed_conversations=?,updated_at=? WHERE archive_id=? AND source_sha256=?",
                             (seen_count, next_byte_offset, total, utc_now(), archive_id, digest))
                add_event(conn, archive_id, digest, "RAW_COMPLETE", seen_count,
                          {"source_conversations": seen_count, "staged_conversations": total})
            return _status(conn, archive_id, digest, db_path, run_mode=run_mode)
        except Exception as exc:
            with conn:
                conn.execute("UPDATE imports SET status='FAILED',last_error=?,updated_at=? WHERE archive_id=? AND source_sha256=?",
                             (str(exc), utc_now(), archive_id, digest))
                add_event(conn, archive_id, digest, "FAILED", next_ordinal, {"error": str(exc)})
            raise
        finally:
            if archive is not None:
                archive.close()
    finally:
        conn.close()



@contextlib.contextmanager
def _exclusive_import_lock(lock_path: Path):
    """Serialize importers for one output directory; OS releases the lock on process exit."""
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+b") as stream:
        if os.name == "nt":
            import msvcrt
            stream.seek(0)
            if stream.read(1) == b"":
                stream.seek(0)
                stream.write(b"0")
                stream.flush()
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def import_export(source: Path, output: Path, archive_id: str, batch_size: int = 100,
                  stop_after_batches: int | None = None) -> dict[str, Any]:
    """Run one serialized import operation for the output directory.

    The lock covers snapshot registration, every batch/checkpoint, and final status.
    It is an OS advisory lock, so a killed process releases it without stale-lock
    cleanup. All cooperating importers must use this entry point.
    """
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    with _exclusive_import_lock(output / ".resumable_chat_import.lock"):
        return _import_export_unlocked(
            source, output, archive_id, batch_size=batch_size,
            stop_after_batches=stop_after_batches,
        )


def _commit_batch(conn: sqlite3.Connection, archive_id: str, digest: str, batch: list[tuple]) -> int:
    first_record, last_record = batch[0], batch[-1]
    first, last = first_record[5], last_record[5]
    with conn:
        for record in batch:
            conn.execute(
                """INSERT INTO raw_conversations
                (archive_id,source_sha256,source_locator,source_conversation_id,identity_method,source_ordinal,payload_json,payload_sha256,imported_at,source_end_byte_offset)
                VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(archive_id,source_sha256,source_locator) DO NOTHING""",
                record,
            )
        next_ordinal = last + 1
        count = conn.execute("SELECT COUNT(*) FROM raw_conversations WHERE archive_id=? AND source_sha256=?",
                             (archive_id, digest)).fetchone()[0]
        # A replayed/stale batch may be idempotent for rows, but must never
        # move the durable checkpoint backwards.
        conn.execute("""UPDATE imports
                        SET next_ordinal=?,next_byte_offset=?,last_source_locator=?,
                            committed_conversations=?,updated_at=?
                        WHERE archive_id=? AND source_sha256=? AND next_ordinal<=?""",
                     (next_ordinal, last_record[9], last_record[2], count, utc_now(),
                      archive_id, digest, next_ordinal))
        add_event(conn, archive_id, digest, "BATCH_COMMITTED", last,
                  {"first_ordinal": first, "last_ordinal": last, "batch_size": len(batch), "staged_total": count, "next_byte_offset": last_record[9], "last_source_locator": last_record[2]})
    return len(batch)


def _status(conn: sqlite3.Connection, archive_id: str, digest: str, db_path: Path, run_mode: str | None = None) -> dict[str, Any]:
    row = conn.execute(
        "SELECT status,next_ordinal,committed_conversations,last_error,snapshot_path,source_bytes,next_byte_offset,last_source_locator FROM imports WHERE archive_id=? AND source_sha256=?",
        (archive_id, digest),
    ).fetchone()
    return {
        "archive_id": archive_id, "source_sha256": digest, "status": row[0], "run_mode": run_mode,
        "next_ordinal": row[1], "committed_conversations": row[2], "last_error": row[3], "next_byte_offset": row[6], "last_source_locator": row[7],
        "snapshot_path": row[4], "source_bytes": row[5], "database_path": str(db_path),
        "resume_command": "rerun the same command with the same source, output directory, and --archive-id",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="ChatGPT conversations.json or ZIP containing exactly one conversations.json")
    parser.add_argument("--out", type=Path, required=True, help="Local durable import directory")
    parser.add_argument("--archive-id", required=True, help="Stable ID for this logical source archive")
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--stop-after-batches", type=int, help=argparse.SUPPRESS)
    args = parser.parse_args()
    print(json.dumps(import_export(args.source, args.out, args.archive_id, args.batch_size, args.stop_after_batches),
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
