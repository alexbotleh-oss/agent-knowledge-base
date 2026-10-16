#!/usr/bin/env python3
"""Append sanitized source-message references to the canonical linked source registry.

The default CLI is dry-run. Use --apply to register metadata-only source records;
this never promotes semantic memory records or assigns a project to raw messages.
"""
from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from plan_memory_intake import build_route_plan
from source_registry_contract import (
    batch_id_for_snapshot,
    identity_payload,
    sha256_hex,
    source_id_for_snapshot,
    utc_now,
    validate_source_record,
)
from validate_memory import validate_intake_manifest

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "registry" / "source_records.jsonl"
SOURCE_LOCATOR_PREFIX = "archive:"


def _parse_source_locator(value: Any) -> tuple[str, str]:
    if not isinstance(value, str) or not value.startswith(SOURCE_LOCATOR_PREFIX) or ":sha256:" not in value:
        raise ValueError("source locator must bind an archive ID to a source snapshot SHA-256")
    archive_id, snapshot_sha = value[len(SOURCE_LOCATOR_PREFIX):].rsplit(":sha256:", 1)
    if not archive_id or len(snapshot_sha) != 64 or any(c not in "0123456789abcdef" for c in snapshot_sha):
        raise ValueError("source locator contains an invalid archive ID or snapshot hash")
    return archive_id, snapshot_sha


def _safe_artifact_path(manifest_path: Path, relative: Any) -> Path:
    if not isinstance(relative, str) or not relative:
        raise ValueError("source-record artifact path is missing")
    rel = Path(relative)
    if rel.is_absolute() or ".." in rel.parts:
        raise ValueError("source-record artifact path must be relative and cannot traverse directories")
    base = manifest_path.resolve().parent
    resolved = (base / rel).resolve()
    if base not in resolved.parents or not resolved.is_file():
        raise ValueError("source-record artifact is missing or escapes the manifest directory")
    return resolved


def _parse_jsonl(data: bytes, label: str) -> list[dict[str, Any]]:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{label} is not UTF-8") from exc
    rows = []
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            raise ValueError(f"{label} contains a blank line at {number}")
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{label} has invalid JSON at line {number}: {exc}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"{label} line {number} must be an object")
        rows.append(value)
    return rows


def _load_batch(manifest_path: Path) -> dict[str, Any]:
    manifest_path = Path(manifest_path).resolve()
    if not manifest_path.is_file():
        raise ValueError("intake manifest is missing")
    before = manifest_path.read_bytes()
    errors = validate_intake_manifest(manifest_path)
    after = manifest_path.read_bytes()
    if before != after:
        raise ValueError("intake manifest changed during validation")
    if errors:
        raise ValueError("intake manifest validation failed: " + "; ".join(errors))
    try:
        manifest = json.loads(after.decode("utf-8"))
    except Exception as exc:
        raise ValueError("intake manifest is not valid UTF-8 JSON") from exc

    plan = build_route_plan(manifest_path)
    if manifest_path.read_bytes() != after:
        raise ValueError("intake manifest changed while its route plan was being built")
    if plan.get("status") != "DRY_RUN_READY":
        raise ValueError("intake route plan is not ready: " + "; ".join(plan.get("validation_errors", [])))
    routes = plan.get("routes", [])
    if len(routes) != 1 or routes[0].get("kind") != "source_records" or routes[0].get("logical_view") != "source_evidence_registry" or routes[0].get("planned_operation") != "append_source_records":
        raise ValueError("this writer only implements the source_records → source_evidence_registry.append_source_records route")

    source = manifest.get("source", {})
    if source.get("source_type") != "structured_export":
        raise ValueError("source registry writer only accepts structured_export source records")
    if source.get("project_id") != "unknown":
        raise ValueError("raw source records must remain project-neutral; project_id must be unknown")
    if manifest.get("payload_classification") != "private_reference_only":
        raise ValueError("source registry accepts metadata-only private_reference_only batches")
    if source.get("parser_version") is None:
        raise ValueError("source.parser_version is required for source-record revision identity")

    artifacts = manifest.get("artifacts", [])
    if len(artifacts) != 1 or artifacts[0].get("kind") != "source_records":
        raise ValueError("exactly one source_records artifact is required")
    artifact = artifacts[0]
    if artifact.get("lifecycle_status") != "candidate":
        raise ValueError("source records must remain candidate records")
    if artifact.get("approval_status") == "user_rejected":
        raise ValueError("user-rejected source batch cannot be registered")
    artifact_path = _safe_artifact_path(manifest_path, artifact.get("path"))
    artifact_bytes = artifact_path.read_bytes()
    if sha256_hex(artifact_bytes) != artifact.get("sha256"):
        raise ValueError("source-record artifact SHA-256 changed after manifest validation")
    rows = _parse_jsonl(artifact_bytes, "source-record artifact")
    if len(rows) != artifact.get("record_count"):
        raise ValueError("source-record artifact count does not match manifest")

    archive_id, snapshot_sha = _parse_source_locator(source.get("source_locator"))
    parser_version = source["parser_version"]
    expected_source_id = source_id_for_snapshot(archive_id, snapshot_sha)
    expected_batch_id = batch_id_for_snapshot(archive_id, snapshot_sha, parser_version)
    if source.get("source_id") != expected_source_id:
        raise ValueError("manifest source_id does not match archive/snapshot identity")
    if manifest.get("batch_id") != expected_batch_id:
        raise ValueError("manifest batch_id does not match archive/snapshot/parser identity")

    seen_ids = set()
    for number, row in enumerate(rows, 1):
        errors = validate_source_record(row)
        if errors:
            raise ValueError(f"invalid source record {number}: " + "; ".join(errors))
        if row["archive_id"] != archive_id:
            raise ValueError(f"source record {number} belongs to another archive")
        if row["source_snapshot_sha256"] != snapshot_sha:
            raise ValueError(f"source record {number} belongs to another source snapshot")
        if row["parser_version"] != parser_version:
            raise ValueError(f"source record {number} has a different parser version")
        if row["source_record_id"] in seen_ids:
            raise ValueError(f"duplicate source_record_id in batch: {row['source_record_id']}")
        seen_ids.add(row["source_record_id"])

    return {
        "manifest": manifest,
        "manifest_sha256": sha256_hex(after),
        "artifact_sha256": sha256_hex(artifact_bytes),
        "batch_id": expected_batch_id,
        "source_snapshot_sha256": snapshot_sha,
        "rows": rows,
        "artifact_path": str(artifact_path),
    }


