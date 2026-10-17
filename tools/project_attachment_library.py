#!/usr/bin/env python3
"""Private, content-addressed project attachment library.

Copies each attachment into a user-local library once, then emits stable refs.
Never store private file bytes in the repository or in dialogue-window records.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any

DEFAULT_LIBRARY_ROOT = Path.home() / ".local" / "share" / "rima" / "project-library"
PROJECT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{1,127}$")


def _required(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _append_idempotent(path: Path, record: dict[str, Any], key: str) -> str:
    """Append one JSONL record; exact replay is idempotent, changed identity conflicts."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(path.suffix + ".lock")
    with lock_path.open("a+b") as lock:
        if os.name == "nt":
            import msvcrt
            lock.seek(0, os.SEEK_END)
            if lock.tell() == 0:
                lock.write(b"0")
                lock.flush()
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            rows = []
            if path.exists():
                for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                    try:
                        item = json.loads(line)
                    except json.JSONDecodeError as exc:
                        raise ValueError(f"corrupt library registry at line {number}") from exc
                    if not isinstance(item, dict):
                        raise ValueError(f"invalid library registry record at line {number}")
                    rows.append(item)
            for prior in rows:
                if prior.get(key) == record.get(key):
                    if prior != record:
                        raise ValueError(f"{key} collision with changed metadata")
                    return "ALREADY_REGISTERED"
            with path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
            return "REGISTERED"
        finally:
            if os.name == "nt":
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def register_attachment(
    source_path: Path | str,
    library_root: Path | str = DEFAULT_LIBRARY_ROOT,
    *,
    project_id: str,
    conversation_id: str,
    source_message_id: str,
    original_name: str | None = None,
    media_type: str | None = None,
) -> dict[str, Any]:
    """Copy an incoming file once into a private project library and return a stable reference."""
    source = Path(source_path).expanduser().resolve()
    root = Path(library_root).expanduser().resolve()
    project_id = _required(project_id, "project_id")
    if not PROJECT_RE.fullmatch(project_id):
        raise ValueError("project_id contains unsupported characters")
    conversation_id = _required(conversation_id, "conversation_id")
    source_message_id = _required(source_message_id, "source_message_id")
    if not source.is_file():
        raise ValueError("source attachment is missing or is not a regular file")

    digest = sha256_file(source)
    # Object paths are hash-only: a renamed file or a different extension must
    # not create a second physical copy for identical bytes.
    object_rel = Path("objects") / project_id / digest[:2] / digest
    destination = root / object_rel
    destination.parent.mkdir(parents=True, exist_ok=True)

    if destination.exists():
        if not destination.is_file() or sha256_file(destination) != digest:
            raise ValueError("existing library object does not match its content hash")
        object_status = "ALREADY_PRESENT"
    else:
        with tempfile.NamedTemporaryFile(prefix=".incoming-", dir=destination.parent, delete=False) as tmp:
            temporary = Path(tmp.name)
            with source.open("rb") as incoming:
                shutil.copyfileobj(incoming, tmp)
            tmp.flush()
            os.fsync(tmp.fileno())
        try:
            if sha256_file(temporary) != digest:
                raise ValueError("copied attachment hash mismatch")
            try:
                os.link(temporary, destination)
            except FileExistsError:
                if sha256_file(destination) != digest:
                    raise ValueError("concurrent library object conflicts with expected hash")
            except OSError:
                if destination.exists():
                    if sha256_file(destination) != digest:
                        raise ValueError("concurrent library object conflicts with expected hash")
                else:
                    os.replace(temporary, destination)
            object_status = "STORED"
        finally:
            if temporary.exists():
                temporary.unlink()

    library_ref = f"project-library://{project_id}/objects/sha256/{digest}"
    object_record = {
        "schema": "rima-library-object-v1",
        "project_id": project_id,
        "library_ref": library_ref,
        "relative_path": object_rel.as_posix(),
        "sha256": digest,
        "size_bytes": destination.stat().st_size,
        "registered_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    object_registry = root / "objects.jsonl"
    if object_registry.exists():
        for number, line in enumerate(object_registry.read_text(encoding="utf-8").splitlines(), 1):
            try:
                prior_object = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"corrupt library object registry at line {number}") from exc
            if prior_object.get("library_ref") == library_ref:
                object_record["registered_at"] = prior_object.get("registered_at")
                break
    object_registry_status = _append_idempotent(
        object_registry, object_record, "library_ref"
    )

    reference_seed = "\0".join((project_id, conversation_id, source_message_id, digest))
    attachment_id = "ATT-" + hashlib.sha256(reference_seed.encode("utf-8")).hexdigest()[:24]
    reference_record = {
        "schema": "rima-attachment-reference-v1",
        "attachment_id": attachment_id,
        "project_id": project_id,
        "conversation_id": conversation_id,
        "source_message_id": source_message_id,
        "library_ref": library_ref,
        "sha256": digest,
        "original_name": original_name or source.name,
        "media_type": media_type,
        "registered_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    # Stable IDs must remain idempotent even when replayed later; retain original registration time.
    refs_path = root / "references.jsonl"
    if refs_path.exists():
        for number, line in enumerate(refs_path.read_text(encoding="utf-8").splitlines(), 1):
            try:
                prior = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"corrupt attachment reference registry at line {number}") from exc
            if prior.get("attachment_id") == attachment_id:
                reference_record["registered_at"] = prior.get("registered_at")
                break
    reference_status = _append_idempotent(refs_path, reference_record, "attachment_id")
    return {
        "status": "REGISTERED" if reference_status == "REGISTERED" else "ALREADY_REGISTERED",
        "object_status": object_status,
        "object_registry_status": object_registry_status,
        "attachment_id": attachment_id,
        "library_ref": library_ref,
        "sha256": digest,
        "size_bytes": destination.stat().st_size,
        "access_status": "AVAILABLE",
        "storage_locator": str(destination),
    }


