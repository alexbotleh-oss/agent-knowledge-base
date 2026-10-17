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
import re
import sys
from pathlib import Path
from typing import Any

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from dialogue_attention_controller import inspect as inspect_attention
from check_reuse_policy import evaluate_check_reuse
from minimal_agent_loop import run_minimal_agent_loop


def _infer_task_id(task_state: Path) -> str | None:
    """Infer only an explicit task ID from canonical task-state markers."""
    try:
        text = Path(task_state).read_text(encoding="utf-8")
    except OSError:
        return None
    match = re.search(r"^\s*(?:parent_task_id|task_id)\s*:\s*(\S+)", text, re.I | re.M)
    if match:
        return match.group(1)
    match = re.search(r"^#\s*TASK_STATE\s*[—-]\s*(\S+)", text, re.I | re.M)
    return match.group(1) if match else None


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
    result["source_record_sha256"] = hashlib.sha256(lines[line_number - 1].encode("utf-8")).hexdigest()
    # Preserve the actual attempt/result fields instead of presenting only a summary.
    result["experience_details"] = {
        key: event[key] for key in (
            "facts", "hypotheses", "action_taken", "outcome", "next_action",
            "notes", "related_event_ids", "relations", "evidence", "evidence_refs",
            "tool_tags", "language_tags", "problem_type", "environment",
        ) if key in event
    }
    return result


