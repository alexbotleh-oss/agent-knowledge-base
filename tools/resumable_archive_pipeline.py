#!/usr/bin/env python3
"""Run the resumable raw import, staging, and metadata-only source registration.

The original export is snapshotted and imported first. Downstream stages only
read the importer's immutable snapshot. Semantic promotion and canonical index
refresh are deliberately outside this pipeline.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from archive_registry_staging import build as build_staging
from resumable_chat_import import import_export
from source_ingestion_runner import run_ingestion


def run_archive_pipeline(
    source: Path,
    work_root: Path,
    archive_id: str,
    *,
    registry_path: Path,
    apply: bool = False,
    batch_size: int = 100,
    stop_after_batches: int | None = None,
) -> dict[str, Any]:
    """Execute the existing stages in order and stop at the first incomplete gate."""
    source = Path(source).resolve()
    work_root = Path(work_root).resolve()
    import_root = work_root / "raw-import"
    staging_root = work_root / "staging"
    run_root = work_root / "source-runs"
    intake_root = work_root / "intake"

    try:
        imported = import_export(
            source,
            import_root,
            archive_id,
            batch_size=batch_size,
            stop_after_batches=stop_after_batches,
        )
    except Exception as exc:
        return {
            "status": "RAW_IMPORT_FAILED",
            "archive_id": archive_id,
            "error": str(exc),
            "writes_performed": True,
            "downstream_started": False,
            "downstream": "not started because raw import failed",
        }

    if imported.get("status") != "RAW_COMPLETE":
        return {
            "status": "RAW_IMPORT_INCOMPLETE",
            "archive_id": archive_id,
            "raw_import": imported,
            "downstream_started": False,
            "downstream": "not started until raw import reaches RAW_COMPLETE",
        }

    snapshot_path = Path(imported["snapshot_path"])
    expected_hash = imported["source_sha256"]
    if not snapshot_path.is_file():
        return {
            "status": "SNAPSHOT_VERIFICATION_FAILED",
            "archive_id": archive_id,
            "raw_import": imported,
            "error": "raw importer snapshot path is missing",
            "downstream_started": False,
        }
    actual_hash = hashlib.sha256(snapshot_path.read_bytes()).hexdigest()
    if actual_hash != expected_hash:
        return {
            "status": "SNAPSHOT_VERIFICATION_FAILED",
            "archive_id": archive_id,
            "raw_import": imported,
            "error": "immutable snapshot hash differs from raw-import result",
            "downstream_started": False,
        }

    try:
        staged = build_staging(snapshot_path, staging_root, archive_id)
        if staged.get("raw_sha256") != expected_hash:
            return {
                "status": "SNAPSHOT_IDENTITY_MISMATCH",
                "archive_id": archive_id,
                "raw_import": imported,
                "staging": staged,
                "error": "staging source hash differs from immutable raw snapshot",
                "downstream_started": False,
            }
        manifest_path = staging_root / "archive_snapshot.json"
        ingestion = run_ingestion(
            manifest_path,
            run_root,
            intake_root=intake_root,
            registry_path=Path(registry_path),
            apply=apply,
        )
    except Exception as exc:
        return {
            "status": "DOWNSTREAM_FAILED",
            "archive_id": archive_id,
            "raw_import": imported,
            "error": str(exc),
            "downstream_started": True,
        }

    return {
        "status": ingestion.get("status", "UNKNOWN"),
        "archive_id": archive_id,
        "raw_import": imported,
        "staging": {
            "manifest_path": str(manifest_path),
            "raw_sha256": staged.get("raw_sha256"),
            "source_record_count": staged.get("coverage", {}).get("source_record_count"),
            "coverage": staged.get("coverage", {}).get("status"),
            "binary_attachment_payloads_verified": False,
        },
        "source_ingestion": ingestion,
        "downstream_started": True,
        "semantic_promotion": "NOT_IMPLEMENTED",
        "canonical_index_refresh": "NOT_IMPLEMENTED",
        "next_session_restore": "NOT_VERIFIED",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="ChatGPT export ZIP or conversations.json")
    parser.add_argument("--work-root", type=Path, required=True)
    parser.add_argument("--archive-id", required=True)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--stop-after-batches", type=int, default=None,
                        help="test hook: pause after this many committed batches")
    parser.add_argument("--apply", action="store_true",
                        help="append metadata-only source records; default is dry-run")
    args = parser.parse_args(argv)
    result = run_archive_pipeline(
        args.source,
        args.work_root,
        args.archive_id,
        registry_path=args.registry,
        apply=args.apply,
        batch_size=args.batch_size,
        stop_after_batches=args.stop_after_batches,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") in {
        "READY_FOR_SOURCE_REGISTRATION", "SOURCE_REGISTERED_DOWNSTREAM_PENDING"
    } else 2


if __name__ == "__main__":
    raise SystemExit(main())
