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


def _evidence_quality(event: dict[str, Any]) -> dict[str, Any]:
    """Describe evidence metadata conservatively; never validate the claim itself."""
    status = event.get("status")
    status_norm = status.casefold().strip() if isinstance(status, str) else "unknown"
    lifecycle = event.get("lifecycle_status")
    lifecycle_norm = lifecycle.casefold().strip() if isinstance(lifecycle, str) else "unknown"
    decision = event.get("decision_status")
    decision_norm = decision.casefold().strip() if isinstance(decision, str) else "unknown"

    evidence_items: list[Any] = []
    for field in ("evidence", "evidence_refs"):
        value = event.get(field)
        if isinstance(value, list):
            evidence_items.extend(value)
        elif isinstance(value, dict):
            evidence_items.append(value)
    refs = []
    for item in evidence_items:
        if isinstance(item, str) and item.strip():
            refs.append(item.strip())
        elif isinstance(item, dict):
            ref = item.get("ref")
            if isinstance(ref, str) and ref.strip():
                refs.append(ref.strip())
    ref_count = len(refs)

    disputed_states = {"disputed", "conflict", "conflicted", "needs_review", "contested"}
    rejected_states = {"rejected", "invalid"}
    quarantined_states = {"quarantined", "blocked"}
    if decision_norm in rejected_states or lifecycle_norm in rejected_states:
        state = "REJECTED"
        interpretation = "Explicit rejected/invalid lifecycle or decision state; do not use as a lesson."
    elif decision_norm in disputed_states or lifecycle_norm in disputed_states:
        state = "DISPUTED_OR_CONFLICTED"
        interpretation = "Conflict state requires reconciliation; preserve this candidate but do not treat it as settled."
    elif lifecycle_norm in quarantined_states or decision_norm in quarantined_states:
        state = "QUARANTINED_OR_BLOCKED"
        interpretation = "Quarantined/blocked state requires separate review before use."
    elif status_norm == "verified" and ref_count:
        state = "VERIFIED_LABEL_WITH_EVIDENCE_POINTERS"
        interpretation = "The record says verified and supplies reference pointers; neither fact independently proves the references support this claim."
    elif status_norm == "verified":
        state = "VERIFIED_LABEL_WITHOUT_EVIDENCE_POINTERS"
        interpretation = "The verified label has no usable evidence reference in the recognized fields."
    elif status_norm == "observed" and ref_count:
        state = "OBSERVED_WITH_EVIDENCE_POINTERS"
        interpretation = "Observation with reference pointers; claim-level validation and applicability remain unassessed."
    elif status_norm == "observed":
        state = "OBSERVED_WITHOUT_EVIDENCE_POINTERS"
        interpretation = "Observation without a usable evidence reference; corroboration remains unknown."
    elif status_norm in {"reported", "hypothesis", "inferred", "proposed", "draft"}:
        state = "REPORTED_OR_HYPOTHESIS"
        interpretation = "Reported/inferred/proposed state is not an established fact."
    else:
        state = "UNKNOWN_OR_INSUFFICIENT"
        interpretation = "Recognized evidence-quality metadata is insufficient to characterize the claim."
    return {
        "state": state,
        "status_label": status if isinstance(status, str) else "UNKNOWN",
        "lifecycle_status": lifecycle if isinstance(lifecycle, str) else "UNKNOWN",
        "decision_status": decision if isinstance(decision, str) else "UNKNOWN",
        "evidence_pointer_count": ref_count,
        "interpretation": interpretation,
    }


