#!/usr/bin/env python3
"""Build rolling dialogue-memory windows from an append-only local message ledger.

This module is a deterministic view builder, not a ChatGPT capture integration.
Keep the canonical ledger outside public repositories. Attachment payloads are
never copied into this ledger/view: messages may contain stable library refs only.
"""
from __future__ import annotations

from collections import OrderedDict
from copy import deepcopy
from typing import Any

SCHEMA = "rima-dialogue-message-v1"
ROLES = {"user", "assistant"}
ATTACHMENT_STATUSES = {"AVAILABLE", "UNKNOWN", "UNAVAILABLE"}
FORBIDDEN_ATTACHMENT_PAYLOAD_KEYS = {
    "bytes", "base64", "binary", "payload", "content", "data", "raw_text"
}


def _required_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value


def _validate_message(event: Any) -> dict[str, Any]:
    if not isinstance(event, dict):
        raise ValueError("message event must be an object")
    if event.get("schema") != SCHEMA:
        raise ValueError("unsupported dialogue message schema")
    for field in ("event_id", "message_id", "conversation_id", "turn_id"):
        _required_text(event.get(field), field)
    if isinstance(event.get("sequence"), bool) or not isinstance(event.get("sequence"), int) or event["sequence"] < 1:
        raise ValueError("sequence must be a positive integer")
    if event.get("role") not in ROLES:
        raise ValueError("role must be user or assistant")
    if not isinstance(event.get("text"), str):
        raise ValueError("text must be a string")
    project_id = event.get("project_id")
    if project_id is not None and (not isinstance(project_id, str) or not project_id.strip()):
        raise ValueError("project_id must be null or a non-empty string")
    attachments = event.get("attachments", [])
    if not isinstance(attachments, list):
        raise ValueError("attachments must be a list of references")
    for index, attachment in enumerate(attachments):
        if not isinstance(attachment, dict):
            raise ValueError(f"attachment {index} must be a reference object")
        if FORBIDDEN_ATTACHMENT_PAYLOAD_KEYS.intersection(attachment):
            raise ValueError("attachment payload is forbidden; store a library reference only")
        _required_text(attachment.get("attachment_id"), f"attachments[{index}].attachment_id")
        _required_text(attachment.get("library_ref"), f"attachments[{index}].library_ref")
        status = attachment.get("access_status", "UNKNOWN")
        if status not in ATTACHMENT_STATUSES:
            raise ValueError(f"attachments[{index}].access_status is invalid")
    return deepcopy(event)


