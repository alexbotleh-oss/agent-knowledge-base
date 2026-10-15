#!/usr/bin/env python3
"""Shared identity and validation contract for metadata-only source records."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "source_record.schema.json"
SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
REQUIRED_FIELDS = tuple(SCHEMA["required"])
ALLOWED_FIELDS = frozenset(SCHEMA["properties"])
HASH_RE = re.compile(r"^[a-f0-9]{64}$")
BATCH_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,127}$")
SOURCE_ID_RE = re.compile(r"^SRC-[a-f0-9]{24}$")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def archive_key(archive_id: str) -> str:
    return sha256_hex(archive_id.encode("utf-8"))[:12]


def source_id_for_snapshot(archive_id: str, snapshot_sha256: str) -> str:
    return f"archive-{archive_key(archive_id)}-{snapshot_sha256[:12]}"


def batch_id_for_snapshot(archive_id: str, snapshot_sha256: str, parser_version: str) -> str:
    parser_key = sha256_hex(parser_version.encode("utf-8"))[:8]
    return f"src-{archive_key(archive_id)}-{snapshot_sha256[:12]}-{parser_key}"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _is_aware_datetime(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def validate_source_record(record: Any) -> list[str]:
    """Validate the canonical SourceRecord shape and reject undeclared/raw fields."""
    if not isinstance(record, dict):
        return ["record must be a JSON object"]
    errors: list[str] = []
    missing = [field for field in REQUIRED_FIELDS if field not in record]
    unknown = sorted(set(record) - ALLOWED_FIELDS)
    if missing:
        errors.append("missing fields: " + ", ".join(missing))
    if unknown:
        errors.append("unsupported fields: " + ", ".join(unknown))

    for field in ("archive_id", "conversation_id", "source_node_id", "source_locator", "parser_version"):
        if field in record and (not isinstance(record[field], str) or not record[field].strip()):
            errors.append(f"invalid:{field}")
    if "source_record_id" in record:
        value = record["source_record_id"]
        if not isinstance(value, str) or not SOURCE_ID_RE.fullmatch(value):
            errors.append("invalid:source_record_id")
    if "source_locator" in record and isinstance(record.get("source_locator"), str):
        expected_id = "SRC-" + sha256_hex(record["source_locator"].encode("utf-8"))[:24]
        if record.get("source_record_id") != expected_id:
            errors.append("source_record_id does not match source_locator")
        if all(isinstance(record.get(k), str) and record[k] for k in ("archive_id", "conversation_id", "source_node_id")):
            expected_locator = f"{record['archive_id']}/{record['conversation_id']}/{record['source_node_id']}"
            if record["source_locator"] != expected_locator:
                errors.append("source_locator does not match archive/conversation/node identity")

    for field in ("text_sha256", "source_snapshot_sha256"):
        if field in record and (not isinstance(record[field], str) or not HASH_RE.fullmatch(record[field])):
            errors.append(f"invalid:{field}")

    for field in ("source_message_id", "parent_node_id", "role", "content_type"):
        if field in record and record[field] is not None and not isinstance(record[field], str):
            errors.append(f"invalid:{field}")
    if "child_node_ids" in record and (
        not isinstance(record["child_node_ids"], list)
        or any(not isinstance(item, str) for item in record["child_node_ids"])
    ):
        errors.append("invalid:child_node_ids")
    if "source_time" in record and record["source_time"] is not None and not _is_aware_datetime(record["source_time"]):
        errors.append("invalid:source_time")
    if "source_time_unix" in record and record["source_time_unix"] is not None and (
        isinstance(record["source_time_unix"], bool)
        or not isinstance(record["source_time_unix"], (int, float))
    ):
        errors.append("invalid:source_time_unix")
    if "has_attachments" in record and not isinstance(record["has_attachments"], bool):
        errors.append("invalid:has_attachments")
    if "attachment_count" in record and record["attachment_count"] is not None and (
        isinstance(record["attachment_count"], bool)
        or not isinstance(record["attachment_count"], int)
        or record["attachment_count"] < 0
    ):
        errors.append("invalid:attachment_count")
    if "attachment_payloads_inspected" in record and record["attachment_payloads_inspected"] is not None and not isinstance(record["attachment_payloads_inspected"], bool):
        errors.append("invalid:attachment_payloads_inspected")

    if "batch_id" in record and (not isinstance(record["batch_id"], str) or not BATCH_RE.fullmatch(record["batch_id"])):
        errors.append("invalid:batch_id")
    if "registered_at" in record and not _is_aware_datetime(record["registered_at"]):
        errors.append("invalid:registered_at")
    if "schema_version" in record and record["schema_version"] != "source-record-v1":
        errors.append("invalid:schema_version")
    return errors


def identity_payload(record: dict[str, Any]) -> dict[str, Any]:
    """Exclude registry bookkeeping when comparing an idempotent replay."""
    return {key: value for key, value in record.items() if key not in {"batch_id", "registered_at", "schema_version"}}