def _validate_evidence_sources(
    event: dict[str, Any], evidence_root: Path | None
) -> dict[str, Any]:
    """Check explicit repository-relative file evidence pointers without network access."""
    refs: list[dict[str, Any]] = []
    evidence_items: list[Any] = []
    for field in ("evidence", "evidence_refs"):
        value = event.get(field)
        if isinstance(value, list):
            evidence_items.extend(value)
        elif isinstance(value, dict):
            evidence_items.append(value)

    root = evidence_root.resolve() if evidence_root is not None else None
    for item in evidence_items:
        if not isinstance(item, dict):
            continue
        kind = item.get("kind")
        ref = item.get("ref")
        if kind != "file" or not isinstance(ref, str) or not ref.strip():
            continue
        raw_ref = ref.strip()
        # Event annotations sometimes append an event/line locator after the path.
        candidate = raw_ref.split(": ", 1)[0]
        path = Path(candidate)
        result: dict[str, Any] = {"ref": raw_ref, "kind": "file"}
        if root is None:
            result["status"] = "NOT_CHECKED_NO_EVIDENCE_ROOT"
        elif path.is_absolute() or path.drive:
            result["status"] = "OUTSIDE_EVIDENCE_ROOT"
        else:
            resolved = (root / path).resolve()
            try:
                resolved.relative_to(root)
            except ValueError:
                result["status"] = "OUTSIDE_EVIDENCE_ROOT"
            else:
                if not resolved.exists():
                    result["status"] = "MISSING"
                elif not resolved.is_file():
                    result["status"] = "NOT_A_FILE"
                else:
                    try:
                        with resolved.open("rb") as handle:
                            handle.read(1)
                    except OSError:
                        result["status"] = "UNREADABLE"
                    else:
                        result["status"] = "EXISTS_READABLE"
        refs.append(result)

    statuses = [item["status"] for item in refs]
    if not refs:
        status = "NO_LOCAL_FILE_REFS"
    elif "MISSING" in statuses:
        status = "MISSING_SOURCE"
    elif "UNREADABLE" in statuses:
        status = "UNREADABLE_SOURCE"
    elif "NOT_A_FILE" in statuses:
        status = "INVALID_SOURCE_TYPE"
    elif "OUTSIDE_EVIDENCE_ROOT" in statuses:
        status = "OUTSIDE_EVIDENCE_ROOT"
    elif "NOT_CHECKED_NO_EVIDENCE_ROOT" in statuses:
        status = "NOT_CHECKED_NO_EVIDENCE_ROOT"
    elif all(value == "EXISTS_READABLE" for value in statuses):
        status = "ALL_LOCAL_FILES_READABLE"
    else:
        status = "UNKNOWN"
    return {
        "status": status,
        "checked_root": str(root) if root is not None else "UNKNOWN",
        "references": refs,
        "claim_validated": False,
    }


def _candidate_review_gate(\n    scope_match: str, evidence_state: str, source_status: str\n) -> str:
    """Combine explicit project scope with metadata quality without granting applicability."""
    if scope_match == "MISMATCH":
        return "OUT_OF_PROJECT_SCOPE"
    if scope_match != "MATCH":
        return "PROJECT_SCOPE_UNKNOWN"
    if source_status in {"MISSING_SOURCE", "UNREADABLE_SOURCE", "INVALID_SOURCE_TYPE"}:
        return "SCOPE_MATCHED_EVIDENCE_SOURCE_UNAVAILABLE_BLOCKED"
    if evidence_state == "DISPUTED_OR_CONFLICTED":
        return "SCOPE_MATCHED_DISPUTED_REQUIRES_CONFLICT_REVIEW"
    if evidence_state in {"REJECTED", "QUARANTINED_OR_BLOCKED"}:
        return "SCOPE_MATCHED_EVIDENCE_STATE_BLOCKED"
    if evidence_state == "VERIFIED_LABEL_WITH_EVIDENCE_POINTERS":
        if source_status == "ALL_LOCAL_FILES_READABLE":
            return "SCOPE_MATCHED_VERIFIED_LABEL_WITH_READABLE_FILES_REVIEW_REQUIRED"
        if source_status == "OUTSIDE_EVIDENCE_ROOT":
            return "SCOPE_MATCHED_EVIDENCE_SOURCE_OUTSIDE_ROOT_REVIEW_REQUIRED"
        if source_status == "NO_LOCAL_FILE_REFS":
            return "SCOPE_MATCHED_NON_FILE_EVIDENCE_REVIEW_REQUIRED"
        return "SCOPE_MATCHED_VERIFIED_LABEL_WITH_REFS_REVIEW_REQUIRED"
    if evidence_state == "VERIFIED_LABEL_WITHOUT_EVIDENCE_POINTERS":
        return "SCOPE_MATCHED_VERIFIED_LABEL_NO_REFS_REVIEW_REQUIRED"
    if evidence_state == "OBSERVED_WITH_EVIDENCE_POINTERS":
        return "SCOPE_MATCHED_OBSERVED_WITH_REFS_REVIEW_REQUIRED"
    if evidence_state == "OBSERVED_WITHOUT_EVIDENCE_POINTERS":
        return "SCOPE_MATCHED_OBSERVED_NO_REFS_REVIEW_REQUIRED"
    if evidence_state == "REPORTED_OR_HYPOTHESIS":
        return "SCOPE_MATCHED_LOW_EVIDENCE_REVIEW_REQUIRED"
    return "SCOPE_MATCHED_EVIDENCE_UNKNOWN_REVIEW_REQUIRED"