def normalize_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Validate and deterministically deduplicate exact replay by event/message ID."""
    if not isinstance(events, list):
        raise ValueError("events must be a list")
    by_event: dict[str, dict[str, Any]] = {}
    by_message: dict[str, dict[str, Any]] = {}
    normalized: list[dict[str, Any]] = []
    for raw in events:
        event = _validate_message(raw)
        eid, mid = event["event_id"], event["message_id"]
        if eid in by_event:
            if by_event[eid] != event:
                raise ValueError(f"event_id collision: {eid}")
            continue
        if mid in by_message:
            if by_message[mid] != event:
                raise ValueError(f"message_id collision: {mid}")
            continue
        by_event[eid] = event
        by_message[mid] = event
        normalized.append(event)
    normalized.sort(key=lambda item: item["sequence"])
    previous = 0
    for event in normalized:
        if event["sequence"] <= previous:
            raise ValueError("sequence values must be strictly increasing and unique")
        previous = event["sequence"]
    return normalized


def _pair(user: dict[str, Any], assistant: dict[str, Any]) -> dict[str, Any]:
    if user["conversation_id"] != assistant["conversation_id"] or user["turn_id"] != assistant["turn_id"]:
        raise ValueError("user and assistant messages do not belong to the same conversation turn")
    if user.get("project_id") != assistant.get("project_id"):
        raise ValueError(f"project boundary conflict in turn {user['turn_id']}")
    return {
        "conversation_id": user["conversation_id"],
        "turn_id": user["turn_id"],
        "project_id": user.get("project_id"),
        "user": {
            "message_id": user["message_id"],
            "sequence": user["sequence"],
            "source_time": user.get("source_time"),
            "text": user["text"],
            "attachments": deepcopy(user.get("attachments", [])),
        },
        "assistant": {
            "message_id": assistant["message_id"],
            "sequence": assistant["sequence"],
            "source_time": assistant.get("source_time"),
            "text": assistant["text"],
            "attachments": deepcopy(assistant.get("attachments", [])),
        },
        "completed_at_sequence": assistant["sequence"],
    }


def build_windows(
    events: list[dict[str, Any]],
    current_conversation_id: str,
    pair_limit: int = 5,
) -> dict[str, Any]:
    """Build global and current-chat windows; incomplete turns are never evicted."""
    _required_text(current_conversation_id, "current_conversation_id")
    if isinstance(pair_limit, bool) or not isinstance(pair_limit, int) or pair_limit < 1:
        raise ValueError("pair_limit must be a positive integer")
    ordered = normalize_events(events)

    turns: OrderedDict[tuple[str, str], dict[str, Any]] = OrderedDict()
    for event in ordered:
        key = (event["conversation_id"], event["turn_id"])
        turn = turns.setdefault(key, {"user": None, "assistant": None})
        role = event["role"]
        if turn[role] is not None:
            raise ValueError(f"duplicate {role} message in turn {event['turn_id']}")
        turn[role] = event

    completed = []
    pending = []
    for (conversation_id, turn_id), turn in turns.items():
        user, assistant = turn["user"], turn["assistant"]
        if user is not None and assistant is not None:
            completed.append(_pair(user, assistant))
        elif user is not None or assistant is not None:
            lone = user if user is not None else assistant
            pending.append({
                "conversation_id": conversation_id,
                "turn_id": turn_id,
                "project_id": lone.get("project_id"),
                "state": "AWAITING_ASSISTANT" if user is not None else "ORPHAN_ASSISTANT",
                "present_message": {
                    "role": lone["role"],
                    "message_id": lone["message_id"],
                    "sequence": lone["sequence"],
                    "text": lone["text"],
                    "attachments": deepcopy(lone.get("attachments", [])),
                },
            })

    completed.sort(key=lambda pair: pair["completed_at_sequence"])
    pending.sort(key=lambda item: item["present_message"]["sequence"])
    current_completed = [p for p in completed if p["conversation_id"] == current_conversation_id]
    current_pending = [p for p in pending if p["conversation_id"] == current_conversation_id]
    global_pending = pending[-1:] if pending else []

    return {
        "schema": "rima-dialogue-window-v1",
        "status": "PARTIAL" if pending else "COMPLETE_FOR_PROVIDED_LEDGER",
        "pair_limit": pair_limit,
        "source_event_count": len(ordered),
        "global_recent_pairs": deepcopy(completed[-pair_limit:]),
        "current_chat_recent_pairs": deepcopy(current_completed[-pair_limit:]),
        "global_pending_turns": deepcopy(global_pending),
        "current_chat_pending_turns": deepcopy(current_pending),
        "evicted_from_windows_but_retained_in_source": max(0, len(completed) - pair_limit),
        "attachment_policy": "REFERENCES_ONLY",
        "capture_integration": "NOT_IMPLEMENTED_BY_THIS_MODULE",
    }


def verify_windows(packet: dict[str, Any], current_conversation_id: str) -> dict[str, Any]:
    """Run a cheap self-check before using the packet to guide an action."""
    errors: list[str] = []
    if packet.get("schema") != "rima-dialogue-window-v1":
        errors.append("unsupported packet schema")
    if packet.get("attachment_policy") != "REFERENCES_ONLY":
        errors.append("attachment policy is not references-only")
    if packet.get("capture_integration") != "NOT_IMPLEMENTED_BY_THIS_MODULE":
        errors.append("capture boundary is missing")
    for pair in packet.get("current_chat_recent_pairs", []):
        if pair.get("conversation_id") != current_conversation_id:
            errors.append("current-chat window contains another conversation")
    for name in ("global_recent_pairs", "current_chat_recent_pairs"):
        pairs = packet.get(name, [])
        if not isinstance(pairs, list):
            errors.append(f"{name} must be a list")
            continue
        sequences = [p.get("completed_at_sequence") for p in pairs]
        if sequences != sorted(sequences):
            errors.append(f"{name} is not in chronological sequence order")
    return {"status": "PASS" if not errors else "BLOCKED", "errors": errors}


__all__ = ["SCHEMA", "normalize_events", "build_windows", "verify_windows"]
