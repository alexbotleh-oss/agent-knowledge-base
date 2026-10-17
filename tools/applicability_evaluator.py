#!/usr/bin/env python3
"""Read-only applicability evaluator for experience candidates (UMC-03 target spec).

The evaluator produces its own assessment of retrieval candidates. It never
writes memory, never changes a record's status or schema, never promotes
anything and never grants permission to plan or act: it can only narrow what
retrieved memory may be used to justify.

Conditions are NOT extracted from free text. Explicit judgments (judged_by: rule | user | agent) are retained with their basis locator, but a caller-supplied label or non-empty basis_ref is not proof. Until a trusted verifier is explicitly injected, permissive judgments stay UNKNOWN and yield INSUFFICIENT_DATA.
"""
from __future__ import annotations

import re
from typing import Any, Callable

APPLICABLE = "APPLICABLE"
APPLICABLE_WITH_ADAPTATION = "APPLICABLE_WITH_ADAPTATION"
NOT_APPLICABLE = "NOT_APPLICABLE"
INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
CONFLICT = "CONFLICT"

# Designed evaluator outcomes. They are not repository record statuses.
OUTCOMES = (APPLICABLE, APPLICABLE_WITH_ADAPTATION, NOT_APPLICABLE, INSUFFICIENT_DATA, CONFLICT)

CORE_CRITERIA = (
    "problem_similarity", "trigger", "applicability",
    "exceptions", "evidence_support", "circumstances_unchanged",
)
CONFLICT_CRITERION = "compatibility"
JUDGES = ("rule", "user", "agent")

# Allowed result values per criterion. Restrictive values only narrow use.
_RESULTS = {name: ("MATCH", "MISMATCH", "UNKNOWN") for name in CORE_CRITERIA}
_RESULTS["exceptions"] = ("NOT_TRIGGERED", "TRIGGERED", "UNKNOWN")
_RESULTS[CONFLICT_CRITERION] = ("COMPATIBLE", "CONFLICT", "UNKNOWN")
_RESTRICTIVE = {"MISMATCH", "TRIGGERED", "CONFLICT"}
_PERMISSIVE = {"MATCH", "NOT_TRIGGERED", "COMPATIBLE"}

RETIRED_STATUSES = {"superseded", "deprecated"}
# Lesson-record status values whose handling is defined in the spec (3.1).
KNOWN_LESSON_STATUSES = {"candidate", "validated", "disputed"} | RETIRED_STATUSES


def _norm_status(value: Any) -> str:
    return value.strip().casefold() if isinstance(value, str) else ""


def _candidate_key(candidate: dict[str, Any]) -> tuple[str, str]:
    ctype = candidate.get("candidate_type", "event")
    cid = candidate.get("lesson_id") if ctype == "lesson" else candidate.get("event_id")
    return str(ctype), str(cid) if cid is not None else "UNKNOWN"


