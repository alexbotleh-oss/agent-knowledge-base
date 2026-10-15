#!/usr/bin/env python3
"""Adapt local archive staging into a sanitized, project-neutral intake batch."""
from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

from source_registry_contract import (
    batch_id_for_snapshot,
    sha256_hex,
    source_id_for_snapshot,
    utc_now,
    validate_source_record,
)

STAGING_FIELDS = {
    "source_record_id", "archive_id", "conversation_id", "conversation_title",
    "source_message_id", "source_node_id", "source_locator", "parent_node_id",
    "child_node_ids", "event_time", "event_time_unix", "role", "author_name",
    "content_type", "text", "text_sha256", "has_attachments", "attachment_count",
    "attachment_payloads_inspected",
}
COVERAGE_STATUS = {"complete": "COMPLETE", "partial": "PARTIAL", "unknown": "UNKNOWN"}


def _safe_snapshot_child(snapshot_dir: Path, relative: str) -> Path:
    rel = Path(relative)
    if not relative or rel.is_absolute() or ".." in rel.parts:
        raise ValueError("records_file must be a safe relative path")
    resolved = (snapshot_dir / rel).resolve()
    if snapshot_dir.resolve() not in resolved.parents:
        raise ValueError("records_file escapes the staging directory")
    if not resolved.is_file():
        raise ValueError("staged records file is missing")
    return resolved


def _read_jsonl(data: bytes) -> list[dict[str, Any]]:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("staged records are not UTF-8") from exc
    rows = []
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            raise ValueError(f"blank JSONL record at line {number}")
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSONL at line {number}: {exc}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"JSONL record at line {number} must be an object")
        rows.append(value)
    return rows


def _durable_write(path: Path, data: bytes) -> None:
    with path.open("xb") as stream:
        stream.write(data)
        stream.flush()
        import os
        os.fsync(stream.fileno())


def _existing_batch_status(batch_dir: Path, artifact_bytes: bytes, batch_id: str, raw_sha: str) -> dict[str, Any]:
    manifest_path = batch_dir / "manifest.json"
    records_path = batch_dir / "source_records.jsonl"
    if not manifest_path.is_file() or not records_path.is_file():
        raise ValueError("output batch directory exists but is incomplete; refusing to overwrite it")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError("existing output manifest is unreadable") from exc
    if (
        manifest.get("batch_id") == batch_id
        and manifest.get("source", {}).get("source_locator", "").endswith("sha256:" + raw_sha)
        and records_path.read_bytes() == artifact_bytes
        and manifest.get("artifacts", [{}])[0].get("sha256") == sha256_hex(artifact_bytes)
    ):
        return {"status": "ALREADY_ADAPTED", "batch_id": batch_id, "manifest_path": str(manifest_path), "writes_performed": False}
    raise ValueError("output batch ID already exists with different content; refusing to overwrite it")


