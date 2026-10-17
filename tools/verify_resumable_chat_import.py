#!/usr/bin/env python3
"""Independently verify a staged resumable chat import against its immutable source.

This is a read-only audit. It never repairs rows, changes checkpoints, or promotes
staged content into canonical memory.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

from resumable_chat_import import conversation_id, iter_json_array, open_conversation_stream, sha256_file


def _fail(reason: str, **details: Any) -> dict[str, Any]:
    return {"verification": "FAIL", "reason": reason, **details}


def verify_import(output: Path, archive_id: str, source_sha256: str | None = None) -> dict[str, Any]:
    """Compare every staged raw conversation with the immutable source snapshot.

    PASS means a complete import matches source payloads, identities, offsets,
    hashes, and checkpoint metadata. PARTIAL means an incomplete/failed import
    has an exact staged prefix and can be investigated or resumed. Any mismatch
    is FAIL. This function is read-only.
    """
    output = output.resolve()
    database = output / "import.sqlite3"
    if not database.is_file():
        return _fail("IMPORT_DATABASE_NOT_FOUND", database_path=str(database))

    conn: sqlite3.Connection | None = None
    archive = None
    try:
        conn = sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True)
        candidates = conn.execute(
            """SELECT archive_id,source_sha256,snapshot_path,source_bytes,status,
                      next_ordinal,committed_conversations,last_error,next_byte_offset,
                      last_source_locator,parser_version,schema_version
               FROM imports WHERE archive_id=? ORDER BY updated_at""",
            (archive_id,),
        ).fetchall()
        if source_sha256 is not None:
            candidates = [row for row in candidates if row[1] == source_sha256]
        if not candidates:
            return _fail("IMPORT_RECORD_NOT_FOUND", archive_id=archive_id, source_sha256=source_sha256)
        if len(candidates) != 1:
            return _fail(
                "SOURCE_SNAPSHOT_AMBIGUOUS",
                archive_id=archive_id,
                available_source_sha256=[row[1] for row in candidates],
                instruction="Pass --source-sha256 to select the intended immutable snapshot.",
            )

        (stored_archive_id, digest, snapshot_name, source_bytes, status, next_ordinal,
         committed_count, last_error, next_byte_offset, last_source_locator,
         parser_version, schema_version) = candidates[0]
        snapshot = Path(snapshot_name)
        if not snapshot.is_file():
            return _fail("IMMUTABLE_SNAPSHOT_NOT_FOUND", snapshot_path=str(snapshot), source_sha256=digest)
        actual_size = snapshot.stat().st_size
        if actual_size != source_bytes:
            return _fail("SNAPSHOT_SIZE_MISMATCH", expected=source_bytes, actual=actual_size)
        actual_digest = sha256_file(snapshot)
        if actual_digest != digest:
            return _fail("SNAPSHOT_HASH_MISMATCH", expected=digest, actual=actual_digest)

        rows = conn.execute(
            """SELECT source_locator,source_conversation_id,identity_method,source_ordinal,
                      payload_json,payload_sha256,source_end_byte_offset
               FROM raw_conversations
               WHERE archive_id=? AND source_sha256=?
               ORDER BY source_ordinal""",
            (stored_archive_id, digest),
        )
        staged_count = conn.execute(
            "SELECT COUNT(*) FROM raw_conversations WHERE archive_id=? AND source_sha256=?",
            (stored_archive_id, digest),
        ).fetchone()[0]

        archive, stream = open_conversation_stream(snapshot)
        source_count = 0
        mismatch_count = 0
        first_mismatches: list[dict[str, Any]] = []
        next_staged = rows.fetchone()
        staged_ordinals_seen: list[int] = []
        last_expected_locator: str | None = None
        last_expected_offset = 0

        with stream:
            for ordinal, conversation, end_offset in iter_json_array(stream):
                source_count += 1
                expected_id, expected_identity_method = conversation_id(conversation, ordinal)
                expected_locator = f"{archive_id}/{digest}/{expected_id}"
                expected_payload = json.dumps(conversation, ensure_ascii=False, separators=(",", ":"))
                expected_payload_hash = hashlib.sha256(expected_payload.encode("utf-8")).hexdigest()
                last_expected_locator = expected_locator
                last_expected_offset = end_offset

                while next_staged is not None and int(next_staged[3]) < ordinal:
                    mismatch_count += 1
                    if len(first_mismatches) < 10:
                        first_mismatches.append({
                            "kind": "EXTRA_OR_OUT_OF_ORDER_STAGED_ORDINAL",
                            "staged_ordinal": int(next_staged[3]),
                        })
                    next_staged = rows.fetchone()

                if next_staged is None or int(next_staged[3]) > ordinal:
                    mismatch_count += 1
                    if len(first_mismatches) < 10:
                        first_mismatches.append({"kind": "MISSING_STAGED_ORDINAL", "source_ordinal": ordinal})
                    continue

                row = next_staged
                staged_ordinal = int(row[3])
                staged_ordinals_seen.append(staged_ordinal)
                checks = {
                    "source_locator": (row[0], expected_locator),
                    "source_conversation_id": (row[1], expected_id),
                    "identity_method": (row[2], expected_identity_method),
                    "payload_json": (row[4], expected_payload),
                    "payload_sha256": (row[5], expected_payload_hash),
                    "source_end_byte_offset": (int(row[6]), end_offset),
                }
                bad_fields = [name for name, (actual, expected) in checks.items() if actual != expected]
                stored_payload_hash = hashlib.sha256(str(row[4]).encode("utf-8")).hexdigest()
                if stored_payload_hash != row[5]:
                    bad_fields.append("stored_payload_hash_does_not_match_payload")
                if bad_fields:
                    mismatch_count += 1
                    if len(first_mismatches) < 10:
                        first_mismatches.append({
                            "kind": "STAGED_ROW_MISMATCH",
                            "source_ordinal": ordinal,
                            "fields": sorted(set(bad_fields)),
                        })
                next_staged = rows.fetchone()

        while next_staged is not None:
            mismatch_count += 1
            if len(first_mismatches) < 10:
                first_mismatches.append({
                    "kind": "EXTRA_STAGED_ORDINAL",
                    "staged_ordinal": int(next_staged[3]),
                })
            next_staged = rows.fetchone()

        if len(staged_ordinals_seen) != staged_count:
            mismatch_count += 1
            if len(first_mismatches) < 10:
                first_mismatches.append({
                    "kind": "STAGED_ROW_COUNT_INCONSISTENT",
                    "iterated_staged_rows": len(staged_ordinals_seen),
                    "database_staged_count": staged_count,
                })

        last_row = conn.execute(
            """SELECT source_ordinal,source_locator,source_end_byte_offset
               FROM raw_conversations WHERE archive_id=? AND source_sha256=?
               ORDER BY source_ordinal DESC LIMIT 1""",
            (stored_archive_id, digest),
        ).fetchone()
        expected_cursor = staged_count
        expected_offset = int(last_row[2]) if last_row else 0
        expected_locator_from_rows = str(last_row[1]) if last_row else None
        checkpoint_mismatches = {}
        if int(next_ordinal) != expected_cursor:
            checkpoint_mismatches["next_ordinal"] = {"actual": next_ordinal, "expected": expected_cursor}
        if int(committed_count) != staged_count:
            checkpoint_mismatches["committed_conversations"] = {"actual": committed_count, "expected": staged_count}
        if int(next_byte_offset) != expected_offset:
            checkpoint_mismatches["next_byte_offset"] = {"actual": next_byte_offset, "expected": expected_offset}
        if last_source_locator != expected_locator_from_rows:
            checkpoint_mismatches["last_source_locator"] = {
                "actual": last_source_locator, "expected": expected_locator_from_rows
            }
        if checkpoint_mismatches:
            mismatch_count += 1

        complete = status == "RAW_COMPLETE"
        if complete and source_count != staged_count:
            mismatch_count += 1
            if len(first_mismatches) < 10:
                first_mismatches.append({
                    "kind": "COMPLETE_STATUS_COUNT_MISMATCH",
                    "source_count": source_count,
                    "staged_count": staged_count,
                })
        if mismatch_count:
            return {
                "verification": "FAIL",
                "reason": "SOURCE_READBACK_MISMATCH",
                "archive_id": archive_id,
                "source_sha256": digest,
                "import_status": status,
                "source_conversations": source_count,
                "staged_conversations": staged_count,
                "mismatch_count": mismatch_count,
                "first_mismatches": first_mismatches,
                "checkpoint_mismatches": checkpoint_mismatches,
            }

        base = {
            "archive_id": archive_id,
            "source_sha256": digest,
            "snapshot_path": str(snapshot),
            "source_bytes": source_bytes,
            "parser_version": parser_version,
            "schema_version": schema_version,
            "import_status": status,
            "source_conversations": source_count,
            "staged_conversations": staged_count,
            "checkpoint": {
                "next_ordinal": next_ordinal,
                "next_byte_offset": next_byte_offset,
                "last_source_locator": last_source_locator,
            },
            "last_error": last_error,
            "read_only": True,
        }
        if complete and source_count == staged_count:
            return {"verification": "PASS", "reason": "COMPLETE_SOURCE_READBACK_MATCH", **base}
        return {"verification": "PARTIAL", "reason": "STAGED_PREFIX_MATCHES_SOURCE; IMPORT_NOT_COMPLETE", **base}
    except Exception as exc:
        return _fail("AUDIT_EXCEPTION", error_type=type(exc).__name__, error=str(exc), archive_id=archive_id)
    finally:
        if archive is not None:
            archive.close()
        if conn is not None:
            conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="Existing local import directory")
    parser.add_argument("--archive-id", required=True, help="Stable logical archive ID")
    parser.add_argument("--source-sha256", help="Required when multiple immutable snapshots share an archive ID")
    args = parser.parse_args()
    result = verify_import(args.out, args.archive_id, args.source_sha256)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return {"PASS": 0, "PARTIAL": 2, "FAIL": 1}[result["verification"]]


if __name__ == "__main__":
    raise SystemExit(main())
