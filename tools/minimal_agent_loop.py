#!/usr/bin/env python3
"""Run a bounded, read-only restore -> candidate-retrieval -> trust-gate pass.

This is an integration primitive, not an autonomous action executor. It never
writes memory, promotes candidates, resolves conflicts, or executes next_step.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from context_extractor import extract_semantic_context
from context_trust_gate import authorize_next_step
from restore_session_packet import build_session_packet

TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)
STOP_WORDS = {
    "and", "the", "for", "with", "from", "that", "this", "into", "when",
    "что", "как", "для", "при", "или", "это", "там", "тут", "надо", "нужно",
    "чтобы", "после", "перед", "тогда", "где", "какой", "какая", "какие",
}


def _tokens(value: str) -> set[str]:
    return {
        token.casefold()
        for token in TOKEN_RE.findall(value)
        if len(token) >= 3 and token.casefold() not in STOP_WORDS
    }


def _strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            # Keys often carry useful schema labels such as "tool_tags".
            if isinstance(key, str):
                yield key
            yield from _strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)


def _event_search_text(event: dict[str, Any]) -> str:
    preferred = (
        "summary", "facts", "hypotheses", "action_taken", "outcome",
        "notes", "tags", "tool_tags", "language_tags", "project_id",
        "type", "status", "lifecycle_status", "decision_status",
    )
    pieces: list[str] = []
    for field in preferred:
        if field in event:
            pieces.extend(_strings(event[field]))
    # Include explicit source references and typed relations for traceability.
    for field in ("evidence", "source_refs", "relations"):
        if field in event:
            pieces.extend(_strings(event[field]))
    return " ".join(pieces)


def retrieve_experience_candidates(
    query: str, log_paths: list[Path], *, limit: int = 10
) -> dict[str, Any]:
    """Return lexical candidates with source provenance; never judge applicability."""
    query_tokens = _tokens(query)
    if not query_tokens:
        return {
            "status": "NO_QUERY_TERMS",
            "query": query,
            "query_terms": [],
            "candidates": [],
            "source_hashes": {},
            "errors": [],
            "writes_performed": False,
        }

    unique_paths: list[Path] = []
    seen_paths: set[str] = set()
    for raw_path in log_paths:
        path = Path(raw_path)
        identity = str(path.resolve())
        if identity not in seen_paths:
            unique_paths.append(path)
            seen_paths.add(identity)

    source_hashes: dict[str, str] = {}
    indexed: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for path in unique_paths:
        if not path.is_file():
            errors.append({"source": str(path), "error": "MISSING_SOURCE"})
            continue
        raw = path.read_bytes()
        source_hashes[str(path)] = hashlib.sha256(raw).hexdigest()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            errors.append({"source": str(path), "error": f"INVALID_UTF8: {exc}"})
            continue
        for line_number, line in enumerate(text.splitlines(), 1):
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except Exception as exc:
                errors.append({
                    "source": str(path),
                    "error": f"INVALID_JSONL line {line_number}: {exc}",
                })
                break
            if not isinstance(event, dict) or not isinstance(event.get("event_id"), str):
                errors.append({
                    "source": str(path),
                    "error": f"INVALID_EVENT line {line_number}: event_id required",
                })
                break
            event_tokens = _tokens(_event_search_text(event))
            overlap = query_tokens & event_tokens
            if not overlap:
                continue
            # Lexical ranking only. The score is not a confidence or applicability score.
            score = len(overlap) / len(query_tokens)
            summary = event.get("summary", "")
            if isinstance(summary, str) and summary and summary.casefold() in query.casefold():
                score += 0.25
            indexed.append({
                "event_id": event["event_id"],
                "score": round(min(score, 1.25), 4),
                "matched_terms": sorted(overlap),
                "summary": summary if isinstance(summary, str) else "",
                "event_type": event.get("type", "UNKNOWN"),
                "evidence_status": event.get("status", "UNKNOWN"),
                "lifecycle_status": event.get("lifecycle_status", "UNKNOWN"),
                "decision_status": event.get("decision_status", "UNKNOWN"),
                "project_id": event.get("project_id", "UNKNOWN"),
                "event_time": event.get("event_time", "UNKNOWN"),
                "source_time": event.get("source_time", "UNKNOWN"),
                "recorded_at": event.get("recorded_at", "UNKNOWN"),
                "evidence_refs": event.get("evidence", []),
                "relations": event.get("relations", []),
                "source": {
                    "path": str(path),
                    "sha256": source_hashes[str(path)],
                    "line": line_number,
                },
                "transfer_decision": "UNASSESSED",
            })

    if errors:
        # Do not present a partial result as a complete retrieval pass.
        return {
            "status": "BLOCKED",
            "query": query,
            "query_terms": sorted(query_tokens),
            "candidates": [],
            "source_hashes": source_hashes,
            "errors": errors,
            "writes_performed": False,
        }

    indexed.sort(key=lambda item: (-item["score"], item["event_id"], item["source"]["path"]))
    return {
        "status": "CANDIDATES_FOUND" if indexed else "NO_MATCHES",
        "query": query,
        "query_terms": sorted(query_tokens),
        "candidates": indexed[:max(0, limit)],
        "candidate_count_before_limit": len(indexed),
        "source_hashes": source_hashes,
        "ranking": "lexical_overlap_only_not_confidence_or_applicability",
        "warnings": [
            "Candidates are evidence pointers, not accepted lessons or instructions.",
            "Conflicting and disputed records are retained; this pass does not resolve them.",
            "Technology/tool/language tags are descriptors, not proof of transferability.",
            "No memory writes, promotion, task-state updates, or action execution occurred.",
        ],
        "writes_performed": False,
    }


def run_minimal_agent_loop(
    task_state: Path,
    handoff: Path,
    event_log: Path,
    user_request: str,
    experience_logs: list[Path] | None = None,
    *,
    limit: int = 10,
) -> dict[str, Any]:
    """Restore first, then search explicitly supplied event logs for candidates."""
    packet = build_session_packet(task_state, handoff, event_log)
    context = extract_semantic_context(packet)
    trust = authorize_next_step(context)
    query_parts = [user_request.strip(), context.get("active_goal", "UNKNOWN")]
    blockers = context.get("blockers", [])
    if isinstance(blockers, list):
        query_parts.extend(item for item in blockers if isinstance(item, str))
    query = " ".join(part for part in query_parts if part and part != "UNKNOWN")

    logs = [Path(item) for item in (experience_logs or [])]
    if not logs:
        logs = [Path(event_log)]
    retrieval = retrieve_experience_candidates(query, logs, limit=limit)

    candidates_reviewable = (
        context.get("semantic_context_usable")
        and retrieval["status"] not in {"BLOCKED", "NO_QUERY_TERMS"}
    )
    # Source hashes prove that bytes have not changed since packet creation;
    # they do not prove that this checkpoint still represents the user's live goal.
    currentness_gate = {
        "status": "BLOCKED_CURRENTNESS_UNVERIFIED",
        "authorized_for_planning": False,
        "reason": (
            "This tool verifies source-byte freshness, not whether the checkpoint "
            "still matches the live user goal or current repository/PR state."
        ),
    }
    return {
        "loop_version": "0.1",
        "status": "READY_FOR_REVIEW" if candidates_reviewable else "CONTEXT_OR_RETRIEVAL_BLOCKED",
        "restore_packet_status": packet.get("status", "UNKNOWN"),
        "context": context,
        "trust_gate": trust,
        "checkpoint_currentness_gate": currentness_gate,
        "retrieval": retrieval,
        "next_action_policy": (
            "REVIEW_CANDIDATES_ONLY_NO_PLANNING"
            if candidates_reviewable
            else "STOP_AND_RECONCILE_SOURCES"
        ),
        "writes_performed": False,
        "execution_performed": False,
        "limitations": [
            "Lexical retrieval only; no semantic embeddings or complete multidimensional index.",
            "A candidate's applicability must be assessed against tool/language/problem context and evidence.",
            "The trust gate authorizes planning only; this loop does not execute next_step.",
            "This command is explicit and local; it is not automatically invoked at new-chat startup.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task_state", type=Path)
    parser.add_argument("handoff", type=Path)
    parser.add_argument("event_log", type=Path)
    parser.add_argument("--request", required=True, help="current user request")
    parser.add_argument(
        "--experience-log", action="append", default=[],
        help="additional canonical JSONL event log to search; may be repeated",
    )
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args(argv)
    result = run_minimal_agent_loop(
        args.task_state, args.handoff, args.event_log, args.request,
        [Path(item) for item in args.experience_log], limit=args.limit,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "READY_FOR_REVIEW" else 2


if __name__ == "__main__":
    raise SystemExit(main())
