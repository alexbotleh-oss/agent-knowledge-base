#!/usr/bin/env python3
"""Read-only inventory and integrity audit for a supplied ZIP chat export.

This tool inventories archive members without extracting or modifying them. It
does not infer export completeness from a filename, nor does it interpret
message semantics or claim that non-conversation files are valid attachments.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import zipfile
import zlib
from typing import Any

NESTED_ARCHIVE_SUFFIX_HINTS = {".zip", ".7z", ".rar", ".tar", ".gz", ".bz2", ".xz", ".tgz"}


def _is_unsafe_member_path(name: str) -> bool:
    """Flag absolute, drive-qualified, or parent-traversal ZIP member paths.

    Backslashes are normalized for detection only; the recorded member name
    remains byte-for-byte as reported by the ZIP directory.
    """
    normalized = name.replace("\\", "/")
    drive_qualified = len(normalized) >= 2 and normalized[0].isalpha() and normalized[1] == ":"
    return normalized.startswith("/") or drive_qualified or ".." in normalized.split("/")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def audit_archive(path: Path) -> dict[str, Any]:
    """Return an inventory; never extract members or write to the source."""
    path = path.resolve()
    if not path.is_file():
        return {"status": "FAIL", "reason": "SOURCE_FILE_NOT_FOUND", "source_path": str(path)}

    try:
        source_bytes = path.stat().st_size
        source_digest = sha256_file(path)
    except OSError as exc:
        return {
            "status": "FAIL",
            "reason": "SOURCE_UNREADABLE",
            "source_path": str(path),
            "error_type": type(exc).__name__,
            "error": str(exc),
            "read_only": True,
        }
    result: dict[str, Any] = {
        "source_path": str(path),
        "source_bytes": source_bytes,
        "source_sha256": source_digest,
        "read_only": True,
    }
    if not zipfile.is_zipfile(path):
        return {**result, "status": "FAIL", "reason": "SOURCE_IS_NOT_A_VALID_ZIP"}

    try:
        with zipfile.ZipFile(path, "r") as archive:
            infos = archive.infolist()
            names = [info.filename for info in infos]
            name_counts = Counter(names)
            duplicate_paths = sorted(name for name, count in name_counts.items() if count > 1)
            unsafe_paths = sorted({info.filename for info in infos if _is_unsafe_member_path(info.filename)})
            conversation_members = [
                info.filename for info in infos
                if not info.is_dir() and Path(info.filename).name == "conversations.json"
            ]
            nested_name_hints = [
                info.filename for info in infos
                if not info.is_dir() and Path(info.filename).suffix.lower() in NESTED_ARCHIVE_SUFFIX_HINTS
            ]
            crc_error_member = archive.testzip()
            members = [
                {
                    "index": index,
                    "path": info.filename,
                    "uncompressed_bytes": info.file_size,
                    "compressed_bytes": info.compress_size,
                    "crc32": f"{info.CRC:08x}",
                    "is_directory": info.is_dir(),
                    "duplicate_path": name_counts[info.filename] > 1,
                    "unsafe_path": _is_unsafe_member_path(info.filename),
                    "is_conversations_json_candidate": (
                        not info.is_dir() and Path(info.filename).name == "conversations.json"
                    ),
                    "nested_archive_name_hint": (
                        not info.is_dir()
                        and Path(info.filename).suffix.lower() in NESTED_ARCHIVE_SUFFIX_HINTS
                    ),
                }
                for index, info in enumerate(infos)
            ]
            result.update({
                "member_count": len(infos),
                "file_member_count": sum(not info.is_dir() for info in infos),
                "directory_member_count": sum(info.is_dir() for info in infos),
                "duplicate_member_paths": duplicate_paths,
                "unsafe_member_paths": unsafe_paths,
                "conversations_json_candidates": conversation_members,
                "conversations_json_candidate_count": len(conversation_members),
                "nested_archive_name_hints": nested_name_hints,
                "crc_error_member": crc_error_member,
                "members": members,
            })
    except (OSError, EOFError, zipfile.BadZipFile, RuntimeError, NotImplementedError, zlib.error) as exc:
        return {
            **result,
            "status": "FAIL",
            "reason": "ARCHIVE_READ_ERROR",
            "error_type": type(exc).__name__,
            "error": str(exc),
        }

    # The inventory is read after the initial hash. Detect a source that
    # changed or became unreadable during the scan rather than returning an
    # inventory bound to a stale digest.
    try:
        final_digest = sha256_file(path)
    except OSError as exc:
        return {
            **result,
            "status": "FAIL",
            "reason": "SOURCE_CHANGED_OR_UNREADABLE_DURING_AUDIT",
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
    if final_digest != result["source_sha256"]:
        return {
            **result,
            "status": "FAIL",
            "reason": "SOURCE_CHANGED_DURING_AUDIT",
            "final_source_sha256": final_digest,
        }

    review_reasons = []
    if result["duplicate_member_paths"]:
        review_reasons.append("DUPLICATE_MEMBER_PATHS")
    if result["unsafe_member_paths"]:
        review_reasons.append("UNSAFE_MEMBER_PATHS")
    if result["conversations_json_candidate_count"] != 1:
        review_reasons.append("EXPECTED_EXACTLY_ONE_CONVERSATIONS_JSON")
    if result["crc_error_member"] is not None:
        return {
            **result,
            "status": "FAIL",
            "reason": "MEMBER_CRC_ERROR",
            "review_reasons": review_reasons,
        }
    if review_reasons:
        return {
            **result,
            "status": "REVIEW_REQUIRED",
            "reason": "ARCHIVE_INVENTORY_NEEDS_REVIEW",
            "review_reasons": review_reasons,
        }
    return {**result, "status": "PASS", "reason": "ZIP_INVENTORY_AND_MEMBER_CRC_PASS"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path, help="Existing ZIP archive; read-only")
    args = parser.parse_args()
    result = audit_archive(args.archive)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return {"PASS": 0, "REVIEW_REQUIRED": 2, "FAIL": 1}[result["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
