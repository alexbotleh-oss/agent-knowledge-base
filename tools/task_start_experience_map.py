#!/usr/bin/env python3
"""Compose task restore, attention state, and provenance-bound experience retrieval.

This is a read-only task-start entry point. It connects existing primitives but
does not claim semantic applicability, full graph retrieval, automatic ChatGPT
startup, planning permission, or execution.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from dialogue_attention_controller import inspect as inspect_attention
from minimal_agent_loop import run_minimal_agent_loop


def _expand_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    """Resolve the candidate's exact source line only if the captured file hash still matches."""
    result = dict(candidate)
    source = candidate.get("source")
    if not isinstance(source, dict) or not isinstance(source.get("path"), str):
        result["source_record_status"] = "SOURCE_POINTER_INVALID"
        return result
    path = Path(source["path"])
    try:
        raw = path.read_bytes()
    except OSError as exc:
        result["source_record_status"] = "SOURCE_UNAVAILABLE"
        result["source_record_error"] = str(exc)
        return result
    actual_hash = hashlib.sha256(raw).hexdigest()
    if actual_hash != source.get("sha256"):
        result["source_record_status"] = "SOURCE_CHANGED_AFTER_RETRIEVAL"
        result["source_record_sha256_observed"] = actual_hash
        return result
    try:
        lines = raw.decode("utf-8").splitlines()
        line_number = source.get("line")
        if not isinstance(line_number, int) or line_number < 1 or line_number > len(lines):
            raise ValueError("source line locator is outside the captured file")
        event = json.loads(lines[line_number - 1])
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        result["source_record_status"] = "SOURCE_RECORD_INVALID"
        result["source_record_error"] = str(exc)
        return result
    if not isinstance(event, dict) or event.get("event_id") != candidate.get("event_id"):
        result["source_record_status"] = "SOURCE_LINE_ID_MISMATCH"
        return result
    result["source_record_status"] = "HASH_AND_EVENT_ID_MATCH"
    # Preserve the actual attempt/result fields instead of presenting only a summary.
    result["experience_details"] = {
        key: event[key] for key in (
            "facts", "hypotheses", "action_taken", "outcome", "next_action",
            "notes", "related_event_ids", "relations", "evidence", "evidence_refs",
            "tool_tags", "language_tags", "problem_type", "environment",
        ) if key in event
    }
    return result