def _expand_lesson_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    """Resolve a lesson source line only while the captured file hash and lesson ID match."""
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
        lesson = json.loads(lines[line_number - 1])
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        result["source_record_status"] = "SOURCE_RECORD_INVALID"
        result["source_record_error"] = str(exc)
        return result
    if not isinstance(lesson, dict) or lesson.get("lesson_id") != candidate.get("lesson_id"):
        result["source_record_status"] = "SOURCE_LINE_ID_MISMATCH"
        return result
    result["source_record_status"] = "HASH_AND_LESSON_ID_MATCH"
    result["source_record_sha256"] = hashlib.sha256(lines[line_number - 1].encode("utf-8")).hexdigest()
    result["experience_details"] = {
        key: lesson[key] for key in (
            "title", "status", "scope", "project_id", "trigger", "observed_problem",
            "prevention_rule", "applicability", "exceptions", "supersedes", "markers",
            "evidence_refs", "related_event_ids",
        ) if key in lesson
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
    lesson_logs: list[Path] | None = None,
    current_markers: dict[str, Any] | None = None,
    judgments: list[dict[str, Any]] | None = None,
    judgment_verifier=None,
    session_packet: dict[str, Any] | None = None,
    prior_failed_attempts: int = 0,
    risk_level: str = "normal",
) -> dict[str, Any]:
    """Restore the task, inspect the return stack, and retrieve bounded experience candidates."""
    task_state, handoff, event_log = Path(task_state), Path(handoff), Path(event_log)
    loop = run_minimal_agent_loop(
        task_state, handoff, event_log, user_request,
        [Path(p) for p in (experience_logs or [])],
        limit=limit, current_project_id=current_project_id, evidence_root=evidence_root,
        lesson_logs=[Path(p) for p in (lesson_logs or [])],
        current_markers=current_markers, judgments=judgments,
        judgment_verifier=judgment_verifier,
        session_packet=session_packet,
        prior_failed_attempts=prior_failed_attempts,
        risk_level=risk_level,
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
        current_task = loop.get("context", {}).get("active_task_id") or _infer_task_id(task_state)
    attention_active = attention.get("active")
    stack = attention.get("return_stack", [])
    if stack:
        effective_active = stack[-1].get("child", {})
        attention_alignment = (
            "MATCH" if current_task and effective_active.get("task_id") == current_task
            else "TASK_ID_UNKNOWN" if not current_task
            else "BRANCH_ACTIVE_TASK_DIFFERS_FROM_TASK_STATE"
        )
    elif attention_active is None:
        effective_active = {"task_id": current_task or "UNKNOWN", "checkpoint_id": current_checkpoint or "UNKNOWN"}
        attention_alignment = "NO_PERSISTED_ATTENTION_STATE"
    else:
        effective_active = attention_active
        attention_alignment = (
            "TASK_ID_UNKNOWN" if not current_task
            else "MATCH" if attention_active.get("task_id") == current_task
            else "ATTENTION_TASK_DIFFERS_FROM_TASK_STATE"
        )

    lesson_retrieval = dict(loop.get("lesson_retrieval", {"status": "NOT_REQUESTED", "candidates": []}))
    raw_lesson_candidates = lesson_retrieval.get("candidates", []) if isinstance(lesson_retrieval, dict) else []
    lesson_candidates = [_expand_lesson_candidate(item) for item in raw_lesson_candidates if isinstance(item, dict)]
    lesson_retrieval["candidates"] = lesson_candidates
    frontier = dict(loop.get("decision_frontier", {})) if isinstance(loop.get("decision_frontier", {}), dict) else {}
    source_status_by_locator = {}
    stale_sources = []
    for candidate, valid_status in [
        *((item, "HASH_AND_EVENT_ID_MATCH") for item in expanded),
        *((item, "HASH_AND_LESSON_ID_MATCH") for item in lesson_candidates),
    ]:
        source = candidate.get("source", {})
        locator = (
            candidate.get("candidate_type", "event" if "event_id" in candidate else "lesson"),
            candidate.get("event_id", candidate.get("lesson_id")),
            source.get("path") if isinstance(source, dict) else None,
            source.get("line") if isinstance(source, dict) else None,
        )
        status_value = candidate.get("source_record_status", "SOURCE_POINTER_INVALID")
        source_status_by_locator[locator] = status_value
        if status_value != valid_status:
            stale_sources.append({
                "candidate_type": locator[0], "candidate_id": locator[1],
                "source": source if isinstance(source, dict) else {},
                "source_record_status": status_value,
            })
    if stale_sources:
        revised_directions = []
        stale_locators = {
            (item["candidate_type"], item["candidate_id"],
             item["source"].get("path"), item["source"].get("line"))
            for item in stale_sources
        }
        for original in frontier.get("directions", []):
            row = dict(original)
            source = row.get("source", {}) if isinstance(row.get("source"), dict) else {}
            locator = (row.get("candidate_type"), row.get("candidate_id"), source.get("path"), source.get("line"))
            if locator in stale_locators:
                status_value = source_status_by_locator.get(locator, "SOURCE_NOT_CURRENT")
                row["classification"] = "HOLD"
                row["reason"] = "SOURCE_NOT_CURRENT:" + status_value
                row["source_record_status"] = status_value
                row["needs"] = ["refresh retrieval from current source bytes before reviewing this candidate"]
            revised_directions.append(row)
        frontier["directions"] = revised_directions
        frontier["next_discriminating_check"] = {
            "type": "REFRESH_CHANGED_SOURCES",
            "target_ids": sorted({str(item["candidate_id"]) for item in stale_sources}),
            "why": "At least one source changed or could not be resolved after retrieval; refresh candidate evidence before further review.",
        }
        frontier["summary"] = dict(frontier.get("summary", {}))
        frontier["summary"]["stale_source_count"] = len(stale_sources)
    directions = frontier.get("directions", [])
    frontier_groups = {
        classification: [row for row in directions if isinstance(row, dict) and row.get("classification") == classification]
        for classification in ("CONFLICT", "HOLD", "KEEP_FOR_RATIONALE_REVIEW", "EXCLUDE", "OUT_OF_SCOPE")
    }
    # Fingerprint semantic task context rather than whole TASK_STATE/HANDOFF files:
    # unrelated checkpoint metadata must not force an identical check to rerun.
    semantic_context = loop.get("context", {})
    context_payload = {
        "user_request": user_request,
        "active_goal": semantic_context.get("active_goal", "UNKNOWN"),
        "project_id": semantic_context.get("project_id", current_project_id or "UNKNOWN"),
        "scope": semantic_context.get("scope", "UNKNOWN"),
        "constraints": semantic_context.get("constraints", []),
        "blockers": semantic_context.get("blockers", []),
        "acceptance_criteria": semantic_context.get("acceptance_criteria", []),
    }
    source_hashes_for_reuse = {
        "semantic_context": hashlib.sha256(
            json.dumps(context_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
    }
    # Candidate record hashes detect changes to the evidence actually reviewed.
    # If a retrieval source was truncated by the candidate limit, retain the
    # whole source hash as a conservative guard against unseen new candidates.
    retrieval_hashes = raw_retrieval.get("source_hashes", {}) if isinstance(raw_retrieval, dict) else {}
    retrieval_truncated = (
        isinstance(raw_retrieval, dict)
        and raw_retrieval.get("candidate_count_before_limit", len(candidates)) > len(candidates)
    )
    if retrieval_truncated and isinstance(retrieval_hashes, dict):
        source_hashes_for_reuse.update({
            f"truncated_events:{key}": value for key, value in retrieval_hashes.items()
            if isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value)
        })
    lesson_hashes = lesson_retrieval.get("source_hashes", {}) if isinstance(lesson_retrieval, dict) else {}
    lesson_truncated = (
        isinstance(lesson_retrieval, dict)
        and lesson_retrieval.get("candidate_count_before_limit", len(lesson_candidates)) > len(lesson_candidates)
    )
    if lesson_truncated and isinstance(lesson_hashes, dict):
        source_hashes_for_reuse.update({
            f"truncated_lessons:{key}": value for key, value in lesson_hashes.items()
            if isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value)
        })
    candidate_fingerprints = [
        {
            "candidate_type": "event", "candidate_id": str(item.get("event_id")),
            "source_sha256": item.get("source_record_sha256", item.get("source", {}).get("sha256")),
            "source_path": item.get("source", {}).get("path", ""),
            "line": item.get("source", {}).get("line"),
        }
        for item in expanded if isinstance(item.get("source"), dict)
    ]
    candidate_fingerprints.extend(
        {
            "candidate_type": "lesson", "candidate_id": str(item.get("lesson_id")),
            "source_sha256": item.get("source", {}).get("sha256"),
            "source_path": item.get("source", {}).get("path", ""),
            "line": item.get("source", {}).get("line"),
        }
        for item in lesson_candidates if isinstance(item, dict) and isinstance(item.get("source"), dict)
    )
    check_spec = frontier.get("next_discriminating_check") if isinstance(frontier, dict) else None
    if stale_sources:
        check_reuse = {
            "status": "BLOCKED_SOURCE_NOT_CURRENT", "action": "STOP_AND_RETRIEVE_AGAIN",
            "stale_sources": stale_sources, "writes_performed": False,
        }
    elif isinstance(check_spec, dict):
        check_reuse = evaluate_check_reuse(
            attention_path, check_spec, source_hashes_for_reuse, candidate_fingerprints
        )
    else:
        check_reuse = {"status": "NO_CHECK_TO_REUSE", "action": "NO_CHECK", "writes_performed": False}

    grouped = {
        "current_project_scope": [c for c in expanded if c.get("project_scope_match") == "MATCH"],
        "cross_project_excluded": [c for c in expanded if c.get("project_scope_match") == "MISMATCH"],
        "scope_unknown": [c for c in expanded if c.get("project_scope_match") == "UNKNOWN"],
    }
    status = "READY_FOR_REVIEW" if loop.get("status") == "READY_FOR_REVIEW" else "CONTEXT_OR_RETRIEVAL_BLOCKED"
    if stale_sources:
        status = "PARTIAL_SOURCE_PROVENANCE_STALE"
    if attention.get("status") != "OK":
        status = "PARTIAL_ATTENTION_STATE_UNAVAILABLE"
    return {
        "map_version": "1.0",
        "status": status,
        "task_restore": {
            "status": loop.get("restore_packet_status", "UNKNOWN"),
            "task_restore_status": loop.get("task_restore_status", loop.get("restore_packet_status", "UNKNOWN")),
            "semantic_memory": loop.get("semantic_memory", {"status": "NOT_REQUESTED", "coverage_status": "UNKNOWN", "records": []}),
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
        "adaptive_task_flow": loop.get("adaptive_task_flow", {"status": "NOT_AVAILABLE", "mode": "STOP_AND_RECONCILE"}),
        "experience_map": {
            "retrieval_status": raw_retrieval.get("status", "UNKNOWN") if isinstance(raw_retrieval, dict) else "UNKNOWN",
            "method": "bounded lexical overlap over explicitly supplied event logs; no semantic/graph ranking",
            "source_hashes": raw_retrieval.get("source_hashes", {}) if isinstance(raw_retrieval, dict) else {},
            "groups": grouped,
            "candidate_count": len(expanded) + len(lesson_candidates),
            "event_candidates": expanded,
            "lesson_retrieval": lesson_retrieval,
            "lesson_search_stages": loop.get("lesson_search_stages", []),
            "current_markers_source": loop.get("current_markers_source", "UNKNOWN"),
            "applicability": loop.get("applicability", {}),
            "decision_frontier": frontier,
            "review_directions_by_classification": frontier_groups,
            "stale_sources": stale_sources,
            "next_discriminating_check": frontier.get("next_discriminating_check") if isinstance(frontier, dict) else None,
            "check_reuse_policy": check_reuse,
            "candidate_review_only": True,
        },
        "decision_policy": {
            "use_as": "candidate paths for human/agent review, not accepted instructions",
            "transfer_decision": "UNASSESSED",
            "planning_authorized": False,
            "execution_performed": False,
            "writes_performed": False,
            "do_not_repeat": "reuse a recorded PASS only when the check signature, relevant source hashes and candidate identities match exactly",
            "next_check_action": check_reuse.get("action", "RUN_CHECK"),
            "repeat_check": check_reuse.get("action") not in {"DO_NOT_REPEAT_CHECK", "NO_CHECK"},
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
    parser.add_argument("--prior-failed-attempts", type=int, default=0)
    parser.add_argument("--risk-level", choices=("low", "normal", "high", "critical"), default="normal")
    parser.add_argument("--project-id")
    parser.add_argument("--evidence-root", type=Path)
    parser.add_argument("--lesson-log", action="append", default=[], type=Path)
    parser.add_argument("--judgments", type=Path)
    args = parser.parse_args(argv)
    judgments = None
    if args.judgments is not None:
        try:
            judgments = json.loads(args.judgments.read_text(encoding="utf-8"))
        except Exception as exc:
            print(json.dumps({"status": "BLOCKED", "error": f"INVALID_JUDGMENTS_FILE: {exc}"}, ensure_ascii=False))
            return 2
    result = build_task_start_experience_map(
        args.task_state, args.handoff, args.event_log, args.request,
        experience_logs=[Path(p) for p in args.experience_log],
        attention_log=args.attention_log, active_task_id=args.task_id,
        active_checkpoint_id=args.checkpoint_id, limit=args.limit,
        current_project_id=args.project_id, evidence_root=args.evidence_root,
        lesson_logs=args.lesson_log, judgments=judgments,
        prior_failed_attempts=args.prior_failed_attempts, risk_level=args.risk_level,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "READY_FOR_REVIEW" else 2


if __name__ == "__main__":
    raise SystemExit(main())
