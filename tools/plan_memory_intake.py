#!/usr/bin/env python3
"""Create a read-only routing proposal from a validated memory intake manifest."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from validate_memory import validate_intake_manifest

EVIDENCE_ROUTES = {
    "raw_source_reference": ("source_evidence_registry", "register_source_reference"),
    "source_inventory": ("source_evidence_registry", "register_inventory"),
    "source_records": ("source_evidence_registry", "append_source_records"),
}
MEMORY_KINDS = {
    "memory_records", "event_records", "lesson_records", "decision_records"
}


def _memory_view(artifact: dict) -> tuple[str, str]:
    if artifact.get("approval_status") == "user_rejected":
        return "rejected_record_quarantine", "preserve_rejection_record"
    lifecycle = artifact.get("lifecycle_status")
    if lifecycle == "accepted" and artifact.get("approval_status") == "user_approved":
        return "accepted_memory_view", "prepare_approved_record_for_review"
    if lifecycle == "disputed":
        return "disputed_memory_view", "preserve_conflicting_candidate"
    if lifecycle in {"superseded", "deprecated"}:
        return "historical_memory_view", "preserve_historical_revision"
    return "candidate_memory_view", "stage_candidate_record"


def build_route_plan(manifest_path: Path) -> dict:
    """Validate first; never write records or trust manifest-provided destination paths."""
    manifest_path = Path(manifest_path)
    errors = validate_intake_manifest(manifest_path)
    if errors:
        return {
            "plan_version": "1.0",
            "status": "REJECTED",
            "manifest": str(manifest_path),
            "validation_errors": errors,
            "routes": [],
            "writes_performed": False,
        }

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    routes = []
    for artifact in manifest["artifacts"]:
        kind = artifact["kind"]
        if kind in EVIDENCE_ROUTES:
            view, operation = EVIDENCE_ROUTES[kind]
        elif kind in MEMORY_KINDS:
            view, operation = _memory_view(artifact)
        elif kind == "relation_records":
            view, operation = "relation_candidates", "validate_relation_endpoints"
        elif kind == "task_state":
            view, operation = "state_change_proposals", "propose_state_update_only"
        elif kind == "handoff":
            view, operation = "handoff_change_proposals", "propose_handoff_update_only"
        else:
            view, operation = "quarantine_unmapped", "quarantine_for_manual_mapping"

        routes.append({
            "artifact_id": artifact["artifact_id"],
            "kind": kind,
            "source_path": artifact["path"],
            "sha256": artifact["sha256"],
            "record_count": artifact.get("record_count"),
            "logical_view": view,
            "planned_operation": operation,
            "lifecycle_status": artifact["lifecycle_status"],
            "evidence_status": artifact["evidence_status"],
            "approval_status": artifact["approval_status"],
            "writes_performed": False,
        })

    return {
        "plan_version": "1.0",
        "status": "DRY_RUN_READY",
        "batch_id": manifest["batch_id"],
        "source_id": manifest["source"]["source_id"],
        "payload_classification": manifest["payload_classification"],
        "routes": routes,
        "warnings": [
            "This is a dry-run proposal only; no canonical records or indexes were changed.",
            "IMPORT_READY is not authorization and does not approve candidate records.",
            "Logical views must be implemented over the existing linked registry; do not create duplicate copies per view.",
            "Technology and tool tags describe observed context; future project applicability is not inferred here.",
        ],
        "writes_performed": False,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="path to manifest.json")
    args = parser.parse_args(argv)
    plan = build_route_plan(args.manifest)
    print(json.dumps(plan, ensure_ascii=False, indent=2))
    return 0 if plan["status"] == "DRY_RUN_READY" else 2


if __name__ == "__main__":
    sys.exit(main())
