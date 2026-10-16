"""Reduce retrieval and applicability outputs into an auditable decision frontier.

This module is intentionally read-only. It does not plan, execute, write memory,
or convert a candidate into permission to act. It makes the current evidence
state explicit so an agent can choose the next *information-gathering* step.
"""
from __future__ import annotations

from typing import Any


def _key(item: dict[str, Any]) -> tuple[str, str]:
    candidate_type = item.get("candidate_type", "lesson")
    candidate_id = item.get("candidate_id", item.get("lesson_id", item.get("event_id", "UNKNOWN")))
    return str(candidate_type), str(candidate_id)


def _candidate_index(candidates: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    return {_key(item): item for item in candidates if isinstance(item, dict)}


def _reason_for(assessment: dict[str, Any]) -> str:
    reason = assessment.get("reason")
    if isinstance(reason, str) and reason:
        return reason
    outcome = assessment.get("outcome")
    return f"NO_EXPLICIT_REASON_FOR_{outcome or 'UNKNOWN_OUTCOME'}"


def _criteria_unknown(assessment: dict[str, Any]) -> list[str]:
    criteria = assessment.get("criteria")
    if not isinstance(criteria, dict):
        return []
    return sorted(
        name for name, item in criteria.items()
        if isinstance(item, dict) and item.get("result") == "UNKNOWN"
    )


def reduce_decision_frontier(
    candidates: list[dict[str, Any]],
    applicability: dict[str, Any],
    *,
    retrieval_status: str = "UNKNOWN",
    lesson_retrieval_status: str = "UNKNOWN",
) -> dict[str, Any]:
    """Build KEEP/EXCLUDE/HOLD/CONFLICT/OUT_OF_SCOPE directions with provenance.

    A direction is a review classification, not an execution instruction.
    Positive KEEP is allowed only when the evaluator has already emitted the
    candidate in usable_as_rationale; outcome labels alone are not trusted.
    """
    if not isinstance(applicability, dict):
        applicability = {}
    indexed = _candidate_index(candidates)
    assessments = applicability.get("assessments", [])
    excluded_rows = applicability.get("excluded", [])
    not_evaluated_rows = applicability.get("not_evaluated", [])
    needs_rows = applicability.get("needs", [])
    conflict_rows = applicability.get("blocked_dependent_decisions", [])
    usable_rows = applicability.get("usable_as_rationale", [])

    def row_map(rows: Any) -> dict[tuple[str, str], dict[str, Any]]:
        if not isinstance(rows, list):
            return {}
        return {_key(row): row for row in rows if isinstance(row, dict)}

    assessment_map = row_map(assessments)
    excluded_map = row_map(excluded_rows)
    not_evaluated_map = row_map(not_evaluated_rows)
    needs_map = row_map(needs_rows)
    conflict_map = row_map(conflict_rows)
    usable_map = row_map(usable_rows)

    directions: list[dict[str, Any]] = []
    for key, candidate in indexed.items():
        assessment = assessment_map.get(key, {})
        outcome = assessment.get("outcome")
        source = candidate.get("source", {})
        provenance = {
            "candidate_id": key[1],
            "candidate_type": key[0],
            "project_id": candidate.get("project_id", "UNKNOWN"),
            "source": source if isinstance(source, dict) else {},
            "retrieval_stage": candidate.get("retrieval_stage", "UNKNOWN"),
            "matched_terms": candidate.get("matched_terms", []),
        }
        if key in conflict_map or outcome == "CONFLICT":
            classification = "CONFLICT"
            reason = _reason_for(assessment) if assessment else "DECLARED_CONFLICT"
            related = conflict_map.get(key, {}).get("conflicts_with", assessment.get("conflicts_with", []))
        elif key in excluded_map or outcome == "NOT_APPLICABLE":
            classification = "EXCLUDE"
            excluded = excluded_map.get(key, {})
            reason = excluded.get("reason") or _reason_for(assessment)
            related = []
        elif key in not_evaluated_map:
            classification = "OUT_OF_SCOPE"
            reason = not_evaluated_map[key].get("reason", "NOT_EVALUATED")
            related = []
        elif key in usable_map:
            classification = "KEEP_FOR_RATIONALE_REVIEW"
            usable = usable_map[key]
            reason = "IN_EVALUATOR_USABLE_AS_RATIONALE"
            related = []
        else:
            classification = "HOLD"
            reason = _reason_for(assessment) if assessment else "NO_APPLICABILITY_ASSESSMENT"
            related = []

        needs = needs_map.get(key, {}).get("needs", [])
        if not isinstance(needs, list):
            needs = []
        unknown_criteria = _criteria_unknown(assessment)
        directions.append({
            **provenance,
            "classification": classification,
            "reason": reason,
            "conflicts_with": related if isinstance(related, list) else [],
            "needs": needs,
            "unknown_criteria": unknown_criteria,
            "adaptation_notes": assessment.get("adaptation_notes", []),
            "caps": assessment.get("caps", []),
        })

    # Keep evaluator-only records visible even if a retrieval wrapper omitted
    # the corresponding source candidate; never silently drop provenance gaps.
    represented = {_key(item) for item in directions}
    for rows, classification in (
        (excluded_rows, "EXCLUDE"),
        (not_evaluated_rows, "OUT_OF_SCOPE"),
        (conflict_rows, "CONFLICT"),
        (needs_rows, "HOLD"),
    ):
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            key = _key(row)
            if key in represented:
                continue
            directions.append({
                "candidate_id": key[1], "candidate_type": key[0],
                "project_id": row.get("project_id", "UNKNOWN"),
                "source": {}, "retrieval_stage": "UNKNOWN", "matched_terms": [],
                "classification": classification,
                "reason": row.get("reason", "ASSESSMENT_WITHOUT_RETRIEVED_CANDIDATE"),
                "conflicts_with": row.get("conflicts_with", []),
                "needs": row.get("needs", []),
                "unknown_criteria": [], "adaptation_notes": [], "caps": [],
                "provenance_gap": True,
            })
            represented.add(key)

    priority = {
        "CONFLICT": 0, "HOLD": 1, "KEEP_FOR_RATIONALE_REVIEW": 2,
        "EXCLUDE": 3, "OUT_OF_SCOPE": 4,
    }
    directions.sort(key=lambda item: (priority.get(item["classification"], 9), item["candidate_type"], item["candidate_id"]))

    conflicts = [item for item in directions if item["classification"] == "CONFLICT"]
    holds = [item for item in directions if item["classification"] == "HOLD"]
    kept = [item for item in directions if item["classification"] == "KEEP_FOR_RATIONALE_REVIEW"]
    excluded = [item for item in directions if item["classification"] == "EXCLUDE"]
    out_of_scope = [item for item in directions if item["classification"] == "OUT_OF_SCOPE"]

    if conflicts:
        next_check = {
            "type": "RECONCILE_CONFLICT",
            "target_ids": sorted({item["candidate_id"] for item in conflicts} | {
                related for item in conflicts for related in item["conflicts_with"] if isinstance(related, str)
            }),
            "why": "Conflicting recommendations block dependent decisions; compare their source evidence and decision scope.",
        }
    elif holds:
        first = holds[0]
        next_check = {
            "type": "RESOLVE_MISSING_EVIDENCE",
            "target_ids": [first["candidate_id"]],
            "criteria": first["unknown_criteria"],
            "needs": first["needs"],
            "why": "Resolve the highest-priority unresolved candidate before treating any lesson as guidance.",
        }
    elif kept:
        next_check = {
            "type": "VERIFY_CURRENT_CONTEXT_AND_BOUNDARIES",
            "target_ids": [item["candidate_id"] for item in kept],
            "why": "Candidates may inform rationale only; currentness, task fit, and action authorization remain separate gates.",
        }
    elif directions:
        next_check = {
            "type": "EXPAND_OR_CHANGE_RETRIEVAL",
            "target_ids": [],
            "why": "No retrieved candidate remains usable; review excluded reasons and broaden the search without reclassifying exclusions as applicable.",
        }
    else:
        next_check = {
            "type": "IMPROVE_RETRIEVAL_INPUTS",
            "target_ids": [],
            "why": "No candidates were retrieved; check query terms, supplied source files, explicit markers, and retrieval status.",
        }

    return {
        "frontier_version": "0.1",
        "status": "FRONTIER_READY" if directions else "NO_CANDIDATES",
        "summary": {
            "candidate_count": len(directions),
            "keep_for_rationale_review": len(kept),
            "excluded": len(excluded),
            "hold": len(holds),
            "conflicts": len(conflicts),
            "out_of_scope": len(out_of_scope),
            "retrieval_status": retrieval_status,
            "lesson_retrieval_status": lesson_retrieval_status,
        },
        "directions": directions,
        "next_discriminating_check": next_check,
        "limitations": [
            "Classification is an evidence-review aid, not a plan or execution permission.",
            "KEEP_FOR_RATIONALE_REVIEW requires membership in evaluator usable_as_rationale.",
            "No source content is changed and no memory is written.",
            "Missing candidate provenance is reported rather than silently repaired.",
        ],
        "writes_performed": False,
        "grants_planning_permission": False,
        "execution_performed": False,
    }
