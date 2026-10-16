#!/usr/bin/env python3
"""Build a deterministic, versioned multidimensional index from the canonical memory registry."""
from __future__ import annotations
import argparse, contextlib, hashlib, json, os, tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "registry" / "memory_records.jsonl"
DEFAULT_CORRECTIONS = ROOT / "registry" / "edge_corrections.jsonl"
DEFAULT_INDEX_ROOT = ROOT / "registry" / "memory_index"
INDEX_SCHEMA = "canonical-memory-index-v1"
INDEXER_VERSION = "1.0.0"
DIMENSIONS = {
    "by_project": ("project_ids", "project_id"),
    "by_task": ("task_ids", "task_id"),
    "by_context": ("context_ids", "context_id"),
    "by_record_type": ("record_type",),
    "by_topic": ("tags",),
    "by_evidence_status": ("evidence_status",),
    "by_record_lifecycle_status": ("lifecycle_status",),
    "by_sign": ("sign",),
    "by_decision_status": ("decision_status",),
    "by_incident": ("incident_ids", "incident_id"),
}

def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")

def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def _jsonl(data: bytes) -> list[dict]:
    try: lines = data.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc: raise ValueError("canonical memory registry is not UTF-8") from exc
    rows = []
    for n, line in enumerate(lines, 1):
        if not line.strip(): raise ValueError(f"blank registry line {n}")
        try: row = json.loads(line)
        except Exception as exc: raise ValueError(f"invalid registry JSON at line {n}: {exc}") from exc
        if not isinstance(row, dict): raise ValueError(f"registry line {n} must be an object")
        rows.append(row)
    return rows

def _values(record: dict, fields: tuple[str, ...]) -> list[str]:
    values = []
    for field in fields:
        value = record.get(field)
        if isinstance(value, str) and value.strip():
            values.append(value.strip())
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, str) and item.strip(): values.append(item.strip())
                elif isinstance(item, dict) and isinstance(item.get("value"), str) and item["value"].strip():
                    values.append(item["value"].strip())
    return sorted(set(values))

def _source_refs(record: dict) -> list[str]:
    refs = []
    for item in record.get("provenance", []) if isinstance(record.get("provenance"), list) else []:
        if isinstance(item, str) and item.strip(): refs.append(item.strip())
        elif isinstance(item, dict):
            for field in ("source_locator", "source_record_id", "source_ref"):
                value = item.get(field)
                if isinstance(value, str) and value.strip():
                    refs.append(f"{field}:{value.strip()}")
    return sorted(set(refs))

def _validate_registry(rows: list[dict]) -> list[dict]:
    by_revision, latest, validated = {}, {}, []
    required = ("registry_schema_version","promotion_id","memory_id","revision_id","record_sha256","record","batch_id","artifact_id","manifest_sha256","artifact_sha256","approval_decision_id","approval_receipt_sha256","promoted_at","previous_revision_id")
    for n, row in enumerate(rows, 1):
        missing = [k for k in required if k not in row]
        if missing: raise ValueError(f"registry line {n} missing fields: {', '.join(missing)}")
        if row.get("registry_schema_version") != "semantic-memory-registry-v1": raise ValueError(f"registry line {n} has unsupported schema")
        rec = row.get("record")
        if not isinstance(rec, dict) or _sha(_canonical(rec)) != row.get("record_sha256"): raise ValueError(f"registry line {n} record hash mismatch")
        if not isinstance(rec.get("provenance"), list) or not rec["provenance"]: raise ValueError(f"registry line {n} lacks required provenance")
        mid, rid = row.get("memory_id"), row.get("revision_id")
        if not isinstance(mid, str) or not mid or not isinstance(rid, str) or not rid: raise ValueError(f"registry line {n} has invalid memory/revision identity")
        if rec.get("memory_id") != mid or not isinstance(rec.get("revision"), dict) or rec["revision"].get("revision_id") != rid:
            raise ValueError(f"registry line {n} envelope identity differs from embedded record")
        if row.get("lifecycle_status") != "accepted": raise ValueError(f"registry line {n} is not accepted")
        key = (mid, rid)
        if key in by_revision: raise ValueError(f"duplicate canonical revision {mid}/{rid}")
        parent = row.get("previous_revision_id")
        current = latest.get(mid)
        if current is None and parent is not None: raise ValueError(f"first revision {mid}/{rid} has unexpected parent")
        if current is not None and parent != current["revision_id"]: raise ValueError(f"broken revision chain for {mid}/{rid}")
        if rec["revision"].get("revision_of") != parent: raise ValueError(f"embedded revision parent differs for {mid}/{rid}")
        by_revision[key] = row
        latest[mid] = row
        validated.append(row)
    return validated


