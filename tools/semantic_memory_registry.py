#!/usr/bin/env python3
"""Guarded promotion of hash-bound, explicitly approved semantic memory."""
from __future__ import annotations
import argparse, contextlib, hashlib, json, os, re, tempfile
from datetime import datetime
from pathlib import Path
from typing import Any
from validate_memory import validate_intake_manifest

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "registry" / "memory_records.jsonl"
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,191}$")
EVIDENCE = {"reported", "observed", "inferred", "verified", "unknown"}

def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")

def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def _aware(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip(): return False
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        return parsed.tzinfo is not None and parsed.utcoffset() is not None
    except ValueError: return False

def _json_object(path: Path, label: str):
    before = path.read_bytes()
    try: value = json.loads(before.decode("utf-8"))
    except Exception as exc: raise ValueError(f"{label} is invalid UTF-8 JSON: {exc}") from exc
    if not isinstance(value, dict): raise ValueError(f"{label} must be an object")
    if path.read_bytes() != before: raise ValueError(f"{label} changed while read")
    return value, before

def _safe_file(base: Path, rel: Any) -> Path:
    if not isinstance(rel, str) or not rel: raise ValueError("memory artifact path is missing")
    p = Path(rel)
    if p.is_absolute() or ".." in p.parts: raise ValueError("artifact path must be relative and traversal-free")
    base = base.resolve(); resolved = (base / p).resolve()
    if base not in resolved.parents or not resolved.is_file(): raise ValueError("artifact is missing or escapes manifest directory")
    return resolved

def _jsonl(data: bytes, label: str) -> list[dict]:
    try: lines = data.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc: raise ValueError(f"{label} is not UTF-8") from exc
    rows = []
    for n, line in enumerate(lines, 1):
        if not line.strip(): raise ValueError(f"{label} has blank line {n}")
        try: row = json.loads(line)
        except Exception as exc: raise ValueError(f"{label} invalid JSON at line {n}: {exc}") from exc
        if not isinstance(row, dict): raise ValueError(f"{label} line {n} must be an object")
        rows.append(row)
    return rows

def _load(manifest_path: Path, receipt_path: Path) -> dict:
    manifest_path, receipt_path = Path(manifest_path).resolve(), Path(receipt_path).resolve()
    if not manifest_path.is_file() or not receipt_path.is_file(): raise ValueError("manifest or approval receipt is missing")
    manifest, mbytes = _json_object(manifest_path, "manifest")
    errors = validate_intake_manifest(manifest_path)
    if errors: raise ValueError("manifest validation failed: " + "; ".join(errors))
    if manifest_path.read_bytes() != mbytes: raise ValueError("manifest changed during validation")
    arts = manifest.get("artifacts", [])
    if len(arts) != 1 or arts[0].get("kind") != "memory_records": raise ValueError("exactly one memory_records artifact is required")
    art = arts[0]
    if art.get("lifecycle_status") != "accepted" or art.get("approval_status") != "user_approved":
        raise ValueError("artifact must be accepted and user_approved")
    if not isinstance(art.get("approval_evidence"), str) or not art["approval_evidence"].strip():
        raise ValueError("approval_evidence must identify a decision receipt")
    apath = _safe_file(manifest_path.parent, art.get("path")); abytes = apath.read_bytes(); ahash = _sha(abytes)
    if ahash != art.get("sha256"): raise ValueError("artifact SHA-256 differs from manifest")
    records = _jsonl(abytes, "memory artifact")
    if not records or art.get("record_count") != len(records): raise ValueError("artifact record_count mismatch or empty batch")
    seen = set()
    for n, rec in enumerate(records, 1):
        missing = [k for k in ("memory_id","record_type","title","summary","evidence_status","provenance","revision") if k not in rec]
        if missing: raise ValueError(f"record {n} missing fields: {', '.join(missing)}")
        mid = rec.get("memory_id")
        if not isinstance(mid, str) or not ID_RE.fullmatch(mid): raise ValueError(f"record {n} has invalid memory_id")
        if not isinstance(rec.get("record_type"), str) or not rec["record_type"].strip(): raise ValueError(f"record {n} has invalid record_type")
        if rec.get("evidence_status") not in EVIDENCE: raise ValueError(f"record {n} has invalid evidence_status")
        prov = rec.get("provenance")
        if not isinstance(prov, list) or not prov: raise ValueError(f"record {n} needs non-empty provenance")
        for source in prov:
            if isinstance(source, str) and source.strip(): continue
            if not isinstance(source, dict) or not any(isinstance(source.get(k), str) and source[k].strip() for k in ("source_locator","source_record_id","source_ref","archive_id")):
                raise ValueError(f"record {n} has unresolved provenance")
        rev = rec.get("revision")
        if not isinstance(rev, dict) or not isinstance(rev.get("revision_id"), str) or not ID_RE.fullmatch(rev["revision_id"]):
            raise ValueError(f"record {n} has invalid revision")
        parent = rev.get("revision_of")
        if parent is not None and (not isinstance(parent, str) or not ID_RE.fullmatch(parent)): raise ValueError(f"record {n} has invalid revision_of")
        key = (mid, rev["revision_id"])
        if key in seen: raise ValueError(f"duplicate revision in batch: {key}")
        seen.add(key)
    receipt, rbytes = _json_object(receipt_path, "approval receipt")
    required = {"schema_version","decision_id","decision","actor_type","actor_ref","decided_at","batch_id","artifact_id","manifest_sha256","artifact_sha256","decision_source_ref","rationale"}
    missing = sorted(required - set(receipt))
    if missing: raise ValueError("approval receipt missing: " + ", ".join(missing))
    did = receipt.get("decision_id")
    if receipt.get("schema_version") != "semantic-memory-approval-v1" or not isinstance(did, str) or not ID_RE.fullmatch(did):
        raise ValueError("approval receipt schema or decision_id invalid")
    if receipt.get("decision") != "approve": raise ValueError("approval receipt does not authorize promotion")
    if receipt.get("actor_type") != "user": raise ValueError("approval actor_type must be user")
    for k in ("actor_ref","decision_source_ref","rationale"):
        if not isinstance(receipt.get(k), str) or not receipt[k].strip(): raise ValueError(f"approval {k} must be non-empty")
    if not _aware(receipt.get("decided_at")): raise ValueError("approval decided_at must be timezone-aware ISO-8601")
    if receipt.get("batch_id") != manifest.get("batch_id") or receipt.get("artifact_id") != art.get("artifact_id"):
        raise ValueError("approval receipt batch/artifact identity mismatch")
    mhash = _sha(mbytes)
    if receipt.get("manifest_sha256") != mhash: raise ValueError("approval receipt is bound to a different manifest SHA-256")
    if receipt.get("artifact_sha256") != ahash: raise ValueError("approval receipt is bound to different artifact bytes")
    if art.get("approval_evidence") != did: raise ValueError("manifest approval_evidence does not match receipt decision_id")
    if manifest_path.read_bytes() != mbytes or apath.read_bytes() != abytes or receipt_path.read_bytes() != rbytes:
        raise ValueError("manifest, artifact, or receipt changed during validation")
    return {"records":records,"manifest_sha256":mhash,"artifact_sha256":ahash,"receipt_sha256":_sha(rbytes),
            "batch_id":manifest["batch_id"],"artifact_id":art["artifact_id"],"decision_id":did}

def _target_error(path: Path):
    path = Path(path); resolved = path.resolve()
    try: resolved.relative_to(ROOT.resolve())
    except ValueError: return None
    if path.absolute() != DEFAULT_REGISTRY.absolute() or resolved != DEFAULT_REGISTRY.resolve():
        return "repository writes are restricted to registry/memory_records.jsonl"
    if DEFAULT_REGISTRY.is_symlink() or DEFAULT_REGISTRY.parent.is_symlink(): return "canonical registry path cannot be a symlink"
    return None

def _load_registry(path: Path):
    if not path.exists(): return [], {}
    rows = _jsonl(path.read_bytes(), "canonical memory registry"); bykey = {}
    required = ("registry_schema_version","promotion_id","memory_id","revision_id","record_sha256","record","batch_id","artifact_id","manifest_sha256","artifact_sha256","approval_decision_id","approval_receipt_sha256","promoted_at")
    for n, row in enumerate(rows, 1):
        missing = [k for k in required if k not in row]
        if missing: raise ValueError(f"registry line {n} missing fields: {', '.join(missing)}")
        if row["registry_schema_version"] != "semantic-memory-registry-v1": raise ValueError(f"registry line {n} has unsupported schema")
        if not isinstance(row["record"], dict) or _sha(_canonical(row["record"])) != row["record_sha256"]: raise ValueError(f"registry line {n} record hash mismatch")
        key = (row["memory_id"], row["revision_id"])
        if key in bykey: raise ValueError(f"duplicate canonical revision: {key}")
        bykey[key] = row
    return rows, bykey

def _additions(batch: dict, existing: list, bykey: dict):
    latest = {}
    for row in existing: latest[row["memory_id"]] = row
    additions, seen, replay = [], set(), 0
    for rec in batch["records"]:
        mid, rid = rec["memory_id"], rec["revision"]["revision_id"]; key = (mid, rid); digest = _sha(_canonical(rec))
        if key in seen: raise ValueError(f"duplicate revision in batch: {key}")
        seen.add(key); prior = bykey.get(key)
        if prior:
            if prior["record_sha256"] != digest: raise ValueError(f"same memory revision has different content: {key}")
            if prior["approval_decision_id"] != batch["decision_id"]: raise ValueError(f"same revision has different approval decision: {key}")
            replay += 1; continue
        current = latest.get(mid); parent = rec["revision"].get("revision_of")
        if current is None and parent is not None: raise ValueError(f"first revision for {mid} must have revision_of=null")
        if current is not None and parent != current["revision_id"]: raise ValueError(f"revision for {mid} must reference current revision {current['revision_id']!r}")
        promotion_id = _sha(_canonical({"batch_id":batch["batch_id"],"artifact_id":batch["artifact_id"],"memory_id":mid,"revision_id":rid,"record_sha256":digest,"decision_id":batch["decision_id"]}))
        row = {"registry_schema_version":"semantic-memory-registry-v1","promotion_id":promotion_id,"memory_id":mid,"revision_id":rid,
               "record_sha256":digest,"lifecycle_status":"accepted","record":rec,"batch_id":batch["batch_id"],"artifact_id":batch["artifact_id"],
               "manifest_sha256":batch["manifest_sha256"],"artifact_sha256":batch["artifact_sha256"],"approval_decision_id":batch["decision_id"],
               "approval_receipt_sha256":batch["receipt_sha256"],"promoted_at":batch["promotion_time"],"previous_revision_id":parent}
        additions.append(row); latest[mid] = row; bykey[key] = row
    return additions, replay

@contextlib.contextmanager
def _lock(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as stream:
        if os.name == "nt":
            import msvcrt
            stream.seek(0, os.SEEK_END)
            if stream.tell() == 0: stream.write(b"0"); stream.flush()
            stream.seek(0); msvcrt.locking(stream.fileno(), msvcrt.LK_LOCK, 1)
            try: yield
            finally: stream.seek(0); msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
            try: yield
            finally: fcntl.flock(stream.fileno(), fcntl.LOCK_UN)

def _atomic_write(path: Path, rows: list[dict]):
    payload = b"".join(_canonical(row) + b"\n" for row in rows)
    fd, raw = tempfile.mkstemp(prefix=path.name + ".tmp-", dir=path.parent); tmp = Path(raw)
    try:
        with os.fdopen(fd, "wb") as stream: stream.write(payload); stream.flush(); os.fsync(stream.fileno())
        os.replace(tmp, path)
        try:
            dfd = os.open(path.parent, os.O_RDONLY)
            try: os.fsync(dfd)
            finally: os.close(dfd)
        except OSError: pass
    finally: tmp.unlink(missing_ok=True)

def promote_memory_records(manifest_path: Path, approval_receipt_path: Path, registry_path: Path = DEFAULT_REGISTRY, *, apply: bool = False) -> dict:
    try: batch = _load(Path(manifest_path), Path(approval_receipt_path))
    except Exception as exc: return {"status":"REJECTED","error":str(exc),"writes_performed":False}
    batch["promotion_time"] = datetime.now().astimezone().isoformat()
    registry_path = Path(registry_path); error = _target_error(registry_path)
    if error: return {"status":"REJECTED","error":error,"writes_performed":False}
    if not apply: return {"status":"DRY_RUN_READY","batch_id":batch["batch_id"],"decision_id":batch["decision_id"],"candidate_count":len(batch["records"]),"registry_path":str(registry_path),"writes_performed":False}
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    with _lock(registry_path.with_name(registry_path.name + ".lock")):
        try: current = _load(Path(manifest_path), Path(approval_receipt_path))
        except Exception as exc: return {"status":"REJECTED","error":str(exc),"writes_performed":False}
        for key in ("manifest_sha256","artifact_sha256","receipt_sha256","decision_id","batch_id","artifact_id"):
            if current[key] != batch[key]: return {"status":"STALE_INPUT","error":f"{key} changed before promotion","writes_performed":False}
        current["promotion_time"] = batch["promotion_time"]
        try: existing, bykey = _load_registry(registry_path); additions, replay = _additions(current, existing, bykey)
        except Exception as exc: return {"status":"CONFLICT","error":str(exc),"writes_performed":False}
        if not additions: return {"status":"ALREADY_PROMOTED","batch_id":current["batch_id"],"promoted_count":0,"already_present":replay,"writes_performed":False}
        try: _atomic_write(registry_path, existing + additions)
        except Exception as exc: return {"status":"WRITE_FAILED","error":str(exc),"writes_performed":False}
        return {"status":"PROMOTED","batch_id":current["batch_id"],"decision_id":current["decision_id"],"promoted_count":len(additions),"already_present":replay,"registry_path":str(registry_path),"writes_performed":True}

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--approval-receipt", type=Path, required=True)
    parser.add_argument("--registry-path", type=Path, default=DEFAULT_REGISTRY, help=argparse.SUPPRESS)
    parser.add_argument("--apply", action="store_true", help="persist approved records; default is read-only")
    args = parser.parse_args(argv)
    result = promote_memory_records(args.manifest, args.approval_receipt, args.registry_path, apply=args.apply)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] in {"DRY_RUN_READY","PROMOTED","ALREADY_PROMOTED"} else 2

if __name__ == "__main__":
    raise SystemExit(main())
