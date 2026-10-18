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



TEMPORAL_RELATIONS = {"preceded_by", "followed_by"}


def validate_temporal_relations(
    records: Iterable[dict[str, Any]],
    trusted_order: dict[str, Any],
) -> list[str]:
    """Validate temporal edges against evidence-backed total or partial order.

    Legacy input is a flat event_id -> integer map. The preferred schema is:
      {"order": {event_id: integer, ...},
       "verified_precedence": [
         {"earlier": id, "later": id, "evidence": "...", "ref": "..."}
       ]}
    Numeric order may represent coarse calendar order; equal values mean the
    records are not ordered by that evidence. Explicit precedence edges can
    resolve same-day order. No ordering is inferred from JSONL row position,
    event IDs, or ingestion time. Corrections are projected in memory only.
    """
    rows = list(records)
    by_id: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    for index, row in enumerate(rows):
        event_id = row.get("event_id")
        if not isinstance(event_id, str) or not event_id:
            errors.append(f"record[{index}]: missing event_id")
            continue
        if event_id in by_id:
            errors.append(f"{event_id}: duplicate event_id")
            continue
        by_id[event_id] = row

    if "order" in trusted_order or "verified_precedence" in trusted_order:
        order = trusted_order.get("order", {})
        precedence_rows = trusted_order.get("verified_precedence", [])
        if not isinstance(order, dict):
            errors.append("trusted-order field 'order' must be an object")
            order = {}
        if not isinstance(precedence_rows, list):
            errors.append("trusted-order field 'verified_precedence' must be a list")
            precedence_rows = []
    else:
        # Backward compatibility with the original flat integer mapping.
        order = trusted_order
        precedence_rows = []

    valid_order: dict[str, int] = {}
    for event_id, value in order.items():
        if not isinstance(event_id, str) or not isinstance(value, int) or isinstance(value, bool):
            errors.append(f"trusted chronology for {event_id!r} must be an integer, not a boolean")
            continue
        valid_order[event_id] = value

    precedence: dict[str, set[str]] = {}
    for index, item in enumerate(precedence_rows):
        if not isinstance(item, dict):
            errors.append(f"verified_precedence[{index}]: expected an object")
            continue
        earlier, later = item.get("earlier"), item.get("later")
        evidence, ref = item.get("evidence"), item.get("ref")
        if not isinstance(earlier, str) or not isinstance(later, str) or earlier == later:
            errors.append(f"verified_precedence[{index}]: earlier/later must be distinct event IDs")
            continue
        if earlier not in by_id or later not in by_id:
            errors.append(f"verified_precedence[{index}]: unknown event ID {earlier!r} or {later!r}")
            continue
        if not isinstance(evidence, str) or not evidence.strip() or not isinstance(ref, str) or not ref.strip():
            errors.append(f"verified_precedence[{index}]: evidence and ref are required")
            continue
        if earlier in valid_order and later in valid_order and valid_order[earlier] > valid_order[later]:
            errors.append(f"verified_precedence[{index}]: ancestry conflicts with coarse order: {earlier} is dated later than {later}")
            continue
        precedence.setdefault(earlier, set()).add(later)

    def reachable(source: str, target: str) -> bool:
        pending = [source]
        visited: set[str] = set()
        while pending:
            current = pending.pop()
            if current == target:
                return True
            if current in visited:
                continue
            visited.add(current)
            pending.extend(precedence.get(current, set()) - visited)
        return False

    # A cycle makes the evidence-backed partial order contradictory.
    for source in precedence:
        if reachable(source, source):
            errors.append(f"trusted precedence contains a cycle involving {source}")
            break

    effective_edges: dict[str, list[dict[str, Any]]] = {
        event_id: [dict(edge) for edge in row.get("relations", []) if isinstance(edge, dict)]
        for event_id, row in by_id.items()
    }

    for correction_record in rows:
        correction_id = correction_record.get("event_id", "<unknown>")
        corrections = correction_record.get("edge_corrections", [])
        if not isinstance(corrections, list):
            errors.append(f"{correction_id}: edge_corrections must be a list")
            continue
        for correction in corrections:
            if not isinstance(correction, dict):
                errors.append(f"{correction_id}: invalid edge correction")
                continue
            target_id = correction.get("record_id")
            if target_id not in by_id:
                errors.append(f"{correction_id}: correction target not found: {target_id}")
                continue
            if correction.get("field") != "relations":
                continue
            old_edge = correction.get("old_relation")
            new_edge = correction.get("corrected_relation")
            if not isinstance(old_edge, dict) or (new_edge is not None and not isinstance(new_edge, dict)):
                errors.append(f"{correction_id}: correction must contain old_relation and a corrected_relation object or null")
                continue
            edges = effective_edges[target_id]
            try:
                edge_index = edges.index(old_edge)
            except ValueError:
                errors.append(f"{correction_id}: old relation not found in {target_id}")
                continue
            if new_edge is None:
                del edges[edge_index]
            else:
                edges[edge_index] = dict(new_edge)

    for source_id, edges in effective_edges.items():
        for edge in edges:
            relation = edge.get("type")
            target_id = edge.get("event_id")
            if relation not in TEMPORAL_RELATIONS:
                continue
            if target_id not in by_id:
                errors.append(f"{source_id}: {relation} target not found: {target_id}")
                continue

            # A coarse order with different values proves date-level direction.
            source_order = valid_order.get(source_id)
            target_order = valid_order.get(target_id)
            if source_order is not None and target_order is not None and source_order != target_order:
                earlier, later = (source_id, target_id) if source_order < target_order else (target_id, source_id)
                if relation == "preceded_by" and source_id == earlier:
                    errors.append(f"{source_id}: preceded_by points to non-earlier event {target_id}")
                elif relation == "followed_by" and source_id == later:
                    errors.append(f"{source_id}: followed_by points to non-later event {target_id}")
                continue

            # Same-day/equal-rank relations require an explicit evidence-backed path.
            source_before_target = reachable(source_id, target_id)
            target_before_source = reachable(target_id, source_id)
            if source_before_target and target_before_source:
                errors.append(f"{source_id}: contradictory trusted precedence for edge to {target_id}")
            elif relation == "preceded_by":
                if source_before_target:
                    errors.append(f"{source_id}: preceded_by points to later event {target_id}")
                elif not target_before_source:
                    errors.append(f"{source_id}: temporal order unresolved for edge to {target_id}")
            else:  # followed_by
                if target_before_source:
                    errors.append(f"{source_id}: followed_by points to earlier event {target_id}")
                elif not source_before_target:
                    errors.append(f"{source_id}: temporal order unresolved for edge to {target_id}")
    return errors

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
