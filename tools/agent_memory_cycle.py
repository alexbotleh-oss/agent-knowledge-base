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
import os

from dialogue_attention_controller import inspect as inspect_attention, _return_to_parent_unchecked
from reconcile_branch_returns import build_report as build_branch_return_report
from task_start_experience_map import build_task_start_experience_map
from memory_aware_session_restore import build_memory_aware_packet
from canonical_memory_index import DEFAULT_INDEX_ROOT, DEFAULT_REGISTRY
from trusted_receipt_verifier import verify_signed_receipt
from adaptive_task_flow import route_after_attempt
from experience_outcome_capture import capture_verified_experience_candidate


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

    # Only the newest result for this branch can authorize a return.
    # An acknowledgement for an older result must not authorize a newer one.
    result = results[-1]
    result_ids = {result["event_id"]}
    acknowledgements = [
        event for event in events
        if event.get("type") == "cross_branch_result_acknowledged"
        and isinstance(event.get("acknowledgement"), dict)
        and event["acknowledgement"].get("result_event_id") in result_ids
    ]
    if not acknowledgements:
        return {"status": "BLOCKED_OWNER_ACK_MISSING", "result_event_ids": sorted(result_ids)}
    latest = acknowledgements[-1]
    ack = latest["acknowledgement"]
    decision = ack.get("decision")
    if decision != "accepted":
        return {
            "status": "BLOCKED_OWNER_DID_NOT_ACCEPT",
            "decision": decision,
            "ack_event_id": latest.get("event_id"),
            "result_event_ids": sorted(result_ids),
        }
    matching_results = [event for event in results if event.get("event_id") == ack.get("result_event_id")]
    if not matching_results:
        return {"status": "BLOCKED_OWNER_ACK_CLAIM_MISMATCH", "ack_event_id": latest.get("event_id")}
    result = matching_results[0]
    branch = result.get("branch_return") or {}
    receipt = ack.get("signed_receipt")
    expected_claim = {
        "result_event_id": result.get("event_id"),
        "child_branch_id": branch.get("child_branch_id"),
        "parent_task_id": branch.get("parent_task_id"),
        "parent_checkpoint_id": branch.get("parent_checkpoint_id"),
        "decision": decision,
        "owner_ref": ack.get("owner_ref"),
    }
    keyring_path = os.environ.get("AGMS_TRUSTED_KEYRING_PATH")
    keyring_sha = os.environ.get("AGMS_TRUSTED_KEYRING_SHA256")
    verification = verify_signed_receipt(
        receipt, expected_claim,
        keyring_path=Path(keyring_path) if keyring_path else None,
        expected_keyring_sha256=keyring_sha,
    )
    if not verification.get("verified") or not isinstance(receipt, dict) or receipt.get("receipt_type") != "owner_acknowledgement":
        return {
            "status": "BLOCKED_OWNER_ACK_UNVERIFIED",
            "ack_event_id": latest.get("event_id"),
            "verification": verification,
            "result_event_ids": sorted(result_ids),
        }
    return {
        "status": "READY",
        "branch_id": branch_id,
        "result_event_ids": sorted(result_ids),
        "ack_event_id": latest.get("event_id"),
        "decision": decision,
        "owner_ack_verification": verification,
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
    repository: str | None = None,
    repository_ref: str | None = None,
    semantic_memory_query: str | None = None,
    memory_registry_path: Path = DEFAULT_REGISTRY,
    memory_index_root: Path = DEFAULT_INDEX_ROOT,
    source_catalog_path: Path | None = None,
    prior_failed_attempts: int = 0,
    risk_level: str = "normal",
    attempt_result_status: str | None = None,
    capture_outcome_candidate: bool = False,
    capture_evidence_root: Path | None = None,
    capture_task_id: str | None = None,
    capture_request_summary: str | None = None,
    capture_action_taken: str | None = None,
    capture_acceptance_criterion: str | None = None,
    capture_expected_evidence_marker: str | None = None,
    capture_evidence_file: Path | None = None,
    capture_observed_outcome: str | None = None,
    capture_related_event_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Build one composed cycle; optionally perform a guarded explicit parent return.

    When repository is supplied, one verified memory-aware packet is built and
    reused by task-start retrieval, avoiding a second independent restore pass.
    """
    task_state, handoff = Path(task_state), Path(handoff)
    project_event_log, attention_log = Path(project_event_log), Path(attention_log)
    states = [Path(path) for path in (task_state_paths or [task_state])]
    experiences = [Path(path) for path in (experience_logs or [])]
    if project_event_log not in experiences:
        experiences.insert(0, project_event_log)
    lessons = [Path(path) for path in (lesson_logs or [])]

    def build_start(task_id: str | None, checkpoint_id: str | None) -> dict[str, Any]:
        session_packet = None
        if isinstance(repository, str) and repository.strip():
            session_packet = build_memory_aware_packet(
                task_state, handoff, project_event_log, repository.strip(), repository_ref,
                task_id=task_id, context_id=checkpoint_id,
                query=semantic_memory_query or user_request,
                registry_path=Path(memory_registry_path), index_root=Path(memory_index_root),
                source_catalog_path=Path(source_catalog_path) if source_catalog_path else None,
            )
        return build_task_start_experience_map(
            task_state, handoff, project_event_log, user_request,
            experience_logs=experiences, lesson_logs=lessons,
            attention_log=attention_log, active_task_id=task_id,
            active_checkpoint_id=checkpoint_id, current_project_id=current_project_id,
            limit=limit, session_packet=session_packet,
            prior_failed_attempts=prior_failed_attempts,
            risk_level=risk_level,
        )

    task_start = build_start(active_task_id, active_checkpoint_id)
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
                task_start = build_start(parent_task_id, active_checkpoint_id)
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
                    def precommit_guard(event_path: Path, expected_top: dict[str, Any]) -> dict[str, Any]:
                        # Recheck the live event log while _return_to_parent_unchecked
                        # holds the shared journal lock, closing the preflight/commit race.
                        current_reconciliation = build_branch_return_report(event_path, states)
                        if current_reconciliation.get("status") != "CONSISTENT":
                            return {
                                "status": "BLOCKED_RECONCILIATION",
                                "reconciliation_status": current_reconciliation.get("status"),
                                "issues": current_reconciliation.get("issues", []),
                            }
                        current_attention = inspect_attention(event_path)
                        current_stack = current_attention.get("return_stack", [])
                        if current_attention.get("status") != "OK":
                            return {
                                "status": "BLOCKED_ATTENTION_STATE",
                                "attention_status": current_attention.get("status"),
                            }
                        if not current_stack or current_stack[-1].get("branch_id") != branch_id:
                            return {"status": "BLOCKED_RETURN_STACK_CHANGED"}
                        current_parent = current_stack[-1].get("parent", {})
                        if (
                            current_parent.get("task_id") != parent_task_id
                            or current_parent.get("checkpoint_id") != parent.get("checkpoint_id")
                            or expected_top.get("branch_id") != branch_id
                        ):
                            return {"status": "BLOCKED_PARENT_MISMATCH"}
                        return _current_branch_result_ready(
                            event_path, str(branch_id), parent_task_id,
                            str(parent.get("checkpoint_id") or ""),
                        )

                    return_result = _return_to_parent_unchecked(
                        attention_log, turn_id=return_turn_id, parent_task_id=parent_task_id,
                        precommit_guard=precommit_guard,
                    )
                    if return_result.get("status") in {"RETURNED", "ALREADY_RETURNED"}:
                        attention = inspect_attention(attention_log)
                        task_start = build_start(parent_task_id, parent.get("checkpoint_id"))

    attempt_outcome_route = (
        route_after_attempt(
            attempt_result_status,
            prior_failed_attempts=prior_failed_attempts,
            risk_level=risk_level,
        )
        if isinstance(attempt_result_status, str) and attempt_result_status.strip()
        else None
    )
    experience_capture: dict[str, Any] = {
        "status": "NOT_REQUESTED", "writes_performed": False,
        "semantic_memory_promoted": False,
    }
    if capture_outcome_candidate:
        if not isinstance(attempt_outcome_route, dict) or attempt_outcome_route.get("mode") != "CAPTURE_CONFIRMED_EXPERIENCE":
            experience_capture = {
                "status": "BLOCKED_ROUTE_NOT_CAPTURE_READY",
                "reason": "An explicit verified-success route is required before capture.",
                "writes_performed": False,
            }
        else:
            capture_required = {
                "capture_evidence_root": capture_evidence_root,
                "capture_task_id": capture_task_id or active_task_id,
                "capture_request_summary": capture_request_summary,
                "capture_action_taken": capture_action_taken,
                "capture_acceptance_criterion": capture_acceptance_criterion,
                "capture_expected_evidence_marker": capture_expected_evidence_marker,
                "capture_evidence_file": capture_evidence_file,
                "capture_observed_outcome": capture_observed_outcome,
            }
            missing_capture_fields = [
                name for name, value in capture_required.items()
                if value is None or (isinstance(value, str) and not value.strip())
            ]
            project_for_capture = current_project_id
            if not project_for_capture:
                project_for_capture = (
                    task_state.parent.name
                    if task_state.name == "TASK_STATE.md" and task_state.parent.parent.name == "projects"
                    else None
                )
            if missing_capture_fields or not project_for_capture:
                experience_capture = {
                    "status": "BLOCKED_CAPTURE_ARGUMENTS_MISSING",
                    "missing_fields": missing_capture_fields + (["project_id"] if not project_for_capture else []),
                    "writes_performed": False,
                }
            else:
                experience_capture = capture_verified_experience_candidate(
                    project_event_log,
                    evidence_root=Path(capture_evidence_root),
                    project_id=str(project_for_capture),
                    task_id=str(capture_task_id or active_task_id),
                    request_summary=str(capture_request_summary),
                    action_taken=str(capture_action_taken),
                    acceptance_criterion=str(capture_acceptance_criterion),
                    expected_evidence_marker=str(capture_expected_evidence_marker),
                    evidence_file=Path(capture_evidence_file),
                    observed_outcome=str(capture_observed_outcome),
                    related_event_ids=capture_related_event_ids,
                )
    blocked_return = return_result is not None and return_result.get("status") not in {
        "RETURNED", "ALREADY_RETURNED"
    }
    capture_blocked = capture_outcome_candidate and experience_capture.get("status") not in {
        "CAPTURED_CANDIDATE", "ALREADY_CAPTURED"
    }
    memory_section = task_start.get("task_restore", {}).get("semantic_memory", {})
    task_start_status = task_start.get("status", "UNKNOWN")
    cluster_issues = []
    if not (isinstance(repository, str) and repository.strip()):
        cluster_issues.append("LIVE_REPOSITORY_AND_APPROVED_MEMORY_NOT_CONFIGURED")
    if task_start_status != "READY_FOR_REVIEW":
        cluster_issues.append("TASK_START_NOT_READY_FOR_REVIEW:" + str(task_start_status))
    if attention.get("status") != "OK":
        cluster_issues.append("ATTENTION_STATE_NOT_VERIFIED")
    if reconciliation.get("status") != "CONSISTENT":
        cluster_issues.append("BRANCH_RECONCILIATION_NOT_CONSISTENT")
    if isinstance(repository, str) and repository.strip():
        if task_start.get("task_restore", {}).get("task_restore_status") not in {"RESTORED_PACKET", "PARTIAL"}:
            cluster_issues.append("VERIFIED_TASK_RESTORE_NOT_COMPLETE")
        if not isinstance(memory_section, dict) or memory_section.get("status") not in {
            "AVAILABLE", "PARTIAL", "PARTIAL_NO_MATCH"
        }:
            cluster_issues.append("APPROVED_MEMORY_NOT_AVAILABLE_OR_COMPLETE")
    cluster_readiness_status = (
        "BLOCKED" if blocked_return or task_start_status == "CONTEXT_OR_RETRIEVAL_BLOCKED"
        else "READY_FOR_REVIEW" if not cluster_issues
        else "PARTIAL"
    )
    return {
        "schema_version": "1.0",
        "status": "BLOCKED" if blocked_return or capture_blocked else "READY",
        "task_start": task_start,
        "semantic_memory_integration": {
            "status": "CONFIGURED" if isinstance(repository, str) and repository.strip() else "NOT_CONFIGURED",
            "repository": repository.strip() if isinstance(repository, str) and repository.strip() else None,
            "packet_status": task_start.get("task_restore", {}).get("status", "UNKNOWN"),
            "approved_memory_status": memory_section.get("status", "UNKNOWN") if isinstance(memory_section, dict) else "UNKNOWN",
            "note": "CONFIGURED means the verified memory-aware restore was invoked; it does not imply approved memory was available or planning was authorized."
                if isinstance(repository, str) and repository.strip()
                else "Legacy local task-start path only; approved semantic-memory retrieval and live repository verification were not invoked.",
        },
        "cluster_readiness": {
            "status": cluster_readiness_status,
            "issues": cluster_issues,
            "planning_authorized": False,
            "execution_performed": False,
            "note": "READY_FOR_REVIEW means the configured read-only cluster produced a reviewable packet; it never authorizes planning or action execution.",
        },
        "attention": attention,
        "branch_reconciliation": reconciliation,
        "parent_return": return_result,
        "attempt_outcome_route": attempt_outcome_route,
        "experience_capture": experience_capture,
        "check_reuse": task_start.get("experience_map", {}).get("check_reuse_policy"),
        "writes_performed": bool((return_result and return_result.get("writes_performed")) or experience_capture.get("writes_performed")),
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
    parser.add_argument("--prior-failed-attempts", type=int, default=0)
    parser.add_argument("--risk-level", choices=("low", "normal", "high", "critical"), default="normal")
    parser.add_argument("--attempt-result-status", choices=("FAIL", "FAILED", "ERROR", "REGRESSION", "NOT_SOLVED", "SUCCESS", "SOLVED", "VERIFIED_SUCCESS", "VERIFIED_SOLVED", "PASS", "BLOCKED", "UNAVAILABLE", "CANNOT_PROCEED", "UNKNOWN"), help="explicit observed outcome of the last attempt; routes the next step without executing it")
    parser.add_argument("--capture-outcome-candidate", action="store_true", help="explicitly persist a provenance-bound outcome candidate only after a verified-success route")
    parser.add_argument("--capture-evidence-root", type=Path)
    parser.add_argument("--capture-task-id")
    parser.add_argument("--capture-request-summary")
    parser.add_argument("--capture-action-taken")
    parser.add_argument("--capture-acceptance-criterion")
    parser.add_argument("--capture-expected-evidence-marker")
    parser.add_argument("--capture-evidence-file", type=Path)
    parser.add_argument("--capture-observed-outcome")
    parser.add_argument("--capture-related-event-id", action="append", default=[])
    parser.add_argument("--return-turn-id")
    parser.add_argument("--parent-task-id")
    parser.add_argument("--repository", help="GitHub owner/repository; enables live revision verification and approved-memory retrieval")
    parser.add_argument("--repository-ref", help="explicit branch/ref to verify; defaults to checkpoint branch")
    parser.add_argument("--memory-query", help="override the current request used for approved-memory retrieval")
    parser.add_argument("--memory-registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--memory-index-root", type=Path, default=DEFAULT_INDEX_ROOT)
    parser.add_argument("--source-catalog", type=Path)
    args = parser.parse_args(argv)
    result = run_cycle(
        args.task_state, args.handoff, args.project_event_log, args.attention_log,
        args.request, experience_logs=args.experience_log, lesson_logs=args.lesson_log,
        task_state_paths=args.reconcile_task_state or [args.task_state],
        active_task_id=args.active_task_id, active_checkpoint_id=args.active_checkpoint_id,
        current_project_id=args.project_id, limit=args.limit,
        return_turn_id=args.return_turn_id, parent_task_id=args.parent_task_id,
        repository=args.repository, repository_ref=args.repository_ref,
        semantic_memory_query=args.memory_query,
        memory_registry_path=args.memory_registry, memory_index_root=args.memory_index_root,
        source_catalog_path=args.source_catalog,
        prior_failed_attempts=args.prior_failed_attempts,
        risk_level=args.risk_level,
        attempt_result_status=args.attempt_result_status,
        capture_outcome_candidate=args.capture_outcome_candidate,
        capture_evidence_root=args.capture_evidence_root,
        capture_task_id=args.capture_task_id,
        capture_request_summary=args.capture_request_summary,
        capture_action_taken=args.capture_action_taken,
        capture_acceptance_criterion=args.capture_acceptance_criterion,
        capture_expected_evidence_marker=args.capture_expected_evidence_marker,
        capture_evidence_file=args.capture_evidence_file,
        capture_observed_outcome=args.capture_observed_outcome,
        capture_related_event_ids=args.capture_related_event_id,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
