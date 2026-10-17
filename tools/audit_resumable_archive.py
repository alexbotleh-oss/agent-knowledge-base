#!/usr/bin/env python3
"""Read-only integrity and coverage audit for a resumable chat import.

This tool validates stored bytes, importer checkpoints, raw payload hashes,
and (optionally) a derived archive-staging manifest. It never repairs files,
extracts semantic memory, or certifies that the source export covered all
conversations the user intended to export.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

from archive_registry_staging import extract_text, iso_utc
from resumable_chat_import import conversation_id, sha256_file


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_jsonl(path: Path, label: str) -> list[dict[str, Any]]:
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as exc:
        raise ValueError(f"{label} is unreadable UTF-8") from exc
    rows: list[dict[str, Any]] = []
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            raise ValueError(f"{label} has a blank line at {number}")
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{label} has invalid JSON at line {number}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"{label} line {number} is not an object")
        rows.append(value)
    return rows


def _audit_staging(
    manifest_path: Path,
    *,
    archive_id: str,
    source_sha256: str,
    source_bytes: int,
    imported_payloads: list[dict[str, Any]],
    errors: list[str],
    warnings: list[str],
) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "manifest_name": manifest_path.name,
        "status": "NOT_CHECKED",
        "source_record_count": None,
        "coverage_status": "UNKNOWN",
        "records_sha256_valid": False,
    }
    if not manifest_path.is_file():
        errors.append("staging manifest does not exist")
        summary["status"] = "FAIL"
        return summary
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        errors.append("staging manifest is unreadable or invalid JSON")
        summary["status"] = "FAIL"
        return summary
    if not isinstance(manifest, dict):
        errors.append("staging manifest root is not an object")
        summary["status"] = "FAIL"
        return summary

    if manifest.get("archive_id") != archive_id:
        errors.append("staging manifest archive_id differs from the selected import")
    if manifest.get("raw_sha256") != source_sha256:
        errors.append("staging manifest raw_sha256 differs from the immutable import snapshot")
    if manifest.get("byte_size") != source_bytes:
        errors.append("staging manifest byte_size differs from the immutable import snapshot")

    coverage = manifest.get("coverage")
    if not isinstance(coverage, dict):
        errors.append("staging manifest coverage object is missing")
        coverage = {}
    coverage_status = coverage.get("status", "unknown")
    summary["coverage_status"] = coverage_status
    summary["source_record_count"] = coverage.get("source_record_count")

    relative = manifest.get("records_file")
    if not isinstance(relative, str) or not relative:
        errors.append("staging manifest records_file is missing")
        summary["status"] = "FAIL"
        return summary
    rel_path = Path(relative)
    base = manifest_path.resolve().parent
    records_path = (base / rel_path).resolve()
    if rel_path.is_absolute() or ".." in rel_path.parts or base not in records_path.parents:
        errors.append("staging records_file path is unsafe or escapes the manifest directory")
        summary["status"] = "FAIL"
        return summary
    if not records_path.is_file():
        errors.append("staged records file is missing")
        summary["status"] = "FAIL"
        return summary

    try:
        records_bytes = records_path.read_bytes()
    except Exception:
        errors.append("staged records file is unreadable")
        summary["status"] = "FAIL"
        return summary
    actual_records_sha = _sha256(records_bytes)
    if actual_records_sha != manifest.get("records_sha256"):
        errors.append("staged records SHA-256 does not match the manifest")
    else:
        summary["records_sha256_valid"] = True

    try:
        records = _read_jsonl(records_path, "staged records")
    except ValueError as exc:
        errors.append(str(exc))
        summary["status"] = "FAIL"
        return summary

    expected_count = coverage.get("source_record_count")
    if expected_count != len(records):
        errors.append("staged record count differs from coverage.source_record_count")
    if coverage.get("conversation_count") != len(imported_payloads):
        errors.append("staging conversation_count differs from imported conversation count")

    expected_messages: dict[tuple[str, str], tuple[dict[str, Any], dict[str, Any]]] = {}
    expected_order: list[tuple[str, str]] = []
    expected_times: dict[tuple[str, str], Any] = {}
    for ordinal, payload in enumerate(imported_payloads):
        cid, _method = conversation_id(payload, ordinal)
        mapping = payload.get("mapping") or {}
        if not isinstance(mapping, dict):
            continue
        for node_id, node in mapping.items():
            if not isinstance(node, dict) or not isinstance(node.get("message"), dict):
                continue
            key = (cid, str(node_id))
            expected_messages[key] = (payload, node)
            expected_order.append(key)
            created = node["message"].get("create_time")
            expected_times[key] = created if isinstance(created, (int, float)) else None

    # Match the staging contract: known timestamps first, stable source order for ties,
    # then unknown timestamps in their original relative order.
    expected_order.sort(
        key=lambda key: (expected_times[key] is None, expected_times[key] or 0)
    )
    observed_order = [
        (record.get("conversation_id"), record.get("source_node_id"))
        for record in records
    ]
    if observed_order != expected_order:
        errors.append("staged record order differs from stable timestamp/source order")

    seen_record_ids: set[str] = set()
    seen_locators: set[str] = set()
    missing_message_ids = 0
    attachment_markers = 0
    for number, record in enumerate(records, 1):
        cid = record.get("conversation_id")
        node_id = record.get("source_node_id")
        if not isinstance(cid, str) or not isinstance(node_id, str):
            errors.append(f"staged record {number} lacks conversation_id/source_node_id")
            continue
        locator = f"{archive_id}/{cid}/{node_id}"
        expected_record_id = "SRC-" + _sha256(locator.encode("utf-8"))[:24]
        if record.get("archive_id") != archive_id:
            errors.append(f"staged record {number} belongs to another archive")
        if record.get("source_locator") != locator:
            errors.append(f"staged record {number} source_locator is inconsistent with its identity")
        if record.get("source_record_id") != expected_record_id:
            errors.append(f"staged record {number} source_record_id is inconsistent with its locator")
        if record.get("source_record_id") in seen_record_ids:
            errors.append(f"duplicate staged source_record_id at record {number}")
        if locator in seen_locators:
            errors.append(f"duplicate staged source_locator at record {number}")
        seen_record_ids.add(record.get("source_record_id"))
        seen_locators.add(locator)

        if record.get("text_sha256") != _sha256(str(record.get("text", "")).encode("utf-8")):
            errors.append(f"staged record {number} text_sha256 mismatch")
        expected = expected_messages.get((cid, node_id))
        if expected is None:
            errors.append(f"staged record {number} does not resolve to an imported conversation/node")
            continue
        _payload, node = expected
        message = node["message"]
        if record.get("source_message_id") != message.get("id"):
            errors.append(f"staged record {number} source_message_id differs from raw source")
        if record.get("parent_node_id") != node.get("parent"):
            errors.append(f"staged record {number} parent_node_id differs from raw source")
        if record.get("child_node_ids") != (node.get("children") or []):
            errors.append(f"staged record {number} child_node_ids differ from raw source")

        content = message.get("content") or {}
        expected_text = extract_text(content)
        if record.get("text") != expected_text:
            errors.append(f"staged record {number} extracted text differs from raw source")
        created = message.get("create_time")
        expected_time = created if isinstance(created, (int, float)) else None
        if record.get("event_time_unix") != expected_time:
            errors.append(f"staged record {number} source timestamp differs from raw source")
        if record.get("event_time") != iso_utc(created):
            errors.append(f"staged record {number} normalized source timestamp differs from raw source")

        if not message.get("id"):
            missing_message_ids += 1
        metadata = message.get("metadata") or {}
        attachments = metadata.get("attachments") or []
        has_attachments = bool(attachments)
        attachment_markers += int(has_attachments)
        if bool(record.get("has_attachments")) != has_attachments:
            errors.append(f"staged record {number} attachment marker differs from raw source")
        expected_attachment_count = len(attachments) if isinstance(attachments, list) else None
        if record.get("attachment_count") != expected_attachment_count:
            errors.append(f"staged record {number} attachment_count differs from raw source")
        if has_attachments and record.get("attachment_payloads_inspected") is not False:
            errors.append(f"staged record {number} incorrectly claims attachment payload inspection")

    if coverage.get("message_id_missing_count") != missing_message_ids:
        errors.append("coverage.message_id_missing_count differs from staged records")
    if coverage.get("records_with_attachment_markers") != attachment_markers:
        errors.append("coverage.records_with_attachment_markers differs from staged records")
    if coverage_status not in {"complete", "partial", "unknown"}:
        errors.append("staging coverage status is invalid")
    if coverage_status == "complete" and (missing_message_ids or attachment_markers):
        errors.append("staging claims complete coverage despite known missing IDs or attachment markers")
    if coverage_status != "complete":
        warnings.append(f"staging coverage is {coverage_status}; integrity does not establish export-scope completeness")
    if attachment_markers:
        warnings.append("binary attachment payloads are not extracted or verified by this audit")

    summary["status"] = "FAIL" if errors else "PASS"
    summary["source_record_count"] = len(records)
    summary["missing_message_id_count"] = missing_message_ids
    summary["records_with_attachment_markers"] = attachment_markers
    return summary


def audit_archive(
    import_dir: Path,
    archive_id: str,
    *,
    source_sha256: str | None = None,
    staging_manifest: Path | None = None,
) -> dict[str, Any]:
    import_dir = Path(import_dir)
    database = import_dir / "import.sqlite3"
    errors: list[str] = []
    warnings: list[str] = []
    result: dict[str, Any] = {
        "schema_version": "resumable-archive-audit-v1",
        "status": "FAIL",
        "integrity_status": "FAIL",
        "archive_id": archive_id,
        "source_sha256": source_sha256,
        "import_status": "UNKNOWN",
        "snapshot_name": None,
        "conversation_count": 0,
        "checks": {},
        "coverage_status": "UNKNOWN",
        "errors": errors,
        "warnings": warnings,
        "writes_performed": False,
    }
    if not database.is_file():
        errors.append("import.sqlite3 is missing")
        return result

    try:
        connection = sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
    except Exception:
        errors.append("import.sqlite3 cannot be opened read-only")
        return result

    try:
        candidates = connection.execute(
            "SELECT archive_id,source_sha256,snapshot_path,source_bytes,parser_version,"
            "schema_version,status,next_ordinal,committed_conversations,last_error,"
            "next_byte_offset,last_source_locator FROM imports WHERE archive_id=? "
            "ORDER BY updated_at,source_sha256",
            (archive_id,),
        ).fetchall()
        if source_sha256:
            candidates = [row for row in candidates if row["source_sha256"] == source_sha256]
        if not candidates:
            errors.append("no import row matches archive_id/source_sha256")
            return result
        if len(candidates) != 1:
            result["status"] = "AMBIGUOUS"
            result["integrity_status"] = "NOT_CHECKED"
            result["available_source_sha256"] = [row["source_sha256"] for row in candidates]
            errors.clear()
            return result

        imported = candidates[0]
        digest = imported["source_sha256"]
        result["source_sha256"] = digest
        result["import_status"] = imported["status"]
        result["parser_version"] = imported["parser_version"]
        result["schema_version"] = imported["schema_version"]
        result["snapshot_name"] = Path(imported["snapshot_path"]).name
        result["checks"]["import_status_raw_complete"] = imported["status"] == "RAW_COMPLETE"
        if imported["status"] != "RAW_COMPLETE":
            warnings.append(f"import status is {imported['status']}, not RAW_COMPLETE")

        snapshot = Path(imported["snapshot_path"])
        if not snapshot.is_file():
            errors.append("immutable snapshot file is missing")
            result["checks"]["snapshot_sha256_valid"] = False
            result["checks"]["snapshot_size_valid"] = False
        else:
            actual_sha = sha256_file(snapshot)
            actual_size = snapshot.stat().st_size
            result["checks"]["snapshot_sha256_valid"] = actual_sha == digest
            result["checks"]["snapshot_size_valid"] = actual_size == imported["source_bytes"]
            if actual_sha != digest:
                errors.append("immutable snapshot SHA-256 differs from import registry")
            if actual_size != imported["source_bytes"]:
                errors.append("immutable snapshot size differs from import registry")

        rows = connection.execute(
            "SELECT source_locator,source_conversation_id,identity_method,source_ordinal,"
            "payload_json,payload_sha256,source_end_byte_offset FROM raw_conversations "
            "WHERE archive_id=? AND source_sha256=? ORDER BY source_ordinal",
            (archive_id, digest),
        ).fetchall()
        result["conversation_count"] = len(rows)
        expected_ordinals = list(range(len(rows)))
        actual_ordinals = [row["source_ordinal"] for row in rows]
        result["checks"]["source_ordinals_contiguous"] = actual_ordinals == expected_ordinals
        if actual_ordinals != expected_ordinals:
            errors.append("raw conversation source ordinals are not contiguous from zero")
        result["checks"]["committed_count_matches"] = len(rows) == imported["committed_conversations"]
        if len(rows) != imported["committed_conversations"]:
            errors.append("raw conversation count differs from committed_conversations")
        result["checks"]["next_ordinal_matches"] = imported["next_ordinal"] == len(rows)
        if imported["next_ordinal"] != len(rows):
            errors.append("imports.next_ordinal differs from raw conversation count")

        payloads: list[dict[str, Any]] = []
        previous_offset = 0
        for ordinal, row in enumerate(rows):
            payload_json = row["payload_json"]
            if _sha256(payload_json.encode("utf-8")) != row["payload_sha256"]:
                errors.append(f"raw payload SHA-256 mismatch at ordinal {ordinal}")
            try:
                payload = json.loads(payload_json)
            except Exception:
                errors.append(f"raw payload is invalid JSON at ordinal {ordinal}")
                continue
            if not isinstance(payload, dict):
                errors.append(f"raw payload is not an object at ordinal {ordinal}")
                continue
            payloads.append(payload)
            expected_id, expected_method = conversation_id(payload, ordinal)
            if row["source_conversation_id"] != expected_id:
                errors.append(f"conversation identity differs from canonical fallback at ordinal {ordinal}")
            if row["identity_method"] != expected_method:
                errors.append(f"identity_method differs from canonical identity at ordinal {ordinal}")
            expected_locator = f"{archive_id}/{digest}/{expected_id}"
            if row["source_locator"] != expected_locator:
                errors.append(f"source locator differs from canonical identity at ordinal {ordinal}")
            offset = row["source_end_byte_offset"]
            if isinstance(offset, int) and offset > 0:
                if offset <= previous_offset:
                    errors.append(f"source byte offsets are not increasing at ordinal {ordinal}")
                previous_offset = offset
            else:
                errors.append(f"source byte offset is missing/invalid at ordinal {ordinal}")

        if rows:
            last = rows[-1]
            if imported["last_source_locator"] not in (None, last["source_locator"]):
                errors.append("imports.last_source_locator differs from the last committed raw row")
            if imported["next_byte_offset"] != last["source_end_byte_offset"]:
                errors.append("imports.next_byte_offset differs from the last committed raw row")
        elif imported["status"] == "RAW_COMPLETE" and imported["next_byte_offset"] != 0:
            errors.append("empty completed import has a nonzero resume offset")

        if staging_manifest is not None:
            staging_summary = _audit_staging(
                Path(staging_manifest),
                archive_id=archive_id,
                source_sha256=digest,
                source_bytes=imported["source_bytes"],
                imported_payloads=payloads,
                errors=errors,
                warnings=warnings,
            )
            result["staging"] = staging_summary
            result["coverage_status"] = staging_summary.get("coverage_status", "UNKNOWN")
            result["checks"]["staging_integrity_valid"] = staging_summary.get("status") == "PASS"
        else:
            warnings.append("no staging manifest supplied; downstream source records were not audited")
            result["coverage_status"] = "UNKNOWN"
            result["checks"]["staging_integrity_valid"] = False

    except Exception:
        errors.append("archive audit could not complete due to an unexpected validation error")
    finally:
        connection.close()

    result["integrity_status"] = "FAIL" if errors else "PASS"
    if errors:
        result["status"] = "FAIL"
    elif imported["status"] != "RAW_COMPLETE":
        result["status"] = "INTEGRITY_PASS_IMPORT_INCOMPLETE"
    elif staging_manifest is None:
        result["status"] = "INTEGRITY_PASS_RAW_ONLY"
    elif result["coverage_status"] != "complete":
        result["status"] = "INTEGRITY_PASS_COVERAGE_PARTIAL"
    else:
        result["status"] = "INTEGRITY_PASS_SCOPE_REVIEW_REQUIRED"
        warnings.append("archive scope still requires comparison against the intended export window")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--import-dir", type=Path, required=True)
    parser.add_argument("--archive-id", required=True)
    parser.add_argument("--source-sha256")
    parser.add_argument("--staging-manifest", type=Path)
    args = parser.parse_args(argv)
    report = audit_archive(
        args.import_dir, args.archive_id,
        source_sha256=args.source_sha256,
        staging_manifest=args.staging_manifest,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 2 if report.get("integrity_status") == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
