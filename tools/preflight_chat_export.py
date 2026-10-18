#!/usr/bin/env python3
"""Run read-only chat-export preflight audits and bind them to one source hash.

This orchestrator never extracts or modifies the archive. It deliberately
cannot return PASS while attachment-reference detection remains heuristic.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from audit_chat_export_archive import audit_archive
from audit_chat_attachment_references import audit_references


def preflight_chat_export(source: Path) -> dict[str, Any]:
    """Run both audits and reject results that do not describe the same bytes."""
    source = source.resolve()
    inventory = audit_archive(source)
    references = audit_references(source)

    inventory_digest = inventory.get("source_sha256")
    references_digest = references.get("source_sha256")
    if inventory_digest and references_digest and inventory_digest != references_digest:
        return {
            "status": "FAIL",
            "reason": "SOURCE_DIGEST_MISMATCH_BETWEEN_AUDITS",
            "source_path": str(source),
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
            "source_sha256": inventory_digest or references_digest,
            "inventory": inventory,
            "attachment_references": references,
            "raw_source_modified": False,
        }

    if not inventory_digest or not references_digest:
        return {
            "status": "FAIL",
            "reason": "SOURCE_DIGEST_UNAVAILABLE",
            "source_path": str(source),
            "inventory": inventory,
            "attachment_references": references,
            "raw_source_modified": False,
        }

    reasons = []
    if inventory.get("status") != "PASS":
        reasons.append("ARCHIVE_INVENTORY_REQUIRES_REVIEW")
    if references.get("status") != "SCAN_COMPLETE_REVIEW_REQUIRED":
        reasons.append("ATTACHMENT_REFERENCE_AUDIT_NOT_COMPLETE")
    # Even a complete candidate scan is heuristic, so overall PASS is not
    # permitted until native-source-specific attachment semantics are reviewed.
    reasons.append("ATTACHMENT_REFERENCE_DETECTION_REMAINS_HEURISTIC")

    return {
        "status": "REVIEW_REQUIRED",
        "reason": "PREFLIGHT_COMPLETE_BUT_SEMANTIC_REVIEW_REQUIRED",
        "review_reasons": list(dict.fromkeys(reasons)),
        "source_path": str(source),
        "source_sha256": inventory_digest,
        "source_hashes_match": inventory_digest == references_digest,
        "inventory_status": inventory.get("status"),
        "attachment_reference_status": references.get("status"),
        "inventory": inventory,
        "attachment_references": references,
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
