#!/usr/bin/env python3
"""Read-only reconciliation report for child-result delivery and task-state projection gaps."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_events(path: Path) -> list[dict[str, Any]]:
    events = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except Exception as exc:
            raise ValueError(f"Invalid JSONL at line {number}: {exc}") from exc
        if not isinstance(event, dict) or not isinstance(event.get("event_id"), str):
            raise ValueError(f"Invalid event at line {number}: event_id required")
        events.append(event)
    return events


def build_report(event_log: Path, task_states: list[Path]) -> dict[str, Any]:
    event_log = Path(event_log)
    task_states = [Path(path) for path in task_states]
    try:
        events = load_events(event_log)
    except Exception as exc:
        return {"status": "REJECTED", "errors": [str(exc)], "writes_performed": False}

    by_id = {event["event_id"]: event for event in events}
    results = {event["event_id"]: event for event in events if event.get("type") == "cross_branch_result"}
    acknowledgements = [
        event for event in events
        if event.get("type") == "cross_branch_result_acknowledged"
        and isinstance(event.get("acknowledgement"), dict)
    ]
    ack_by_result: dict[str, list[dict[str, Any]]] = {}
    for ack in acknowledgements:
        result_id = ack["acknowledgement"].get("result_event_id")
        if result_id:
            ack_by_result.setdefault(result_id, []).append(ack)

    state_texts = {}
    for path in task_states:
        if not path.is_file():
            return {"status": "REJECTED", "errors": [f"Task-state file not found: {path}"], "writes_performed": False}
        state_texts[str(path)] = {
            "text": path.read_text(encoding="utf-8"),
            "sha256": sha256_file(path),
        }

    issues = []
    for result_id, result in results.items():
        acks = ack_by_result.get(result_id, [])
        if not acks:
            issues.append({
                "issue_id": "MISSING_OWNER_ACK:" + result_id,
                "kind": "missing_owner_acknowledgement",
                "result_event_id": result_id,
                "parent_checkpoint_id": (result.get("branch_return") or {}).get("parent_checkpoint_id"),
                "parent_task_id": (result.get("branch_return") or {}).get("parent_task_id"),
                "recommended_action": "Review child result and append explicit owner acknowledgement if appropriate.",
            })
            continue
        latest_ack = acks[-1]
        ack_data = latest_ack["acknowledgement"]
        if ack_data.get("decision") == "accepted":
            ack_id = latest_ack["event_id"]
            linked_states = [
                path for path, state in state_texts.items()
                if ack_id in state["text"]
            ]
            if not linked_states:
                issues.append({
                    "issue_id": "MISSING_TASK_CHECKPOINT:" + ack_id,
                    "kind": "accepted_ack_without_task_checkpoint",
                    "result_event_id": result_id,
                    "ack_event_id": ack_id,
                    "parent_checkpoint_id": ack_data.get("parent_checkpoint_id"),
                    "recommended_action": "Prepare an append-only TASK_STATE checkpoint proposal using the current file hash; do not auto-resolve the parent goal.",
                    "candidate_task_state_files": [
                        {"path": path, "sha256": state["sha256"]}
                        for path, state in state_texts.items()
                    ],
                })

    return {
        "report_version": "1.0",
        "status": "RECONCILIATION_REQUIRED" if issues else "CONSISTENT",
        "event_log": str(event_log),
        "event_log_sha256": sha256_file(event_log),
        "events_seen": len(events),
        "child_results_seen": len(results),
        "acknowledgements_seen": len(acknowledgements),
        "issues": issues,
        "writes_performed": False,
        "warnings": [
            "Read-only report; no acknowledgement or task-state changes were made.",
            "This checks only supplied task-state files and cannot infer that an unlinked checkpoint never existed elsewhere.",
            "An accepted child result does not prove the parent task is complete.",
        ],
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("event_log", type=Path)
    parser.add_argument("--task-state", action="append", type=Path, required=True,
                        help="TASK_STATE.md to inspect; may be supplied more than once")
    args = parser.parse_args(argv)
    report = build_report(args.event_log, args.task_state)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] in {"CONSISTENT", "RECONCILIATION_REQUIRED"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