def build_task_start_experience_map(
    task_state: Path,
    handoff: Path,
    event_log: Path,
    user_request: str,
    *,
    experience_logs: list[Path] | None = None,
    attention_log: Path | None = None,
    active_task_id: str | None = None,
    active_checkpoint_id: str | None = None,
    limit: int = 10,
    current_project_id: str | None = None,
    evidence_root: Path | None = None,
) -> dict[str, Any]:
    """Restore the task, inspect the return stack, and retrieve bounded experience candidates."""
    task_state, handoff, event_log = Path(task_state), Path(handoff), Path(event_log)
    loop = run_minimal_agent_loop(
        task_state, handoff, event_log, user_request,
        [Path(p) for p in (experience_logs or [])],
        limit=limit, current_project_id=current_project_id, evidence_root=evidence_root,
    )
    attention_path = Path(attention_log) if attention_log else (
        Path(__file__).resolve().parents[1] / "projects" / "AGENT_MEMORY_SYSTEM" / "events.jsonl"
    )
    try:
        attention = inspect_attention(attention_path)
    except (OSError, ValueError) as exc:
        attention = {
            "status": "BLOCKED", "reason": str(exc), "active": None,
            "return_stack": [], "deferred_ideas": [], "open_branch_count": None,
        }

    raw_retrieval = loop.get("retrieval", {})
    candidates = raw_retrieval.get("candidates", []) if isinstance(raw_retrieval, dict) else []
    expanded = [_expand_candidate(item) for item in candidates if isinstance(item, dict)]
    current_task = active_task_id
    current_checkpoint = active_checkpoint_id
    if not current_task:
        current_task = loop.get("context", {}).get("active_task_id")
    attention_active = attention.get("active")
    stack = attention.get("return_stack", [])
    if stack:
        effective_active = stack[-1].get("child", {})
        attention_alignment = (
            "MATCH" if current_task and effective_active.get("task_id") == current_task
            else "BRANCH_ACTIVE_TASK_DIFFERS_FROM_TASK_STATE"
        )
    elif attention_active is None:
        effective_active = {"task_id": current_task or "UNKNOWN", "checkpoint_id": current_checkpoint or "UNKNOWN"}
        attention_alignment = "NO_PERSISTED_ATTENTION_STATE"
    else:
        effective_active = attention_active
        attention_alignment = (
            "MATCH" if not current_task or attention_active.get("task_id") == current_task
            else "ATTENTION_TASK_DIFFERS_FROM_TASK_STATE"
        )

    grouped = {
        "current_project_scope": [c for c in expanded if c.get("project_scope_match") == "MATCH"],
        "cross_project_excluded": [c for c in expanded if c.get("project_scope_match") == "MISMATCH"],
        "scope_unknown": [c for c in expanded if c.get("project_scope_match") == "UNKNOWN"],
    }
    status = "READY_FOR_REVIEW" if loop.get("status") == "READY_FOR_REVIEW" else "CONTEXT_OR_RETRIEVAL_BLOCKED"
    if attention.get("status") != "OK":
        status = "PARTIAL_ATTENTION_STATE_UNAVAILABLE"
    return {
        "map_version": "1.0",
        "status": status,
        "task_restore": {
            "status": loop.get("restore_packet_status", "UNKNOWN"),
            "context": loop.get("context", {}),
            "trust_gate": loop.get("trust_gate", {}),
            "checkpoint_currentness_gate": loop.get("checkpoint_currentness_gate", {}),
        },
        "attention": {
            "status": attention.get("status", "UNKNOWN"),
            "active": effective_active,
            "alignment_with_task_state": attention_alignment,
            "return_stack": stack,
            "deferred_ideas": attention.get("deferred_ideas", []),
            "open_branch_count": attention.get("open_branch_count", 0),
        },
        "experience_map": {
            "retrieval_status": raw_retrieval.get("status", "UNKNOWN") if isinstance(raw_retrieval, dict) else "UNKNOWN",
            "method": "bounded lexical overlap over explicitly supplied event logs; no semantic/graph ranking",
            "source_hashes": raw_retrieval.get("source_hashes", {}) if isinstance(raw_retrieval, dict) else {},
            "groups": grouped,
            "candidate_count": len(expanded),
            "candidate_review_only": True,
        },
        "decision_policy": {
            "use_as": "candidate paths for human/agent review, not accepted instructions",
            "transfer_decision": "UNASSESSED",
            "planning_authorized": False,
            "execution_performed": False,
            "writes_performed": False,
            "do_not_repeat": "reuse prior verification only when its evidence is still current and its inputs have not changed",
        },
        "limitations": [
            "Task-start invocation is explicit; automatic new-chat startup is not implemented.",
            "The attention classifier is lexical and its state is only as current as the last event recorded by its caller.",
            "The return stack is not yet wired to automatically update TASK_STATE/HANDOFF.",
            "Experience retrieval is bounded and lexical over supplied logs; it is not full canonical-memory graph traversal or semantic ranking.",
            "Candidate source bytes and event IDs are checked, but claim truth and transferability are not independently validated.",
        ],
        "writes_performed": False,
        "execution_performed": False,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task_state", type=Path)
    parser.add_argument("handoff", type=Path)
    parser.add_argument("event_log", type=Path)
    parser.add_argument("--request", required=True)
    parser.add_argument("--experience-log", action="append", default=[])
    parser.add_argument("--attention-log", type=Path)
    parser.add_argument("--task-id")
    parser.add_argument("--checkpoint-id")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--project-id")
    parser.add_argument("--evidence-root", type=Path)
    args = parser.parse_args(argv)
    result = build_task_start_experience_map(
        args.task_state, args.handoff, args.event_log, args.request,
        experience_logs=[Path(p) for p in args.experience_log],
        attention_log=args.attention_log, active_task_id=args.task_id,
        active_checkpoint_id=args.checkpoint_id, limit=args.limit,
        current_project_id=args.project_id, evidence_root=args.evidence_root,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "READY_FOR_REVIEW" else 2


if __name__ == "__main__":
    raise SystemExit(main())
