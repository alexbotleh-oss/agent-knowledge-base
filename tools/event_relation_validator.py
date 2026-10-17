#!/usr/bin/env python3
"""Pre-write and whole-log validation for temporal event relations.

The validator preserves append-only history and applies explicit correction
overlays when interpreting relations. It never rewrites events or corrections.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

TEMPORAL_DIRECTIONS = {
    "followed_by": "target_after",
    "causes": "target_after",
    "superseded_by": "target_after",
    "corrected_by": "target_after",
    "preceded_by": "target_before",
    "caused_by": "target_before",
    "supersedes": "target_before",
    "corrects": "target_before",
}


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _time_value(event: dict[str, Any]) -> datetime | None:
    value = event.get("event_time")
    if not isinstance(value, str) or not value.strip() or value.strip().casefold() in {"unknown", "null"}:
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed


def _time_order(source: dict[str, Any], target: dict[str, Any]) -> int | None:
    """Return -1 if source precedes target, +1 if source follows target, else unknown/equal."""
    left = _time_value(source)
    right = _time_value(target)
    if left is None or right is None:
        return None
    source_precision = source.get("time_precision", "unknown")
    target_precision = target.get("time_precision", "unknown")
    if left.date() != right.date():
        return -1 if left.date() < right.date() else 1
    if source_precision == "day" or target_precision == "day":
        return None
    if left == right:
        return 0
    return -1 if left < right else 1


def _subset_match(actual: dict[str, Any], expected: Any) -> bool:
    return isinstance(expected, dict) and all(actual.get(key) == value for key, value in expected.items())


def _apply_relation_corrections(events: list[dict[str, Any]]) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    by_id = {
        event.get("event_id"): event
        for event in events
        if isinstance(event.get("event_id"), str)
    }
    active = {
        event_id: [dict(item) for item in event.get("relations", []) if isinstance(item, dict)]
        for event_id, event in by_id.items()
    }
    issues = []
    for correction_event in events:
        corrections = correction_event.get("edge_corrections", [])
        if not isinstance(corrections, list):
            issues.append({
                "code": "INVALID_EDGE_CORRECTIONS",
                "event_id": correction_event.get("event_id"),
            })
            continue
        for correction in corrections:
            if not isinstance(correction, dict) or correction.get("field") != "relations":
                continue
            target_id = correction.get("record_id")
            relations = active.get(target_id)
            if relations is None:
                issues.append({
                    "code": "CORRECTION_TARGET_EVENT_NOT_FOUND",
                    "correction_event_id": correction_event.get("event_id"),
                    "target_event_id": target_id,
                })
                continue
            old = correction.get("old_relation")
            matches = [i for i, relation in enumerate(relations) if _subset_match(relation, old)]
            if len(matches) != 1:
                issues.append({
                    "code": "CORRECTION_TARGET_RELATION_MISSING_OR_AMBIGUOUS",
                    "correction_event_id": correction_event.get("event_id"),
                    "target_event_id": target_id,
                    "match_count": len(matches),
                })
                continue
            index = matches[0]
            new_relation = correction.get("corrected_relation")
            if new_relation is None:
                relations.pop(index)
            elif isinstance(new_relation, dict):
                relations[index] = dict(new_relation)
            else:
                issues.append({
                    "code": "INVALID_CORRECTED_RELATION",
                    "correction_event_id": correction_event.get("event_id"),
                    "target_event_id": target_id,
                })
    return active, issues


def _direction_issue(
    source: dict[str, Any], relation: dict[str, Any],
    target: dict[str, Any], source_index: int, target_index: int,
) -> dict[str, Any] | None:
    relation_type = relation.get("type")
    expected = TEMPORAL_DIRECTIONS.get(relation_type)
    if expected is None:
        return None
    target_id = relation.get("event_id") or relation.get("target_event_id")
    if not isinstance(target_id, str) or not target_id:
        return {
            "code": "TEMPORAL_RELATION_TARGET_ID_MISSING",
            "event_id": source.get("event_id"),
            "relation_type": relation_type,
        }
    if target_id == source.get("event_id"):
        return {
            "code": "TEMPORAL_RELATION_SELF_REFERENCE",
            "event_id": source.get("event_id"),
            "relation_type": relation_type,
        }

    # A deliberate historical backfill may point to an event appended later.
    # It is accepted only when timestamps with sufficient precision establish direction.
    time_order = _time_order(source, target)
    if expected == "target_after":
        correct_by_time = time_order == -1
        wrong_by_time = time_order == 1
        correct_by_append = target_index > source_index
    else:
        correct_by_time = time_order == 1
        wrong_by_time = time_order == -1
        correct_by_append = target_index < source_index

    if correct_by_time:
        return None
    if wrong_by_time:
        return {
            "code": "TEMPORAL_DIRECTION_CONTRADICTS_EVENT_TIME",
            "event_id": source.get("event_id"),
            "relation_type": relation_type,
            "target_event_id": target_id,
            "source_event_time": source.get("event_time"),
            "target_event_time": target.get("event_time"),
        }
    if correct_by_append:
        return None

    override = relation.get("chronology_override")
    if isinstance(override, dict):
        reason = override.get("reason")
        refs = override.get("evidence_refs")
        if isinstance(reason, str) and reason.strip() and isinstance(refs, list) and refs and all(
            isinstance(ref, str) and ref.strip() for ref in refs
        ):
            return None
    return {
        "code": "TEMPORAL_DIRECTION_CONTRADICTS_APPEND_ORDER",
        "event_id": source.get("event_id"),
        "relation_type": relation_type,
        "target_event_id": target_id,
        "source_index": source_index,
        "target_index": target_index,
        "note": "If this is a historical backfill, provide precise timestamps or an explicit chronology_override with evidence_refs.",
    }


def audit_event_log(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Audit active temporal relations after applying append-only correction overlays."""
    issues = []
    by_id: dict[str, tuple[int, dict[str, Any]]] = {}
    for index, event in enumerate(events):
        if not isinstance(event, dict):
            issues.append({"code": "INVALID_EVENT_OBJECT", "index": index})
            continue
        event_id = event.get("event_id")
        if not isinstance(event_id, str) or not event_id.strip():
            issues.append({"code": "EVENT_ID_MISSING", "index": index})
            continue
        if event_id in by_id:
            issues.append({"code": "DUPLICATE_EVENT_ID", "event_id": event_id, "index": index})
        else:
            by_id[event_id] = (index, event)

    active, correction_issues = _apply_relation_corrections(events)
    issues.extend(correction_issues)
    for source_id, (source_index, source) in by_id.items():
        relations = active.get(source_id, [])
        for relation in relations:
            relation_type = relation.get("type")
            if relation_type not in TEMPORAL_DIRECTIONS:
                continue
            target_id = relation.get("event_id") or relation.get("target_event_id")
            target_entry = by_id.get(target_id) if isinstance(target_id, str) else None
            if target_entry is None:
                issues.append({
                    "code": "TEMPORAL_TARGET_NOT_FOUND_IN_CURRENT_LOG",
                    "event_id": source_id,
                    "relation_type": relation_type,
                    "target_event_id": target_id,
                })
                continue
            target_index, target = target_entry
            issue = _direction_issue(source, relation, target, source_index, target_index)
            if issue:
                issues.append(issue)

    errors = [item for item in issues if item.get("code") != "TEMPORAL_TARGET_NOT_FOUND_IN_CURRENT_LOG"]
    status = "REJECTED" if errors else "REVIEW_REQUIRED" if issues else "PASS"
    return {
        "schema_version": "event-relation-audit-v1",
        "status": status,
        "event_count": len(events),
        "active_temporal_relation_count": sum(
            1 for relations in active.values() for relation in relations
            if relation.get("type") in TEMPORAL_DIRECTIONS
        ),
        "issue_count": len(issues),
        "issues": issues,
        "writes_performed": False,
    }