def resolve_attachment(
    library_root: Path | str = DEFAULT_LIBRARY_ROOT,
    *,
    attachment_id: str,
    library_ref: str | None = None,
) -> dict[str, Any]:
    """Resolve a registered occurrence to its private object after scope/hash checks."""
    root = Path(library_root).expanduser().resolve()
    attachment_id = _required(attachment_id, "attachment_id")
    refs_path = root / "references.jsonl"
    if not refs_path.is_file():
        return {"status": "UNAVAILABLE", "reason": "attachment reference registry is missing"}
    occurrence = None
    for number, line in enumerate(refs_path.read_text(encoding="utf-8").splitlines(), 1):
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"corrupt attachment reference registry at line {number}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"invalid attachment reference registry at line {number}")
        if row.get("attachment_id") == attachment_id:
            if occurrence is not None and occurrence != row:
                raise ValueError(f"duplicate attachment_id conflict: {attachment_id}")
            occurrence = row
    if occurrence is None:
        return {"status": "UNAVAILABLE", "reason": "attachment reference was not found",
                "attachment_id": attachment_id}
    resolved_ref = occurrence.get("library_ref")
    if library_ref is not None and library_ref != resolved_ref:
        raise ValueError("attachment_id/library_ref mismatch")
    project_id = occurrence.get("project_id")
    if not isinstance(project_id, str) or not PROJECT_RE.fullmatch(project_id):
        raise ValueError("attachment reference has invalid project scope")

    object_path = root / "objects.jsonl"
    if not object_path.is_file():
        return {"status": "UNAVAILABLE", "reason": "library object registry is missing",
                "attachment_id": attachment_id, "library_ref": resolved_ref}
    obj = None
    for number, line in enumerate(object_path.read_text(encoding="utf-8").splitlines(), 1):
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"corrupt library object registry at line {number}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"invalid library object registry at line {number}")
        if row.get("library_ref") == resolved_ref:
            if obj is not None and obj != row:
                raise ValueError(f"duplicate library_ref conflict: {resolved_ref}")
            obj = row
    if obj is None:
        return {"status": "UNAVAILABLE", "reason": "library object record was not found",
                "attachment_id": attachment_id, "library_ref": resolved_ref}
    if obj.get("project_id") != project_id or obj.get("sha256") != occurrence.get("sha256"):
        raise ValueError("attachment reference does not match object project/hash")
    expected_ref = f"project-library://{project_id}/objects/sha256/{obj['sha256']}"
    if resolved_ref != expected_ref:
        raise ValueError("library_ref does not match canonical project/hash identity")
    relative = obj.get("relative_path")
    if not isinstance(relative, str) or not relative:
        raise ValueError("library object has no relative storage path")
    candidate = (root / relative).resolve()
    if root not in candidate.parents:
        raise ValueError("library object path escapes the private library root")
    if not candidate.is_file():
        return {"status": "UNAVAILABLE", "reason": "library object bytes are missing",
                "attachment_id": attachment_id, "library_ref": resolved_ref}
    actual_hash = sha256_file(candidate)
    if actual_hash != obj["sha256"]:
        raise ValueError("library object hash mismatch; refusing to return corrupted bytes")
    return {
        "status": "AVAILABLE",
        "attachment_id": attachment_id,
        "project_id": project_id,
        "conversation_id": occurrence.get("conversation_id"),
        "source_message_id": occurrence.get("source_message_id"),
        "library_ref": resolved_ref,
        "sha256": actual_hash,
        "size_bytes": candidate.stat().st_size,
        "storage_locator": str(candidate),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_path")
    parser.add_argument("--library-root", default=str(DEFAULT_LIBRARY_ROOT))
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--conversation-id", required=True)
    parser.add_argument("--source-message-id", required=True)
    parser.add_argument("--original-name")
    parser.add_argument("--media-type")
    args = parser.parse_args()
    try:
        result = register_attachment(
            args.source_path, args.library_root, project_id=args.project_id,
            conversation_id=args.conversation_id, source_message_id=args.source_message_id,
            original_name=args.original_name, media_type=args.media_type,
        )
    except Exception as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
