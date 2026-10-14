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
import tempfile
from pathlib import Path
from typing import Any


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _load_event_ids(event_log: Path) -> set[str]:
    ids: set[str] = set()
    for number, line in enumerate(event_log.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except Exception as exc:
            raise ValueError(f"Invalid event log at line {number}: {exc}") from exc
        if not isinstance(event, dict) or not isinstance(event.get("event_id"), str):
            raise ValueError(f"Invalid event record at line {number}: event_id is required")
        ids.add(event["event_id"])
    return ids


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
        event_ids = _load_event_ids(event_log)
    except ValueError as exc:
        return {"status": "REJECTED", "writes_performed": False, "errors": [str(exc)]}
    if proposal["event_id"] not in event_ids:
        return {"status": "REJECTED", "writes_performed": False,
                "errors": ["event_id is not present in the canonical event log"]}

    lock_path = task_state.with_name(task_state.name + ".lock")
    try:
        lock_fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        return {"status": "LOCKED", "writes_performed": False, "error": f"Lock exists: {lock_path}"}
    try:
        os.close(lock_fd)
        # Re-read under lock; a stale proposal must never overwrite a concurrent update.
        current = task_state.read_bytes()
        actual_hash = sha256_bytes(current)
        current_text = current.decode("utf-8")
        if actual_hash.lower() != proposal["expected_sha256"].lower():
            return {"status": "STALE_REVISION", "writes_performed": False,
                    "expected_sha256": proposal["expected_sha256"], "actual_sha256": actual_hash}
        if marker in current_text:
            return {"status": "ALREADY_APPLIED" if proposal["checkpoint_markdown"].strip() in current_text[current_text.index(marker):]
                    else "CONFLICT", "update_id": proposal["update_id"], "writes_performed": False}

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