def _target_path_error(path: Path) -> str | None:
    resolved = Path(path).resolve()
    root = ROOT.resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        return None  # temporary external paths are useful for isolated tests
    if Path(path).absolute() != DEFAULT_REGISTRY.absolute() or resolved != DEFAULT_REGISTRY.resolve():
        return "writes inside the repository are restricted to registry/source_records.jsonl"
    if DEFAULT_REGISTRY.is_symlink() or DEFAULT_REGISTRY.parent.is_symlink():
        return "canonical source registry path must not be a symlink"
    return None


def _load_existing_registry(path: Path) -> tuple[list[dict[str, Any]], dict[tuple[str, str, str], dict[str, Any]]]:
    if not path.exists():
        return [], {}
    rows = _parse_jsonl(path.read_bytes(), "canonical source registry")
    by_key: dict[tuple[str, str, str], dict[str, Any]] = {}
    for number, row in enumerate(rows, 1):
        errors = validate_source_record(row)
        if errors:
            raise ValueError(f"invalid canonical source record at line {number}: " + "; ".join(errors))
        if not all(row.get(field) for field in ("batch_id", "registered_at", "schema_version")):
            raise ValueError(f"canonical source record at line {number} lacks registry metadata")
        key = (row["source_record_id"], row["source_snapshot_sha256"], row["parser_version"])
        if key in by_key:
            raise ValueError(f"duplicate canonical source-record revision at line {number}: {key[0]}")
        by_key[key] = row
    return rows, by_key


def _logical_payload(record: dict[str, Any]) -> dict[str, Any]:
    """Compare stable source content across snapshots, ignoring only snapshot provenance/bookkeeping."""
    return {
        key: value
        for key, value in record.items()
        if key not in {"source_snapshot_sha256", "batch_id", "registered_at", "schema_version"}
    }


def _write_atomic(path: Path, rows: list[dict[str, Any]]) -> None:
    payload = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        for row in rows
    ).encode("utf-8")
    fd, raw_tmp = tempfile.mkstemp(prefix=path.name + ".tmp-", dir=path.parent)
    tmp = Path(raw_tmp)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
        try:
            dir_fd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        except OSError:
            pass
    finally:
        tmp.unlink(missing_ok=True)