def _load_corrections(correction_bytes: bytes | None, rows: list[dict]):
    if correction_bytes is None:
        return {}, {}, {"path":"registry/edge_corrections.jsonl","sha256":None,"byte_count":0,"correction_count":0,"active_count":0}, "NOT_AVAILABLE_NO_CANONICAL_OVERLAY_SOURCE"
    source={(row["memory_id"],row["revision_id"]):row for row in rows}
    active_relations={key:list(row["record"].get("relations",[])) for key,row in source.items()}
    applied_ids={key:[] for key in source}
    corrections=_jsonl(correction_bytes)
    seen=set()
    active_count=0
    for n,envelope in enumerate(corrections,1):
        correction=envelope.get("correction")
        if envelope.get("registry_schema_version")!="edge-correction-registry-v1" or not isinstance(correction,dict):
            raise ValueError(f"invalid edge correction envelope at line {n}")
        digest=_sha(_canonical(correction))
        if digest!=envelope.get("correction_sha256"): raise ValueError(f"edge correction hash mismatch at line {n}")
        cid=correction.get("correction_id")
        if not isinstance(cid,str) or not cid or cid in seen: raise ValueError(f"missing or duplicate correction_id at line {n}")
        seen.add(cid)
        if correction.get("schema_version")!="edge-correction-v1": raise ValueError(f"unsupported correction schema at line {n}")
        if correction.get("status") not in {"candidate","accepted","disputed","rejected","superseded"}:
            raise ValueError(f"invalid correction status at line {n}")
        key=(correction.get("source_memory_id"),correction.get("source_revision_id"))
        source_row=source.get(key)
        if source_row is None or source_row.get("record_sha256")!=correction.get("source_record_sha256"):
            raise ValueError(f"edge correction source reference is missing or stale at line {n}")
        if correction["status"]!="accepted": continue
        if not isinstance(envelope.get("approval_receipt_sha256"),str) or len(envelope["approval_receipt_sha256"])!=64:
            raise ValueError(f"accepted correction lacks approval receipt hash at line {n}")
        if not isinstance(correction.get("decision_id"),str) or not correction["decision_id"].strip() or not isinstance(correction.get("decision_source_ref"),str) or not correction["decision_source_ref"].strip():
            raise ValueError(f"accepted correction lacks decision provenance at line {n}")
        action=correction.get("action")
        relations=active_relations[key]
        if action=="add":
            relation=correction.get("relation")
            if not isinstance(relation,dict): raise ValueError(f"add correction lacks relation at line {n}")
            relation_hash=_sha(_canonical(relation))
            if any(isinstance(item,dict) and _sha(_canonical(item))==relation_hash for item in relations):
                raise ValueError(f"add correction duplicates an effective relation at line {n}")
            relations.append(relation)
        elif action in {"retract","replace"}:
            target=correction.get("target_relation_sha256")
            if not isinstance(target,str) or len(target)!=64: raise ValueError(f"correction target fingerprint is invalid at line {n}")
            matches=[i for i,item in enumerate(relations) if isinstance(item,dict) and _sha(_canonical(item))==target]
            if len(matches)!=1: raise ValueError(f"correction target relation is missing or ambiguous at line {n}")
            if action=="retract": relations.pop(matches[0])
            else:
                replacement=correction.get("replacement_relation")
                if not isinstance(replacement,dict): raise ValueError(f"replace correction lacks replacement relation at line {n}")
                relations[matches[0]]=replacement
        else: raise ValueError(f"unsupported correction action at line {n}")
        applied_ids[key].append(cid)
        active_count+=1
    status="APPLIED" if active_count else "VALIDATED_NO_ACTIVE_CORRECTIONS"
    meta={"path":"registry/edge_corrections.jsonl","sha256":_sha(correction_bytes),"byte_count":len(correction_bytes),
          "correction_count":len(corrections),"active_count":active_count}
    return active_relations,applied_ids,meta,status

