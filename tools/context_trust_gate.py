#!/usr/bin/env python3
"""Fail-closed policy gate for actions that depend on restored session context."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def authorize_next_step(context: dict[str, Any]) -> dict[str, str]:
    """Return an explicit decision; this module never executes the requested action."""
    if not context.get("freshness_verified", False):
        return {
            "status": "REFUSED_UNVERIFIED_CONTEXT",
            "reason": "Source freshness has not been verified.",
        }
    if not context.get("semantic_context_usable", False):
        return {
            "status": "REFUSED_UNUSABLE_CONTEXT",
            "reason": "Semantic context is not marked usable.",
        }
    if not context.get("event_linkage_complete", False):
        return {
            "status": "PLAN_REQUIRES_CONFIRMATION",
            "reason": "Event history is incomplete; do not infer previous steps.",
        }
    if (
        context.get("event_log_scope_match") is not True
        and context.get("cross_project_linkage_verified") is not True
    ):
        return {
            "status": "PLAN_REQUIRES_CONFIRMATION",
            "reason": "Event-log project scope is mismatched or unknown; validate an explicit cross-project link before planning.",
        }
    next_step = context.get("next_step", "UNKNOWN")
    if not isinstance(next_step, str) or not next_step.strip() or next_step == "UNKNOWN":
        return {
            "status": "REFUSED_UNKNOWN_NEXT_STEP",
            "reason": "No explicit next step is available.",
        }
    return {"status": "AUTHORIZED_FOR_PLANNING", "reason": "Context gates passed."}


def _timestamp_key(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def select_authoritative_checkpoint(candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Select newest checkpoint only among trusted candidates with valid timezone-aware timestamps.

    Timestamp ordering is normalized to UTC after trust gates pass. Missing or
    malformed timestamps are not guessed; no eligible checkpoint returns None.
    """
    eligible = []
    for candidate in candidates:
        if not (
            candidate.get("freshness_verified") is True
            and candidate.get("semantic_context_usable") is True
            and candidate.get("event_linkage_complete") is True
            and (
                candidate.get("event_log_scope_match") is True
                or candidate.get("cross_project_linkage_verified") is True
            )
        ):
            continue
        timestamp = _timestamp_key(candidate.get("timestamp"))
        if timestamp is not None:
            eligible.append((timestamp, candidate))
    if not eligible:
        return None
    return max(eligible, key=lambda item: item[0])[1]
