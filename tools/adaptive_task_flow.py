#!/usr/bin/env python3
"""Adaptive task-routing policy: experience first, deeper analysis on failure.

This module chooses the next mode; it does not execute tasks or perform web
searches. Callers must report observed outcomes rather than assuming success.
"""
from __future__ import annotations

from typing import Any

RISK_LEVELS = {"low", "normal", "high", "critical"}
FAILURE_RESULTS = {"FAIL", "FAILED", "ERROR", "REGRESSION", "NOT_SOLVED"}
SUCCESS_RESULTS = {"SUCCESS", "SOLVED"}
VERIFIED_SUCCESS_RESULTS = {"VERIFIED_SUCCESS", "VERIFIED_SOLVED", "PASS"}
BLOCKED_RESULTS = {"BLOCKED", "UNAVAILABLE", "CANNOT_PROCEED"}


def _status(value: Any) -> str:
    return value.strip().upper() if isinstance(value, str) else "UNKNOWN"


def select_initial_route(
    *,
    experience_status: str,
    lesson_status: str,
    applicable_experience_count: int = 0,
    unresolved_candidate_count: int = 0,
    candidate_count: int = 0,
    prior_failed_attempts: int = 0,
    risk_level: str = "normal",
    semantic_memory_status: str = "NOT_REQUESTED",
) -> dict[str, Any]:
    """Choose an initial route without treating unavailable memory as empty."""
    risk = _status(risk_level).lower()
    if risk not in RISK_LEVELS:
        return {
            "status": "INVALID_INPUT",
            "mode": "STOP_AND_RECONCILE",
            "reason": "risk_level must be low, normal, high, or critical",
            "writes_performed": False,
        }
    counts = (applicable_experience_count, unresolved_candidate_count, candidate_count, prior_failed_attempts)
    if any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in counts):
        return {
            "status": "INVALID_INPUT",
            "mode": "STOP_AND_RECONCILE",
            "reason": "candidate and attempt counts must be non-negative integers",
            "writes_performed": False,
        }

    exp_status, lesson_status = _status(experience_status), _status(lesson_status)
    mem_status = _status(semantic_memory_status)
    incomplete_statuses = {"BLOCKED", "UNAVAILABLE", "STALE", "INVALID", "UNKNOWN", "NOT_REQUESTED"}
    search_incomplete = (
        exp_status in incomplete_statuses
        or lesson_status in incomplete_statuses
        or mem_status in incomplete_statuses
    )

    if risk in {"high", "critical"}:
        mode = "DEEP_ANALYSIS_BEFORE_EXECUTION"
        reason = "Risk level requires critical analysis before acting."
    elif prior_failed_attempts > 0:
        mode = "DEEP_ANALYSIS_BEFORE_RETRY"
        reason = "Prior failed attempts raise the analysis depth before another execution."
    elif applicable_experience_count > 0:
        mode = "APPLY_RELEVANT_EXPERIENCE"
        reason = "A candidate passed the current applicability evaluator; apply only within its supported scope."
    elif unresolved_candidate_count > 0:
        mode = "REVIEW_EXPERIENCE_CANDIDATES"
        reason = "Relevant candidates exist but applicability or evidence remains unresolved."
    elif candidate_count > 0:
        mode = "STANDARD_EXECUTION_AFTER_EXPERIENCE_REVIEW"
        reason = "Retrieved candidates were not assessed as applicable; do not treat them as instructions."
    else:
        mode = "STANDARD_EXECUTION_AFTER_EXPERIENCE_REVIEW"
        reason = "No applicable experience was found in the completed local search; proceed with ordinary execution."

    if search_incomplete and risk not in {"high", "critical"} and prior_failed_attempts == 0:
        reason += " One or more experience sources were unavailable/incomplete, so this is not proof that no experience exists."
    return {
        "status": "ROUTE_SELECTED",
        "mode": mode,
        "reason": reason,
        "risk_level": risk,
        "prior_failed_attempts": prior_failed_attempts,
        "experience_search": {
            "event_status": exp_status,
            "lesson_status": lesson_status,
            "semantic_memory_status": mem_status,
            "search_incomplete": search_incomplete,
            "absence_proven": (
                exp_status in {"NO_MATCHES", "NO_MATCH"}
                and lesson_status in {"NO_MATCHES", "NO_MATCH"}
                and mem_status in {"NO_MATCHES", "NO_MATCH"}
            ),
        },
        "applicable_experience_count": applicable_experience_count,
        "unresolved_candidate_count": unresolved_candidate_count,
        "candidate_count": candidate_count,
        "external_search_required_now": mode in {
            "DEEP_ANALYSIS_BEFORE_EXECUTION", "DEEP_ANALYSIS_BEFORE_RETRY"
        },
        "writes_performed": False,
        "execution_performed": False,
    }


def route_after_attempt(
    result_status: str,
    *,
    prior_failed_attempts: int = 0,
    risk_level: str = "normal",
) -> dict[str, Any]:
    """Route from an explicitly reported attempt outcome to the next step."""
    result = _status(result_status)
    risk = _status(risk_level).lower()
    if risk not in RISK_LEVELS or isinstance(prior_failed_attempts, bool) or not isinstance(prior_failed_attempts, int) or prior_failed_attempts < 0:
        return {
            "status": "INVALID_INPUT",
            "mode": "STOP_AND_RECONCILE",
            "reason": "invalid risk level or prior failed-attempt count",
            "writes_performed": False,
        }
    if result in VERIFIED_SUCCESS_RESULTS:
        mode = "CAPTURE_CONFIRMED_EXPERIENCE"
        reason = "A verified successful result can be considered for provenance-backed experience capture."
        external = False
    elif result in SUCCESS_RESULTS:
        mode = "VERIFY_RESULT"
        reason = "A reported success is not yet verified; check the acceptance criterion before capturing it as successful experience."
        external = False
    elif result in FAILURE_RESULTS:
        mode = "DEEP_ANALYSIS_EXTERNAL_SEARCH"
        reason = "The attempt did not solve the task; diagnose the cause and consult relevant external documentation/resources before another attempt."
        external = True
    elif result in BLOCKED_RESULTS:
        mode = "RESOLVE_BLOCKER_OR_REPORT_LIMIT"
        reason = "The attempt was blocked; resolve the concrete access/source/environment blocker before treating it as a solution failure."
        external = False
    else:
        mode = "VERIFY_RESULT"
        reason = "Outcome is unknown or unrecognized; establish the actual result before deciding the next step."
        external = False
    if prior_failed_attempts > 0 and result not in VERIFIED_SUCCESS_RESULTS:
        reason += " Earlier failed attempts also argue against repeating the same approach."
        if result in SUCCESS_RESULTS:
            mode = "DEEP_ANALYSIS_EXTERNAL_SEARCH"
            external = True
    if risk in {"high", "critical"} and result not in VERIFIED_SUCCESS_RESULTS:
        reason += " Risk remains elevated; do not proceed on an unverified assumption."
    return {
        "status": "ROUTE_SELECTED",
        "mode": mode,
        "reason": reason,
        "result_status": result,
        "prior_failed_attempts": prior_failed_attempts,
        "risk_level": risk,
        "external_search_required_now": external,
        "writes_performed": False,
        "execution_performed": False,
    }