def build_index_payload(registry_bytes: bytes, correction_bytes: bytes | None = None) -> dict:
    rows = _validate_registry(_jsonl(registry_bytes))
    registry_sha = _sha(registry_bytes)
    effective_relations, applied_corrections, correction_meta, correction_status = _load_corrections(correction_bytes, rows)
    latest = {}
    for row in rows: latest[row["memory_id"]] = row["revision_id"]
    records, indexes = [], {name: {} for name in DIMENSIONS}
    indexes["by_event_time"] = {}
    indexes["by_source_time"] = {}
    indexes["by_source_ref"] = {}
    indexes["by_relation_type"] = {}
    indexes["by_relation_target"] = {}
    for position, row in enumerate(rows, 1):
        rec = row["record"]
        current = latest[row["memory_id"]] == row["revision_id"]
        refs = _source_refs(rec)
        item = {
            "memory_id": row["memory_id"], "revision_id": row["revision_id"],
            "record_sha256": row["record_sha256"], "registry_position": position,
            "current_revision": current, "lifecycle_status": row["lifecycle_status"],
            "record_lifecycle_status": rec.get("lifecycle_status", "unknown"),
            "evidence_status": rec.get("evidence_status", "unknown"),
            "project_ids": _values(rec, ("project_ids", "project_id")),
            "task_ids": _values(rec, ("task_ids", "task_id")),
            "context_ids": _values(rec, ("context_ids", "context_id")),
            "record_type": rec.get("record_type") if isinstance(rec.get("record_type"), str) else "unknown",
            "tags": _values(rec, ("tags",)), "source_refs": refs,
            "relations": effective_relations[(row["memory_id"],row["revision_id"])],
            "applied_correction_ids": applied_corrections[(row["memory_id"],row["revision_id"])],
        }
        records.append(item)
        for name, fields in DIMENSIONS.items():
            for value in _values(rec, fields):
                indexes[name].setdefault(value, []).append({"memory_id":row["memory_id"],"revision_id":row["revision_id"],"record_sha256":row["record_sha256"]})
        for field, name in (("event_time","by_event_time"),("source_time","by_source_time")):
            value = rec.get(field)
            if isinstance(value, str) and value.strip() and value.strip().lower() != "unknown":
                indexes[name].setdefault(value.strip(), []).append({"memory_id":row["memory_id"],"revision_id":row["revision_id"],"record_sha256":row["record_sha256"]})
        for ref in refs: indexes["by_source_ref"].setdefault(ref, []).append({"memory_id":row["memory_id"],"revision_id":row["revision_id"],"record_sha256":row["record_sha256"]})
        relations = effective_relations[(row["memory_id"],row["revision_id"])]
        if isinstance(relations, list):
            for relation in relations:
                if not isinstance(relation, dict): continue
                rtype = relation.get("type")
                target = relation.get("target_id") or relation.get("event_id") or relation.get("source_id")
                entry = {"memory_id":row["memory_id"],"revision_id":row["revision_id"],"record_sha256":row["record_sha256"]}
                if isinstance(rtype, str) and rtype.strip(): indexes["by_relation_type"].setdefault(rtype.strip(), []).append(entry)
                if isinstance(target, str) and target.strip(): indexes["by_relation_target"].setdefault(target.strip(), []).append(entry)
    for view in indexes.values():
        for value in view:
            view[value].sort(key=lambda x:(x["memory_id"],x["revision_id"]))
    correction_sha = correction_meta["sha256"]
    generation_id = _sha(_canonical({"schema":INDEX_SCHEMA,"indexer":INDEXER_VERSION,"registry_sha256":registry_sha,"correction_registry_sha256":correction_sha,"correction_overlay_status":correction_status}))
    return {
        "schema_version":INDEX_SCHEMA,"indexer_version":INDEXER_VERSION,"generation_id":generation_id,
        "source_registry":{"path":"registry/memory_records.jsonl","sha256":registry_sha,"byte_count":len(registry_bytes),"record_count":len(rows)},
        "correction_registry":correction_meta,
        "coverage":{"status":"PARTIAL","records_indexed":len(records),"memory_ids":len(latest),"revisions_indexed":len(records),
                    "current_revisions":len(latest),"correction_overlay_applied":correction_status=="APPLIED",
                    "correction_overlay_status":correction_status},
        "current_revision_by_memory_id":dict(sorted(latest.items())),
        "records":records,"indexes":indexes,
        "warnings":["Index is derived; canonical records remain authoritative.",
                    ("No canonical edge-correction overlay source exists; corrections were not applied." if correction_status=="NOT_AVAILABLE_NO_CANONICAL_OVERLAY_SOURCE" else "Coverage remains partial because source/archive completeness is not established."),
                    "All accepted revisions are indexed; use current_revision_by_memory_id/current_revision flag for current views."]
    }