def retrieve_experience_candidates(
    query: str,
    log_paths: list[Path],
    *,
    limit: int = 10,
    current_project_id: str | None = None,
    evidence_root: Path | None = None,
) -> dict[str, Any]:
    """Return lexical candidates with provenance and conservative review gates.

    A matching project is only a necessary scope condition, never proof that a
    candidate is applicable. Branch/task matching is not attempted because the
    current event schema does not guarantee a canonical task_branch field.
    """
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
            candidate_project_id = event.get("project_id")
            if not isinstance(candidate_project_id, str) or not candidate_project_id.strip():
                candidate_project_id = None
            if not current_project_id or not current_project_id.strip() or not candidate_project_id:
                scope_match = "UNKNOWN"
            elif candidate_project_id == current_project_id:
                scope_match = "MATCH"
            else:
                scope_match = "MISMATCH"
            evidence_quality = _evidence_quality(event)
            evidence_source_validation = _validate_evidence_sources(
                event, evidence_root
            )
            indexed.append({
                "event_id": event["event_id"],
                "score": round(min(score, 1.25), 4),
                "matched_terms": sorted(overlap),
                "summary": summary if isinstance(summary, str) else "",
                "event_type": event.get("type", "UNKNOWN"),
                "evidence_status": event.get("status", "UNKNOWN"),
                "lifecycle_status": event.get("lifecycle_status", "UNKNOWN"),
                "decision_status": event.get("decision_status", "UNKNOWN"),
                "project_id": candidate_project_id or "UNKNOWN",
                "project_scope_match": scope_match,
                "applicability_gate": (
                    "SCOPE_MATCHED_REQUIRES_REVIEW"
                    if scope_match == "MATCH"
                    else "OUT_OF_PROJECT_SCOPE"
                    if scope_match == "MISMATCH"
                    else "PROJECT_SCOPE_UNKNOWN"
                ),
                "evidence_quality": evidence_quality,
                "evidence_source_validation": evidence_source_validation,
                "candidate_review_gate": _candidate_review_gate(
                    scope_match,
                    evidence_quality["state"],
                    evidence_source_validation["status"],
                ),
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
        "applicability_policy": {
            "current_project_id": current_project_id or "UNKNOWN",
            "project_match_is_necessary_not_sufficient": True,
            "task_branch_match": "NOT_EVALUATED_SCHEMA_FIELD_NOT_GUARANTEED",
            "same_project_does_not_promote_candidate": True,
            "evidence_quality_is_metadata_not_claim_validation": True,
            "verified_label_alone_is_never_sufficient": True,
            "candidate_review_gate_is_explanatory_not_authorization": True,
            "evidence_source_check_is_local_file_existence_and_readability_only": True,
            "evidence_source_check_never_validates_claim_content": True,
        },
        "warnings": [
            "Candidates are evidence pointers, not accepted lessons or instructions.",
            "A verified status label and a non-empty evidence pointer do not prove that the cited source supports the claim.",
            "Evidence quality, local source availability and project scope only route candidates for review; transfer_decision remains UNASSESSED.",
            "Local file evidence is checked only under an explicit --evidence-root; URLs and non-file references are not fetched or validated.",
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
    current_project_id: str | None = None,
    evidence_root: Path | None = None,
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
    retrieval = retrieve_experience_candidates(
        query, logs, limit=limit, current_project_id=current_project_id,
        evidence_root=evidence_root,
    )

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
    parser.add_argument(
        "--project-id",
        default=None,
        help="explicit canonical project_id for conservative experience scope matching",
    )
    parser.add_argument(
        "--evidence-root",
        type=Path,
        default=None,
        help="root for checking repository-relative kind=file evidence references; no network access",
    )
    args = parser.parse_args(argv)
    result = run_minimal_agent_loop(
        args.task_state, args.handoff, args.event_log, args.request,
        [Path(item) for item in args.experience_log],
        limit=args.limit,
        current_project_id=args.project_id,
        evidence_root=args.evidence_root,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "READY_FOR_REVIEW" else 2


if __name__ == "__main__":
    raise SystemExit(main())
