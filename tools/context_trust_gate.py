#!/usr/bin/env python3
"""Fail-closed policy gate for actions that depend on restored session context."""
from __future__ import annotations

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
    next_step = context.get("next_step", "UNKNOWN")
    if not isinstance(next_step, str) or not next_step.strip() or next_step == "UNKNOWN":
        return {
            "status": "REFUSED_UNKNOWN_NEXT_STEP",
            "reason": "No explicit next step is available.",
        }
    return {"status": "AUTHORIZED_FOR_PLANNING", "reason": "Context gates passed."}


def select_authoritative_checkpoint(candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Select newest checkpoint only among fully verified candidates.

    Timestamp ordering is considered only after trust gates pass. No eligible
    checkpoint returns None, requiring reconciliation rather than guessing.
    """
    eligible = [
        candidate for candidate in candidates
        if candidate.get("freshness_verified") is True
        and candidate.get("semantic_context_usable") is True
        and candidate.get("event_linkage_complete") is True
    ]
    if not eligible:
        return None
    return max(eligible, key=lambda candidate: candidate.get("timestamp", ""))