def _target_error(registry_path: Path, index_root: Path, corrections_path: Path):
    for path, allowed in ((Path(registry_path), DEFAULT_REGISTRY), (Path(index_root), DEFAULT_INDEX_ROOT), (Path(corrections_path), DEFAULT_CORRECTIONS)):
        resolved = path.resolve()
        try: resolved.relative_to(ROOT.resolve())
        except ValueError: continue
        if path.absolute() != allowed.absolute() or resolved != allowed.resolve():
            return f"repository paths are restricted to {allowed.relative_to(ROOT)}"
    if DEFAULT_REGISTRY.is_symlink() or DEFAULT_REGISTRY.parent.is_symlink() or DEFAULT_INDEX_ROOT.is_symlink() or DEFAULT_CORRECTIONS.is_symlink():
        return "canonical registry/index path cannot be a symlink"
    if DEFAULT_INDEX_ROOT.exists() and ((DEFAULT_INDEX_ROOT / "generations").is_symlink() or (DEFAULT_INDEX_ROOT / "CURRENT.json").is_symlink()):
        return "canonical index generations/CURRENT pointer cannot be a symlink"
    return None

@contextlib.contextmanager
def _lock(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as stream:
        if os.name == "nt":
            import msvcrt
            stream.seek(0,os.SEEK_END)
            if stream.tell()==0: stream.write(b"0"); stream.flush()
            stream.seek(0); msvcrt.locking(stream.fileno(),msvcrt.LK_LOCK,1)
            try: yield
            finally: stream.seek(0); msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)
        else:
            import fcntl
            fcntl.flock(stream.fileno(),fcntl.LOCK_EX)
            try: yield
            finally: fcntl.flock(stream.fileno(),fcntl.LOCK_UN)

def _atomic_write(path: Path, payload: bytes):
    fd, raw = tempfile.mkstemp(prefix=path.name+".tmp-",dir=path.parent); tmp=Path(raw)
    try:
        with os.fdopen(fd,"wb") as stream: stream.write(payload); stream.flush(); os.fsync(stream.fileno())
        os.replace(tmp,path)
        try:
            dfd=os.open(path.parent,os.O_RDONLY)
            try: os.fsync(dfd)
            finally: os.close(dfd)
        except OSError: pass
    finally: tmp.unlink(missing_ok=True)

