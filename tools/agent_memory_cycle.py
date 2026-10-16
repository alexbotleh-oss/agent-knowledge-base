#!/usr/bin/env python3
"""Compose task-start memory retrieval, branch reconciliation, and causal return.

This is the single local entry point for the current connected memory cycle.
It does not observe ChatGPT automatically. Parent return is explicit and fails
closed unless the active branch has an accepted child result, an acknowledged
parent checkpoint, and a consistent reconciliation report.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from dialogue_attention_controller import inspect as inspect_attention, _return_to_parent_unchecked
from reconcile_branch_returns import build_report as build_branch_return_report
from task_start_experience_map import build_task_start_experience_map


def _current_branch_result_ready(
    event_log: Path, branch_id: str, parent_task_id: str, parent_checkpoint_id: str
) -> dict[str, Any]:
    """Require a matching child result and explicit accepted acknowledgement."""
    try:
        events = []
        seen = set()
        for number, line in enumerate(Path(event_log).read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            event = json.loads(line)
            if not isinstance(event, dict) or not isinstance(event.get("event_id"), str):
                raise ValueError(f"invalid event at line {number}")
            if event["event_id"] in seen:
                raise ValueError(f"duplicate event_id at line {number}: {event['event_id']}")
            seen.add(event["event_id"])
            events.append(event)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return {"status": "BLOCKED_EVENT_LOG_INVALID", "reason": str(exc)}

    results = [
        event for event in events
        if event.get("type") == "cross_branch_result"
        and isinstance(event.get("branch_return"), dict)
        and event["branch_return"].get("child_branch_id") == branch_id
        and event["branch_return"].get("parent_task_id") == parent_task_id
        and event["branch_return"].get("parent_checkpoint_id") == parent_checkpoint_id
    ]
    if not results:
        return {"status": "BLOCKED_CHILD_RESULT_MISSING", "branch_id": branch_id}
    result_ids = {event["event_id"] for event in results}
    acknowledgements = [
        event for event in events
        if event.get("type") == "cross_branch_result_acknowledged"
        and isinstance(event.get("acknowledgement"), dict)
        and event["acknowledgement"].get("result_event_id") in result_ids
    ]
    if not acknowledgements:
        return {"status": "BLOCKED_OWNER_ACK_MISSING", "result_event_ids": sorted(result_ids)}
    latest = acknowledgements[-1]
    decision = latest["acknowledgement"].get("decision")
    if decision != "accepted":
        return {
            "status": "BLOCKED_OWNER_DID_NOT_ACCEPT",
            "decision": decision,
            "ack_event_id": latest.get("event_id"),
            "result_event_ids": sorted(result_ids),
        }
    return {
        "status": "READY",
        "branch_id": branch_id,
        "result_event_ids": sorted(result_ids),
        "ack_event_id": latest.get("event_id"),
        "decision": decision,
    }


def run_cycle(
    task_state: Path,
    handoff: Path,
    project_event_log: Path,
    attention_log: Path,
    user_request: str,
    *,
    experience_logs: list[Path] | None = None,
    lesson_logs: list[Path] | None = None,
    task_state_paths: list[Path] | None = None,
    active_task_id: str | None = None,
    active_checkpoint_id: str | None = None,
    current_project_id: str | None = None,
    limit: int = 10,
    return_turn_id: str | None = None,
    parent_task_id: str | None = None,
) -> dict[str, Any]:
    """Build one composed cycle; optionally perform a guarded explicit parent return."""
    task_state, handoff = Path(task_state), Path(handoff)
    project_event_log, attention_log = Path(project_event_log), Path(attention_log)
    states = [Path(path) for path in (task_state_paths or [task_state])]
    experiences = [Path(path) for path in (experience_logs or [])]
    if project_event_log not in experiences:
        experiences.insert(0, project_event_log)
    lessons = [Path(path) for path in (lesson_logs or [])]

    task_start = build_task_start_experience_map(
        task_state, handoff, project_event_log, user_request,
        experience_logs=experiences, lesson_logs=lessons,
        attention_log=attention_log, active_task_id=active_task_id,
        active_checkpoint_id=active_checkpoint_id, current_project_id=current_project_id,
        limit=limit,
    )
    try:
        attention = inspect_attention(attention_log)
    except (OSError, ValueError) as exc:
        attention = {"status": "BLOCKED", "reason": str(exc), "active": None, "return_stack": []}
    reconciliation = build_branch_return_report(attention_log, states)

    return_result = None
    if (return_turn_id is None) != (parent_task_id is None):
        return_result = {
            "status": "REJECTED_RETURN_REQUEST",
            "reason": "return_turn_id and parent_task_id must be supplied together",
            "writes_performed": False,
        }
    elif return_turn_id is not None and parent_task_id is not None:
        if reconciliation.get("status") != "CONSISTENT":
            return_result = {
                "status": "BLOCKED_RECONCILIATION",
                "reconciliation_status": reconciliation.get("status"),
                "issues": reconciliation.get("issues", []),
                "writes_performed": False,
            }
        elif attention.get("status") != "OK":
            return_result = {
                "status": "BLOCKED_ATTENTION_STATE",
                "attention_status": attention.get("status"),
                "writes_performed": False,
            }
        elif not attention.get("return_stack"):
            # Preserve controller idempotency: a replay of the same return turn
            # is a no-op success, not a new blocked operation.
            return_result = _return_to_parent_unchecked(
                attention_log, turn_id=return_turn_id, parent_task_id=parent_task_id
            )
            if return_result.get("status") == "ALREADY_RETURNED":
                task_start = build_task_start_experience_map(
                    task_state, handoff, project_event_log, user_request,
                    experience_logs=experiences, lesson_logs=lessons,
                    attention_log=attention_log, active_task_id=parent_task_id,
                    active_checkpoint_id=active_checkpoint_id,
                    current_project_id=current_project_id, limit=limit,
                )
                attention = inspect_attention(attention_log)
        else:
            top = attention["return_stack"][-1]
            parent = top.get("parent", {}) if isinstance(top, dict) else {}
            branch_id = top.get("branch_id")
            if parent.get("task_id") != parent_task_id:
                return_result = {
                    "status": "BLOCKED_PARENT_MISMATCH",
                    "expected_parent_task_id": parent.get("task_id"),
                    "requested_parent_task_id": parent_task_id,
                    "writes_performed": False,
                }
            else:
                ready = _current_branch_result_ready(
                    attention_log, str(branch_id), parent_task_id,
                    str(parent.get("checkpoint_id") or ""),
                )
                if ready.get("status") != "READY":
                    return_result = {**ready, "writes_performed": False}
                else:
                    return_result = _return_to_parent_unchecked(
                        attention_log, turn_id=return_turn_id, parent_task_id=parent_task_id
                    )
                    if return_result.get("status") in {"RETURNED", "ALREADY_RETURNED"}:
                        attention = inspect_attention(attention_log)
                        task_start = build_task_start_experience_map(
                            task_state, handoff, project_event_log, user_request,
                            experience_logs=experiences, lesson_logs=lessons,
                            attention_log=attention_log, active_task_id=parent_task_id,
                            active_checkpoint_id=parent.get("checkpoint_id"),
                            current_project_id=current_project_id, limit=limit,
                        )

    blocked_return = return_result is not None and return_result.get("status") not in {
        "RETURNED", "ALREADY_RETURNED"
    }
    return {
        "schema_version": "1.0",
        "status": "BLOCKED" if blocked_return else "READY",
        "task_start": task_start,
        "attention": attention,
        "branch_reconciliation": reconciliation,
        "parent_return": return_result,
        "check_reuse": task_start.get("experience_map", {}).get("check_reuse_policy"),
        "writes_performed": bool(return_result and return_result.get("writes_performed")),
        "capability_boundary": {
            "local_explicit_invocation_only": True,
            "automatic_chatgpt_capture": False,
            "planning_authorized": False,
            "note": "A consistent local cycle is not proof of production applicability or authorization to execute the next task.",
        },
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-state", required=True, type=Path)
    parser.add_argument("--handoff", required=True, type=Path)
    parser.add_argument("--project-event-log", required=True, type=Path)
    parser.add_argument("--attention-log", required=True, type=Path)
    parser.add_argument("--request", required=True)
    parser.add_argument("--experience-log", action="append", default=[], type=Path)
    parser.add_argument("--lesson-log", action="append", default=[], type=Path)
    parser.add_argument("--reconcile-task-state", action="append", default=[], type=Path)
    parser.add_argument("--active-task-id")
    parser.add_argument("--active-checkpoint-id")
    parser.add_argument("--project-id")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--return-turn-id")
    parser.add_argument("--parent-task-id")
    args = parser.parse_args(argv)
    result = run_cycle(
        args.task_state, args.handoff, args.project_event_log, args.attention_log,
        args.request, experience_logs=args.experience_log, lesson_logs=args.lesson_log,
        task_state_paths=args.reconcile_task_state or [args.task_state],
        active_task_id=args.active_task_id, active_checkpoint_id=args.active_checkpoint_id,
        current_project_id=args.project_id, limit=args.limit,
        return_turn_id=args.return_turn_id, parent_task_id=args.parent_task_id,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
