#!/usr/bin/env python3
"""Resumable orchestration for source staging → intake → source registry.

This runner deliberately stops after metadata-only source registration. It does
not promote semantic memory, rebuild canonical indexes, or claim session restore.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from adapt_archive_staging_to_intake import adapt_archive_staging_to_intake
from plan_memory_intake import build_route_plan
from source_evidence_registry import DEFAULT_REGISTRY, append_source_records
from source_registry_contract import batch_id_for_snapshot, sha256_hex, utc_now


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, raw_tmp = tempfile.mkstemp(prefix=path.name + ".tmp-", dir=path.parent)
    tmp = Path(raw_tmp)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
        try:
            dir_fd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        except OSError:
            # Some platforms/filesystems do not support directory fsync.
            pass
    finally:
        tmp.unlink(missing_ok=True)


@contextlib.contextmanager
def _exclusive_lock(path: Path):
    """OS-managed advisory lock; process death releases it without stale lock files."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as stream:
        if os.name == "nt":
            import msvcrt
            stream.seek(0, os.SEEK_END)
            if stream.tell() == 0:
                stream.write(b"0")
                stream.flush()
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def _load_events(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except Exception as exc:
        raise ValueError(f"run event ledger cannot be read: {exc}") from exc
    events: list[dict[str, Any]] = []
    previous = None
    for number, line in enumerate(lines, 1):
        if not line.strip():
            raise ValueError(f"run event ledger has a blank line at {number}")
        try:
            event = json.loads(line)
        except Exception as exc:
            raise ValueError(f"run event ledger has invalid JSON at line {number}") from exc
        if not isinstance(event, dict) or event.get("sequence") != number:
            raise ValueError(f"run event ledger sequence is invalid at line {number}")
        if event.get("previous_event_sha256") != previous:
            raise ValueError(f"run event ledger hash-chain link is invalid at line {number}")
        digest = event.get("event_sha256")
        body = {key: value for key, value in event.items() if key != "event_sha256"}
        expected = hashlib.sha256(_canonical(body)).hexdigest()
        if digest != expected:
            raise ValueError(f"run event ledger hash mismatch at line {number}")
        previous = digest
        events.append(event)
    return events


def _write_projection(run_dir: Path, events: list[dict[str, Any]]) -> None:
    if not events:
        return
    last = events[-1]
    projection = {
        "schema_version": "source-ingestion-run-state-v1",
        "run_id": last["run_id"],
        "batch_id": last["batch_id"],
        "source_identity": last["source_identity"],
        "latest_sequence": last["sequence"],
        "latest_event_sha256": last["event_sha256"],
        "latest_stage": last["stage"],
        "status": last["status"],
        "updated_at": last["occurred_at"],
        "downstream": "NOT_IMPLEMENTED_BY_THIS_RUNNER",
    }
    _atomic_write(run_dir / "run_state.json", _canonical(projection) + b"\n")


def _append_event(run_dir: Path, events: list[dict[str, Any]], *, run_id: str,
                  batch_id: str, source_identity: dict[str, str], stage: str,
                  status: str, details: dict[str, Any]) -> list[dict[str, Any]]:
    previous = events[-1]["event_sha256"] if events else None
    body = {
        "sequence": len(events) + 1,
        "occurred_at": utc_now(),
        "run_id": run_id,
        "batch_id": batch_id,
        "source_identity": source_identity,
        "stage": stage,
        "status": status,
        "details": details,
        "previous_event_sha256": previous,
    }
    event = dict(body)
    event["event_sha256"] = hashlib.sha256(_canonical(body)).hexdigest()
    updated = [*events, event]
    payload = b"".join(_canonical(item) + b"\n" for item in updated)
    _atomic_write(run_dir / "run_events.jsonl", payload)
    # The append-only hash-chained ledger is authoritative. If projection write
    # fails, a later invocation rebuilds it from the verified event ledger.
    _write_projection(run_dir, updated)
    return updated


def run_ingestion(snapshot_path: Path, run_root: Path, *, intake_root: Path | None = None,
                  registry_path: Path = DEFAULT_REGISTRY, apply: bool = False) -> dict[str, Any]:
    snapshot_path = Path(snapshot_path).resolve()
    if not snapshot_path.is_file():
        return {"status": "BLOCKED", "error": "archive_snapshot.json is missing", "writes_performed": False}
    try:
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"status": "BLOCKED", "error": f"archive snapshot is invalid: {exc}", "writes_performed": False}
    archive_id = snapshot.get("archive_id")
    raw_sha = snapshot.get("raw_sha256")
    parser_version = snapshot.get("parser_version")
    if not all(isinstance(value, str) and value.strip() for value in (archive_id, parser_version)):
        return {"status": "BLOCKED", "error": "archive_id and parser_version are required", "writes_performed": False}
    if not isinstance(raw_sha, str) or len(raw_sha) != 64 or any(c not in "0123456789abcdef" for c in raw_sha):
        return {"status": "BLOCKED", "error": "raw_sha256 is invalid", "writes_performed": False}

    batch_id = batch_id_for_snapshot(archive_id, raw_sha, parser_version)
    run_root = Path(run_root).resolve()
    run_dir = run_root / batch_id
    run_dir.mkdir(parents=True, exist_ok=True)
    intake_root = Path(intake_root).resolve() if intake_root else run_root / "intake"
    source_identity = {
        "archive_id": archive_id,
        "raw_sha256": raw_sha,
        "parser_version": parser_version,
    }
    events_path = run_dir / "run_events.jsonl"
    wrote_anything = False

    with _exclusive_lock(run_dir / ".run.lock"):
        try:
            events = _load_events(events_path)
        except ValueError as exc:
            return {"status": "BLOCKED", "batch_id": batch_id, "run_dir": str(run_dir),
                    "error": str(exc), "writes_performed": False}
        if any(event.get("source_identity") != source_identity for event in events):
            return {"status": "BLOCKED", "batch_id": batch_id, "run_dir": str(run_dir),
                    "error": "run ledger source identity does not match current archive snapshot",
                    "writes_performed": False}
        # Rebuild a missing/stale projection from the authoritative event ledger.
        if events:
            try:
                projection = json.loads((run_dir / "run_state.json").read_text(encoding="utf-8"))
            except Exception:
                projection = {}
            if projection.get("latest_event_sha256") != events[-1]["event_sha256"]:
                _write_projection(run_dir, events)
        events = _append_event(
            run_dir, events, run_id=batch_id, batch_id=batch_id,
            source_identity=source_identity, stage="RUN_RESUMED" if events else "RUN_STARTED",
            status="RUNNING", details={"mode": "apply" if apply else "dry_run"},
        )

        try:
            adapted = adapt_archive_staging_to_intake(snapshot_path, intake_root)
            if adapted.get("status") not in {"ADAPTED", "ALREADY_ADAPTED"}:
                raise ValueError("intake adapter returned " + str(adapted.get("status")))
            wrote_anything = wrote_anything or bool(adapted.get("writes_performed"))
            manifest_path = Path(adapted["manifest_path"])
            manifest_sha = sha256_hex(manifest_path.read_bytes())
            events = _append_event(
                run_dir, events, run_id=batch_id, batch_id=batch_id,
                source_identity=source_identity, stage="INTAKE_ADAPTED",
                status=adapted["status"],
                details={"manifest_path": str(manifest_path), "manifest_sha256": manifest_sha,
                         "record_count": adapted.get("record_count")},
            )

            plan = build_route_plan(manifest_path)
            if plan.get("status") != "DRY_RUN_READY":
                raise ValueError("route plan rejected: " + "; ".join(plan.get("validation_errors", [])))
            routes = plan.get("routes", [])
            if len(routes) != 1 or routes[0].get("kind") != "source_records" or routes[0].get("logical_view") != "source_evidence_registry" or routes[0].get("planned_operation") != "append_source_records":
                raise ValueError("runner only supports the source_records → source_evidence_registry route")
            events = _append_event(
                run_dir, events, run_id=batch_id, batch_id=batch_id,
                source_identity=source_identity, stage="ROUTE_VALIDATED",
                status="DRY_RUN_READY",
                details={"manifest_sha256": manifest_sha, "route_count": len(routes),
                         "writes_performed": False},
            )

            registration = append_source_records(manifest_path, registry_path, apply=apply)
            status = registration.get("status")
            wrote_anything = wrote_anything or bool(registration.get("writes_performed"))
            events = _append_event(
                run_dir, events, run_id=batch_id, batch_id=batch_id,
                source_identity=source_identity, stage="SOURCE_REGISTRATION",
                status=status or "UNKNOWN",
                details={"registry_path": registration.get("registry_path", str(registry_path)),
                         "result": registration, "apply": apply},
            )
            if not apply and status == "DRY_RUN_READY":
                final_status = "READY_FOR_SOURCE_REGISTRATION"
            elif apply and status in {"APPENDED", "ALREADY_REGISTERED"}:
                final_status = "SOURCE_REGISTERED_DOWNSTREAM_PENDING"
            else:
                final_status = "BLOCKED"
            events = _append_event(
                run_dir, events, run_id=batch_id, batch_id=batch_id,
                source_identity=source_identity, stage="RUN_RESULT",
                status=final_status,
                details={
                    "semantic_promotion": "NOT_IMPLEMENTED",
                    "canonical_index_refresh": "NOT_IMPLEMENTED",
                    "next_session_restore": "NOT_VERIFIED",
                    "writes_performed_this_run": wrote_anything,
                },
            )
            return {
                "status": final_status,
                "batch_id": batch_id,
                "run_dir": str(run_dir),
                "run_state_path": str(run_dir / "run_state.json"),
                "event_ledger_path": str(events_path),
                "latest_event_sha256": events[-1]["event_sha256"],
                "registration_status": status,
                "writes_performed": wrote_anything,
                "downstream": "semantic promotion, canonical index refresh and next-session restore are not implemented by this runner",
            }
        except Exception as exc:
            events = _append_event(
                run_dir, events, run_id=batch_id, batch_id=batch_id,
                source_identity=source_identity, stage="RUN_BLOCKED",
                status="BLOCKED", details={"error": str(exc), "writes_performed_this_run": wrote_anything},
            )
            return {"status": "BLOCKED", "batch_id": batch_id, "run_dir": str(run_dir),
                    "event_ledger_path": str(events_path), "error": str(exc),
                    "writes_performed": wrote_anything}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive_snapshot", type=Path)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--intake-root", type=Path, default=None)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--apply", action="store_true", help="append metadata-only source records; default is dry-run")
    args = parser.parse_args(argv)
    result = run_ingestion(args.archive_snapshot, args.run_root, intake_root=args.intake_root,
                           registry_path=args.registry, apply=args.apply)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] in {"READY_FOR_SOURCE_REGISTRATION", "SOURCE_REGISTERED_DOWNSTREAM_PENDING"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
