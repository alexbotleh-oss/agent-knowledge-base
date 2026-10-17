#!/usr/bin/env python3
"""Execute one explicitly reviewed action informed by retrieved experience.

This is a bounded local runner, not an autonomous planner. It first retrieves
experience through minimal_agent_loop, requires the selected event to be in
that retrieval result and an explicit operator review, executes argv without a
shell only when requested, independently evaluates artifact-based acceptance
checks, then captures a provenance-bound outcome candidate. It never promotes
semantic memory.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from minimal_agent_loop import run_minimal_agent_loop
from experience_outcome_capture import append_observed_failure_event, capture_verified_experience_candidate

MAX_TIMEOUT_SECONDS = 300
MAX_OUTPUT_BYTES = 1_000_000
TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)
STOP_WORDS = {"and", "the", "for", "with", "from", "that", "this", "into", "when", "after", "before", "then", "prior", "experience", "identified", "run", "verify", "verified", "result", "task", "action", "fix", "fixed"}
ARTIFACT_CHECK_TYPES = {"file_contains", "file_sha256", "json_field_equals"}
ALLOWED_CHECK_TYPES = ARTIFACT_CHECK_TYPES | {"command_exit_code"}


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _tokens(value: str) -> set[str]:
    return {
        token.casefold()
        for token in TOKEN_RE.findall(value)
        if len(token) >= 3 and token.casefold() not in STOP_WORDS
    }


def _inside(root: Path, value: Path, label: str) -> tuple[Path | None, str | None]:
    candidate = value if value.is_absolute() else root / value
    if candidate.is_symlink():
        return None, f"{label.upper()}_SYMLINK"
    resolved = candidate.resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        return None, f"{label.upper()}_OUTSIDE_ROOT"
    return resolved, None


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    result = []
    seen = set()
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            raise ValueError(f"blank line in event log at {line_no}")
        item = json.loads(line)
        if not isinstance(item, dict) or not isinstance(item.get("event_id"), str):
            raise ValueError(f"invalid event object at line {line_no}")
        if item["event_id"] in seen:
            raise ValueError(f"duplicate event_id at line {line_no}")
        seen.add(item["event_id"])
        result.append(item)
    return result


def _retrieved_candidate(loop_result: dict[str, Any], event_id: str) -> dict[str, Any] | None:
    for section in ("retrieval", "lesson_retrieval"):
        block = loop_result.get(section)
        if not isinstance(block, dict):
            continue
        candidates = block.get("candidates", [])
        if isinstance(candidates, list):
            for item in candidates:
                if isinstance(item, dict) and item.get("event_id") == event_id:
                    return item
                if isinstance(item, dict) and item.get("lesson_id") == event_id:
                    return item
    return None


def _field_value(document: Any, dotted_path: str) -> Any:
    value = document
    for part in dotted_path.split("."):
        if isinstance(value, dict) and part in value:
            value = value[part]
        elif isinstance(value, list) and part.isdigit() and int(part) < len(value):
            value = value[int(part)]
        else:
            raise KeyError(dotted_path)
    return value


def _evaluate_checks(
    root: Path,
    criteria: list[dict[str, Any]],
    return_code: int,
) -> tuple[list[dict[str, Any]], bool]:
    results = []
    for index, criterion in enumerate(criteria):
        kind = criterion.get("type")
        result: dict[str, Any] = {"index": index, "type": kind, "passed": False}
        try:
            if kind == "command_exit_code":
                expected = criterion.get("expected", 0)
                result.update(expected=expected, observed=return_code, passed=return_code == expected)
            elif kind == "file_contains":
                path, error = _inside(root, Path(str(criterion.get("path", ""))), "criterion_file")
                if error:
                    result["error"] = error
                else:
                    data = path.read_bytes()
                    marker = criterion.get("expected")
                    result.update(
                        path=path.relative_to(root).as_posix(),
                        file_sha256=_sha(data),
                        expected=marker,
                        passed=isinstance(marker, str) and marker in data.decode("utf-8"),
                    )
            elif kind == "file_sha256":
                path, error = _inside(root, Path(str(criterion.get("path", ""))), "criterion_file")
                if error:
                    result["error"] = error
                else:
                    digest = _sha(path.read_bytes())
                    expected = criterion.get("expected_sha256")
                    result.update(
                        path=path.relative_to(root).as_posix(),
                        expected_sha256=expected,
                        observed_sha256=digest,
                        passed=isinstance(expected, str) and digest == expected,
                    )
            elif kind == "json_field_equals":
                path, error = _inside(root, Path(str(criterion.get("path", ""))), "criterion_file")
                if error:
                    result["error"] = error
                else:
                    data = path.read_bytes()
                    document = json.loads(data.decode("utf-8"))
                    field = criterion.get("field")
                    observed = _field_value(document, field) if isinstance(field, str) and field else None
                    expected = criterion.get("expected")
                    result.update(
                        path=path.relative_to(root).as_posix(),
                        file_sha256=_sha(data),
                        field=field,
                        expected=expected,
                        observed=observed,
                        passed=observed == expected,
                    )
            else:
                result["error"] = "UNSUPPORTED_ACCEPTANCE_CHECK"
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            result["error"] = f"{type(exc).__name__}: {exc}"
        results.append(result)
    has_artifact_check = any(item.get("type") in ARTIFACT_CHECK_TYPES for item in criteria)
    passed = bool(criteria) and has_artifact_check and all(item.get("passed") is True for item in results)
    return results, passed


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_path, path)
        try:
            dir_fd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        except OSError:
            pass
    finally:
        try:
            temp_path.unlink()
        except FileNotFoundError:
            pass


def run_reviewed_action(
    *,
    workspace_root: Path,
    task_state: Path,
    handoff: Path,
    event_log: Path,
    experience_logs: list[Path],
    request: str,
    project_id: str,
    task_id: str,
    reviewed_experience_event_id: str,
    action_rationale: str,
    action_argv: list[str],
    action_cwd: Path,
    acceptance_criterion: str,
    acceptance_checks: list[dict[str, Any]],
    evidence_report: Path,
    observed_outcome: str,
    execute: bool = False,
    timeout_seconds: int = 60,
    lesson_logs: list[Path] | None = None,
    prior_failed_attempts: int = 0,
    risk_level: str = "normal",
) -> dict[str, Any]:
    """Run one reviewed action and persist a candidate only after independent checks pass."""
    root = Path(workspace_root).resolve()
    required_strings = {
        "request": request,
        "project_id": project_id,
        "task_id": task_id,
        "reviewed_experience_event_id": reviewed_experience_event_id,
        "action_rationale": action_rationale,
        "acceptance_criterion": acceptance_criterion,
        "observed_outcome": observed_outcome,
    }
    missing = [name for name, value in required_strings.items() if not isinstance(value, str) or not value.strip()]
    if missing:
        return {"status": "BLOCKED_REQUIRED_FIELDS_MISSING", "missing_fields": missing, "writes_performed": False}
    if not isinstance(action_argv, list) or not action_argv or any(not isinstance(arg, str) or not arg or "\x00" in arg for arg in action_argv):
        return {"status": "BLOCKED_INVALID_ACTION_ARGV", "writes_performed": False}
    if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, int) or not 1 <= timeout_seconds <= MAX_TIMEOUT_SECONDS:
        return {"status": "BLOCKED_INVALID_TIMEOUT", "writes_performed": False}
    if not isinstance(acceptance_checks, list) or any(not isinstance(check, dict) or check.get("type") not in ALLOWED_CHECK_TYPES for check in acceptance_checks):
        return {"status": "BLOCKED_INVALID_ACCEPTANCE_CHECKS", "writes_performed": False}
    if not any(check.get("type") in ARTIFACT_CHECK_TYPES for check in acceptance_checks):
        return {"status": "BLOCKED_NO_INDEPENDENT_ARTIFACT_CHECK", "writes_performed": False}

    resolved = {}
    for name, value in (
        ("task_state", task_state),
        ("handoff", handoff),
        ("event_log", event_log),
        ("action_cwd", action_cwd),
        ("evidence_report", evidence_report),
    ):
        path, error = _inside(root, Path(value), name)
        if error:
            return {"status": "BLOCKED_PATH", "path": name, "reason": error, "writes_performed": False}
        resolved[name] = path
    resolved_experience_logs = []
    for log in experience_logs:
        path, error = _inside(root, Path(log), "experience_log")
        if error:
            return {"status": "BLOCKED_PATH", "path": str(log), "reason": error, "writes_performed": False}
        resolved_experience_logs.append(path)
    resolved_lesson_logs = []
    for log in (lesson_logs or []):
        path, error = _inside(root, Path(log), "lesson_log")
        if error:
            return {"status": "BLOCKED_PATH", "path": str(log), "reason": error, "writes_performed": False}
        resolved_lesson_logs.append(path)
    if not resolved["action_cwd"].is_dir():
        return {"status": "BLOCKED_ACTION_CWD_NOT_DIRECTORY", "writes_performed": False}
    if not resolved["task_state"].is_file() or not resolved["handoff"].is_file():
        return {"status": "BLOCKED_TASK_CHECKPOINT_MISSING", "writes_performed": False}
    if not resolved["event_log"].is_file():
        return {"status": "BLOCKED_EVENT_LOG_MISSING", "writes_performed": False}

    try:
        loop_result = run_minimal_agent_loop(
            resolved["task_state"],
            resolved["handoff"],
            resolved["event_log"],
            request,
            experience_logs=resolved_experience_logs or [resolved["event_log"]],
            current_project_id=project_id,
            evidence_root=root,
            lesson_logs=resolved_lesson_logs,
            prior_failed_attempts=prior_failed_attempts,
            risk_level=risk_level,
        )
    except Exception as exc:
        return {"status": "BLOCKED_EXPERIENCE_RETRIEVAL_ERROR", "reason": f"{type(exc).__name__}: {exc}", "writes_performed": False}
    if loop_result.get("status") != "READY_FOR_REVIEW":
        return {
            "status": "BLOCKED_EXPERIENCE_RETRIEVAL",
            "loop_status": loop_result.get("status"),
            "writes_performed": False,
        }
    trust_gate = loop_result.get("trust_gate")
    trust_gate_status = trust_gate.get("status") if isinstance(trust_gate, dict) else None
    if trust_gate_status != "AUTHORIZED_FOR_PLANNING":
        return {
            "status": "BLOCKED_CONTEXT_TRUST_GATE",
            "trust_gate": trust_gate,
            "reason": "The restored task context must pass its existing trust gate before this explicitly approved action can be considered.",
            "writes_performed": False,
            "execution_performed": False,
        }
    route = loop_result.get("adaptive_task_flow")
    route_mode = route.get("mode") if isinstance(route, dict) else None
    if route_mode not in {"APPLY_RELEVANT_EXPERIENCE", "REVIEW_EXPERIENCE_CANDIDATES"}:
        return {
            "status": "BLOCKED_ROUTE_REQUIRES_DEEPER_ANALYSIS",
            "route": route,
            "writes_performed": False,
            "execution_performed": False,
        }
    candidate = _retrieved_candidate(loop_result, reviewed_experience_event_id)
    if candidate is None:
        return {
            "status": "BLOCKED_EXPERIENCE_NOT_RETRIEVED",
            "event_id": reviewed_experience_event_id,
            "retrieval_status": loop_result.get("retrieval", {}).get("status"),
            "writes_performed": False,
        }
    try:
        events = _read_jsonl(resolved["event_log"])
    except (OSError, UnicodeDecodeError, ValueError, json.JSONDecodeError) as exc:
        return {"status": "BLOCKED_EVENT_LOG_INVALID", "reason": str(exc), "writes_performed": False}
    source_events = list(events)
    source_logs = resolved_experience_logs or [resolved["event_log"]]
    try:
        for source_log in source_logs:
            if source_log == resolved["event_log"]:
                continue
            source_events.extend(_read_jsonl(source_log))
    except (OSError, UnicodeDecodeError, ValueError, json.JSONDecodeError) as exc:
        return {"status": "BLOCKED_EXPERIENCE_LOG_INVALID", "reason": str(exc), "writes_performed": False}
    source_event = next((item for item in source_events if item.get("event_id") == reviewed_experience_event_id), None)
    if source_event is None or source_event.get("project_id") != project_id:
        return {"status": "BLOCKED_EXPERIENCE_SCOPE_MISMATCH", "writes_performed": False}
    source_text_parts = []
    for field in ("summary", "facts", "hypotheses", "action_taken", "outcome", "tags", "tool_tags", "language_tags"):
        value = source_event.get(field)
        if isinstance(value, str):
            source_text_parts.append(value)
        elif isinstance(value, list):
            source_text_parts.extend(item for item in value if isinstance(item, str))
    source_tokens = _tokens(" ".join(source_text_parts))
    rationale_tokens = _tokens(action_rationale)
    overlap_tokens = sorted(source_tokens & rationale_tokens)
    if len(overlap_tokens) < 2:
        return {
            "status": "BLOCKED_EXPERIENCE_NOT_LINKED_TO_ACTION",
            "reason": "The action rationale must share at least two meaningful terms with the retrieved experience; this is a lexical link check, not semantic proof.",
            "overlap_tokens": overlap_tokens,
            "writes_performed": False,
        }

    protected_paths = {
        resolved["task_state"], resolved["handoff"], resolved["event_log"], *source_logs
    }
    if resolved["evidence_report"] in protected_paths:
        return {"status": "BLOCKED_EVIDENCE_REPORT_OVERWRITES_PROTECTED_SOURCE", "writes_performed": False}
    protected_hashes = {}
    try:
        for protected_path in protected_paths:
            if protected_path.is_file():
                protected_hashes[str(protected_path)] = _sha(protected_path.read_bytes())
    except OSError as exc:
        return {"status": "BLOCKED_PROTECTED_SOURCE_UNREADABLE", "reason": str(exc), "writes_performed": False}
    if not execute:
        return {
            "status": "PLAN_READY_REQUIRES_EXPLICIT_EXECUTE",
            "retrieved_event_id": reviewed_experience_event_id,
            "route_mode": route_mode,
            "trust_gate_status": trust_gate_status,
            "action_rationale": action_rationale,
            "action_argv": action_argv,
            "acceptance_checks": acceptance_checks,
            "execution_performed": False,
            "writes_performed": False,
        }

    started = datetime.now().astimezone().isoformat()
    safe_env = {
        key: value for key, value in os.environ.items()
        if key in {"PATH", "SYSTEMROOT", "WINDIR", "HOME", "TMPDIR", "TEMP", "TMP", "LANG", "LC_ALL"}
    }
    try:
        completed = subprocess.run(
            action_argv,
            cwd=resolved["action_cwd"],
            env=safe_env,
            shell=False,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
        stdout = completed.stdout[:MAX_OUTPUT_BYTES]
        stderr = completed.stderr[:MAX_OUTPUT_BYTES]
        truncated = len(completed.stdout) > MAX_OUTPUT_BYTES or len(completed.stderr) > MAX_OUTPUT_BYTES
        return_code = completed.returncode
        action_status = "COMPLETED"
    except subprocess.TimeoutExpired as exc:
        stdout = (exc.stdout or b"")[:MAX_OUTPUT_BYTES]
        stderr = (exc.stderr or b"")[:MAX_OUTPUT_BYTES]
        truncated = True
        return_code = None
        action_status = "TIMED_OUT"
    except OSError as exc:
        stdout, stderr, truncated, return_code = b"", str(exc).encode("utf-8", errors="replace"), False, None
        action_status = "LAUNCH_FAILED"
    finished = datetime.now().astimezone().isoformat()
    protected_source_changes = []
    try:
        for protected_path in protected_paths:
            before = protected_hashes.get(str(protected_path))
            after = _sha(protected_path.read_bytes()) if protected_path.is_file() else None
            if before != after:
                protected_source_changes.append({
                    "path": str(protected_path.relative_to(root)),
                    "before_sha256": before,
                    "after_sha256": after,
                })
    except OSError as exc:
        protected_source_changes.append({"error": f"{type(exc).__name__}: {exc}"})
    checks, checks_passed = _evaluate_checks(root, acceptance_checks, return_code if return_code is not None else -999)
    verification_status = "PASS" if action_status == "COMPLETED" and checks_passed and not protected_source_changes else "FAIL"
    report = {
        "report_version": "1",
        "task_id": task_id,
        "project_id": project_id,
        "request": request,
        "context_trust_gate": {
            "status": trust_gate_status,
            "reason": trust_gate.get("reason") if isinstance(trust_gate, dict) else "UNKNOWN",
        },
        "task_route": {
            "mode": route_mode,
            "reason": route.get("reason") if isinstance(route, dict) else "UNKNOWN",
        },
        "retrieved_experience": {
            "event_id": reviewed_experience_event_id,
            "source_event_sha256": _sha(json.dumps(source_event, ensure_ascii=False, sort_keys=True).encode("utf-8")),
            "summary": candidate.get("summary", candidate.get("title", "")),
            "action_rationale_overlap_tokens": overlap_tokens,
        },
        "action": {
            "rationale": action_rationale,
            "argv": action_argv,
            "cwd": resolved["action_cwd"].relative_to(root).as_posix(),
            "started_at": started,
            "finished_at": finished,
            "status": action_status,
            "return_code": return_code,
            "stdout_sha256": _sha(stdout),
            "stderr_sha256": _sha(stderr),
            "stdout_excerpt": stdout.decode("utf-8", errors="replace"),
            "stderr_excerpt": stderr.decode("utf-8", errors="replace"),
            "output_truncated": truncated,
        },
        "acceptance": {
            "criterion": acceptance_criterion,
            "checks": checks,
            "status": verification_status,
            "independent_artifact_check_required": True,
            "protected_source_changes": protected_source_changes,
        },
        "VERIFICATION_STATUS": verification_status,
        "semantic_memory_promoted": False,
    }
    report_bytes = (json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + f"\nVERIFICATION_STATUS={verification_status}\n").encode("utf-8")
    try:
        _atomic_write(resolved["evidence_report"], report_bytes)
    except OSError as exc:
        return {
            "status": "BLOCKED_EVIDENCE_REPORT_WRITE_FAILED",
            "reason": f"{type(exc).__name__}: {exc}",
            "action_status": action_status,
            "return_code": return_code,
            "writes_performed": False,
        }
    if verification_status != "PASS":
        event_log_relative = resolved["event_log"].relative_to(root).as_posix()
        event_log_was_modified_by_action = any(
            item.get("path") == event_log_relative or "error" in item
            for item in protected_source_changes
        )
        failure_event = (
            {
                "status": "BLOCKED_EVENT_LOG_CHANGED_DURING_ACTION",
                "writes_performed": False,
            }
            if event_log_was_modified_by_action
            else append_observed_failure_event(
                resolved["event_log"],
                evidence_root=root,
                project_id=project_id,
                task_id=task_id,
                request_summary=request,
                action_taken=" ".join(action_argv),
                acceptance_criterion=acceptance_criterion,
                evidence_file=resolved["evidence_report"],
                observed_outcome=(
                    f"Action status {action_status}; return code {return_code}; "
                    f"acceptance verification {verification_status}"
                ),
                related_event_ids=[reviewed_experience_event_id],
            )
        )
        return {
            "status": "ACTION_OR_ACCEPTANCE_CHECK_FAILED",
            "action_status": action_status,
            "return_code": return_code,
            "verification_status": verification_status,
            "checks": checks,
            "protected_source_changes": protected_source_changes,
            "failure_event": failure_event,
            "evidence_report": resolved["evidence_report"].relative_to(root).as_posix(),
            "evidence_sha256": _sha(report_bytes),
            "execution_performed": True,
            "writes_performed": True,
            "semantic_memory_promoted": False,
        }

    capture = capture_verified_experience_candidate(
        resolved["event_log"],
        evidence_root=root,
        project_id=project_id,
        task_id=task_id,
        request_summary=request,
        action_taken=" ".join(action_argv),
        acceptance_criterion=acceptance_criterion,
        expected_evidence_marker="VERIFICATION_STATUS=PASS",
        evidence_file=resolved["evidence_report"],
        observed_outcome=observed_outcome,
        related_event_ids=[reviewed_experience_event_id],
    )
    status = "VERIFIED_ACTION_AND_CAPTURED" if capture.get("status") == "CAPTURED_CANDIDATE" else (
        "VERIFIED_ACTION_CAPTURE_ALREADY_PRESENT" if capture.get("status") == "ALREADY_CAPTURED" else "VERIFIED_ACTION_CAPTURE_BLOCKED"
    )
    return {
        "status": status,
        "retrieved_experience_event_id": reviewed_experience_event_id,
        "route_mode": route_mode,
        "trust_gate_status": trust_gate_status,
        "action_status": action_status,
        "return_code": return_code,
        "acceptance_checks": checks,
        "verification_status": verification_status,
        "evidence_report": resolved["evidence_report"].relative_to(root).as_posix(),
        "evidence_sha256": _sha(report_bytes),
        "capture": capture,
        "execution_performed": True,
        "writes_performed": True,
        "semantic_memory_promoted": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-root", required=True, type=Path)
    parser.add_argument("--task-state", required=True, type=Path)
    parser.add_argument("--handoff", required=True, type=Path)
    parser.add_argument("--event-log", required=True, type=Path)
    parser.add_argument("--experience-log", action="append", default=[], type=Path)
    parser.add_argument("--lesson-log", action="append", default=[], type=Path)
    parser.add_argument("--request", required=True)
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--reviewed-experience-event-id", required=True)
    parser.add_argument("--action-rationale", required=True)
    parser.add_argument("--action-spec", required=True, type=Path, help="JSON object with argv, cwd, acceptance_criterion, acceptance_checks, evidence_report, observed_outcome")
    parser.add_argument("--timeout-seconds", type=int, default=60)
    parser.add_argument("--prior-failed-attempts", type=int, default=0)
    parser.add_argument("--risk-level", choices=("low", "normal", "high", "critical"), default="normal")
    parser.add_argument("--execute", action="store_true", help="actually execute the command; without this flag only retrieval/plan validation occurs")
    args = parser.parse_args(argv)
    try:
        spec = json.loads(args.action_spec.read_text(encoding="utf-8"))
        if not isinstance(spec, dict):
            raise ValueError("action spec must be a JSON object")
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"status": "BLOCKED_INVALID_ACTION_SPEC", "reason": str(exc)}, ensure_ascii=False))
        return 2
    result = run_reviewed_action(
        workspace_root=args.workspace_root,
        task_state=args.task_state,
        handoff=args.handoff,
        event_log=args.event_log,
        experience_logs=args.experience_log,
        lesson_logs=args.lesson_log,
        request=args.request,
        project_id=args.project_id,
        task_id=args.task_id,
        reviewed_experience_event_id=args.reviewed_experience_event_id,
        action_rationale=args.action_rationale,
        action_argv=spec.get("argv"),
        action_cwd=Path(spec.get("cwd", ".")),
        acceptance_criterion=spec.get("acceptance_criterion", ""),
        acceptance_checks=spec.get("acceptance_checks"),
        evidence_report=Path(spec.get("evidence_report", "")),
        observed_outcome=spec.get("observed_outcome", ""),
        execute=args.execute,
        timeout_seconds=args.timeout_seconds,
        prior_failed_attempts=args.prior_failed_attempts,
        risk_level=args.risk_level,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") in {"PLAN_READY_REQUIRES_EXPLICIT_EXECUTE", "VERIFIED_ACTION_AND_CAPTURED", "VERIFIED_ACTION_CAPTURE_ALREADY_PRESENT"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