def adapt_archive_staging_to_intake(snapshot_path: Path, output_root: Path | None = None) -> dict[str, Any]:
    snapshot_path = Path(snapshot_path).resolve()
    if not snapshot_path.is_file():
        raise ValueError("archive_snapshot.json is missing")
    snapshot_dir = snapshot_path.parent.resolve()
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    archive_id = snapshot.get("archive_id")
    raw_sha = snapshot.get("raw_sha256")
    parser_version = snapshot.get("parser_version")
    if not isinstance(archive_id, str) or not archive_id.strip():
        raise ValueError("archive_snapshot archive_id is required")
    if not isinstance(raw_sha, str) or len(raw_sha) != 64 or any(c not in "0123456789abcdef" for c in raw_sha):
        raise ValueError("archive_snapshot raw_sha256 is invalid")
    if not isinstance(parser_version, str) or not parser_version.strip():
        raise ValueError("archive_snapshot parser_version is required")
    coverage = snapshot.get("coverage")
    if not isinstance(coverage, dict) or coverage.get("status") not in COVERAGE_STATUS:
        raise ValueError("archive_snapshot coverage status is invalid")
    expected_count = coverage.get("source_record_count")
    if isinstance(expected_count, bool) or not isinstance(expected_count, int) or expected_count < 0:
        raise ValueError("archive_snapshot source_record_count is invalid")
    records_path = _safe_snapshot_child(snapshot_dir, snapshot.get("records_file", ""))
    records_bytes = records_path.read_bytes()
    if sha256_hex(records_bytes) != snapshot.get("records_sha256"):
        raise ValueError("staged records_sha256 mismatch")
    source_rows = _read_jsonl(records_bytes)
    if len(source_rows) != expected_count:
        raise ValueError("staged record count does not match archive_snapshot")
    sanitized_rows = []
    seen_ids = set()
    for number, row in enumerate(source_rows, 1):
        unknown = sorted(set(row) - STAGING_FIELDS)
        if unknown:
            raise ValueError(f"staged record {number} has unsupported fields: {', '.join(unknown)}")
        if "project_id" in row:
            raise ValueError(f"staged record {number} contains project_id; source layer must remain unclassified")
        text = row.get("text")
        if not isinstance(text, str):
            raise ValueError(f"staged record {number} has no text string to hash")
        if sha256_hex(text.encode("utf-8")) != row.get("text_sha256"):
            raise ValueError(f"staged record {number} text_sha256 mismatch")
        if row.get("archive_id") != archive_id:
            raise ValueError(f"staged record {number} belongs to another archive")
        locator = row.get("source_locator")
        expected_locator = f"{archive_id}/{row.get('conversation_id')}/{row.get('source_node_id')}"
        if not isinstance(locator, str) or locator != expected_locator:
            raise ValueError(f"staged record {number} source_locator does not match source identity")
        source_record_id = "SRC-" + sha256_hex(locator.encode("utf-8"))[:24]
        if row.get("source_record_id") != source_record_id:
            raise ValueError(f"staged record {number} source_record_id mismatch")
        if source_record_id in seen_ids:
            raise ValueError(f"duplicate source_record_id in staged generation: {source_record_id}")
        seen_ids.add(source_record_id)
        sanitized = {
            "source_record_id": source_record_id,
            "archive_id": archive_id,
            "conversation_id": str(row["conversation_id"]),
            "source_message_id": row.get("source_message_id"),
            "source_node_id": str(row["source_node_id"]),
            "source_locator": locator,
            "parent_node_id": row.get("parent_node_id"),
            "child_node_ids": row.get("child_node_ids") or [],
            # staging.event_time is the export's message timestamp, not semantic event_time
            "source_time": row.get("event_time"),
            "source_time_unix": row.get("event_time_unix"),
            "role": row.get("role"),
            "content_type": row.get("content_type"),
            "text_sha256": row["text_sha256"],
            "source_snapshot_sha256": raw_sha,
            "parser_version": parser_version,
            "has_attachments": bool(row.get("has_attachments")),
            "attachment_count": row.get("attachment_count"),
            "attachment_payloads_inspected": row.get("attachment_payloads_inspected"),
        }
        errors = validate_source_record(sanitized)
        if errors:
            raise ValueError(f"invalid sanitized source record {number}: " + "; ".join(errors))
        sanitized_rows.append(sanitized)

    artifact_bytes = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        for row in sanitized_rows
    ).encode("utf-8")
    archive_key = __import__("hashlib").sha256(archive_id.encode("utf-8")).hexdigest()[:12]
    batch_id = batch_id_for_snapshot(archive_id, raw_sha, parser_version)
    source_id = source_id_for_snapshot(archive_id, raw_sha)
    output_root = Path(output_root).resolve() if output_root else snapshot_dir / "intake"
    output_root.mkdir(parents=True, exist_ok=True)
    batch_dir = output_root / batch_id
    if batch_dir.exists():
        return _existing_batch_status(batch_dir, artifact_bytes, batch_id, raw_sha)

    scope_status = COVERAGE_STATUS[coverage["status"]]
    conversation_ids = sorted({row["conversation_id"] for row in sanitized_rows})
    manifest = {
        "schema_version": "1.0",
        "command": "IMPORT_READY",
        "batch_id": batch_id,
        "created_at": utc_now(),
        "payload_classification": "private_reference_only",
        "source": {
            "source_type": "structured_export",
            "source_id": source_id,
            "project_id": "unknown",
            "scope_status": scope_status,
            "conversation_ids": conversation_ids,
            "source_locator": f"archive:{archive_id}:sha256:{raw_sha}",
            "captured_at": "unknown",
            "parser_version": parser_version,
        },
        "artifacts": [{
            "artifact_id": f"source-records-{archive_key}-{raw_sha[:12]}-{sha256_hex(parser_version.encode('utf-8'))[:8]}",
            "kind": "source_records",
            "path": "source_records.jsonl",
            "sha256": sha256_hex(artifact_bytes),
            "record_count": len(sanitized_rows),
            "lifecycle_status": "candidate",
            "evidence_status": "observed",
            "approval_status": "not_requested",
            "notes": "Metadata-only source records; message text, conversation title, author name and project assignment are not copied.",
        }],
        "notes": "Project attribution is intentionally unknown at raw-source ingestion. Source message timestamps are stored as source_time, not semantic event_time.",
    }
    manifest_bytes = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    temp_dir = Path(tempfile.mkdtemp(prefix=f".{batch_id}.tmp-", dir=output_root))
    try:
        _durable_write(temp_dir / "source_records.jsonl", artifact_bytes)
        _durable_write(temp_dir / "manifest.json", manifest_bytes)
        try:
            temp_dir.rename(batch_dir)
        except OSError:
            # Concurrent publishers may surface EEXIST or ENOTEMPTY depending
            # on platform when the competing complete directory wins the race.
            if not batch_dir.is_dir():
                raise
            shutil.rmtree(temp_dir, ignore_errors=True)
            return _existing_batch_status(batch_dir, artifact_bytes, batch_id, raw_sha)
    finally:
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
    return {"status": "ADAPTED", "batch_id": batch_id, "manifest_path": str(batch_dir / "manifest.json"), "record_count": len(sanitized_rows), "writes_performed": True}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive_snapshot", type=Path)
    parser.add_argument("--output-root", type=Path, default=None)
    args = parser.parse_args(argv)
    try:
        result = adapt_archive_staging_to_intake(args.archive_snapshot, args.output_root)
    except Exception as exc:
        result = {"status": "REJECTED", "error": str(exc), "writes_performed": False}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] in {"ADAPTED", "ALREADY_ADAPTED"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
