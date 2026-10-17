#!/usr/bin/env python3
"""Persistent dialogue attention and causal-return controller (local primitive).

This controller is deliberately conservative: lexical classification is a proposal,
not proof of intent. Ambiguous turns are recorded as NEEDS_REVIEW. State is rebuilt
from the canonical AGENT_MEMORY_SYSTEM event log; no second task-state database is
created. It does not observe ChatGPT automatically or execute deferred ideas.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

CLASSIFICATIONS = {
    "CONTINUATION", "CORRECTION", "SIDE_BRANCH", "DEFERRED_IDEA",
    "NEW_TASK", "PRIORITY_CHANGE", "RETURN_TO_PARENT", "AMBIGUOUS",
}
SWITCHING = {"SIDE_BRANCH", "NEW_TASK", "PRIORITY_CHANGE"}
CONTROLLER_TYPES = {
    "attention_turn_classified", "attention_branch_opened",
    "attention_idea_deferred", "attention_returned",
}
DEFAULT_LOG = Path(__file__).resolve().parents[1] / "projects" / "AGENT_MEMORY_SYSTEM" / "events.jsonl"


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _stable_payload(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _stable_payload(v) for k, v in value.items()
                if k not in {"recorded_at", "returned_at"}}
    if isinstance(value, list):
        return [_stable_payload(item) for item in value]
    return value


def _event_id(turn_id: str, kind: str, payload: dict[str, Any]) -> str:
    material = _canonical({"turn_id": turn_id, "kind": kind, "payload": _stable_payload(payload)})
    return "EVT-ATTN-" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:24].upper()


def _same_event(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return _canonical(_stable_payload(left)) == _canonical(_stable_payload(right))


def classify_turn(text: str) -> dict[str, Any]:
    """Return a deterministic suggestion; low-specificity language stays ambiguous."""
    value = re.sub(r"\s+", " ", text.casefold()).strip()
    rules = [
        ("RETURN_TO_PARENT", (
            r"\bвернись к (?:основной|исходной|родительской) задач",
            r"\bвозвращаемся к (?:основной|исходной|предыдущей) задач",
            r"\bвернуться к основной задач", r"\breturn to (?:the )?parent",
            r"\bresume (?:the )?parent task",
        )),
        ("PRIORITY_CHANGE", (
            r"\bтеперь приоритет", r"\bсначала делаем", r"\bвместо этого",
            r"\bотложи основную задач", r"\bменяем приоритет", r"\bpriority change",
        )),
        ("DEFERRED_IDEA", (
            r"\bзапомни (?:эту )?идею", r"\bотложи (?:эту )?идею",
            r"\bвернёмся к этому позже", r"\bпотом рассмотрим", r"\bdefer this idea",
        )),
        ("SIDE_BRANCH", (
            r"\bкстати\b", r"\bотдельный вопрос", r"\bпока отвлечёмся",
            r"\bпараллельно проверь", r"\bside question", r"\bseparate question",
        )),
        ("NEW_TASK", (
            r"\bновая задача", r"\bначнём новый проект", r"\bдругая задача",
            r"\bnew task", r"\bstart a new project",
        )),
        ("CORRECTION", (
            r"^(нет|не так|ошибка|исправь|поправь)\b", r"\bя имел в виду\b",
            r"\bэто неверно\b", r"\bcorrection:",
        )),
        ("CONTINUATION", (
            r"^(продолжай|продолжай работу|дальше|продолжи|поехали)\b",
            r"\bпродолжай именно задачу\b", r"\bcontinue\b", r"\bgo on\b",
        )),
    ]
    for label, patterns in rules:
        if any(re.search(pattern, value) for pattern in patterns):
            return {
                "classification": label,
                "confidence": "RULE_MATCH",
                "matched_rule": next(pattern for pattern in patterns if re.search(pattern, value)),
                "needs_confirmation": label in SWITCHING or label == "RETURN_TO_PARENT",
            }
    return {
        "classification": "AMBIGUOUS",
        "confidence": "INSUFFICIENT_SIGNAL",
        "matched_rule": None,
        "needs_confirmation": True,
    }


def read_events(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    events = []
    seen = set()
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"corrupt canonical event log at line {line_no}: {exc}") from exc
        if (not isinstance(event, dict) or not isinstance(event.get("event_id"), str)
                or not event.get("event_id", "").strip()):
            raise ValueError(f"invalid canonical event at line {line_no}: non-empty event_id required")
        if event["event_id"] in seen:
            raise ValueError(f"duplicate event_id {event['event_id']} at line {line_no}")
        seen.add(event["event_id"])
        events.append(event)
    return events


def project_state(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Rebuild the active attention state and return stack from canonical events."""
    stack: list[dict[str, Any]] = []
    active: dict[str, Any] | None = None
    turn_records: dict[str, dict[str, Any]] = {}
    for event in events:
        kind = event.get("type")
        data = event.get("attention") if isinstance(event.get("attention"), dict) else {}
        if kind == "attention_turn_classified":
            turn_id = data.get("turn_id")
            required_fields = ("turn_id", "active_task_id", "active_checkpoint_id")
            if any(not isinstance(data.get(key), str) or not data.get(key).strip()
                   for key in required_fields):
                raise ValueError(
                    f"attention event {event['event_id']} missing turn/task/checkpoint identifier"
                )
            previous = turn_records.get(turn_id)
            if previous is not None and _canonical(previous) != _canonical(data):
                raise ValueError(f"conflicting turn_id {turn_id} at event {event['event_id']}")
            turn_records[turn_id] = data
            # Outside a suspended branch, the latest caller-observed task is the
            # current projection. While a branch is open, its child remains active
            # until an explicit LIFO return event restores the parent.
            if not stack:
                active = {
                    "task_id": data.get("active_task_id"),
                    "checkpoint_id": data.get("active_checkpoint_id"),
                }
        elif kind == "attention_branch_opened":
            parent = data.get("parent")
            child = data.get("child")
            if not isinstance(parent, dict) or not isinstance(child, dict):
                raise ValueError(f"invalid branch-open event {event['event_id']}")
            required_strings = ("branch_id", "classification", "turn_id")
            if any(not isinstance(data.get(key), str) or not data.get(key).strip()
                   for key in required_strings):
                raise ValueError(f"invalid branch-open event {event['event_id']}: required identifiers missing")
            if any(not isinstance(frame.get(key), str) or not frame.get(key).strip()
                   for frame in (parent, child) for key in ("task_id", "checkpoint_id")):
                raise ValueError(f"invalid branch-open event {event['event_id']}: task/checkpoint missing")
            if active is not None and active.get("task_id") != parent.get("task_id"):
                raise ValueError(f"causal stack mismatch at {event['event_id']}: active task differs from parent")
            stack.append({
                "branch_id": data["branch_id"],
                "classification": data["classification"],
                "parent": parent,
                "return_condition": data.get("return_condition", "branch result reviewed"),
                "opened_by_turn_id": data["turn_id"],
                "child": child,
            })
            active = dict(child)
        elif kind == "attention_idea_deferred":
            turn_id = data.get("turn_id")
            required_fields = ("turn_id", "active_task_id", "active_checkpoint_id")
            if any(not isinstance(data.get(key), str) or not data.get(key).strip()
                   for key in required_fields):
                raise ValueError(
                    f"deferred idea event {event['event_id']} missing turn/task/checkpoint identifier"
                )
            previous = turn_records.get(turn_id)
            if previous is not None and _canonical(previous) != _canonical(data):
                raise ValueError(f"conflicting turn_id {turn_id} at event {event['event_id']}")
            turn_records[turn_id] = data
            if not stack:
                active = {
                    "task_id": data.get("active_task_id"),
                    "checkpoint_id": data.get("active_checkpoint_id"),
                }
        elif kind == "attention_returned":
            if not stack:
                raise ValueError(f"return event {event['event_id']} has no open parent frame")
            top = stack[-1]
            if data.get("branch_id") != top["branch_id"]:
                raise ValueError(f"return event {event['event_id']} does not target top stack frame")
            if data.get("parent_task_id") != top["parent"].get("task_id"):
                raise ValueError(f"return event {event['event_id']} parent task mismatch")
            if data.get("parent_checkpoint_id") != top["parent"].get("checkpoint_id"):
                raise ValueError(f"return event {event['event_id']} parent checkpoint mismatch")
            if data.get("child_task_id") != top["child"].get("task_id"):
                raise ValueError(f"return event {event['event_id']} child task mismatch")
            stack.pop()
            active = dict(top["parent"])
    return {
        "active": active,
        "return_stack": stack,
        "deferred_ideas": [
            record for record in turn_records.values()
            if record.get("classification") == "DEFERRED_IDEA"
        ],
        "turns": turn_records,
        "open_branch_count": len(stack),
    }


