#!/usr/bin/env python3
"""Run read-only chat-export preflight audits and bind them to one source hash.

This orchestrator never extracts or modifies the archive. It deliberately
cannot return PASS while attachment-reference detection remains heuristic.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tempfile
from typing import Any

from audit_chat_export_archive import audit_archive
from audit_chat_attachment_references import audit_references
from resumable_chat_import import sha256_file


def _copy_source_snapshot(source: Path, snapshot: Path) -> str:
    """Copy and hash the exact byte stream that both sub-audits will inspect."""
    digest = hashlib.sha256()
    with source.open("rb") as input_stream, snapshot.open("wb") as output_stream:
        for chunk in iter(lambda: input_stream.read(1024 * 1024), b""):
            output_stream.write(chunk)
            digest.update(chunk)
    return digest.hexdigest()


def preflight_chat_export(source: Path) -> dict[str, Any]:
    """Run both audits against one private snapshot and bind them to its hash."""
    source = source.resolve()
    if not source.is_file():
        inventory = audit_archive(source)
        references = audit_references(source)
        return {
            "status": "FAIL",
            "reason": "SUBAUDIT_FAILED",
            "source_path": str(source),
            "inventory": inventory,
            "attachment_references": references,
            "raw_source_modified": False,
        }

    try:
        source_digest_before = sha256_file(source)
    except OSError as exc:
        return {
            "status": "FAIL",
            "reason": "SOURCE_UNREADABLE",
            "source_path": str(source),
            "error_type": type(exc).__name__,
            "error": str(exc),
            "raw_source_modified": False,
        }

    try:
        with tempfile.TemporaryDirectory(prefix="chat-export-preflight-") as temp_dir:
            snapshot = Path(temp_dir) / "source.zip"
            snapshot_digest = _copy_source_snapshot(source, snapshot)
            source_digest_after = sha256_file(source)
            if source_digest_before != snapshot_digest or source_digest_before != source_digest_after:
                return {
                    "status": "FAIL",
                    "reason": "SOURCE_CHANGED_DURING_SNAPSHOT",
                    "source_path": str(source),
                    "source_sha256_before": source_digest_before,
                    "snapshot_sha256": snapshot_digest,
                    "source_sha256_after": source_digest_after,
                    "raw_source_modified": False,
                }

            inventory = audit_archive(snapshot)
            references = audit_references(snapshot)
            inventory["source_path"] = str(source)
            references["source_path"] = str(source)

            inventory_digest = inventory.get("source_sha256")
            references_digest = references.get("source_sha256")
            if not inventory_digest or not references_digest:
                return {
                    "status": "FAIL",
                    "reason": "SOURCE_DIGEST_UNAVAILABLE",
                    "source_path": str(source),
                    "source_sha256": snapshot_digest,
                    "inventory": inventory,
                    "attachment_references": references,
                    "raw_source_modified": False,
                }
            if inventory_digest != references_digest or inventory_digest != snapshot_digest:
                return {
                    "status": "FAIL",
                    "reason": "SOURCE_DIGEST_MISMATCH_BETWEEN_AUDITS",
                    "source_path": str(source),
                    "source_sha256": snapshot_digest,
                    "inventory_source_sha256": inventory_digest,
                    "references_source_sha256": references_digest,
                    "inventory": inventory,
                    "attachment_references": references,
                    "raw_source_modified": False,
                }

            if inventory.get("status") == "FAIL" or references.get("status") == "FAIL":
                return {
                    "status": "FAIL",
                    "reason": "SUBAUDIT_FAILED",
                    "source_path": str(source),
                    "source_sha256": snapshot_digest,
                    "inventory": inventory,
                    "attachment_references": references,
                    "raw_source_modified": False,
                }

            reasons = []
            if inventory.get("status") != "PASS":
                reasons.append("ARCHIVE_INVENTORY_REQUIRES_REVIEW")
            if references.get("status") != "SCAN_COMPLETE_REVIEW_REQUIRED":
                reasons.append("ATTACHMENT_REFERENCE_AUDIT_NOT_COMPLETE")
            reasons.append("ATTACHMENT_REFERENCE_DETECTION_REMAINS_HEURISTIC")

            return {
                "status": "REVIEW_REQUIRED",
                "reason": "PREFLIGHT_COMPLETE_BUT_SEMANTIC_REVIEW_REQUIRED",
                "review_reasons": list(dict.fromkeys(reasons)),
                "source_path": str(source),
                "source_sha256": snapshot_digest,
                "source_hashes_match": inventory_digest == references_digest == snapshot_digest,
                "inventory_status": inventory.get("status"),
                "attachment_reference_status": references.get("status"),
                "inventory": inventory,
                "attachment_references": references,
                "raw_source_modified": False,
            }
    except OSError as exc:
        return {
            "status": "FAIL",
            "reason": "SNAPSHOT_READ_FAILED",
            "source_path": str(source),
            "error_type": type(exc).__name__,
            "error": str(exc),
            "raw_source_modified": False,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path, help="Existing ZIP chat export; read-only")
    args = parser.parse_args()
    result = preflight_chat_export(args.archive)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return {"REVIEW_REQUIRED": 2, "FAIL": 1}.get(result["status"], 1)


if __name__ == "__main__":
    raise SystemExit(main())