def append_source_records(
    manifest_path: Path,
    registry_path: Path = DEFAULT_REGISTRY,
    *,
    apply: bool = False,
) -> dict[str, Any]:
    """Validate and optionally append metadata-only source records.

    The default is read-only. Exact source-record revisions are idempotent.
    Across a newer snapshot, unchanged logical records are skipped even when
    the snapshot hash changes; changed content is appended as a new revision.
    Older snapshots and changed-content revisions are retained.
    """
    registry_path = Path(registry_path)
    try:
        batch = _load_batch(Path(manifest_path))
    except Exception as exc:
        return {"status": "REJECTED", "error": str(exc), "writes_performed": False}
    rows = batch["rows"]
    if not rows:
        return {"status": "NO_RECORDS", "batch_id": batch["batch_id"], "writes_performed": False}
    if not apply:
        return {
            "status": "DRY_RUN_READY",
            "batch_id": batch["batch_id"],
            "candidate_count": len(rows),
            "registry_path": str(registry_path),
            "writes_performed": False,
        }
    target_error = _target_path_error(registry_path)
    if target_error:
        return {"status": "REJECTED", "error": target_error, "writes_performed": False}

    registry_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = registry_path.with_name(registry_path.name + ".lock")
    try:
        lock_fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        return {"status": "LOCKED", "error": f"source registry lock exists: {lock_path}", "writes_performed": False}
    try:
        with os.fdopen(lock_fd, "w", encoding="utf-8") as stream:
            stream.write(json.dumps({"pid": os.getpid(), "started_at": utc_now()}))
            stream.flush()
            os.fsync(stream.fileno())
        try:
            current_batch = _load_batch(Path(manifest_path))
        except Exception as exc:
            return {"status": "REJECTED", "error": str(exc), "writes_performed": False}
        if (
            current_batch["manifest_sha256"] != batch["manifest_sha256"]
            or current_batch["artifact_sha256"] != batch["artifact_sha256"]
        ):
            return {"status": "STALE_INPUT", "error": "manifest or source artifact changed before registry write", "writes_performed": False}
        try:
            existing_rows, existing_by_key = _load_existing_registry(registry_path)
        except Exception as exc:
            return {"status": "REJECTED", "error": str(exc), "writes_performed": False}

        additions = []
        already_present = 0
        existing_by_logical: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for prior_row in existing_rows:
            logical_key = (prior_row["source_record_id"], prior_row["parser_version"])
            existing_by_logical.setdefault(logical_key, []).append(prior_row)

        for row in current_batch["rows"]:
            key = (row["source_record_id"], row["source_snapshot_sha256"], row["parser_version"])
            prior = existing_by_key.get(key)
            if prior is not None:
                if identity_payload(prior) != identity_payload(row):
                    return {
                        "status": "CONFLICT",
                        "error": f"same source record/snapshot/parser key has different content: {row['source_record_id']}",
                        "writes_performed": False,
                    }
                already_present += 1
                continue

            logical_key = (row["source_record_id"], row["parser_version"])
            unchanged_prior = next(
                (
                    candidate for candidate in existing_by_logical.get(logical_key, [])
                    if _logical_payload(candidate) == _logical_payload(row)
                ),
                None,
            )
            if unchanged_prior is not None:
                # Raw snapshots remain separately preserved by the import/staging
                # layer; do not duplicate an unchanged logical source record here.
                already_present += 1
                continue

            stored = dict(row)
            stored["batch_id"] = current_batch["batch_id"]
            stored["registered_at"] = utc_now()
            stored["schema_version"] = "source-record-v1"
            errors = validate_source_record(stored)
            if errors:
                return {"status": "REJECTED", "error": "invalid registry record: " + "; ".join(errors), "writes_performed": False}
            additions.append(stored)
            existing_by_key[key] = stored
            existing_by_logical.setdefault(logical_key, []).append(stored)

        if not additions:
            return {
                "status": "ALREADY_REGISTERED",
                "batch_id": current_batch["batch_id"],
                "already_present": already_present,
                "writes_performed": False,
            }
        _write_atomic(registry_path, existing_rows + additions)
        return {
            "status": "APPENDED",
            "batch_id": current_batch["batch_id"],
            "added_count": len(additions),
            "already_present": already_present,
            "registry_path": str(registry_path),
            "writes_performed": True,
        }
    finally:
        lock_path.unlink(missing_ok=True)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="validated metadata-only intake manifest")
    parser.add_argument("--apply", action="store_true", help="append source records; without this flag the command is read-only")
    args = parser.parse_args(argv)
    result = append_source_records(args.manifest, apply=args.apply)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] in {"DRY_RUN_READY", "APPENDED", "ALREADY_REGISTERED", "NO_RECORDS"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
