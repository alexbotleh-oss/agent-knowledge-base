#!/usr/bin/env python3
"""Apply an append-only task-state checkpoint guarded by expected file hash and event evidence.

This tool appends a new checkpoint block; it never replaces prior task-state text.
It is a local repository primitive, not an automatic chat synchronizer.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _load_event_records(event_log: Path) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for number, line in enumerate(event_log.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except Exception as exc:
            raise ValueError(f"Invalid event log at line {number}: {exc}") from exc
        if not isinstance(event, dict) or not isinstance(event.get("event_id"), str):
            raise ValueError(f"Invalid event record at line {number}: event_id is required")
        event_id = event["event_id"]
        if event_id in records:
            raise ValueError(f"Duplicate event_id {event_id!r} at line {number}")
        records[event_id] = event
    return records


def _task_id_from_state(task_state: Path) -> str | None:
    text = task_state.read_text(encoding="utf-8")
    match = re.search(r"^#\s*(?:TASK_STATE|Task state)\s*[—-]\s*(\S+)", text, re.I | re.M)
    return match.group(1).strip() if match else None


def _relation_value(event: dict[str, Any], relation_type: str, key: str) -> Any:
    relations = event.get("relations")
    if not isinstance(relations, list):
        return None
    for relation in relations:
        if isinstance(relation, dict) and relation.get("type") == relation_type:
            return relation.get(key)
    return None


def _validate_supporting_event(
    event_records: dict[str, dict[str, Any]],
    event_id: str,
    proposal: dict[str, Any],
    task_state: Path,
    event_log: Path,
) -> str | None:
    event = event_records.get(event_id)
    if event is None:
        return "event_id is not present in the canonical event log"

    task_project = task_state.resolve().parent.name
    event_project = event_log.resolve().parent.name
    event_type = event.get("type")

    if event_type == "cross_branch_result":
        return "cross_branch_result must be acknowledged before it can update task state"

    if event_type == "cross_branch_result_acknowledged":
        acknowledgement = event.get("acknowledgement")
        if not isinstance(acknowledgement, dict):
            return "cross-branch acknowledgement metadata is missing"
        if event.get("outcome") != "accepted" or acknowledgement.get("decision") != "accepted":
            return "only an explicitly accepted cross-branch result may update task state"
        task_id = _task_id_from_state(task_state)
        if not task_id:
            return "target TASK_STATE.md must declare its task ID for cross-project result application"
        if acknowledgement.get("parent_checkpoint_id") != proposal.get("parent_checkpoint_id"):
            return "acknowledgement parent checkpoint does not match the proposed checkpoint"
        if _relation_value(event, "reports_to_checkpoint", "checkpoint_id") != proposal.get("parent_checkpoint_id"):
            return "acknowledgement checkpoint relation does not match the proposed checkpoint"
        if _relation_value(event, "belongs_to_task", "task_id") != task_id:
            return "acknowledgement task relation does not match target TASK_STATE.md"
        result_id = acknowledgement.get("result_event_id")
        result_event = event_records.get(result_id) if isinstance(result_id, str) else None
        if not isinstance(result_event, dict) or result_event.get("type") != "cross_branch_result":
            return "acknowledgement does not reference an existing cross_branch_result"
        branch_return = result_event.get("branch_return")
        if not isinstance(branch_return, dict):
            return "cross-branch result metadata is missing"
        if branch_return.get("parent_checkpoint_id") != proposal.get("parent_checkpoint_id"):
            return "child result parent checkpoint does not match the proposed checkpoint"
        if branch_return.get("parent_task_id") != task_id:
            return "child result parent task does not match target TASK_STATE.md"
        if _relation_value(event, "acknowledges_result", "event_id") != result_id:
            return "acknowledgement relation does not match its result event"
        return None

    if task_project != event_project:
        return "cross-project event evidence requires an accepted, explicitly linked cross-branch acknowledgement"
    recorded_project = event.get("project_id")
    if isinstance(recorded_project, str) and recorded_project.strip() and recorded_project != task_project:
        return "event project_id does not match target project directory"
    return None


def apply_checkpoint(
    task_state: Path,
    event_log: Path,
    proposal: dict[str, Any],
    *,
    trust_verdict: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Apply a checkpoint only when an explicit trust-gate decision authorizes planning.

    The verdict is an input contract, not cryptographic proof of its origin. Callers
    must obtain it from context_trust_gate.authorize_next_step; this function fails
    closed when it is absent, malformed, or not explicitly authorized.
    """
    required = ("update_id", "expected_sha256", "parent_checkpoint_id", "event_id", "checkpoint_markdown")
    errors = [f"missing:{key}" for key in required if key not in proposal or proposal[key] is None]
    for key in ("update_id", "expected_sha256", "parent_checkpoint_id", "event_id", "checkpoint_markdown"):
        if key in proposal and (not isinstance(proposal[key], str) or not proposal[key].strip()):
            errors.append(f"invalid:{key}")
    if errors:
        return {"status": "REJECTED", "errors": errors, "writes_performed": False}
    if len(proposal["expected_sha256"]) != 64 or any(c not in "0123456789abcdefABCDEF" for c in proposal["expected_sha256"]):
        return {"status": "REJECTED", "errors": ["invalid:expected_sha256"], "writes_performed": False}

    task_state = Path(task_state)
    event_log = Path(event_log)
    if task_state.name != "TASK_STATE.md" or "projects" not in task_state.parts:
        return {"status": "REJECTED", "errors": ["writes are restricted to a TASK_STATE.md under a projects/ directory"], "writes_performed": False}
    if event_log.name != "events.jsonl" or "projects" not in event_log.parts:
        return {"status": "REJECTED", "errors": ["event evidence must come from an events.jsonl under a projects/ directory"], "writes_performed": False}
    if not task_state.is_file() or not event_log.is_file():
        return {"status": "REJECTED", "errors": ["task state and canonical event log must already exist"], "writes_performed": False}
    marker = f"<!-- guarded-task-update:{proposal['update_id']} -->"
    current = task_state.read_bytes()
    current_text = current.decode("utf-8")
    if marker in current_text:
        marker_pos = current_text.index(marker)
        prior_block = current_text[marker_pos:]
        if proposal["checkpoint_markdown"].strip() in prior_block:
            return {"status": "ALREADY_APPLIED", "update_id": proposal["update_id"], "writes_performed": False}
        return {"status": "CONFLICT", "update_id": proposal["update_id"], "writes_performed": False,
                "error": "Update ID already exists with different content."}

    actual_hash = sha256_bytes(current)
    if actual_hash.lower() != proposal["expected_sha256"].lower():
        return {"status": "STALE_REVISION", "writes_performed": False,
                "expected_sha256": proposal["expected_sha256"], "actual_sha256": actual_hash}
    try:
        event_records = _load_event_records(event_log)
    except ValueError as exc:
        return {"status": "REJECTED", "writes_performed": False, "errors": [str(exc)]}
    evidence_error = _validate_supporting_event(
        event_records, proposal["event_id"], proposal, task_state, event_log
    )
    if evidence_error:
        return {"status": "REJECTED", "writes_performed": False, "errors": [evidence_error]}

    # No-write validation (schema, path, idempotency, revision and event evidence)
    # runs before trust authorization so callers receive precise conflict/stale
    # statuses. The gate remains mandatory before any write attempt.
    if not isinstance(trust_verdict, dict):
        return {
            "status": "BLOCKED",
            "reason": "TrustPolicyViolated",
            "trust_status": "MISSING_TRUST_VERDICT",
            "writes_performed": False,
        }
    if trust_verdict.get("status") != "AUTHORIZED_FOR_PLANNING":
        return {
            "status": "BLOCKED",
            "reason": "TrustPolicyViolated",
            "trust_status": trust_verdict.get("status", "INVALID_TRUST_VERDICT"),
            "writes_performed": False,
        }

    # Global lock order: journal lock -> task-state lock. Event registry writers
    # acquire only the journal lock, so this order avoids lock-order cycles and
    # keeps event evidence stable through the final trust check and state replace.
    journal_lock_path = event_log.with_name(event_log.name + ".lock")
    task_lock_path = task_state.with_name(task_state.name + ".lock")
    acquired: list[Path] = []
    try:
        for lock_path, label in (
            (journal_lock_path, "Journal"),
            (task_lock_path, "Task-state"),
        ):
            try:
                lock_fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            except FileExistsError:
                return {
                    "status": "LOCKED",
                    "writes_performed": False,
                    "error": f"{label} lock exists: {lock_path}. Verify no writer is active before manual stale-lock recovery.",
                }
            acquired.append(lock_path)
            with os.fdopen(lock_fd, "w", encoding="utf-8") as lock_stream:
                lock_stream.write(json.dumps({"pid": os.getpid(), "started_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()}))
                lock_stream.flush()
                os.fsync(lock_stream.fileno())

        # Re-read under both locks. The shared journal lock prevents the event
        # registry from changing evidence until this operation completes.
        current = task_state.read_bytes()
        actual_hash = sha256_bytes(current)
        current_text = current.decode("utf-8")
        if actual_hash.lower() != proposal["expected_sha256"].lower():
            return {"status": "STALE_REVISION", "writes_performed": False,
                    "expected_sha256": proposal["expected_sha256"], "actual_sha256": actual_hash}
        if marker in current_text:
            return {"status": "ALREADY_APPLIED" if proposal["checkpoint_markdown"].strip() in current_text[current_text.index(marker):]
                    else "CONFLICT", "update_id": proposal["update_id"], "writes_performed": False}

        # Trust is recomputed while both canonical files are protected by the
        # lock protocol. HANDOFF is still externally mutable and not covered by
        # these locks; source freshness checks therefore remain mandatory.
        handoff_path = task_state.with_name("HANDOFF.md")
        try:
            from context_extractor import extract_semantic_context
            from context_trust_gate import authorize_next_step
            from restore_session_packet import build_session_packet

            packet = build_session_packet(task_state, handoff_path, event_log)
            current_context = extract_semantic_context(packet)
            current_verdict = authorize_next_step(current_context)
        except Exception as exc:
            return {
                "status": "BLOCKED",
                "reason": "TrustPolicyViolated",
                "trust_status": "TRUST_RECHECK_FAILED",
                "details": str(exc),
                "writes_performed": False,
            }
        if current_verdict.get("status") != "AUTHORIZED_FOR_PLANNING":
            return {
                "status": "BLOCKED",
                "reason": "TrustPolicyViolated",
                "trust_status": current_verdict.get("status", "INVALID_TRUST_VERDICT"),
                "writes_performed": False,
            }
        try:
            event_records = _load_event_records(event_log)
        except ValueError as exc:
            return {"status": "REJECTED", "writes_performed": False, "errors": [str(exc)]}
        evidence_error = _validate_supporting_event(
            event_records, proposal["event_id"], proposal, task_state, event_log
        )
        if evidence_error:
            return {"status": "REJECTED", "writes_performed": False, "errors": [evidence_error]}

        block = (
            f"\n\n## Checkpoint update {proposal['update_id']}\n\n"
            f"{marker}\n"
            f"- Parent checkpoint: `{proposal['parent_checkpoint_id']}`\n"
            f"- Supporting event: `{proposal['event_id']}`\n\n"
            f"{proposal['checkpoint_markdown'].strip()}\n"
        )
        new_bytes = current + block.encode("utf-8")
        fd, temp_name = tempfile.mkstemp(prefix=".task-state-", suffix=".tmp", dir=task_state.parent)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(new_bytes)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp_name, task_state)
        finally:
            Path(temp_name).unlink(missing_ok=True)
        return {"status": "APPLIED", "update_id": proposal["update_id"],
                "event_id": proposal["event_id"], "new_sha256": sha256_bytes(new_bytes),
                "writes_performed": True}
    finally:
        # Release in reverse acquisition order. Never break a lock automatically:
        # a leftover lock requires operator inspection before recovery.
        for lock_path in reversed(acquired):
            lock_path.unlink(missing_ok=True)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task_state", type=Path)
    parser.add_argument("event_log", type=Path)
    parser.add_argument("proposal_json", type=Path)
    parser.add_argument(
        "--trust-verdict-json", type=Path, required=True,
        help="JSON decision produced by context_trust_gate.py; only AUTHORIZED_FOR_PLANNING permits writes",
    )
    args = parser.parse_args(argv)
    proposal = json.loads(args.proposal_json.read_text(encoding="utf-8"))
    trust_verdict = json.loads(args.trust_verdict_json.read_text(encoding="utf-8"))
    result = apply_checkpoint(args.task_state, args.event_log, proposal, trust_verdict=trust_verdict)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] in {"APPLIED", "ALREADY_APPLIED"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
