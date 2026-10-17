"""Small, dependency-free primitives for snapshot-aware evolving memory.

This module is deliberately additive: it does not rewrite legacy memory files.
It models source snapshots, assertion revisions, lineage and downstream impact.
"""
from __future__ import annotations

from collections import deque
from datetime import datetime
from typing import Any, Iterable


VALID_COVERAGE = {"COMPLETE", "PARTIAL", "UNKNOWN"}
VALID_EVIDENCE = {"reported", "observed", "inferred", "verified", "unknown"}
VALID_LIFECYCLE = {"candidate", "accepted", "disputed", "superseded", "deprecated"}
DEPENDENCY_RELATIONS = {
    "derived_from", "supports", "contradicts", "refines", "supersedes",
    "implements", "summarizes", "depends_on",
}


def _parse_time(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty ISO-8601 timestamp")
    normalized = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(f"{field} must be ISO-8601: {value!r}") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must include a timezone")
    return parsed


def validate_snapshot(snapshot: dict[str, Any]) -> list[str]:
    """Return all validation errors; never infer missing scope/time/hash."""
    errors: list[str] = []
    required = (
        "snapshot_id", "scope_id", "counting_unit",
        "inclusion_rules_id", "exclusion_rules_id", "coverage_status",
    )
    for field in required:
        if not snapshot.get(field):
            errors.append(f"missing:{field}")
    if snapshot.get("captured_at"):
        try:
            _parse_time(snapshot["captured_at"], "captured_at")
        except ValueError as exc:
            errors.append(str(exc))
    if snapshot.get("coverage_status") not in VALID_COVERAGE:
        errors.append("invalid:coverage_status")
    counts = snapshot.get("counts")
    if not isinstance(counts, dict):
        errors.append("invalid:counts")
    elif any(not isinstance(v, int) or isinstance(v, bool) or v < 0 for v in counts.values()):
        errors.append("invalid:counts values must be non-negative integers")
    return errors


def compare_snapshots(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    """Compare counts only when scope and counting semantics match.

    Different capture times are allowed and retained. A count delta is not, by
    itself, evidence of data loss or corruption.
    """
    errors = validate_snapshot(left) + validate_snapshot(right)
    if errors:
        return {"status": "invalid_snapshot", "errors": errors}
    aligned_fields = (
        "scope_id", "counting_unit", "inclusion_rules_id", "exclusion_rules_id",
    )
    mismatches = [
        field for field in aligned_fields if left.get(field) != right.get(field)
    ]
    if mismatches:
        return {
            "status": "not_comparable",
            "mismatched_dimensions": mismatches,
            "left_snapshot_id": left["snapshot_id"],
            "right_snapshot_id": right["snapshot_id"],
            "reason": "Collection scope or counting semantics differ.",
        }
    left_counts, right_counts = left["counts"], right["counts"]
    keys = sorted(set(left_counts) | set(right_counts))
    deltas = {key: right_counts.get(key, 0) - left_counts.get(key, 0) for key in keys}
    return {
        "status": "comparable",
        "left_snapshot_id": left["snapshot_id"],
        "right_snapshot_id": right["snapshot_id"],
        "left_captured_at": left["captured_at"],
        "right_captured_at": right["captured_at"],
        "counting_unit": left["counting_unit"],
        "deltas": deltas,
        "interpretation": "Count changes describe snapshot differences; cause is undetermined.",
    }


def validate_assertion(assertion: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in ("assertion_id", "claim", "recorded_at", "evidence_status", "lifecycle_status", "source_refs"):
        if field not in assertion or assertion[field] is None:
            errors.append(f"missing:{field}")
    if assertion.get("evidence_status") not in VALID_EVIDENCE:
        errors.append("invalid:evidence_status")
    if assertion.get("lifecycle_status") not in VALID_LIFECYCLE:
        errors.append("invalid:lifecycle_status")
    if assertion.get("recorded_at"):
        try:
            _parse_time(assertion["recorded_at"], "recorded_at")
        except ValueError as exc:
            errors.append(str(exc))
    if not isinstance(assertion.get("source_refs"), list) or not assertion.get("source_refs"):
        errors.append("source_refs must be a non-empty list")
    return errors


def assertions_as_of(
    assertions: Iterable[dict[str, Any]], cutoff: str, *, include_disputed: bool = True
) -> list[dict[str, Any]]:
    """Return records known by cutoff; does not mutate or delete prior claims."""
    cutoff_dt = _parse_time(cutoff, "cutoff")
    result = []
    for item in assertions:
        if validate_assertion(item):
            continue
        if _parse_time(item["recorded_at"], "recorded_at") > cutoff_dt:
            continue
        if item["lifecycle_status"] in {"superseded", "deprecated"}:
            continue
        if not include_disputed and item["lifecycle_status"] == "disputed":
            continue
        result.append(item)
    return sorted(result, key=lambda row: (_parse_time(row["recorded_at"], "recorded_at"), row["assertion_id"]))


def downstream_impact(
    changed_id: str, relations: Iterable[dict[str, Any]]
) -> list[str]:
    """Find transitive dependants without asserting the changed node is false."""
    adjacency: dict[str, set[str]] = {}
    for edge in relations:
        relation_type = edge.get("type")
        source = edge.get("source_id")
        target = edge.get("target_id")
        if relation_type in DEPENDENCY_RELATIONS and source and target:
            adjacency.setdefault(source, set()).add(target)
    visited: set[str] = set()
    queue = deque(adjacency.get(changed_id, set()))
    while queue:
        current = queue.popleft()
        if current == changed_id or current in visited:
            continue
        visited.add(current)
        queue.extend(adjacency.get(current, set()) - visited)
    return sorted(visited)