def _validate_judgments(judgments: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return (usable judgments, issues). Malformed items are reported, never guessed."""
    usable: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    if judgments is None:
        return usable, issues
    if not isinstance(judgments, list):
        return usable, [{"issue": "JUDGMENTS_NOT_A_LIST"}]
    for index, item in enumerate(judgments):
        problem = None
        if not isinstance(item, dict):
            problem = "NOT_AN_OBJECT"
        else:
            criterion = item.get("criterion")
            if criterion not in _RESULTS:
                problem = "UNKNOWN_CRITERION"
            elif item.get("result") not in _RESULTS[criterion]:
                problem = "INVALID_RESULT_FOR_CRITERION"
            elif item.get("judged_by") not in JUDGES:
                problem = "INVALID_JUDGED_BY"
            elif not isinstance(item.get("candidate_id"), str) or not item["candidate_id"].strip():
                problem = "MISSING_CANDIDATE_ID"
            elif item.get("candidate_type", "lesson") not in ("lesson", "event"):
                problem = "INVALID_CANDIDATE_TYPE"
            elif criterion == CONFLICT_CRITERION and item.get("result") == "CONFLICT" and not (
                isinstance(item.get("with_candidate_id"), str) and item["with_candidate_id"].strip()
            ):
                problem = "CONFLICT_WITHOUT_with_candidate_id"
        if problem:
            issues.append({"index": index, "issue": problem})
        else:
            usable.append(item)
    return usable, issues


def _basis_ok(judgment: dict[str, Any]) -> bool:
    """A non-empty reference is a locator, not proof that a condition holds.

    The current repository has no executable rule registry or source resolver
    that can verify a permissive judgment. Do not turn caller-supplied labels
    (including ``judged_by=rule``) into evidence. This intentionally returns
    False until a trusted verifier is integrated.
    """
    return False


def _verification_receipt_ok(
    receipt: Any, candidate: dict[str, Any], judgment: dict[str, Any]
) -> bool:
    """Validate that an injected trusted verifier bound its verdict to this claim.

    The callback itself is a trust boundary: it must independently verify the
    claim and source, not echo the judgment. This function checks receipt shape
    and exact binding; it cannot make an untrusted callback trustworthy.
    """
    if not isinstance(receipt, dict) or receipt.get("verified") is not True:
        return False
    ctype, cid = _candidate_key(candidate)
    if receipt.get("candidate_id") != cid or receipt.get("candidate_type") != ctype:
        return False
    if receipt.get("criterion") != judgment.get("criterion"):
        return False
    if receipt.get("result") != judgment.get("result"):
        return False
    basis_ref = judgment.get("basis_ref")
    if not isinstance(basis_ref, str) or not basis_ref.strip() or receipt.get("basis_ref") != basis_ref:
        return False
    verifier_id = receipt.get("verifier_id")
    source_sha256 = receipt.get("source_sha256")
    return (
        isinstance(verifier_id, str) and bool(verifier_id.strip())
        and isinstance(source_sha256, str)
        and re.fullmatch(r"[0-9a-f]{64}", source_sha256) is not None
    )


def _effective(
    judgments: list[dict[str, Any]],
    candidate: dict[str, Any],
    verifier: Callable[[dict[str, Any], dict[str, Any]], Any] | None = None,
) -> dict[str, Any]:
    """Combine judgments; restrictive claims win, permissive claims need proof.

    `verifier` is deliberately a programmatic dependency, never a field in the
    judgments JSON. It must be supplied only by a trusted composition root.
    """
    restrictive = [j for j in judgments if j["result"] in _RESTRICTIVE]
    if restrictive:
        chosen = restrictive[0]
        return {
            "result": chosen["result"], "judged_by": chosen["judged_by"],
            "basis_ref": chosen.get("basis_ref", "UNKNOWN"),
            "adaptation_note": chosen.get("adaptation_note"),
            "with_candidate_id": chosen.get("with_candidate_id"),
        }
    permissive = [j for j in judgments if j["result"] in _PERMISSIVE]
    verified = []
    if verifier is not None:
        for judgment in permissive:
            try:
                receipt = verifier(dict(candidate), dict(judgment))
            except Exception:
                receipt = None
            if _verification_receipt_ok(receipt, candidate, judgment):
                verified.append((judgment, receipt))
    if verified:
        chosen, receipt = verified[0]
        return {
            "result": chosen["result"],
            "judged_by": "rule",
            "asserted_by": chosen["judged_by"],
            "basis_ref": chosen["basis_ref"],
            "adaptation_note": chosen.get("adaptation_note"),
            "with_candidate_id": chosen.get("with_candidate_id"),
            "verification": {
                "verifier_id": receipt["verifier_id"],
                "source_sha256": receipt["source_sha256"],
                "basis_ref": receipt["basis_ref"],
            },
        }
    return {
        "result": "UNKNOWN", "judged_by": "UNKNOWN",
        "basis_ref": "UNKNOWN", "adaptation_note": None,
        "with_candidate_id": None,
        "note": "permissive assertion not verified; basis_ref is not proof" if permissive else None,
        "claims_for_review": [
            {"result": j["result"], "judged_by": j["judged_by"],
             "basis_ref": j.get("basis_ref")}
            for j in permissive
        ],
    }


def _empty_assessment(candidate: dict[str, Any]) -> dict[str, Any]:
    ctype, cid = _candidate_key(candidate)
    return {
        "candidate_id": cid, "candidate_type": ctype,
        "project_id": candidate.get("project_id", "UNKNOWN"),
        "scope": candidate.get("scope", "UNKNOWN"),
        "status": candidate.get("status", "UNKNOWN"),
        "outcome": None, "reason": None, "criteria": {},
        "evidence_assessment": "UNASSESSED",
        "needs": [], "adaptation_notes": [], "caps": [],
    }


def evaluate_applicability(
    candidates: list[dict[str, Any]],
    judgments: list[dict[str, Any]] | None = None,
    *,
    verifier: Callable[[dict[str, Any], dict[str, Any]], Any] | None = None,
) -> dict[str, Any]:
    """Assess candidates; pure function, no I/O, no writes.

    Positive judgments are accepted only when a trusted verifier is injected
    and returns a receipt bound to the exact candidate, criterion, result and
    source digest. Without it, behavior remains fail-closed.
    """
    usable_judgments, judgment_issues = _validate_judgments(judgments)
    by_key: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for item in usable_judgments:
        key = (item.get("candidate_type", "lesson"), item["candidate_id"], item["criterion"])
        by_key.setdefault(key, []).append(item)

    known = {_candidate_key(c) for c in candidates}
    for item in usable_judgments:
        if (item.get("candidate_type", "lesson"), item["candidate_id"]) not in known:
            judgment_issues.append({
                "issue": "JUDGMENT_FOR_UNKNOWN_CANDIDATE",
                "candidate_type": item.get("candidate_type", "lesson"),
                "candidate_id": item["candidate_id"],
            })

    # Replacement links for retired lessons come only from other candidates'
    # `supersedes`; otherwise the replacement stays UNKNOWN.
    replaced_by: dict[str, str] = {}
    for cand in candidates:
        if cand.get("candidate_type") == "lesson" and isinstance(cand.get("supersedes"), list):
            for old in cand["supersedes"]:
                if isinstance(old, str):
                    replaced_by.setdefault(old, str(cand.get("lesson_id")))

    assessments: list[dict[str, Any]] = []
    not_evaluated: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    declared_conflicts: dict[tuple[str, str], set[str]] = {}

    def criteria_for(candidate: dict[str, Any]) -> dict[str, dict[str, Any]]:
        ctype, cid = _candidate_key(candidate)
        return {
            name: _effective(by_key.get((ctype, cid, name), []), candidate, verifier)
            for name in (*CORE_CRITERIA, CONFLICT_CRITERION)
        }

    pending: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for cand in candidates:
        ctype, cid = _candidate_key(cand)
        result = _empty_assessment(cand)
        gate = cand.get("candidate_review_gate", "UNKNOWN")

        # R0: outside the current search scope is not an applicability verdict.
        if gate == "OUT_OF_PROJECT_SCOPE" or (ctype == "lesson" and cand.get("scope") == "global"):
            not_evaluated.append({
                "candidate_id": cid, "candidate_type": ctype,
                "project_id": cand.get("project_id", "UNKNOWN"),
                "scope": cand.get("scope", "UNKNOWN"),
                "reason": "OUT_OF_CURRENT_SEARCH_SCOPE",
                "note": "Not an applicability verdict; the record is unchanged.",
            })
            continue

        # R1: unknown scope or blocked evidence route.
        if gate == "PROJECT_SCOPE_UNKNOWN" or str(gate).endswith("_BLOCKED"):
            result.update(outcome=INSUFFICIENT_DATA, reason=f"candidate_review_gate={gate}")
            result["needs"].append(f"resolve candidate_review_gate: {gate}")
            assessments.append(result)
            continue

        # R7: events are history, not rules.
        if ctype != "lesson":
            result.update(outcome=INSUFFICIENT_DATA, reason="EVENT_IS_HISTORY_NOT_A_RULE")
            result["needs"].append(
                "event has no structured applicability/exceptions; use it as history "
                "or as evidence for a lesson record"
            )
            result["informational"] = True
            assessments.append(result)
            continue

        status = _norm_status(cand.get("status"))
        if status in RETIRED_STATUSES:
            excluded.append({
                "candidate_id": cid, "candidate_type": ctype, "reason": status,
                "replacement": replaced_by.get(cid, "UNKNOWN"),
            })
            continue
        if status not in KNOWN_LESSON_STATUSES:
            result.update(outcome=INSUFFICIENT_DATA, reason="STATUS_SEMANTICS_UNDEFINED")
            result["needs"].append(f"status semantics undefined: {cand.get('status', 'UNKNOWN')!r}")
            assessments.append(result)
            continue
        if status == "disputed":
            result.update(outcome=INSUFFICIENT_DATA, reason="LESSON_DISPUTED")
            result["needs"].append("resolve dispute (UMC-06) before use")
            assessments.append(result)
            continue

        criteria = criteria_for(cand)
        result["criteria"] = {name: criteria[name] for name in (*CORE_CRITERIA, CONFLICT_CRITERION)}
        result["_status"] = status
        if criteria[CONFLICT_CRITERION]["result"] == "CONFLICT":
            other = criteria[CONFLICT_CRITERION]["with_candidate_id"]
            declared_conflicts.setdefault((ctype, cid), set()).add(str(other))
            declared_conflicts.setdefault((ctype, str(other)), set()).add(cid)
        pending.append((cand, result))

    # R4: declared incompatibility makes both sides CONFLICT; nothing is resolved.
    for cand, result in pending:
        ctype, cid = _candidate_key(cand)
        # R2 precedes R4: a triggered exception already excludes the lesson.
        if (ctype, cid) in declared_conflicts and result["criteria"]["exceptions"]["result"] != "TRIGGERED":
            result.update(outcome=CONFLICT, reason="DECLARED_INCOMPATIBLE_RECOMMENDATION")
            result["conflicts_with"] = sorted(declared_conflicts[(ctype, cid)])
            assessments.append(result)
            continue
        _decide(cand, result)
        assessments.append(result)

    for item in assessments:
        item.pop("_status", None)

    usable = [
        {"candidate_id": a["candidate_id"], "candidate_type": a["candidate_type"],
         "outcome": a["outcome"], "adaptation_notes": a["adaptation_notes"], "caps": a["caps"]}
        for a in assessments if a["outcome"] in (APPLICABLE, APPLICABLE_WITH_ADAPTATION)
    ]
    for a in assessments:
        if a["outcome"] == NOT_APPLICABLE:
            excluded.append({
                "candidate_id": a["candidate_id"], "candidate_type": a["candidate_type"],
                "reason": a["reason"],
            })
    needs = [
        {"candidate_id": a["candidate_id"], "candidate_type": a["candidate_type"],
         "needs": a["needs"], "informational": bool(a.get("informational"))}
        for a in assessments if a["outcome"] == INSUFFICIENT_DATA
    ]
    blocked = [
        {"candidate_id": a["candidate_id"], "candidate_type": a["candidate_type"],
         "conflicts_with": a.get("conflicts_with", [])}
        for a in assessments if a["outcome"] == CONFLICT
    ]
    lesson_insufficient = any(
        a["outcome"] == INSUFFICIENT_DATA and a["candidate_type"] == "lesson" for a in assessments
    )
    if blocked:
        policy = "STOP_RESOLVE_CONFLICT"
    elif lesson_insufficient:
        policy = "ASK_OR_SEARCH_MORE"
    else:
        policy = None
    return {
        "evaluator_version": "0.1",
        "assessments": assessments,
        "usable_as_rationale": usable,
        "excluded": excluded,
        "not_evaluated": not_evaluated,
        "needs": needs,
        "blocked_dependent_decisions": blocked,
        "judgment_issues": judgment_issues,
        # Restrictive refinement only. Never a permission to plan or act.
        "restrictive_policy": policy,
        "grants_planning_permission": False,
        "writes_performed": False,
    }


def _decide(candidate: dict[str, Any], result: dict[str, Any]) -> None:
    criteria = result["criteria"]

    # R2: a triggered exception, or a violated essential condition.
    if criteria["exceptions"]["result"] == "TRIGGERED":
        result.update(outcome=NOT_APPLICABLE, reason="EXCEPTION_HOLDS")
        return
    if criteria["problem_similarity"]["result"] == "MISMATCH":
        result.update(outcome=NOT_APPLICABLE, reason="PROBLEM_NOT_SIMILAR")
        return
    if criteria["evidence_support"]["result"] == "MISMATCH":
        result.update(outcome=NOT_APPLICABLE, reason="EVIDENCE_DOES_NOT_SUPPORT_CLAIM")
        result["evidence_assessment"] = "DOES_NOT_SUPPORT"
        return
    adaptable = ("trigger", "applicability", "circumstances_unchanged")
    for name in adaptable:
        if criteria[name]["result"] == "MISMATCH" and not criteria[name].get("adaptation_note"):
            result.update(outcome=NOT_APPLICABLE, reason=f"{name.upper()}_VIOLATED_WITHOUT_ADAPTATION")
            return

    # R3/R7/R9: missing or unbased criteria never turn into applicability.
    missing = [name for name in CORE_CRITERIA if criteria[name]["result"] == "UNKNOWN"]
    if missing:
        result.update(outcome=INSUFFICIENT_DATA, reason="CRITERIA_UNDETERMINED")
        result["needs"].extend(f"judgment with basis_ref required: {name}" for name in missing)
        return

    result["evidence_assessment"] = "SUPPORTS_CLAIM"
    adapted = [name for name in adaptable if criteria[name]["result"] == "MISMATCH"]
    caps: list[str] = result["caps"]
    # R8: agent-judged criteria cannot establish plain applicability.
    agent_judged = [n for n in CORE_CRITERIA if criteria[n]["judged_by"] == "agent"]
    if agent_judged:
        caps.append("agent-judged criteria: " + ", ".join(agent_judged))
    # R12: a candidate lesson is limited by its own status.
    if result.get("_status") == "candidate":
        caps.append("lesson status is candidate")
    if adapted:
        result["adaptation_notes"].extend(
            f"{name}: {criteria[name]['adaptation_note']}" for name in adapted
        )
    if adapted or caps:
        result.update(outcome=APPLICABLE_WITH_ADAPTATION,
                      reason="ADAPTATION_NEEDED" if adapted else "CAPPED")
        if caps and not adapted:
            result["adaptation_notes"].append("no condition differs; outcome is capped: " + "; ".join(caps))
    else:
        result.update(outcome=APPLICABLE, reason="ALL_CRITERIA_JUDGED_WITH_BASIS")
