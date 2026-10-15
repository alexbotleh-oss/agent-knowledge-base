#!/usr/bin/env python3
"""Append-only lifecycle ledger for recoverable assistant turns.

The ledger is intended for a trusted local/client integration. It cannot observe
ChatGPT messages by itself; the caller must register each user turn before work.
Do not put the default ledger inside a public repository.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

SCHEMA = "agent-turn-ledger-v1"
EVENTS = {
    "TURN_RECEIVED", "WORK_STARTED", "PROGRESS", "ARTIFACT_CREATED",
    "REPORT_PREPARED", "RESPONSE_SUBMITTED", "DELIVERY_ACKNOWLEDGED",
    "TURN_FAILED", "TURN_ABANDONED",
}
TERMINAL = {"DELIVERY_ACKNOWLEDGED", "TURN_FAILED", "TURN_ABANDONED"}
DEFAULT_LEDGER = Path.home() / ".local" / "state" / "agent-turn-ledger" / "events.jsonl"


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _lock(stream):
    if os.name == "nt":
        import msvcrt
        stream.seek(0, os.SEEK_END)
        if stream.tell() == 0:
            stream.write(b"0")
            stream.flush()
        stream.seek(0)
        msvcrt.locking(stream.fileno(), msvcrt.LK_LOCK, 1)
    else:
        import fcntl
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX)


def _unlock(stream):
    if os.name == "nt":
        import msvcrt
        stream.seek(0)
        msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl
        fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def read_events(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    result = []
    with path.open("r", encoding="utf-8") as f:
        for number, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"corrupt ledger JSON at line {number}: {exc}") from exc
            if item.get("schema") != SCHEMA or item.get("event_type") not in EVENTS:
                raise ValueError(f"invalid ledger event at line {number}")
            result.append(item)
    return result


def project_turns(events: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    turns: dict[str, dict[str, Any]] = {}
    for event in events:
        tid = event["turn_id"]
        kind = event["event_type"]
        if kind == "TURN_RECEIVED":
            if tid in turns:
                raise ValueError(f"duplicate TURN_RECEIVED for {tid}")
            turns[tid] = {
                "turn_id": tid, "task_id": event.get("task_id"),
                "received_at": event["timestamp"], "exact_user_text": event["user_text"],
                "user_text_sha256": event["user_text_sha256"],
                "previous_checkpoint": event.get("previous_checkpoint"),
                "state": "AWAITING_START", "last_event": event,
                "progress": [], "artifacts": [],
            }
            continue
        if tid not in turns:
            raise ValueError(f"event {kind} references unknown turn {tid}")
        turn = turns[tid]
        if turn["state"] in {"CLOSED_DELIVERED", "CLOSED_FAILED", "CLOSED_ABANDONED"}:
            raise ValueError(f"event after terminal state for {tid}")
        if kind == "WORK_STARTED":
            turn["state"] = "IN_PROGRESS"
        elif kind == "PROGRESS":
            turn["progress"].append(event.get("detail", ""))
        elif kind == "ARTIFACT_CREATED":
            turn["artifacts"].append(event.get("artifact", {}))
        elif kind == "REPORT_PREPARED":
            turn["state"] = "REPORT_PREPARED_UNCONFIRMED"
            turn["report"] = event.get("report", {})
        elif kind == "RESPONSE_SUBMITTED":
            turn["state"] = "RESPONSE_SUBMITTED_UNCONFIRMED"
            turn["response_submission"] = event.get("submission", {})
        elif kind == "DELIVERY_ACKNOWLEDGED":
            turn["state"] = "CLOSED_DELIVERED"
            turn["delivery"] = event.get("delivery", {})
        elif kind == "TURN_FAILED":
            turn["state"] = "CLOSED_FAILED"
            turn["failure"] = event.get("detail", "")
        elif kind == "TURN_ABANDONED":
            turn["state"] = "CLOSED_ABANDONED"
            turn["abandonment"] = event.get("detail", "")
        turn["last_event"] = event
    return turns


def append_event(path: Path, event: dict[str, Any]) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Open one stable inode; lock + append + fsync makes concurrent local writers
    # serialize. A partial final line is treated as corruption, never silently skipped.
    with path.open("a+b") as stream:
        _lock(stream)
        try:
            stream.seek(0)
            raw = stream.read().decode("utf-8")
            existing = []
            for line_no, line in enumerate(raw.splitlines(), 1):
                try:
                    existing.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise ValueError(f"corrupt ledger JSON at line {line_no}; refusing append") from exc
            # Stable event IDs make retries idempotent even when a caller loses
            # the acknowledgement after the append reached durable storage.
            for prior in existing:
                if prior.get("event_id") == event.get("event_id"):
                    prior_cmp = {k: v for k, v in prior.items() if k != "timestamp"}
                    event_cmp = {k: v for k, v in event.items() if k != "timestamp"}
                    if prior_cmp == event_cmp:
                        return {"status": "ALREADY_RECORDED", "event": prior}
                    raise ValueError(f"event_id collision with different content: {event.get('event_id')}")
            current = project_turns(existing)
            tid = event["turn_id"]
            if event["event_type"] == "TURN_RECEIVED":
                if tid in current:
                    old = current[tid]
                    if old["user_text_sha256"] == event["user_text_sha256"] and old.get("task_id") == event.get("task_id"):
                        return {"status": "ALREADY_REGISTERED", "turn": old}
                    raise ValueError(f"turn_id collision with different input: {tid}")
            elif tid not in current:
                raise ValueError(f"unknown turn_id: {tid}; register TURN_RECEIVED first")
            elif current[tid]["state"] in {"CLOSED_DELIVERED", "CLOSED_FAILED", "CLOSED_ABANDONED"}:
                raise ValueError(f"turn is already terminal: {tid}")
            stream.seek(0, os.SEEK_END)
            stream.write((json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8"))
            stream.flush()
            os.fsync(stream.fileno())
        finally:
            _unlock(stream)
    return {"status": "APPENDED", "event": event}


def record(path: Path, event_type: str, turn_id: str, **fields) -> dict[str, Any]:
    if event_type not in EVENTS:
        raise ValueError(f"unsupported event_type: {event_type}")
    event = {
        "schema": SCHEMA, "event_id": fields.pop("event_id", None) or f"{turn_id}:{event_type}:{digest(json.dumps(fields, sort_keys=True, ensure_ascii=False))[:12]}",
        "timestamp": now(), "event_type": event_type, "turn_id": turn_id, **fields,
    }
    return append_event(path, event)


def inspect(path: Path, turn_id: str | None = None) -> dict[str, Any]:
    turns = project_turns(read_events(path))
    chosen = {k: v for k, v in turns.items() if turn_id is None or k == turn_id}
    incomplete = [v for v in chosen.values() if v["state"] not in {"CLOSED_DELIVERED", "CLOSED_FAILED", "CLOSED_ABANDONED"}]
    return {"status": "OK", "turns": list(chosen.values()), "incomplete_turn_ids": [v["turn_id"] for v in incomplete]}


def scan_artifacts(roots: list[Path], since: str | None = None) -> list[dict[str, Any]]:
    """Find suspicious leftovers. Findings are leads, not proof of task ownership."""
    cutoff = dt.datetime.fromisoformat(since).timestamp() if since else None
    found = []
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            try:
                stat = path.stat()
                size = stat.st_size
                mtime = stat.st_mtime
                if cutoff is not None and mtime < cutoff:
                    continue
                name = path.name.lower()
                suspicious = size == 0 or name.endswith((".tmp", ".part", ".partial", ".lock")) or ".tmp-" in name or name.endswith((".pending", ".inprogress"))
                if suspicious:
                    found.append({
                        "path": str(path), "size_bytes": size,
                        "modified_at": dt.datetime.fromtimestamp(mtime, dt.timezone.utc).isoformat(),
                        "signals": (["empty_file"] if size == 0 else []) +
                                   (["temporary_or_in_progress_name"] if suspicious and size != 0 else []),
                        "ownership": "UNKNOWN_REQUIRES_CORRELATION",
                    })
            except OSError as exc:
                found.append({"path": str(path), "status": "UNREADABLE", "detail": str(exc), "ownership": "UNKNOWN"})
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER,
                        help="protected local JSONL path; do not store exact messages in a public repo")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("receive", help="persist exact user input before processing")
    p.add_argument("--turn-id", required=True); p.add_argument("--task-id", required=True)
    p.add_argument("--text", required=True); p.add_argument("--previous-checkpoint")
    p = sub.add_parser("event", help="append a lifecycle event")
    p.add_argument("--turn-id", required=True)
    p.add_argument("--type", required=True, choices=sorted(EVENTS - {"TURN_RECEIVED"}))
    p.add_argument("--detail", default="")
    p.add_argument("--artifact-path"); p.add_argument("--artifact-status")
    p.add_argument("--report-path"); p.add_argument("--report-sha256")
    p.add_argument("--submission-ref"); p.add_argument("--delivery-ref")
    p = sub.add_parser("inspect", help="show open/incomplete turns")
    p.add_argument("--turn-id")
    p = sub.add_parser("scan-artifacts", help="find possible incomplete workspace artifacts")
    p.add_argument("--root", type=Path, action="append", required=True)
    p.add_argument("--since", help="ISO timestamp; optional")
    args = parser.parse_args(argv)
    try:
        if args.command == "receive":
            result = record(args.ledger, "TURN_RECEIVED", args.turn_id, task_id=args.task_id,
                            user_text=args.text, user_text_sha256=digest(args.text),
                            previous_checkpoint=args.previous_checkpoint)
        elif args.command == "event":
            fields: dict[str, Any] = {"detail": args.detail}
            if args.artifact_path:
                fields["artifact"] = {"path": args.artifact_path, "status": args.artifact_status or "UNKNOWN"}
            if args.report_path:
                fields["report"] = {"path": args.report_path, "sha256": args.report_sha256}
            if args.submission_ref: fields["submission"] = {"reference": args.submission_ref}
            if args.delivery_ref: fields["delivery"] = {"reference": args.delivery_ref}
            result = record(args.ledger, args.type, args.turn_id, **fields)
        elif args.command == "inspect":
            result = inspect(args.ledger, args.turn_id)
        else:
            result = {"status": "SCAN_COMPLETE", "findings": scan_artifacts(args.root, args.since)}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
