#!/usr/bin/env python3
"""Record and reuse completed checks only when the exact check inputs still match.

The policy is conservative and read-only during evaluation. A prior PASS is a
recorded result, not independent proof or planning permission. Recording writes
an append-only event to the canonical AGENT_MEMORY_SYSTEM event log.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from trusted_receipt_verifier import make_check_receipt_verifier_from_env

DEFAULT_LOG = Path(__file__).resolve().parents[1] / "projects" / "AGENT_MEMORY_SYSTEM" / "events.jsonl"
RESULTS = {"PASS", "FAIL", "BLOCKED", "UNKNOWN"}
HASH_RE = re.compile(r"^[0-9a-f]{64}$")


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _normalize_check(check_spec: Any) -> dict[str, Any] | None:
    if not isinstance(check_spec, dict):
        return None
    kind = check_spec.get("type")
    targets = check_spec.get("target_ids", [])
    if not isinstance(kind, str) or not kind.strip() or not isinstance(targets, list):
        return None
    if any(not isinstance(target, str) or not target.strip() for target in targets):
        return None
    normalized = dict(check_spec)
    normalized["type"] = kind.strip()
    normalized["target_ids"] = sorted(set(targets))
    return normalized


def _check_key(check_spec: dict[str, Any]) -> str:
    return "CHECK-" + _sha({
        "type": check_spec["type"],
        "target_ids": check_spec["target_ids"],
    })[:24].upper()


def _normalize_source_hashes(source_hashes: Any) -> dict[str, str] | None:
    if not isinstance(source_hashes, dict) or not source_hashes:
        return None
    normalized = {}
    for key, value in source_hashes.items():
        if not isinstance(key, str) or not key.strip() or not isinstance(value, str) or not HASH_RE.fullmatch(value):
            return None
        normalized[key] = value
    return dict(sorted(normalized.items()))


def _normalize_candidate_fingerprints(candidates: Any) -> list[dict[str, Any]] | None:
    if not isinstance(candidates, list):
        return None
    result = []
    for item in candidates:
        if not isinstance(item, dict):
            return None
        ctype = item.get("candidate_type")
        cid = item.get("candidate_id")
        source_hash = item.get("source_sha256")
        source_path = item.get("source_path", "")
        line = item.get("line")
        if ctype not in {"event", "lesson"} or not isinstance(cid, str) or not cid.strip():
            return None
        if not isinstance(source_hash, str) or not HASH_RE.fullmatch(source_hash):
            return None
        if not isinstance(source_path, str):
            return None
        if line is not None and (not isinstance(line, int) or line < 1):
            return None
        result.append({
            "candidate_type": ctype, "candidate_id": cid,
            "source_sha256": source_hash, "source_path": source_path, "line": line,
        })
    result.sort(key=lambda x: (x["candidate_type"], x["candidate_id"], x["source_path"], x["line"] or 0))
    return result


def make_fingerprint(
    check_spec: Any, source_hashes: Any, candidate_fingerprints: Any
) -> dict[str, Any]:
    check = _normalize_check(check_spec)
    sources = _normalize_source_hashes(source_hashes)
    candidates = _normalize_candidate_fingerprints(candidate_fingerprints)
    if check is None or sources is None or candidates is None:
        return {"status": "INSUFFICIENT_INPUT_FINGERPRINT", "writes_performed": False}
    payload = {"check_spec": check, "source_hashes": sources, "candidate_fingerprints": candidates}
    return {
        "status": "FINGERPRINT_READY",
        "check_key": _check_key(check),
        "input_fingerprint": _sha(payload),
        "check_spec": check,
        "source_hashes": sources,
        "candidate_fingerprints": candidates,
        "writes_performed": False,
    }


def _load_events(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    events = []
    seen = set()
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"corrupt canonical event log at line {number}: {exc}") from exc
        if not isinstance(event, dict) or not isinstance(event.get("event_id"), str):
            raise ValueError(f"invalid canonical event at line {number}: event_id required")
        if event["event_id"] in seen:
            raise ValueError(f"duplicate event_id {event['event_id']} at line {number}")
        seen.add(event["event_id"])
        events.append(event)
    return events


def evaluate_check_reuse(
    event_log: Path,
    check_spec: Any,
    source_hashes: Any,
    candidate_fingerprints: Any,
    *,
    receipt_verifier=None,
) -> dict[str, Any]:
    """Decide whether an exact prior recorded PASS can be reused without rerunning."""
    fingerprint = make_fingerprint(check_spec, source_hashes, candidate_fingerprints)
    if fingerprint["status"] != "FINGERPRINT_READY":
        return {**fingerprint, "status": "INSUFFICIENT_INPUT_FINGERPRINT", "action": "RUN_CHECK"}
    try:
        events = _load_events(Path(event_log))
    except (OSError, ValueError) as exc:
        return {
            **fingerprint, "status": "BLOCKED_JOURNAL_INVALID", "action": "STOP_AND_RECONCILE",
            "error": str(exc), "writes_performed": False,
        }
    prior = []
    for event in events:
        if event.get("type") != "verification_check_completed":
            continue
        record = event.get("check_result")
        if isinstance(record, dict) and record.get("check_key") == fingerprint["check_key"]:
            prior.append(event)
    exact = [
        event for event in prior
        if isinstance(event.get("check_result"), dict)
        and event["check_result"].get("input_fingerprint") == fingerprint["input_fingerprint"]
    ]
    exact_results = {
        event["check_result"].get("result_status")
        for event in exact if isinstance(event.get("check_result"), dict)
    }
    if len(exact_results) > 1:
        return {
            **fingerprint, "status": "CHECK_RESULT_CONFLICT", "action": "STOP_AND_RECONCILE",
            "prior_event_ids": [event["event_id"] for event in exact],
            "writes_performed": False,
        }
    if exact:
        event = exact[-1]
        record = event["check_result"]
        evidence_refs = record.get("evidence_refs")
        if (
            record.get("result_status") == "PASS"
            and isinstance(evidence_refs, list)
            and evidence_refs
            and all(isinstance(ref, str) and ref.strip() for ref in evidence_refs)
        ):
            expected_claim = {
                "check_key": fingerprint["check_key"],
                "input_fingerprint": fingerprint["input_fingerprint"],
                "result_status": "PASS",
                "evidence_refs": evidence_refs,
                "source_hashes": fingerprint["source_hashes"],
                "candidate_fingerprints": fingerprint["candidate_fingerprints"],
            }
            verifier = receipt_verifier if receipt_verifier is not None else make_check_receipt_verifier_from_env()
            receipt = record.get("signed_receipt")
            if isinstance(receipt, dict) and verifier is not None:
                verification = verifier(receipt, expected_claim)
                if isinstance(verification, dict) and verification.get("verified") is True:
                    return {
                        **fingerprint, "status": "REUSE_VERIFIED_PASS", "action": "DO_NOT_REPEAT_CHECK",
                        "prior_event_id": event["event_id"], "result_status": "PASS",
                        "evidence_refs": evidence_refs, "recorded_by": record.get("recorded_by", "UNKNOWN"),
                        "receipt_id": verification.get("receipt_id"),
                        "trust_boundary": "Ed25519 receipt verified against externally pinned trusted keyring and exact input claim",
                        "writes_performed": False,
                    }
                verification_status = verification.get("status", "RECEIPT_VERIFICATION_FAILED") if isinstance(verification, dict) else "RECEIPT_VERIFICATION_FAILED"
            else:
                verification_status = "TRUST_ROOT_UNCONFIGURED_OR_RECEIPT_MISSING"
            return {
                **fingerprint, "status": "REUSE_RECORDED_PASS_UNTRUSTED", "action": "REVIEW_PRIOR_RESULT",
                "prior_event_id": event["event_id"], "result_status": "PASS",
                "evidence_refs": evidence_refs, "recorded_by": record.get("recorded_by", "UNKNOWN"),
                "receipt_verification_status": verification_status,
                "trust_boundary": "Unsigned or unverified result is a review hint only; it cannot suppress the check",
                "writes_performed": False,
            }
        return {
            **fingerprint, "status": "RECHECK_PRIOR_RESULT_NOT_REUSABLE", "action": "RUN_CHECK",
            "prior_event_id": event["event_id"], "result_status": record.get("result_status", "UNKNOWN"),
            "writes_performed": False,
        }
    if prior:
        return {
            **fingerprint, "status": "RECHECK_INPUTS_CHANGED", "action": "RUN_CHECK",
            "prior_event_ids": [event["event_id"] for event in prior],
            "prior_fingerprints": sorted({
                event["check_result"].get("input_fingerprint", "UNKNOWN")
                for event in prior if isinstance(event.get("check_result"), dict)
            }),
            "writes_performed": False,
        }
    return {**fingerprint, "status": "RUN_CHECK", "action": "RUN_CHECK", "writes_performed": False}


def _event_id(check_key: str, input_fingerprint: str, result_status: str) -> str:
    return "EVT-AGMS-CHECK-" + hashlib.sha256(
        "\0".join((check_key, input_fingerprint, result_status)).encode("utf-8")
    ).hexdigest()[:20].upper()


def record_check_result(
    event_log: Path,
    check_spec: Any,
    source_hashes: Any,
    candidate_fingerprints: Any,
    *,
    result_status: str,
    evidence_refs: list[str],
    summary: str,
    recorded_by: str,
    signed_receipt: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Append a source-bound check result. PASS requires evidence references."""
    fingerprint = make_fingerprint(check_spec, source_hashes, candidate_fingerprints)
    if fingerprint["status"] != "FINGERPRINT_READY":
        return {"status": "REJECTED", "reason": "INSUFFICIENT_INPUT_FINGERPRINT", "writes_performed": False}
    if result_status not in RESULTS:
        return {"status": "REJECTED", "reason": "INVALID_RESULT_STATUS", "writes_performed": False}
    if not isinstance(evidence_refs, list) or any(not isinstance(ref, str) or not ref.strip() for ref in evidence_refs):
        return {"status": "REJECTED", "reason": "INVALID_EVIDENCE_REFS", "writes_performed": False}
    if result_status == "PASS" and not evidence_refs:
        return {"status": "REJECTED", "reason": "PASS_REQUIRES_EVIDENCE_REFS", "writes_performed": False}
    if not isinstance(summary, str) or not summary.strip() or not isinstance(recorded_by, str) or not recorded_by.strip():
        return {"status": "REJECTED", "reason": "SUMMARY_AND_RECORDED_BY_REQUIRED", "writes_performed": False}
    if signed_receipt is not None and not isinstance(signed_receipt, dict):
        return {"status": "REJECTED", "reason": "INVALID_SIGNED_RECEIPT", "writes_performed": False}
    path = Path(event_log)
    record = {
        "check_key": fingerprint["check_key"],
        "input_fingerprint": fingerprint["input_fingerprint"],
        "check_spec": fingerprint["check_spec"],
        "source_hashes": fingerprint["source_hashes"],
        "candidate_fingerprints": fingerprint["candidate_fingerprints"],
        "result_status": result_status,
        "evidence_refs": evidence_refs,
        "recorded_by": recorded_by,
        "summary": summary.strip(),
    }
    if signed_receipt is not None:
        record["signed_receipt"] = signed_receipt
    event = {
        "event_id": _event_id(record["check_key"], record["input_fingerprint"], result_status),
        "project_id": "AGENT_MEMORY_SYSTEM",
        "event_time": "unknown", "source_time": "unknown", "recorded_at": _now(),
        "type": "verification_check_completed", "status": "observed",
        "summary": record["summary"], "facts": [], "hypotheses": [],
        "action_taken": "Recorded a source-bound check result for future no-repeat evaluation.",
        "outcome": result_status, "evidence": [{"kind": "reference", "ref": ref} for ref in evidence_refs],
        "related_event_ids": [], "relations": [],
        "check_result": record,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_name(path.name + ".lock")
    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        return {"status": "LOCKED", "writes_performed": False, "error": f"Journal lock exists: {lock_path}"}
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as lock_stream:
            lock_stream.write(json.dumps({"pid": os.getpid(), "started_at": _now()}))
            lock_stream.flush()
            os.fsync(lock_stream.fileno())
        try:
            events = _load_events(path)
        except (OSError, ValueError) as exc:
            return {"status": "BLOCKED_JOURNAL_INVALID", "writes_performed": False, "error": str(exc)}
        for prior in events:
            if prior.get("event_id") != event["event_id"]:
                continue
            prior_compare = {k: v for k, v in prior.items() if k != "recorded_at"}
            event_compare = {k: v for k, v in event.items() if k != "recorded_at"}
            if _canonical(prior_compare) == _canonical(event_compare):
                return {"status": "ALREADY_RECORDED", "event_id": event["event_id"], "writes_performed": False}
            return {"status": "CONFLICT", "event_id": event["event_id"], "writes_performed": False}
        with path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(_canonical(event) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        return {"status": "RECORDED", "event_id": event["event_id"], "writes_performed": True,
                "check_key": record["check_key"], "input_fingerprint": record["input_fingerprint"]}
    finally:
        lock_path.unlink(missing_ok=True)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("event_log", type=Path, nargs="?", default=DEFAULT_LOG)
    sub = parser.add_subparsers(dest="command", required=True)
    evaluate = sub.add_parser("evaluate")
    evaluate.add_argument("--check-spec", required=True, type=Path)
    evaluate.add_argument("--source-hashes", required=True, type=Path)
    evaluate.add_argument("--candidate-fingerprints", required=True, type=Path)
    record = sub.add_parser("record")
    record.add_argument("--check-spec", required=True, type=Path)
    record.add_argument("--source-hashes", required=True, type=Path)
    record.add_argument("--candidate-fingerprints", required=True, type=Path)
    record.add_argument("--result-status", required=True, choices=sorted(RESULTS))
    record.add_argument("--evidence-ref", action="append", default=[])
    record.add_argument("--summary", required=True)
    record.add_argument("--recorded-by", required=True)
    record.add_argument("--signed-receipt", type=Path)
    args = parser.parse_args(argv)
    try:
        check_spec = json.loads(args.check_spec.read_text(encoding="utf-8"))
        source_hashes = json.loads(args.source_hashes.read_text(encoding="utf-8"))
        candidates = json.loads(args.candidate_fingerprints.read_text(encoding="utf-8"))
        signed_receipt = json.loads(args.signed_receipt.read_text(encoding="utf-8")) if getattr(args, "signed_receipt", None) else None
    except Exception as exc:
        print(json.dumps({"status": "BLOCKED", "error": f"INVALID_INPUT_FILE: {exc}"}, ensure_ascii=False))
        return 2
    if args.command == "evaluate":
        result = evaluate_check_reuse(args.event_log, check_spec, source_hashes, candidates)
    else:
        result = record_check_result(
            args.event_log, check_spec, source_hashes, candidates,
            result_status=args.result_status, evidence_refs=args.evidence_ref,
            summary=args.summary, recorded_by=args.recorded_by, signed_receipt=signed_receipt,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") in {"RUN_CHECK", "REUSE_VERIFIED_PASS", "REUSE_RECORDED_PASS_UNTRUSTED",
        "RECHECK_INPUTS_CHANGED", "RECHECK_PRIOR_RESULT_NOT_REUSABLE", "CHECK_RESULT_CONFLICT",
        "RECORDED", "ALREADY_RECORDED"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