def _append_unlocked(path: Path, event: dict[str, Any]) -> dict[str, Any]:
    events = read_events(path)
    for old in events:
        if old["event_id"] == event["event_id"]:
            if _same_event(old, event):
                return {"status": "ALREADY_RECORDED", "event_id": event["event_id"], "writes_performed": False}
            return {"status": "CONFLICT", "event_id": event["event_id"], "writes_performed": False}
    # Validate the projected stack before committing the proposed event.
    project_state(events + [event])
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(_canonical(event) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    return {"status": "RECORDED", "event_id": event["event_id"], "writes_performed": True}


def _run_exclusive(path: Path, operation, *args) -> dict[str, Any]:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_name(path.name + ".lock")
    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        return {"status": "LOCKED", "writes_performed": False,
                "error": f"Journal lock exists: {lock_path}; verify no writer is active before manual recovery."}
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(json.dumps({"pid": os.getpid(), "started_at": now()}))
            stream.flush()
            os.fsync(stream.fileno())
        return operation(path, *args)
    finally:
        lock_path.unlink(missing_ok=True)


def process_turn(
    event_log: Path,
    *,
    turn_id: str,
    text: str,
    active_task_id: str,
    active_checkpoint_id: str,
    explicit_classification: str | None = None,
    child_task_id: str | None = None,
    child_checkpoint_id: str | None = None,
    return_condition: str = "branch result reviewed and parent acceptance criteria reconciled",
) -> dict[str, Any]:
    """Classify and persist a turn; branch switches require explicit child identity."""
    required = (turn_id, text, active_task_id, active_checkpoint_id)
    if any(not isinstance(v, str) or not v.strip() for v in required):
        return {"status": "REJECTED", "writes_performed": False, "errors": ["turn_id, text, active task and checkpoint are required"]}
    suggestion = classify_turn(text)
    classification = explicit_classification or suggestion["classification"]
    if classification not in CLASSIFICATIONS:
        return {"status": "REJECTED", "writes_performed": False, "errors": ["invalid classification"]}
    if explicit_classification:
        suggestion = {**suggestion, "classification": classification, "confidence": "CALLER_CONFIRMED",
                      "needs_confirmation": False}
    data: dict[str, Any] = {
        "turn_id": turn_id, "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "classification": classification, "classifier": suggestion,
        "active_task_id": active_task_id, "active_checkpoint_id": active_checkpoint_id,
        "recorded_at": now(),
    }
    event = {
        "event_id": _event_id(turn_id, "attention_turn_classified", data),
        "project_id": "AGENT_MEMORY_SYSTEM", "type": "attention_turn_classified",
        "event_time": "unknown", "source_time": "unknown", "recorded_at": data["recorded_at"],
        "status": "observed" if classification != "AMBIGUOUS" else "unknown",
        "summary": f"Dialogue attention classification: {classification} for turn {turn_id}.",
        "related_event_ids": [], "attention": data,
    }
    path = Path(event_log)
    if classification in SWITCHING:
        if not child_task_id or not child_checkpoint_id:
            return {"status": "NEEDS_CHILD_CONTEXT", "classification": classification,
                    "suggestion": suggestion, "writes_performed": False,
                    "required": ["child_task_id", "child_checkpoint_id"]}
        branch_id = "BR-" + hashlib.sha256(f"{turn_id}\0{active_task_id}\0{child_task_id}".encode()).hexdigest()[:20].upper()
        branch_data = {
            "turn_id": turn_id, "branch_id": branch_id, "classification": classification,
            "parent": {"task_id": active_task_id, "checkpoint_id": active_checkpoint_id},
            "child": {"task_id": child_task_id, "checkpoint_id": child_checkpoint_id},
            "return_condition": return_condition,
        }
        branch_event = {
            "event_id": _event_id(turn_id, "attention_branch_opened", branch_data),
            "project_id": "AGENT_MEMORY_SYSTEM", "type": "attention_branch_opened",
            "event_time": "unknown", "source_time": "unknown", "recorded_at": now(),
            "status": "observed", "summary": f"Opened {classification} branch {branch_id}.",
            "related_event_ids": [event["event_id"]], "attention": branch_data,
        }
        def operation(target: Path):
            first = _append_unlocked(target, event)
            if first["status"] not in {"RECORDED", "ALREADY_RECORDED"}:
                return first
            second = _append_unlocked(target, branch_event)
            if second["status"] not in {"RECORDED", "ALREADY_RECORDED"}:
                return {"status": "PARTIAL", "writes_performed": first.get("writes_performed", False),
                        "classification_event_id": event["event_id"], "branch_event": second}
            return {"status": "BRANCH_OPENED", "classification": classification,
                    "branch_id": branch_id, "active_task_id": child_task_id,
                    "classification_event_id": event["event_id"], "branch_event_id": branch_event["event_id"],
                    "writes_performed": first.get("writes_performed", False) or second.get("writes_performed", False),
                    "suggestion": suggestion}
        return _run_exclusive(path, operation)

    if classification == "DEFERRED_IDEA":
        event["type"] = "attention_idea_deferred"
        event["event_id"] = _event_id(turn_id, event["type"], data)
        event["attention"]["return_condition"] = "user explicitly selects this idea for execution"
    def operation(target: Path):
        result = _append_unlocked(target, event)
        if result["status"] not in {"RECORDED", "ALREADY_RECORDED"}:
            return result
        state = project_state(read_events(target))
        return {"status": "TURN_RECORDED", "classification": classification,
                "suggestion": suggestion, "active": state["active"],
                "open_branch_count": state["open_branch_count"],
                "writes_performed": result.get("writes_performed", False),
                "event_id": result["event_id"]}
    result = _run_exclusive(path, operation)
    if classification == "RETURN_TO_PARENT" and result.get("status") in {"TURN_RECORDED", "ALREADY_RECORDED"}:
        state = inspect(path)
        if not state["return_stack"]:
            return {"status": "NO_PARENT", "classification": classification,
                    "classification_event_id": result.get("event_id"), "writes_performed": result.get("writes_performed", False)}
        parent_id = state["return_stack"][-1]["parent"].get("task_id")
        returned = return_to_parent(path, turn_id=turn_id + "-RETURN", parent_task_id=parent_id)
        return {"status": returned.get("status"), "classification": classification,
                "classification_event_id": result.get("event_id"), "return": returned,
                "writes_performed": result.get("writes_performed", False) or returned.get("writes_performed", False)}
    return result


def return_to_parent(
    event_log: Path,
    *,
    turn_id: str,
    parent_task_id: str,
    authorization: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Direct calls cannot commit a return; use the unified memory cycle."""
    if isinstance(authorization, dict):
        if authorization.get("reconciliation_status") != "CONSISTENT":
            return {"status": "BLOCKED_RECONCILIATION", "writes_performed": False}
        if authorization.get("child_result_status") != "READY":
            return {"status": "BLOCKED_CHILD_RESULT", "writes_performed": False}
    return {
        "status": "BLOCKED_GUARD_REQUIRED",
        "reason": "Use tools/agent_memory_cycle.py for guarded parent return.",
        "writes_performed": False,
    }

def _return_to_parent_unchecked(
    event_log: Path, *, turn_id: str, parent_task_id: str,
    precommit_guard: Callable[[Path, dict[str, Any]], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Internal journal primitive; callers must already have passed the guard."""
    path = Path(event_log)
    def operation(target: Path):
        events = read_events(target)
        state = project_state(events)
        prior_returns = [
            event for event in events
            if event.get("type") == "attention_returned"
            and isinstance(event.get("attention"), dict)
            and event["attention"].get("turn_id") == turn_id
        ]
        if prior_returns:
            prior = prior_returns[-1]
            prior_data = prior.get("attention", {})
            if prior_data.get("parent_task_id") != parent_task_id:
                return {"status": "TURN_ID_CONFLICT", "writes_performed": False,
                        "existing_parent_task_id": prior_data.get("parent_task_id")}
            return {"status": "ALREADY_RETURNED", "active": state["active"],
                    "branch_id": prior_data.get("branch_id"), "event_id": prior["event_id"],
                    "writes_performed": False}
        if not state["return_stack"]:
            return {"status": "NO_PARENT", "writes_performed": False}
        top = state["return_stack"][-1]
        if top["parent"].get("task_id") != parent_task_id:
            return {"status": "PARENT_MISMATCH", "writes_performed": False,
                    "expected_parent_task_id": top["parent"].get("task_id")}
        if precommit_guard is not None:
            try:
                guarded = precommit_guard(target, top)
            except Exception as exc:
                return {"status": "BLOCKED_PRECOMMIT_GUARD", "reason": str(exc), "writes_performed": False}
            if not isinstance(guarded, dict) or guarded.get("status") != "READY":
                if isinstance(guarded, dict):
                    return {**guarded, "writes_performed": False}
                return {"status": "BLOCKED_PRECOMMIT_GUARD", "writes_performed": False}
        data = {"turn_id": turn_id, "branch_id": top["branch_id"],
                "parent_task_id": parent_task_id, "parent_checkpoint_id": top["parent"].get("checkpoint_id"),
                "child_task_id": top["child"].get("task_id"), "returned_at": now()}
        event = {
            "event_id": _event_id(turn_id, "attention_returned", data),
            "project_id": "AGENT_MEMORY_SYSTEM", "type": "attention_returned",
            "event_time": "unknown", "source_time": "unknown", "recorded_at": data["returned_at"],
            "status": "observed", "summary": f"Returned from branch {top['branch_id']} to parent task {parent_task_id}.",
            "related_event_ids": [], "attention": data,
        }
        result = _append_unlocked(target, event)
        if result["status"] not in {"RECORDED", "ALREADY_RECORDED"}:
            return result
        restored = project_state(read_events(target))["active"]
        return {"status": "RETURNED", "active": restored, "branch_id": top["branch_id"],
                "event_id": result["event_id"], "writes_performed": result.get("writes_performed", False)}
    return _run_exclusive(path, operation)


def inspect(event_log: Path) -> dict[str, Any]:
    events = read_events(Path(event_log))
    state = project_state(events)
    return {"status": "OK", "events_seen": len(events), **state}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("event_log", type=Path, nargs="?", default=DEFAULT_LOG)
    sub = parser.add_subparsers(dest="command", required=True)
    classify = sub.add_parser("classify")
    classify.add_argument("--turn-id", required=True)
    classify.add_argument("--text", required=True)
    classify.add_argument("--task-id", required=True)
    classify.add_argument("--checkpoint-id", required=True)
    classify.add_argument("--classification", choices=sorted(CLASSIFICATIONS))
    classify.add_argument("--child-task-id")
    classify.add_argument("--child-checkpoint-id")
    classify.add_argument("--return-condition", default="branch result reviewed and parent acceptance criteria reconciled")
    sub.add_parser("inspect")
    ret = sub.add_parser("return")
    ret.add_argument("--turn-id", required=True)
    ret.add_argument("--parent-task-id", required=True)
    args = parser.parse_args(argv)
    if args.command == "classify":
        result = process_turn(args.event_log, turn_id=args.turn_id, text=args.text,
                              active_task_id=args.task_id, active_checkpoint_id=args.checkpoint_id,
                              explicit_classification=args.classification, child_task_id=args.child_task_id,
                              child_checkpoint_id=args.child_checkpoint_id, return_condition=args.return_condition)
    elif args.command == "return":
        result = return_to_parent(args.event_log, turn_id=args.turn_id, parent_task_id=args.parent_task_id)
    else:
        result = inspect(args.event_log)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") in {"OK", "TURN_RECORDED", "BRANCH_OPENED", "RETURNED", "ALREADY_RETURNED", "ALREADY_RECORDED"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
