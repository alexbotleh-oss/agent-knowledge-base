#!/usr/bin/env python3
"""Persist a verified outcome as a provenance-bound experience candidate.

This is an explicit capture step, not automatic semantic-memory promotion.
It verifies that a caller-specified acceptance marker occurs in a real evidence
file, then appends an auditable candidate event to a project event log. The
marker check proves only that narrow condition; it does not judge the meaning
of the evidence or make the candidate an approved instruction.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,191}$")


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@contextlib.contextmanager
def _lock(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as stream:
        if os.name == "nt":
            import msvcrt
            stream.seek(0, os.SEEK_END)
            if stream.tell() == 0:
                stream.write(b"0")
                stream.flush()
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def _read_events(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    raw = path.read_bytes()
    try:
        lines = raw.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise ValueError("event log is not UTF-8") from exc
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for number, line in enumerate(lines, 1):
        if not line.strip():
            raise ValueError(f"event log has blank line {number}")
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"event log has invalid JSON at line {number}") from exc
        if not isinstance(row, dict) or not isinstance(row.get("event_id"), str):
            raise ValueError(f"event log line {number} must be an object with event_id")
        if row["event_id"] in seen:
            raise ValueError(f"event log has duplicate event_id at line {number}")
        seen.add(row["event_id"])
        rows.append(row)
    return rows


def capture_verified_experience_candidate(
    event_log: Path,
    *,
    evidence_root: Path,
    project_id: str,
    task_id: str,
    request_summary: str,
    action_taken: str,
    acceptance_criterion: str,
    expected_evidence_marker: str,
    evidence_file: Path,
    observed_outcome: str,
    related_event_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Append one idempotent candidate only after an exact evidence-marker check."""
    required = {
        "project_id": project_id,
        "task_id": task_id,
        "request_summary": request_summary,
        "action_taken": action_taken,
        "acceptance_criterion": acceptance_criterion,
        "expected_evidence_marker": expected_evidence_marker,
        "observed_outcome": observed_outcome,
    }
    if any(not isinstance(value, str) or not value.strip() for value in required.values()):
        return {"status": "BLOCKED_REQUIRED_FIELD_MISSING", "writes_performed": False}
    if not ID_RE.fullmatch(task_id) or not ID_RE.fullmatch(project_id):
        return {"status": "BLOCKED_INVALID_PROJECT_OR_TASK_ID", "writes_performed": False}
    if not isinstance(related_event_ids, (list, type(None))) or any(
        not isinstance(item, str) or not ID_RE.fullmatch(item) for item in (related_event_ids or [])
    ):
        return {"status": "BLOCKED_INVALID_RELATED_EVENT_ID", "writes_performed": False}

    root = Path(evidence_root).resolve()
    evidence_path = Path(evidence_file)
    if evidence_path.is_symlink():
        return {"status": "BLOCKED_EVIDENCE_SYMLINK", "writes_performed": False}
    resolved_evidence = evidence_path.resolve()
    try:
        relative_evidence = resolved_evidence.relative_to(root).as_posix()
    except ValueError:
        return {"status": "BLOCKED_EVIDENCE_OUTSIDE_ROOT", "writes_performed": False}
    try:
        evidence_bytes = resolved_evidence.read_bytes()
        evidence_text = evidence_bytes.decode("utf-8")
    except (OSError, UnicodeDecodeError):
        return {"status": "BLOCKED_EVIDENCE_UNREADABLE", "writes_performed": False}
    if expected_evidence_marker not in evidence_text:
        return {
            "status": "BLOCKED_ACCEPTANCE_MARKER_NOT_FOUND",
            "evidence_sha256": _sha(evidence_bytes),
            "writes_performed": False,
        }

    target = Path(event_log)
    if target.is_symlink():
        return {"status": "BLOCKED_EVENT_LOG_SYMLINK", "writes_performed": False}
    target = target.resolve()
    try:
        target.relative_to(root)
    except ValueError:
        return {"status": "BLOCKED_EVENT_LOG_OUTSIDE_ROOT", "writes_performed": False}

    evidence_sha = _sha(evidence_bytes)
    identity = {
        "project_id": project_id,
        "task_id": task_id,
        "request_summary": request_summary.strip(),
        "action_taken": action_taken.strip(),
        "acceptance_criterion": acceptance_criterion.strip(),
        "expected_evidence_marker": expected_evidence_marker,
        "observed_outcome": observed_outcome.strip(),
        "evidence_ref": relative_evidence,
        "evidence_sha256": evidence_sha,
        "related_event_ids": sorted(set(related_event_ids or [])),
    }
    event_id = "EXP-" + _sha(_canonical(identity))[:32]
    now = datetime.now().astimezone().isoformat()
    record = {
        "event_id": event_id,
        "project_id": project_id,
        "event_time": now,
        "source_time": "unknown",
        "recorded_at": now,
        "time_precision": "exact",
        "temporal_basis": "artifact_timestamp",
        "type": "test",
        "summary": f"Verified outcome candidate for {request_summary.strip()}",
        "status": "verified",
        "facts": [
            f"Acceptance criterion: {acceptance_criterion.strip()}",
            f"Evidence marker was found exactly in {relative_evidence}",
            f"Evidence SHA-256: {evidence_sha}",
        ],
        "hypotheses": [],
        "action_taken": action_taken.strip(),
        "outcome": observed_outcome.strip(),
        "evidence": [{
            "kind": "file",
            "ref": relative_evidence,
            "sha256": evidence_sha,
            "source_created_at": "unknown",
        }],
        "related_event_ids": identity["related_event_ids"],
        "relations": [],
        "next_action": "Review applicability and provenance before treating this candidate as guidance",
        "confidence": "medium",
        "notes": (
            "Experience candidate only; not an approved lesson and not promoted to semantic memory. "
            "The capture tool checked the exact marker's presence and evidence hash; it did not "
            "independently interpret the acceptance criterion or prove general applicability."
        ),
        "capture_identity_sha256": _sha(_canonical(identity)),
    }

    try:
        with _lock(target.with_name(target.name + ".capture.lock")):
            rows = _read_events(target)
            for existing in rows:
                if existing.get("event_id") == event_id:
                    if existing.get("capture_identity_sha256") == record["capture_identity_sha256"]:
                        return {
                            "status": "ALREADY_CAPTURED",
                            "event_id": event_id,
                            "event_log": str(target),
                            "evidence_sha256": evidence_sha,
                            "writes_performed": False,
                        }
                    return {
                        "status": "BLOCKED_EVENT_ID_CONFLICT",
                        "event_id": event_id,
                        "writes_performed": False,
                    }
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("ab") as stream:
                stream.write(_canonical(record) + b"\n")
                stream.flush()
                os.fsync(stream.fileno())
    except (OSError, ValueError) as exc:
        return {"status": "BLOCKED_EVENT_LOG_INVALID_OR_UNWRITABLE", "reason": str(exc), "writes_performed": False}

    return {
        "status": "CAPTURED_CANDIDATE",
        "event_id": event_id,
        "event_log": str(target),
        "evidence_sha256": evidence_sha,
        "semantic_memory_promoted": False,
        "writes_performed": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event-log", required=True, type=Path)
    parser.add_argument("--evidence-root", required=True, type=Path)
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--request-summary", required=True)
    parser.add_argument("--action-taken", required=True)
    parser.add_argument("--acceptance-criterion", required=True)
    parser.add_argument("--expected-evidence-marker", required=True)
    parser.add_argument("--evidence-file", required=True, type=Path)
    parser.add_argument("--observed-outcome", required=True)
    parser.add_argument("--related-event-id", action="append", default=[])
    args = parser.parse_args(argv)
    result = capture_verified_experience_candidate(
        args.event_log,
        evidence_root=args.evidence_root,
        project_id=args.project_id,
        task_id=args.task_id,
        request_summary=args.request_summary,
        action_taken=args.action_taken,
        acceptance_criterion=args.acceptance_criterion,
        expected_evidence_marker=args.expected_evidence_marker,
        evidence_file=args.evidence_file,
        observed_outcome=args.observed_outcome,
        related_event_ids=args.related_event_id,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") in {"CAPTURED_CANDIDATE", "ALREADY_CAPTURED"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
