#!/usr/bin/env python3
"""Append-only, idempotent child-result publication into the canonical event log.

This is a local repository primitive, not a background cross-chat service.
It writes the existing AGENT_MEMORY_SYSTEM/events.jsonl; it does not create a
second journal or silently resolve the parent task.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REQUIRED = (
    "child_branch_id",
    "parent_checkpoint_id",
    "parent_task_id",
    "result_status",
    "summary",
    "source_refs",
    "reported_at",
)
RESULT_STATUSES = {"RESULT_REPORTED", "NEEDS_REVIEW", "NO_CHANGE"}
EVIDENCE_STATUSES = {"reported", "observed", "inferred", "verified", "unknown"}


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _event_id(child_branch_id: str, parent_checkpoint_id: str, result_key: str) -> str:
    digest = hashlib.sha256(
        "\0".join((child_branch_id, parent_checkpoint_id, result_key)).encode("utf-8")
    ).hexdigest()[:20].upper()
    return "EVT-AGMS-XBR-" + digest


def validate_result(result: dict[str, Any]) -> list[str]:
    errors = []
    for field in REQUIRED:
        if field not in result or result[field] is None:
            errors.append(f"missing:{field}")
    for field in ("child_branch_id", "parent_checkpoint_id", "parent_task_id", "summary", "reported_at"):
        if field in result and (not isinstance(result[field], str) or not result[field].strip()):
            errors.append(f"invalid:{field}")
    if result.get("result_status") not in RESULT_STATUSES:
        errors.append("invalid:result_status")
    if not isinstance(result.get("source_refs"), list) or not result.get("source_refs") or any(
        not isinstance(item, str) or not item.strip() for item in result.get("source_refs", [])
    ):
        errors.append("invalid:source_refs")
    if not isinstance(result.get("result_key"), str) or not result.get("result_key", "").strip():
        errors.append("missing_or_invalid:result_key")
    if result.get("evidence_status", "unknown") not in EVIDENCE_STATUSES:
        errors.append("invalid:evidence_status")
    if result.get("result_status") == "RESULT_REPORTED" and result.get("evidence_status") == "unknown":
        errors.append("reported_result_requires_non_unknown_evidence_status")
    return errors


def _load_events(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    events = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except Exception as exc:
            raise ValueError(f"Invalid JSONL at line {number}: {exc}") from exc
        if not isinstance(item, dict) or not isinstance(item.get("event_id"), str):
            raise ValueError(f"Event at line {number} must be an object with event_id")
        events.append(item)
    return events


def publish_result(event_log: Path, result: dict[str, Any]) -> dict[str, Any]:
    """Validate and append a linked result; exact replay is a no-op, ID conflict fails."""
    errors = validate_result(result)
    if errors:
        return {"status": "REJECTED", "errors": errors, "writes_performed": False}

    event_log = Path(event_log)
    existing = _load_events(event_log)
    event_id = _event_id(result["child_branch_id"], result["parent_checkpoint_id"], result["result_key"])
    evidence_status = result.get("evidence_status", "unknown")
    event = {
        "event_id": event_id,
        "project_id": result.get("project_id", "AGENT_MEMORY_SYSTEM"),
        "event_time": result.get("event_time", "unknown"),
        "source_time": result.get("source_time", "unknown"),
        "recorded_at": result["reported_at"],
        "time_precision": result.get("time_precision", "unknown"),
        "temporal_basis": result.get("temporal_basis", "reported"),
        "type": "cross_branch_result",
        "status": evidence_status,
        "summary": result["summary"],
        "facts": result.get("facts", []),
        "hypotheses": result.get("hypotheses", []),
        "action_taken": result.get("action_taken", "Child branch result published to parent checkpoint."),
        "outcome": result["result_status"],
        "evidence": [{"kind": "reference", "ref": ref} for ref in result["source_refs"]],
        "related_event_ids": result.get("related_event_ids", []),
        "relations": [
            {"type": "reports_to_checkpoint", "checkpoint_id": result["parent_checkpoint_id"]},
            {"type": "belongs_to_task", "task_id": result["parent_task_id"]},
            {"type": "produced_by_branch", "branch_id": result["child_branch_id"]},
        ],
        "next_action": result.get("next_action", "Parent task owner reviews this result before resolving any acceptance criterion."),
        "confidence": result.get("confidence", "unknown"),
        "notes": result.get("notes", ""),
        "branch_return": {
            "child_branch_id": result["child_branch_id"],
            "parent_checkpoint_id": result["parent_checkpoint_id"],
            "parent_task_id": result["parent_task_id"],
            "result_key": result["result_key"],
            "result_status": result["result_status"],
            "owner_acknowledgement": "PENDING",
        },
    }

    for prior in existing:
        if prior.get("event_id") == event_id:
            if _canonical(prior) == _canonical(event):
                return {"status": "ALREADY_PUBLISHED", "event_id": event_id, "writes_performed": False}
            return {
                "status": "CONFLICT",
                "event_id": event_id,
                "writes_performed": False,
                "error": "Same stable result identity already exists with different content; append a correction with a new result_key.",
            }

    event_log.parent.mkdir(parents=True, exist_ok=True)
    new_text = event_log.read_text(encoding="utf-8") if event_log.exists() else ""
    if new_text and not new_text.endswith("\n"):
        new_text += "\n"
    new_text += _canonical(event) + "\n"
    fd, temp_name = tempfile.mkstemp(prefix=".events-", suffix=".tmp", dir=event_log.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(new_text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, event_log)
    finally:
        Path(temp_name).unlink(missing_ok=True)

    return {
        "status": "RESULT_REPORTED",
        "event_id": event_id,
        "parent_checkpoint_id": result["parent_checkpoint_id"],
        "owner_acknowledgement": "PENDING",
        "writes_performed": True,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("event_log", type=Path, help="canonical projects/AGENT_MEMORY_SYSTEM/events.jsonl")
    parser.add_argument("result_json", type=Path, help="child result envelope JSON")
    args = parser.parse_args(argv)
    result = json.loads(args.result_json.read_text(encoding="utf-8"))
    response = publish_result(args.event_log, result)
    print(json.dumps(response, ensure_ascii=False, indent=2))
    return 0 if response["status"] in {"RESULT_REPORTED", "ALREADY_PUBLISHED"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
