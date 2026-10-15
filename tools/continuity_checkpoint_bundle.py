#!/usr/bin/env python3
"""Crash-recoverable paired TASK_STATE.md + HANDOFF.md checkpoint bundle.

The immutable generation is written first. CURRENT_CHECKPOINT.json is the single
commit point. Markdown files are projections: if a process dies after pointer
publication but before both projections are materialized, recover replays them
from the committed generation. This is a repository tool, not ChatGPT autosave.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "continuity-checkpoint-bundle-v1"
CHECKPOINT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,127}$")
CANONICAL_FILES = ("TASK_STATE.md", "HANDOFF.md", "events.jsonl")


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def atomic_write(path: Path, payload: bytes) -> None:
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
            pass
    finally:
        tmp.unlink(missing_ok=True)


@contextlib.contextmanager
def exclusive_lock(path: Path):
    """Use an OS-managed lock so process death does not leave a stale lock file."""
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


def _paths(project_dir: Path) -> tuple[Path, Path, Path]:
    root = Path(project_dir).resolve()
    return root / "CURRENT_CHECKPOINT.json", root / "checkpoints", root / ".continuity-checkpoint.lock"


def _load_pointer(pointer_path: Path, generations_dir: Path) -> tuple[dict[str, Any], Path, dict[str, Any]]:
    if not pointer_path.is_file():
        raise ValueError("CURRENT_CHECKPOINT.json is missing")
    try:
        pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"current checkpoint pointer is invalid JSON: {exc}") from exc
    if not isinstance(pointer, dict) or pointer.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("current checkpoint pointer has an unsupported schema")
    checkpoint_id = pointer.get("checkpoint_id")
    if not isinstance(checkpoint_id, str) or not CHECKPOINT_ID_RE.fullmatch(checkpoint_id):
        raise ValueError("current checkpoint pointer has an invalid checkpoint_id")
    expected_rel = Path("checkpoints") / f"{checkpoint_id}.json"
    if pointer.get("generation_path") != expected_rel.as_posix():
        raise ValueError("current checkpoint pointer path does not match checkpoint_id")
    generation_path = (pointer_path.parent / expected_rel).resolve()
    if generations_dir.resolve() not in generation_path.parents or not generation_path.is_file():
        raise ValueError("current checkpoint generation is missing or escapes project directory")
    raw = generation_path.read_bytes()
    actual_sha = sha256_bytes(raw)
    if actual_sha != pointer.get("generation_sha256"):
        raise ValueError("current checkpoint generation hash does not match pointer")
    try:
        generation = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise ValueError(f"checkpoint generation is invalid JSON: {exc}") from exc
    if not isinstance(generation, dict) or generation.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("checkpoint generation has an unsupported schema")
    recorded_hash = generation.get("bundle_sha256")
    body = {key: value for key, value in generation.items() if key != "bundle_sha256"}
    if recorded_hash != sha256_bytes(canonical(body)):
        raise ValueError("checkpoint generation content hash is invalid")
    if generation.get("checkpoint_id") != checkpoint_id:
        raise ValueError("checkpoint generation ID does not match pointer")
    return pointer, generation_path, generation


def _validate_chain(project_dir: Path, generation: dict[str, Any]) -> list[str]:
    seen: set[str] = set()
    chain: list[str] = []
    current = generation
    while True:
        checkpoint_id = current.get("checkpoint_id")
        if not isinstance(checkpoint_id, str) or checkpoint_id in seen:
            raise ValueError("checkpoint parent chain has a cycle or invalid ID")
        seen.add(checkpoint_id)
        chain.append(checkpoint_id)
        parent_id = current.get("parent_checkpoint_id")
        parent_sha = current.get("parent_generation_sha256")
        if parent_id is None:
            if parent_sha is not None:
                raise ValueError("root checkpoint unexpectedly has a parent hash")
            break
        if not isinstance(parent_id, str) or not CHECKPOINT_ID_RE.fullmatch(parent_id):
            raise ValueError("checkpoint parent ID is invalid")
        parent_path = project_dir / "checkpoints" / f"{parent_id}.json"
        if not parent_path.is_file():
            raise ValueError(f"parent checkpoint generation is missing: {parent_id}")
        raw = parent_path.read_bytes()
        if sha256_bytes(raw) != parent_sha:
            raise ValueError(f"parent checkpoint hash mismatch: {parent_id}")
        try:
            parent = json.loads(raw.decode("utf-8"))
        except Exception as exc:
            raise ValueError(f"parent checkpoint is invalid JSON: {parent_id}") from exc
        body = {key: value for key, value in parent.items() if key != "bundle_sha256"}
        if parent.get("bundle_sha256") != sha256_bytes(canonical(body)):
            raise ValueError(f"parent checkpoint content hash mismatch: {parent_id}")
        current = parent
    return list(reversed(chain))


def _materialize(project_dir: Path, generation: dict[str, Any]) -> None:
    for name in ("TASK_STATE.md", "HANDOFF.md"):
        record = generation.get("projections", {}).get(name)
        if not isinstance(record, dict) or not isinstance(record.get("content"), str):
            raise ValueError(f"checkpoint generation has no valid {name} projection")
        content = record["content"].encode("utf-8")
        if sha256_bytes(content) != record.get("sha256"):
            raise ValueError(f"checkpoint projection hash is invalid: {name}")
        atomic_write(project_dir / name, content)


def capture(project_dir: Path, *, checkpoint_id: str, summary: str,
            source_head: str | None = None, ci_run_id: str | None = None) -> dict[str, Any]:
    project_dir = Path(project_dir).resolve()
    if not CHECKPOINT_ID_RE.fullmatch(checkpoint_id):
        return {"status": "REJECTED", "error": "invalid checkpoint_id", "writes_performed": False}
    if not isinstance(summary, str) or not summary.strip():
        return {"status": "REJECTED", "error": "summary is required", "writes_performed": False}
    missing = [name for name in CANONICAL_FILES if not (project_dir / name).is_file()]
    if missing:
        return {"status": "BLOCKED", "error": "missing canonical sources: " + ", ".join(missing),
                "writes_performed": False}
    pointer_path, generations_dir, lock_path = _paths(project_dir)
    with exclusive_lock(lock_path):
        previous_pointer = None
        previous_generation = None
        if pointer_path.exists():
            try:
                previous_pointer, _, previous_generation = _load_pointer(pointer_path, generations_dir)
                _validate_chain(project_dir, previous_generation)
            except ValueError as exc:
                return {"status": "BLOCKED", "error": str(exc), "writes_performed": False}
        task_bytes = (project_dir / "TASK_STATE.md").read_bytes()
        handoff_bytes = (project_dir / "HANDOFF.md").read_bytes()
        event_bytes = (project_dir / "events.jsonl").read_bytes()
        generation_path = generations_dir / f"{checkpoint_id}.json"
        if generation_path.exists():
            try:
                existing_raw = generation_path.read_bytes()
                existing = json.loads(existing_raw.decode("utf-8"))
            except Exception as exc:
                return {"status": "BLOCKED", "error": f"existing checkpoint generation is unreadable: {exc}",
                        "writes_performed": False}
            current_hashes = {
                "TASK_STATE.md": sha256_bytes(task_bytes),
                "HANDOFF.md": sha256_bytes(handoff_bytes),
                "events.jsonl": sha256_bytes(event_bytes),
            }
            if (
                previous_pointer
                and previous_pointer.get("checkpoint_id") == checkpoint_id
                and previous_pointer.get("generation_sha256") == sha256_bytes(existing_raw)
                and existing.get("summary") == summary.strip()
                and existing.get("source_head") == source_head
                and existing.get("ci_run_id") == ci_run_id
                and existing.get("source_hashes") == current_hashes
            ):
                return {"status": "ALREADY_CAPTURED", "checkpoint_id": checkpoint_id,
                        "generation_sha256": previous_pointer["generation_sha256"], "writes_performed": False}
            return {"status": "CONFLICT", "error": "checkpoint_id already exists with different or stale content",
                    "writes_performed": False}
        body = {
            "schema_version": SCHEMA_VERSION,
            "checkpoint_id": checkpoint_id,
            "project_id": project_dir.name,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "summary": summary.strip(),
            "source_head": source_head,
            "ci_run_id": ci_run_id,
            "parent_checkpoint_id": previous_pointer.get("checkpoint_id") if previous_pointer else None,
            "parent_generation_sha256": previous_pointer.get("generation_sha256") if previous_pointer else None,
            "source_hashes": {
                "TASK_STATE.md": sha256_bytes(task_bytes),
                "HANDOFF.md": sha256_bytes(handoff_bytes),
                "events.jsonl": sha256_bytes(event_bytes),
            },
            "projections": {
                "TASK_STATE.md": {"sha256": sha256_bytes(task_bytes), "content": task_bytes.decode("utf-8")},
                "HANDOFF.md": {"sha256": sha256_bytes(handoff_bytes), "content": handoff_bytes.decode("utf-8")},
            },
        }
        body["bundle_sha256"] = sha256_bytes(canonical(body))
        generation_path = generations_dir / f"{checkpoint_id}.json"
        generation_bytes = canonical(body) + b"\n"
        generation_sha = sha256_bytes(generation_bytes)
        if generation_path.exists():
            if generation_path.read_bytes() != generation_bytes:
                return {"status": "CONFLICT", "error": "checkpoint_id already exists with different content",
                        "writes_performed": False}
            if previous_pointer and previous_pointer.get("checkpoint_id") == checkpoint_id:
                return {"status": "ALREADY_CAPTURED", "checkpoint_id": checkpoint_id, "writes_performed": False}
            return {"status": "CONFLICT", "error": "checkpoint_id exists but is not the current checkpoint",
                    "writes_performed": False}
        generations_dir.mkdir(parents=True, exist_ok=True)
        atomic_write(generation_path, generation_bytes)
        pointer = {
            "schema_version": SCHEMA_VERSION,
            "checkpoint_id": checkpoint_id,
            "generation_path": (Path("checkpoints") / f"{checkpoint_id}.json").as_posix(),
            "generation_sha256": generation_sha,
        }
        # This pointer is the single commit point. Recovery replays projections if
        # the process dies after pointer replacement and before materialization.
        atomic_write(pointer_path, canonical(pointer) + b"\n")
        try:
            _materialize(project_dir, body)
        except Exception as exc:
            return {"status": "COMMITTED_PROJECTIONS_PENDING", "checkpoint_id": checkpoint_id,
                    "generation_sha256": generation_sha, "error": str(exc), "writes_performed": True}
        return {"status": "CAPTURED", "checkpoint_id": checkpoint_id,
                "generation_sha256": generation_sha, "parent_checkpoint_id": body["parent_checkpoint_id"],
                "writes_performed": True}


def verify(project_dir: Path) -> dict[str, Any]:
    project_dir = Path(project_dir).resolve()
    pointer_path, generations_dir, _ = _paths(project_dir)
    try:
        pointer, generation_path, generation = _load_pointer(pointer_path, generations_dir)
        chain = _validate_chain(project_dir, generation)
    except ValueError as exc:
        return {"status": "BLOCKED", "error": str(exc), "writes_performed": False}
    drift = {}
    for name in ("TASK_STATE.md", "HANDOFF.md", "events.jsonl"):
        path = project_dir / name
        expected = generation["source_hashes"].get(name) if name in generation["source_hashes"] else None
        if not path.is_file():
            drift[name] = {"status": "MISSING"}
        else:
            actual = sha256_file(path)
            if actual != expected:
                drift[name] = {"status": "DRIFT", "checkpoint_sha256": expected, "actual_sha256": actual}
    return {
        "status": "CURRENT" if not drift else "PROJECTION_OR_SOURCE_DRIFT",
        "checkpoint_id": pointer["checkpoint_id"],
        "generation_sha256": pointer["generation_sha256"],
        "chain": chain,
        "drift": drift,
        "writes_performed": False,
    }


def recover(project_dir: Path) -> dict[str, Any]:
    project_dir = Path(project_dir).resolve()
    pointer_path, generations_dir, lock_path = _paths(project_dir)
    with exclusive_lock(lock_path):
        try:
            pointer, _, generation = _load_pointer(pointer_path, generations_dir)
            chain = _validate_chain(project_dir, generation)
            _materialize(project_dir, generation)
        except (ValueError, OSError) as exc:
            return {"status": "BLOCKED", "error": str(exc), "writes_performed": False}
        return {"status": "RECOVERED", "checkpoint_id": pointer["checkpoint_id"],
                "chain": chain, "writes_performed": True,
                "note": "TASK_STATE.md and HANDOFF.md were rebuilt from the committed checkpoint bundle; events.jsonl was not changed."}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    cap = sub.add_parser("capture", help="commit a paired checkpoint bundle")
    cap.add_argument("project_dir", type=Path)
    cap.add_argument("--checkpoint-id", required=True)
    cap.add_argument("--summary", required=True)
    cap.add_argument("--source-head")
    cap.add_argument("--ci-run-id")
    ver = sub.add_parser("verify", help="verify pointer, generation chain and projection freshness")
    ver.add_argument("project_dir", type=Path)
    rec = sub.add_parser("recover", help="rebuild paired markdown projections from the committed bundle")
    rec.add_argument("project_dir", type=Path)
    args = parser.parse_args(argv)
    if args.command == "capture":
        result = capture(args.project_dir, checkpoint_id=args.checkpoint_id, summary=args.summary,
                         source_head=args.source_head, ci_run_id=args.ci_run_id)
    elif args.command == "verify":
        result = verify(args.project_dir)
    else:
        result = recover(args.project_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] in {"CAPTURED", "ALREADY_CAPTURED", "CURRENT", "RECOVERED"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
