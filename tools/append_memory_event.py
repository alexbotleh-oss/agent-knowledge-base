"""Validated append-only writer for temporal memory events.

The caller must provide trusted chronology; this module never infers it from
journal line order, event IDs, or ingestion timestamps.
"""
from __future__ import annotations

import json
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from temporal_memory_model import validate_temporal_relations


@contextmanager
def _exclusive_lock(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as stream:
        if os.name == "nt":
            import msvcrt
            stream.seek(0, os.SEEK_END)
            if stream.tell() == 0:
                stream.write(b"\\0")
                stream.flush()
            stream.seek(0)
            try:
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise RuntimeError("Another event writer holds the journal lock") from exc
            try:
                yield
            finally:
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            try:
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                raise RuntimeError("Another event writer holds the journal lock") from exc
            try:
                yield
            finally:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def read_event_journal(path: Path) -> list[dict[str, Any]]:
    records = []
    if not path.exists():
        return records
    with path.open("r", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at line {line_number}: {exc}") from exc
            if not isinstance(record, dict):
                raise ValueError(f"Journal line {line_number} is not a JSON object")
            records.append(record)
    return records


def append_event_record(
    journal_path: Path, record: dict[str, Any], trusted_order: dict[str, int]
) -> dict[str, Any]:
    """Validate the full temporal graph, then append exactly one event durably.

    Existing rows are never rewritten. If validation or the write fails, this
    function raises; it does not report a successful append prematurely.
    """
    journal_path = Path(journal_path)
    if not isinstance(record, dict):
        raise TypeError("record must be a JSON object")
    event_id = record.get("event_id")
    if not isinstance(event_id, str) or not event_id.strip():
        raise ValueError("record.event_id is required")
    if not isinstance(trusted_order, dict):
        raise TypeError("trusted_order must be an explicit mapping")
    journal_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = journal_path.with_name(journal_path.name + ".lock")
    with _exclusive_lock(lock_path):
        existing = read_event_journal(journal_path)
        if any(row.get("event_id") == event_id for row in existing):
            raise ValueError(f"event_id already exists: {event_id}")
        candidate_rows = existing + [record]
        errors = validate_temporal_relations(candidate_rows, trusted_order)
        if errors:
            raise ValueError("Temporal relation validation failed: " + "; ".join(errors))
        payload = (json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
        with journal_path.open("ab") as stream:
            written = stream.write(payload)
            if written != len(payload):
                raise OSError(f"Short append: wrote {written} of {len(payload)} bytes")
            stream.flush()
            os.fsync(stream.fileno())
        return {"status": "APPENDED", "event_id": event_id, "bytes_written": len(payload)}


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--journal", required=True, type=Path)
    parser.add_argument("--event", required=True, type=Path, help="JSON file containing one event object")
    parser.add_argument("--trusted-order", required=True, type=Path, help="JSON object mapping event IDs to trusted integer order")
    args = parser.parse_args()
    record = json.loads(args.event.read_text(encoding="utf-8"))
    trusted_order = json.loads(args.trusted_order.read_text(encoding="utf-8"))
    result = append_event_record(args.journal, record, trusted_order)
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