def _read_pointer(index_root: Path):
    pointer_path=index_root/"CURRENT.json"
    if not pointer_path.is_file(): return None
    try: pointer=json.loads(pointer_path.read_text(encoding="utf-8"))
    except Exception as exc: raise ValueError(f"CURRENT pointer is invalid JSON: {exc}") from exc
    if not isinstance(pointer,dict): raise ValueError("CURRENT pointer must be an object")
    return pointer

def check_index_freshness(registry_path: Path=DEFAULT_REGISTRY,index_root: Path=DEFAULT_INDEX_ROOT,corrections_path: Path|None=None) -> dict:
    registry_path,index_root=Path(registry_path),Path(index_root)
    corrections_path=Path(corrections_path) if corrections_path is not None else registry_path.with_name("edge_corrections.jsonl")
    if not registry_path.is_file(): return {"status":"UNAVAILABLE","reason":"canonical memory registry is missing"}
    try:
        pointer=_read_pointer(index_root)
        if pointer is None: return {"status":"UNAVAILABLE","reason":"CURRENT index pointer is missing"}
        if pointer.get("schema_version") != "canonical-memory-index-pointer-v1":
            return {"status":"INVALID","reason":"unsupported CURRENT pointer schema"}
        rel = pointer.get("generation_file")
        if not isinstance(rel, str) or not rel or Path(rel).is_absolute() or ".." in Path(rel).parts:
            return {"status":"INVALID","reason":"unsafe generation_file in CURRENT pointer"}
        generation_path=(index_root/rel).resolve()
        if index_root.resolve() not in generation_path.parents:
            return {"status":"INVALID","reason":"generation path escapes index root"}
        if not generation_path.is_file(): return {"status":"INVALID","reason":"referenced index generation is missing"}
        payload=generation_path.read_bytes()
        if _sha(payload)!=pointer.get("index_sha256"): return {"status":"INVALID","reason":"index generation hash mismatch"}
        generation=json.loads(payload.decode("utf-8"))
        if generation.get("generation_id") != pointer.get("generation_id"):
            return {"status":"INVALID","reason":"CURRENT pointer generation ID mismatch"}
        live_sha=_sha(registry_path.read_bytes())
        if generation.get("source_registry",{}).get("sha256")!=live_sha or pointer.get("source_registry_sha256")!=live_sha:
            return {"status":"STALE","reason":"canonical memory registry changed after index generation","live_registry_sha256":live_sha,"indexed_registry_sha256":generation.get("source_registry",{}).get("sha256")}
        live_correction_sha=_sha(corrections_path.read_bytes()) if corrections_path.is_file() else None
        if generation.get("correction_registry",{}).get("sha256")!=live_correction_sha or pointer.get("correction_registry_sha256")!=live_correction_sha:
            return {"status":"STALE","reason":"edge correction registry changed after index generation","live_correction_registry_sha256":live_correction_sha,"indexed_correction_registry_sha256":generation.get("correction_registry",{}).get("sha256")}
        return {"status":"CURRENT_PARTIAL" if generation.get("coverage",{}).get("status")=="PARTIAL" else "CURRENT",
                "generation_id":generation.get("generation_id"),"source_registry_sha256":live_sha,
                "correction_overlay_status":generation.get("coverage",{}).get("correction_overlay_status")}
    except Exception as exc: return {"status":"INVALID","reason":str(exc)}

