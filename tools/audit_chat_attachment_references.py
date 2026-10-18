#!/usr/bin/env python3
"""Conservatively inventory candidate attachment references in raw chat exports.

Candidate detection is heuristic. Only exact archive-member path matches are
reported as exact; unresolved references are preserved for later human/source
format reconciliation. Raw conversation payloads are never rewritten.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import zipfile
from typing import Any

from resumable_chat_import import iter_json_array, open_conversation_stream, sha256_file

REFERENCE_KEY_HINT = re.compile(r"(file|attach|asset|image|audio|video|document|upload|href|url|path)", re.I)


def _pointer_part(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def _candidate_references(value: Any, pointer: str = ""):
    if isinstance(value, dict):
        for key, child in value.items():
            child_pointer = pointer + "/" + _pointer_part(str(key))
            if isinstance(child, str) and child.strip():
                if "://" in child or REFERENCE_KEY_HINT.search(str(key)):
                    yield child_pointer, str(key), child
            else:
                yield from _candidate_references(child, child_pointer)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            child_pointer = pointer + "/" + str(index)
            yield from _candidate_references(child, child_pointer)


def audit_references(source: Path) -> dict[str, Any]:
    """Scan one JSON export or ZIP without changing the source or its payloads."""
    source = source.resolve()
    if not source.is_file():
        return {"status": "FAIL", "reason": "SOURCE_FILE_NOT_FOUND", "source_path": str(source)}

    try:
        digest = sha256_file(source)
    except OSError as exc:
        return {
            "status": "FAIL",
            "reason": "SOURCE_UNREADABLE",
            "source_path": str(source),
            "error_type": type(exc).__name__,
            "error": str(exc),
            "raw_payloads_modified": False,
        }
    member_paths: list[str] = []
    archive = None
    stream = None
    references: list[dict[str, Any]] = []
    conversation_count = 0
    try:
        archive, stream = open_conversation_stream(source)
        if archive is not None:
            member_paths = [
                info.filename for info in archive.infolist()
                if not info.is_dir() and Path(info.filename).name != "conversations.json"
            ]
        exact_path_counts = Counter(member_paths)
        with stream:
            for ordinal, conversation, _end_offset in iter_json_array(stream):
                conversation_count += 1
                conversation_id = conversation.get("id") or conversation.get("conversation_id") or f"ordinal-{ordinal}"
                for pointer, key, reference in _candidate_references(conversation):
                    exact_count = exact_path_counts.get(reference, 0)
                    if exact_count == 1:
                        match_status = "EXACT_MEMBER_PATH_MATCH"
                    elif exact_count > 1:
                        match_status = "AMBIGUOUS_DUPLICATE_MEMBER_PATH"
                    else:
                        match_status = "UNRESOLVED"
                    references.append({
                        "conversation_ordinal": ordinal,
                        "conversation_id": str(conversation_id),
                        "json_pointer": pointer,
                        "source_key": key,
                        "source_value": reference,
                        "match_status": match_status,
                        "exact_member_match_count": exact_count,
                    })
    except (OSError, ValueError, zipfile.BadZipFile, RuntimeError, UnicodeDecodeError) as exc:
        return {
            "status": "FAIL",
            "reason": "SOURCE_SCAN_FAILED",
            "source_path": str(source),
            "source_sha256": digest,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "raw_payloads_modified": False,
        }
    finally:
        if stream is not None:
            stream.close()
        if archive is not None:
            archive.close()

    # The scan reads the source after the initial hash. Do not report its
    # results under a digest that no longer describes the current source.
    try:
        final_digest = sha256_file(source)
    except OSError as exc:
        return {
            "status": "FAIL",
            "reason": "SOURCE_CHANGED_OR_UNREADABLE_DURING_SCAN",
            "source_path": str(source),
            "source_sha256": digest,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "raw_payloads_modified": False,
        }
    if final_digest != digest:
        return {
            "status": "FAIL",
            "reason": "SOURCE_CHANGED_DURING_SCAN",
            "source_path": str(source),
            "source_sha256": digest,
            "final_source_sha256": final_digest,
            "raw_payloads_modified": False,
        }

    counts = Counter(item["match_status"] for item in references)
    return {
        "status": "SCAN_COMPLETE_REVIEW_REQUIRED",
        "reason": "CANDIDATE_DETECTION_IS_HEURISTIC; UNRESOLVED_VALUES_ARE_NOT_REWRITTEN",
        "source_path": str(source),
        "source_sha256": digest,
        "source_bytes": source.stat().st_size,
        "source_format": "ZIP" if source.suffix.lower() == ".zip" else "JSON",
        "conversation_count_scanned": conversation_count,
        "archive_member_path_count": len(member_paths),
        "candidate_reference_count": len(references),
        "exact_member_path_matches": counts["EXACT_MEMBER_PATH_MATCH"],
        "unresolved_candidates": counts["UNRESOLVED"],
        "ambiguous_duplicate_path_candidates": counts["AMBIGUOUS_DUPLICATE_MEMBER_PATH"],
        "raw_payloads_modified": False,
        "references": references,
        "interpretation_boundary": (
            "An exact path match is only a path-level correspondence, not proof that the member is the intended attachment. "
            "No match is inferred from basename, identifier substring, filename extension, or URI parsing."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="conversations.json or ZIP containing exactly one conversations.json")
    args = parser.parse_args()
    result = audit_references(args.source)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result["status"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
