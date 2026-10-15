#!/usr/bin/env python3
"""Build a source-backed session recovery packet from canonical project files."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

EVENT_ID_RE = re.compile(r"\bEVT-[A-Z0-9-]+\b")
CHECKPOINT_RE = re.compile(r"^#{1,4} .*checkpoint.*$", re.IGNORECASE | re.MULTILINE)


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


def _tail_with_checkpoints(text: str, max_chars: int) -> str:
    headings = list(CHECKPOINT_RE.finditer(text))
    if headings:
        start = headings[-min(6, len(headings))].start()
        selected = text[start:]
        if len(selected) <= max_chars:
            return selected
    return text[-max_chars:]


def build_session_packet(task_state: Path, handoff: Path, event_log: Path,
                         *, max_chars: int = 12000) -> dict[str, Any]:
    task_state, handoff, event_log = Path(task_state), Path(handoff), Path(event_log)
    missing = [str(path) for path in (task_state, handoff, event_log) if not path.is_file()]
    if missing:
        return {
            "status": "BLOCKED",
            "reason": "Required canonical source files are unavailable.",
            "missing_sources": missing,
            "writes_performed": False,
        }
    if task_state.resolve().parent != handoff.resolve().parent:
        return {
            "status": "BLOCKED",
            "reason": "TASK_STATE.md and HANDOFF.md must come from the same project directory.",
            "project_scope": {
                "task_state_path": str(task_state),
                "handoff_path": str(handoff),
                "event_log_path": str(event_log),
            },
            "writes_performed": False,
        }
    try:
        task_text = task_state.read_text(encoding="utf-8")
        handoff_text = handoff.read_text(encoding="utf-8")
        events = load_events(event_log)
    except Exception as exc:
        return {"status": "BLOCKED", "reason": f"Source validation failed: {exc}", "writes_performed": False}

    seen_event_ids: set[str] = set()
    duplicate_event_ids: set[str] = set()
    for event in events:
        event_id = event["event_id"]
        if event_id in seen_event_ids:
            duplicate_event_ids.add(event_id)
        seen_event_ids.add(event_id)
    if duplicate_event_ids:
        return {
            "status": "BLOCKED",
            "reason": "Duplicate event_id values make source linkage ambiguous.",
            "duplicate_event_ids": sorted(duplicate_event_ids),
            "writes_performed": False,
        }

    task_slice = _tail_with_checkpoints(task_text, max_chars)
    handoff_slice = _tail_with_checkpoints(handoff_text, max_chars)
    referenced_ids = set(EVENT_ID_RE.findall(task_text[:5000] + "\n" + task_slice + "\n" + handoff_slice))
    event_by_id = {event["event_id"]: event for event in events}
    linked_events = [event_by_id[event_id] for event_id in sorted(referenced_ids) if event_id in event_by_id]
    missing_event_refs = sorted(referenced_ids - set(event_by_id))
    latest_task_checkpoint = task_slice
    latest_handoff_checkpoint = handoff_slice

    return {
        "packet_version": "1.0",
        "status": "RESTORED_PACKET" if not missing_event_refs else "PARTIAL",
        "project_scope": {
            "task_state_path": str(task_state),
            "handoff_path": str(handoff),
            "event_log_path": str(event_log),
            "task_project_id": task_state.resolve().parent.name,
            "handoff_project_id": handoff.resolve().parent.name,
            "event_log_project_id": event_log.resolve().parent.name,
            "event_log_scope_match": task_state.resolve().parent == event_log.resolve().parent,
        },
        "source_hashes": {
            "task_state_sha256": sha256_file(task_state),
            "handoff_sha256": sha256_file(handoff),
            "event_log_sha256": sha256_file(event_log),
        },
        "task_state_header": "\n".join(task_text.splitlines()[:18]),
        "latest_task_state_excerpt": latest_task_checkpoint,
        "latest_handoff_excerpt": latest_handoff_checkpoint,
        "linked_events": linked_events,
        "missing_event_refs": missing_event_refs,
        "event_count": len(events),
        "warnings": [
            "This is a source-backed recovery packet, not proof that every chat message was captured.",
            "Excerpts preserve source text; the caller must interpret goal, status and next action without treating hypotheses as facts.",
            "Missing event references cause PARTIAL status; unavailable canonical files cause BLOCKED.",
            "No source file is modified.",
        ],
        "writes_performed": False,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task_state", type=Path)
    parser.add_argument("handoff", type=Path)
    parser.add_argument("event_log", type=Path)
    parser.add_argument("--max-chars", type=int, default=12000)
    args = parser.parse_args(argv)
    packet = build_session_packet(args.task_state, args.handoff, args.event_log, max_chars=args.max_chars)
    print(json.dumps(packet, ensure_ascii=False, indent=2))
    return 0 if packet["status"] == "RESTORED_PACKET" else 2


if __name__ == "__main__":
    raise SystemExit(main())