def refresh_canonical_index(registry_path: Path=DEFAULT_REGISTRY,index_root: Path=DEFAULT_INDEX_ROOT,*,corrections_path: Path|None=None,apply:bool=False) -> dict:
    registry_path,index_root=Path(registry_path),Path(index_root)
    corrections_path=Path(corrections_path) if corrections_path is not None else registry_path.with_name("edge_corrections.jsonl")
    error=_target_error(registry_path,index_root,corrections_path)
    if error: return {"status":"REJECTED","reason":error,"writes_performed":False}
    if not registry_path.is_file(): return {"status":"BLOCKED","reason":"canonical memory registry is missing","writes_performed":False}
    if not apply:
        try: payload=build_index_payload(registry_path.read_bytes(),corrections_path.read_bytes() if corrections_path.is_file() else None)
        except Exception as exc: return {"status":"BLOCKED","reason":str(exc),"writes_performed":False}
        return {"status":"DRY_RUN_READY","generation_id":payload["generation_id"],"records_indexed":payload["coverage"]["records_indexed"],
                "coverage_status":payload["coverage"]["status"],"correction_overlay_status":payload["coverage"]["correction_overlay_status"],
                "writes_performed":False}
    with _lock(registry_path.with_name(registry_path.name+".lock")):
      with _lock(corrections_path.with_name(corrections_path.name+".lock")):
       with _lock(index_root/".index.lock"):
        try:
            source_bytes=registry_path.read_bytes()
            correction_bytes=corrections_path.read_bytes() if corrections_path.is_file() else None
            payload=build_index_payload(source_bytes,correction_bytes)
        except Exception as exc:
            return {"status":"BLOCKED","reason":str(exc),"writes_performed":False}
        encoded=_canonical(payload)+b"\n"
        generation_id=payload["generation_id"]
        generation_rel=f"generations/{generation_id}.json"
        generation_path=index_root/generation_rel
        try:
            generation_path.parent.mkdir(parents=True,exist_ok=True)
            if generation_path.exists():
                if generation_path.read_bytes()!=encoded: return {"status":"CONFLICT","reason":"existing generation ID has different bytes","writes_performed":False}
            else: _atomic_write(generation_path,encoded)
            if _sha(registry_path.read_bytes())!=payload["source_registry"]["sha256"]:
                return {"status":"STALE_INPUT","reason":"canonical registry changed during index generation","writes_performed":False}
            live_correction_sha=_sha(corrections_path.read_bytes()) if corrections_path.is_file() else None
            if live_correction_sha!=payload["correction_registry"]["sha256"]:
                return {"status":"STALE_INPUT","reason":"edge correction registry changed during index generation","writes_performed":False}
            pointer={"schema_version":"canonical-memory-index-pointer-v1","generation_id":generation_id,
                     "generation_file":generation_rel,"index_sha256":_sha(encoded),
                     "source_registry_sha256":payload["source_registry"]["sha256"],"correction_registry_sha256":payload["correction_registry"]["sha256"],"coverage_status":payload["coverage"]["status"]}
            _atomic_write(index_root/"CURRENT.json",_canonical(pointer)+b"\n")
            return {"status":"BUILT_PARTIAL","generation_id":generation_id,"records_indexed":payload["coverage"]["records_indexed"],
                    "generation_file":str(generation_path),"pointer_file":str(index_root/"CURRENT.json"),
                    "correction_overlay_status":payload["coverage"]["correction_overlay_status"],"writes_performed":True}
        except Exception as exc:
            return {"status":"WRITE_FAILED","reason":str(exc),"writes_performed":False}

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check",action="store_true",help="check whether the current index matches the registry")
    parser.add_argument("--apply",action="store_true",help="publish a new index generation; default is dry-run")
    parser.add_argument("--registry-path",type=Path,default=DEFAULT_REGISTRY,help=argparse.SUPPRESS)
    parser.add_argument("--index-root",type=Path,default=DEFAULT_INDEX_ROOT,help=argparse.SUPPRESS)
    args=parser.parse_args(argv)
    if args.check: result=check_index_freshness(args.registry_path,args.index_root)
    else: result=refresh_canonical_index(args.registry_path,args.index_root,apply=args.apply)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0 if result["status"] in {"DRY_RUN_READY","BUILT_PARTIAL","CURRENT","CURRENT_PARTIAL"} else 2

if __name__=="__main__":
    raise SystemExit(main())