def validate_event_append(candidate: dict[str, Any], existing_events: list[dict[str, Any]]) -> dict[str, Any]:
    """Validate the whole resulting log before a candidate event is appended."""
    if not isinstance(candidate, dict):
        return {"status": "REJECTED", "issues": [{"code": "INVALID_CANDIDATE_EVENT"}], "writes_performed": False}
    candidate_id = candidate.get("event_id")
    if not isinstance(candidate_id, str) or not candidate_id.strip():
        return {"status": "REJECTED", "issues": [{"code": "EVENT_ID_MISSING"}], "writes_performed": False}
    if any(isinstance(event, dict) and event.get("event_id") == candidate_id for event in existing_events):
        return {"status": "REJECTED", "issues": [{"code": "DUPLICATE_EVENT_ID", "event_id": candidate_id}], "writes_performed": False}
    if "relations" in candidate and not isinstance(candidate.get("relations"), list):
        return {"status": "REJECTED", "issues": [{"code": "INVALID_RELATIONS_LIST", "event_id": candidate_id}], "writes_performed": False}
    combined = [*existing_events, candidate]
    report = audit_event_log(combined)
    return {
        "status": report["status"],
        "issues": report["issues"],
        "event_count": report["event_count"],
        "writes_performed": False,
        "note": "Candidate is not written by this validator; caller must stop unless status is PASS.",
    }


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    events = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            raise ValueError(f"blank line at {number}")
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON at line {number}: {exc}") from exc
        if not isinstance(event, dict):
            raise ValueError(f"event at line {number} is not an object")
        events.append(event)
    return events


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event-log", type=Path, required=True)
    parser.add_argument("--candidate-event", type=Path, help="optional JSON event to validate before append")
    args = parser.parse_args(argv)
    try:
        existing = _read_jsonl(args.event_log)
        if args.candidate_event:
            candidate = json.loads(args.candidate_event.read_text(encoding="utf-8"))
            report = validate_event_append(candidate, existing)
        else:
            report = audit_event_log(existing)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        report = {"status": "REJECTED", "issues": [{"code": "INPUT_ERROR", "reason": str(exc)}], "writes_performed": False}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("status") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
