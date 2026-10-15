#!/usr/bin/env python3
"""Extract conservative, source-backed task semantics from a recovery packet."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

UNKNOWN = "UNKNOWN"

# Match explicit labels used in the current Markdown memory format. Do not infer
# a next step from a plan or an "Осталось" list.
LABELS = {
    "active_goal": re.compile(r"^\\s*[-*]?\\s*\\*\\*(?:Активная задача в текущей сессии|Current task|Задача этого PR|Текущая задача):\\*\\*\\s*(.+?)\\s*$", re.I),
    "historical_goal": re.compile(r"^\s*[-*]?\s*\*\*Историческая задача[^:]*:\*\*\s*(.+?)\s*$", re.I),
    "next_step": re.compile(r"^\s*[-*]?\s*\*\*(?:Следующий шаг|Текущий следующий шаг):\*\*\s*(.+?)\s*$", re.I),
    "blockers": re.compile(r"^\s*[-*]?\s*\*\*Блокеры / решение пользователя:\*\*\s*(.+?)\s*$", re.I),
    "last_event": re.compile(r"^\s*[-*]?\s*\*\*Последнее событие:\*\*\s*(.+?)\s*$", re.I),
}


def _lines(*fragments: tuple[str, str]) -> list[tuple[str, str]]:
    result = []
    for source_name, fragment in fragments:
        for line in fragment.splitlines():
            result.append((source_name, line.strip()))
    return result


def _ref(source: str, line: str, digest: str | None) -> dict[str, Any]:
    return {"source": source, "fragment": line, "source_sha256": digest}


def extract_semantic_context(packet: dict[str, Any], *, verify_sources: bool = True) -> dict[str, Any]:
    """Interpret a build_session_packet result without guessing missing fields.

    The packet schema is the one returned by tools/restore_session_packet.py.
    When verify_sources is true, compare current source bytes with the packet's
    hashes so an old packet cannot silently be presented as current.
    """
    status = packet.get("status", UNKNOWN)
    scope = packet.get("project_scope") or {}
    hashes = packet.get("source_hashes") or {}
    source_hashes = {
        "task_state": hashes.get("task_state_sha256", UNKNOWN),
        "handoff": hashes.get("handoff_sha256", UNKNOWN),
        "events": hashes.get("event_log_sha256", UNKNOWN),
    }
    freshness: dict[str, str] = {}
    if verify_sources:
        paths = {
            "task_state": scope.get("task_state_path"),
            "handoff": scope.get("handoff_path"),
            "events": scope.get("event_log_path"),
        }
        for key, raw_path in paths.items():
            expected = source_hashes[key]
            if not raw_path or expected == UNKNOWN:
                freshness[key] = "UNKNOWN"
                continue
            path = Path(raw_path)
            if not path.is_file():
                freshness[key] = "MISSING"
                continue
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            freshness[key] = "CURRENT" if actual == expected else "CHANGED"
        if any(value in {"MISSING", "CHANGED"} for value in freshness.values()):
            status = "SOURCE_CHANGED" if "CHANGED" in freshness.values() else "SOURCE_MISSING"

    task_header = packet.get("task_state_header") or ""
    task_excerpt = packet.get("latest_task_state_excerpt") or ""
    handoff_excerpt = packet.get("latest_handoff_excerpt") or ""
    task_digest = source_hashes["task_state"]
    handoff_digest = source_hashes["handoff"]
    lines = _lines(("TASK_STATE.md", task_header), ("TASK_STATE.md", task_excerpt),
                   ("HANDOFF.md", handoff_excerpt))

    values: dict[str, Any] = {
        "active_goal": UNKNOWN,
        "historical_goal": UNKNOWN,
        "next_step": UNKNOWN,
        "open_questions": [],
        "blockers": [],
        "last_event": UNKNOWN,
    }
    provenance: dict[str, Any] = {
        "active_goal": None, "historical_goal": None, "next_step": None,
        "open_questions": [], "blockers": [], "last_event": None,
    }
    seen: set[tuple[str, str]] = set()
    question_mode: str | None = None
    for source, line in lines:
        if not line:
            if question_mode:
                question_mode = None
            continue
        # Avoid duplicate matches because the packet header may overlap excerpt text.
        key = (source, line)
        if key in seen:
            continue
        seen.add(key)
        if line.casefold() in {"## открытые вопросы", "## open questions"}:
            question_mode = source
            continue
        if line.startswith("#"):
            question_mode = None
        elif question_mode and re.match(r"^[-*]\s+.+\?\s*$", line):
            question = re.sub(r"^[-*]\s+", "", line).strip()
            values["open_questions"].append(question)
            digest = task_digest if source == "TASK_STATE.md" else handoff_digest
            provenance["open_questions"].append(_ref(source, line, digest))
            continue
        elif question_mode and re.match(r"^[-*]\s+", line):
            # A list item in a clearly labelled open-questions section is retained
            # as written, even if it is not punctuated with a question mark.
            question = re.sub(r"^[-*]\s+", "", line).strip()
            values["open_questions"].append(question)
            digest = task_digest if source == "TASK_STATE.md" else handoff_digest
            provenance["open_questions"].append(_ref(source, line, digest))
            continue
        for field, pattern in LABELS.items():
            match = pattern.match(line)
            if not match:
                continue
            value = match.group(1).strip().rstrip(".")
            digest = task_digest if source == "TASK_STATE.md" else handoff_digest
            # TASK_STATE is session-scoped and takes precedence over the
            # project-level HANDOFF. HANDOFF fills only fields absent in TASK_STATE.
            if source == "HANDOFF.md" and values[field] != UNKNOWN and values[field] != []:
                break
            if field == "blockers":
                values[field] = [value]
                provenance[field] = [_ref(source, line, digest)]
            else:
                values[field] = value
                provenance[field] = _ref(source, line, digest)
            break

    # Keep source-specific status and uncertainty visible; do not promote
    # packet status to proof of semantic restoration.
    field_status = {
        field: ("FOUND" if (value != UNKNOWN and value != []) else "UNKNOWN")
        for field, value in values.items()
    }
    if status in {"SOURCE_CHANGED", "SOURCE_MISSING"}:
        # Preserve extracted text for audit, but do not label it as current.
        field_status = {
            field: ("STALE_SOURCE" if state == "FOUND" else state)
            for field, state in field_status.items()
        }
    freshness_verified = (
        verify_sources
        and len(freshness) == 3
        and all(value == "CURRENT" for value in freshness.values())
        and status not in {"BLOCKED", "SOURCE_CHANGED", "SOURCE_MISSING", UNKNOWN}
    )
    semantic_context_usable = (
        freshness_verified
        and status in {"RESTORED_PACKET", "PARTIAL"}
        and bool(values["active_goal"] != UNKNOWN)
    )
    event_linkage_complete = (
        freshness_verified
        and status == "RESTORED_PACKET"
        and not packet.get("missing_event_refs")
    )
    return {
        **values,
        "source_hashes": source_hashes,
        "source_freshness": freshness,
        "status": status,
        "freshness_verified": freshness_verified,
        "semantic_context_usable": semantic_context_usable,
        "event_linkage_complete": event_linkage_complete,
        "field_status": field_status,
        "provenance": provenance,
        "writes_performed": False,
    }
