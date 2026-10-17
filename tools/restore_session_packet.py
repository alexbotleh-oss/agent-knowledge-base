#!/usr/bin/env python3
"""Build a source-backed session recovery packet from canonical project files."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

EVENT_ID_RE = re.compile(r"\bEVT-[A-Z0-9-]+\b")
CHECKPOINT_RE = re.compile(r"^#{1,4} .*checkpoint.*$", re.IGNORECASE | re.MULTILINE)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_events(path: Path) -> list[dict[str, Any]]:
    events = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except Exception as exc:
            raise ValueError(f"Invalid JSONL at line {number}: {exc}") from exc
        if not isinstance(event, dict) or not isinstance(event.get("event_id"), str):
            raise ValueError(f"Invalid event at line {number}: event_id required")
        events.append(event)
    return events


def _tail_with_checkpoints(text: str, max_chars: int) -> str:
    headings = list(CHECKPOINT_RE.finditer(text))
    if headings:
        start = headings[-min(6, len(headings))].start()
        selected = text[start:]
        if len(selected) <= max_chars:
            return selected
    return text[-max_chars:]


def load_revision_evidence(project_dir: Path, *, observed_code_head: str | None = None,
                         observed_ci_run_id: str | None = None) -> dict[str, Any]:
    """Expose stored code/CI evidence without treating it as live GitHub state.

    Observed values are supplied by the caller; this function does not fetch remote state.
    """
    path = Path(project_dir) / "CONTINUITY_CHECKPOINT.json"
    if not path.is_file():
        return {"status": "UNAVAILABLE", "reason": "CONTINUITY_CHECKPOINT.json is missing", "writes_performed": False}
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"status": "INVALID", "reason": f"checkpoint JSON is invalid: {exc}", "writes_performed": False}
    if not isinstance(record, dict) or not isinstance(record.get("repository_state"), dict):
        return {"status": "INVALID", "reason": "repository_state is missing or invalid", "writes_performed": False}
    current = record["repository_state"]
    code_head = current.get("last_verified_code_head")
    ci_run_id = current.get("exact_head_ci_run_id")
    ci_conclusion = current.get("exact_head_ci_conclusion")
    if not isinstance(code_head, str) or not re.fullmatch(r"[0-9a-fA-F]{40}", code_head):
        return {"status": "INVALID", "reason": "last_verified_code_head must be a 40-character SHA", "writes_performed": False}
    if not isinstance(ci_run_id, (str, int)) or isinstance(ci_run_id, bool):
        return {"status": "INVALID", "reason": "exact_head_ci_run_id is missing or invalid", "writes_performed": False}
    status = "RECORDED_EVIDENCE_ONLY"
    if observed_code_head is not None:
        status = "OBSERVED_CODE_HEAD_MATCH" if observed_code_head.lower() == code_head.lower() else "OBSERVED_CODE_HEAD_MISMATCH"
    ci_matches = None
    if observed_ci_run_id is not None:
        ci_matches = str(observed_ci_run_id) == str(ci_run_id)
        if observed_code_head is not None and observed_code_head.lower() == code_head.lower() and ci_matches and ci_conclusion == "success":
            status = "OBSERVED_CODE_AND_CI_MATCH"
        elif status == "OBSERVED_CODE_HEAD_MATCH":
            status = "OBSERVED_CI_RUN_MISMATCH"
    return {
        "status": status,
        "recorded_code_head": code_head,
        "recorded_ci_run_id": str(ci_run_id),
        "recorded_ci_conclusion": ci_conclusion,
        "observed_code_head": observed_code_head,
        "observed_ci_run_id": observed_ci_run_id,
        "observed_ci_run_matches": ci_matches,
        "historical_repository_state": record.get("historical_repository_state") if isinstance(record.get("historical_repository_state"), dict) else None,
        "revision_semantics": record.get("revision_semantics") if isinstance(record.get("revision_semantics"), dict) else {},
        "note": "Stored metadata is not live repository/CI proof; observed values are caller-supplied and not independently verified here.",
        "writes_performed": False,
    }

def build_session_packet(task_state: Path, handoff: Path, event_log: Path,
                         *, max_chars: int = 12000, observed_code_head: str | None = None,
                         observed_ci_run_id: str | None = None) -> dict[str, Any]:
    task_state, handoff, event_log = Path(task_state), Path(handoff), Path(event_log)
    missing = [str(path) for path in (task_state, handoff, event_log) if not path.is_file()]
    if missing:
        return {
            "status": "BLOCKED",
            "reason": "Required canonical source files are unavailable.",
            "missing_sources": missing,
            "writes_performed": False,
        }
    if task_state.resolve().parent != handoff.resolve().parent:
        return {
            "status": "BLOCKED",
            "reason": "TASK_STATE.md and HANDOFF.md must come from the same project directory.",
            "project_scope": {
                "task_state_path": str(task_state),
                "handoff_path": str(handoff),
                "event_log_path": str(event_log),
            },
            "writes_performed": False,
        }
    try:
        task_text = task_state.read_text(encoding="utf-8")
        handoff_text = handoff.read_text(encoding="utf-8")
        events = load_events(event_log)
    except Exception as exc:
        return {"status": "BLOCKED", "reason": f"Source validation failed: {exc}", "writes_performed": False}

    seen_event_ids: set[str] = set()
    duplicate_event_ids: set[str] = set()
    for event in events:
        event_id = event["event_id"]
        if event_id in seen_event_ids:
            duplicate_event_ids.add(event_id)
        seen_event_ids.add(event_id)
    if duplicate_event_ids:
        return {
            "status": "BLOCKED",
            "reason": "Duplicate event_id values make source linkage ambiguous.",
            "duplicate_event_ids": sorted(duplicate_event_ids),
            "writes_performed": False,
        }

    task_slice = _tail_with_checkpoints(task_text, max_chars)
    handoff_slice = _tail_with_checkpoints(handoff_text, max_chars)
    referenced_ids = set(EVENT_ID_RE.findall(task_text[:5000] + "\n" + task_slice + "\n" + handoff_slice))
    event_by_id = {event["event_id"]: event for event in events}

    # Resolve the explicit causal references of each linked event as well as
    # direct references from TASK_STATE/HANDOFF. This restores the source event
    # behind an acknowledgement, correction, or other linked event without
    # guessing from semantic similarity.
    pending_ids = list(sorted(referenced_ids))
    linked_event_ids: set[str] = set()
    missing_event_ids: set[str] = set()
    while pending_ids:
        event_id = pending_ids.pop()
        if event_id in linked_event_ids or event_id in missing_event_ids:
            continue
        event = event_by_id.get(event_id)
        if event is None:
            missing_event_ids.add(event_id)
            continue
        linked_event_ids.add(event_id)
        related_ids = event.get("related_event_ids", [])
        if isinstance(related_ids, list):
            pending_ids.extend(
                related_id for related_id in related_ids
                if isinstance(related_id, str) and EVENT_ID_RE.fullmatch(related_id)
            )
        relations = event.get("relations", [])
        if isinstance(relations, list):
            pending_ids.extend(
                relation["event_id"] for relation in relations
                if isinstance(relation, dict)
                and isinstance(relation.get("event_id"), str)
                and EVENT_ID_RE.fullmatch(relation["event_id"])
            )
        acknowledgement = event.get("acknowledgement")
        if isinstance(acknowledgement, dict):
            result_event_id = acknowledgement.get("result_event_id")
            if isinstance(result_event_id, str) and EVENT_ID_RE.fullmatch(result_event_id):
                pending_ids.append(result_event_id)

    # Keep journal order (not lexicographic ID order) to preserve source chronology.
    linked_events = [event for event in events if event["event_id"] in linked_event_ids]
    missing_event_refs = sorted(missing_event_ids)
    latest_task_checkpoint = task_slice
    latest_handoff_checkpoint = handoff_slice

    return {
        "packet_version": "1.0",
        "status": "RESTORED_PACKET" if not missing_event_refs else "PARTIAL",
        "project_scope": {
            "task_state_path": str(task_state),
            "handoff_path": str(handoff),
            "event_log_path": str(event_log),
            "task_project_id": task_state.resolve().parent.name,
            "handoff_project_id": handoff.resolve().parent.name,
            "event_log_project_id": event_log.resolve().parent.name,
            "event_log_scope_match": task_state.resolve().parent == event_log.resolve().parent,
        },
        "source_hashes": {
            "task_state_sha256": sha256_file(task_state),
            "handoff_sha256": sha256_file(handoff),
            "event_log_sha256": sha256_file(event_log),
        },
        "repository_revision_evidence": load_revision_evidence(
            task_state.parent, observed_code_head=observed_code_head,
            observed_ci_run_id=observed_ci_run_id,
        ),
        "task_state_header": "\n".join(task_text.splitlines()[:18]),
        "latest_task_state_excerpt": latest_task_checkpoint,
        "latest_handoff_excerpt": latest_handoff_checkpoint,
        "linked_events": linked_events,
        "missing_event_refs": missing_event_refs,
        "event_count": len(events),
        "warnings": [
            "This is a source-backed recovery packet, not proof that every chat message was captured.",
            "Excerpts preserve source text; the caller must interpret goal, status and next action without treating hypotheses as facts.",
            "Missing event references cause PARTIAL status; unavailable canonical files cause BLOCKED.",
            "No source file is modified.",
        ],
        "writes_performed": False,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task_state", type=Path)
    parser.add_argument("handoff", type=Path)
    parser.add_argument("event_log", type=Path)
    parser.add_argument("--max-chars", type=int, default=12000)
    parser.add_argument("--observed-code-head", help="Code HEAD independently observed by the caller")
    parser.add_argument("--observed-ci-run-id", help="CI run ID independently observed by the caller")
    args = parser.parse_args(argv)
    packet = build_session_packet(args.task_state, args.handoff, args.event_log, max_chars=args.max_chars,
                                  observed_code_head=args.observed_code_head,
                                  observed_ci_run_id=args.observed_ci_run_id)
    print(json.dumps(packet, ensure_ascii=False, indent=2))
    return 0 if packet["status"] == "RESTORED_PACKET" else 2


if __name__ == "__main__":
    raise SystemExit(main())
