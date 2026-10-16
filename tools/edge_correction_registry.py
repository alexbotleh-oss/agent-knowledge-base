#!/usr/bin/env python3
"""Validate and append source-bound edge corrections; default operation is dry-run."""
from __future__ import annotations
import argparse, contextlib, hashlib, json, os, re, tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[1]
DEFAULT_SOURCE=ROOT/"registry"/"memory_records.jsonl"
DEFAULT_REGISTRY=ROOT/"registry"/"edge_corrections.jsonl"
ID_RE=re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,191}$")
HASH_RE=re.compile(r"^[0-9a-f]{64}$")
STATUSES={"candidate","accepted","disputed","rejected","superseded"}
ACTIONS={"add","retract","replace"}

def _canonical(value:Any)->bytes:
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")
def _sha(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()
def _aware(value:Any)->bool:
    if not isinstance(value,str) or not value.strip(): return False
    try:
        parsed=datetime.fromisoformat(value.strip().replace("Z","+00:00"))
        return parsed.tzinfo is not None and parsed.utcoffset() is not None
    except ValueError: return False
def _read_object(path:Path,label:str):
    before=path.read_bytes()
    try: value=json.loads(before.decode("utf-8"))
    except Exception as exc: raise ValueError(f"{label} is invalid UTF-8 JSON: {exc}") from exc
    if not isinstance(value,dict): raise ValueError(f"{label} must be a JSON object")
    if path.read_bytes()!=before: raise ValueError(f"{label} changed while read")
    return value,before
def _jsonl(data:bytes,label:str)->list[dict]:
    try: lines=data.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc: raise ValueError(f"{label} is not UTF-8") from exc
    rows=[]
    for n,line in enumerate(lines,1):
        if not line.strip(): raise ValueError(f"{label} has blank line {n}")
        try: row=json.loads(line)
        except Exception as exc: raise ValueError(f"{label} invalid JSON at line {n}") from exc
        if not isinstance(row,dict): raise ValueError(f"{label} line {n} must be an object")
        rows.append(row)
    return rows
def _relation(value:Any,label:str):
    if not isinstance(value,dict): raise ValueError(f"{label} must be an object")
    for field in ("type","target_id","basis","status"):
        if not isinstance(value.get(field),str) or not value[field].strip(): raise ValueError(f"{label}.{field} is required")
    if value.get("confidence") not in {"low","medium","high","unknown"}: raise ValueError(f"{label}.confidence is invalid")
    if value.get("status") not in STATUSES: raise ValueError(f"{label}.status is invalid")
    refs=value.get("source_refs")
    if not isinstance(refs,list) or not refs or any(not isinstance(v,str) or not v.strip() for v in refs):
        raise ValueError(f"{label}.source_refs must be non-empty strings")
def _load_source(source_path:Path):
    if not source_path.is_file(): raise ValueError("canonical memory registry is missing")
    data=source_path.read_bytes(); rows=_jsonl(data,"canonical memory registry"); found={}
    for n,row in enumerate(rows,1):
        rec=row.get("record")
        if not isinstance(rec,dict) or _sha(_canonical(rec))!=row.get("record_sha256"):
            raise ValueError(f"canonical memory registry record hash mismatch at line {n}")
        key=(row.get("memory_id"),row.get("revision_id"))
        if key in found: raise ValueError(f"duplicate canonical memory revision {key}")
        found[key]=row
    return data,found
def _validate_correction(c:dict,source_rows:dict):
    required=("schema_version","correction_id","action","status","source_memory_id","source_revision_id","source_record_sha256","recorded_at","rationale","source_refs")
    missing=[k for k in required if k not in c]
    if missing: raise ValueError("correction missing fields: "+", ".join(missing))
    if c.get("schema_version")!="edge-correction-v1": raise ValueError("unsupported correction schema_version")
    for field in ("correction_id","source_memory_id","source_revision_id"):
        if not isinstance(c.get(field),str) or not ID_RE.fullmatch(c[field]): raise ValueError(f"invalid {field}")
    if c.get("action") not in ACTIONS or c.get("status") not in STATUSES: raise ValueError("invalid correction action/status")
    if not HASH_RE.fullmatch(str(c.get("source_record_sha256",""))): raise ValueError("invalid source_record_sha256")
    if not _aware(c.get("recorded_at")): raise ValueError("recorded_at must be timezone-aware ISO-8601")
    if not isinstance(c.get("rationale"),str) or not c["rationale"].strip(): raise ValueError("rationale is required")
    refs=c.get("source_refs")
    if not isinstance(refs,list) or not refs or any(not isinstance(v,str) or not v.strip() for v in refs): raise ValueError("source_refs must be non-empty strings")
    key=(c["source_memory_id"],c["source_revision_id"]); envelope=source_rows.get(key)
    if envelope is None: raise ValueError("correction source memory revision does not exist")
    if envelope.get("record_sha256")!=c["source_record_sha256"]: raise ValueError("correction source record hash is stale")
    record=envelope["record"]; relations=record.get("relations",[])
    if not isinstance(relations,list): raise ValueError("source record relations must be a list")
    action=c["action"]; target=c.get("target_relation_sha256")
    if action=="add":
        if target is not None: raise ValueError("add correction must not set target_relation_sha256")
        _relation(c.get("relation"),"relation")
        digest=_sha(_canonical(c["relation"]))
        if any(isinstance(item,dict) and _sha(_canonical(item))==digest for item in relations): raise ValueError("added relation already exists in source record")
    else:
        if not isinstance(target,str) or not HASH_RE.fullmatch(target): raise ValueError("retract/replace requires target_relation_sha256")
        matches=[item for item in relations if isinstance(item,dict) and _sha(_canonical(item))==target]
        if len(matches)!=1: raise ValueError("target relation fingerprint is missing or ambiguous in the bound source revision")
        if action=="replace": _relation(c.get("replacement_relation"),"replacement_relation")
    return envelope
def _load_input(correction_path:Path,receipt_path:Path|None,source_path:Path):
    correction_path=Path(correction_path).resolve()
    c,cbytes=_read_object(correction_path,"correction")
    source_bytes,source_rows=_load_source(Path(source_path))
    _validate_correction(c,source_rows)
    receipt=None; receipt_bytes=None
    if c["status"]=="accepted":
        if receipt_path is None or not Path(receipt_path).is_file(): raise ValueError("accepted correction requires an approval receipt")
        receipt,receipt_bytes=_read_object(Path(receipt_path).resolve(),"approval receipt")
        required=("schema_version","decision_id","decision","actor_type","actor_ref","decided_at","correction_id","correction_sha256","decision_source_ref","rationale")
        missing=[k for k in required if k not in receipt]
        if missing: raise ValueError("approval receipt missing fields: "+", ".join(missing))
        if receipt.get("schema_version")!="edge-correction-approval-v1" or receipt.get("decision")!="approve" or receipt.get("actor_type")!="user":
            raise ValueError("approval receipt does not contain an explicit user approval")
        if not isinstance(receipt.get("decision_id"),str) or not receipt["decision_id"].strip(): raise ValueError("approval decision_id is required")
        for field in ("actor_ref","decision_source_ref","rationale"):
            if not isinstance(receipt.get(field),str) or not receipt[field].strip(): raise ValueError(f"approval {field} is required")
        if not _aware(receipt.get("decided_at")): raise ValueError("approval decided_at must be timezone-aware ISO-8601")
        if receipt.get("correction_id")!=c["correction_id"] or receipt.get("correction_sha256")!=_sha(cbytes):
            raise ValueError("approval receipt is not bound to these exact correction bytes")
        if c.get("decision_id")!=receipt.get("decision_id") or c.get("decision_source_ref")!=receipt.get("decision_source_ref"):
            raise ValueError("correction decision reference differs from approval receipt")
    if correction_path.read_bytes()!=cbytes: raise ValueError("correction changed during validation")
    if receipt_path and receipt_bytes is not None and Path(receipt_path).read_bytes()!=receipt_bytes: raise ValueError("approval receipt changed during validation")
    if Path(source_path).read_bytes()!=source_bytes: raise ValueError("source registry changed during validation")
    return {"correction":c,"correction_bytes":cbytes,"correction_sha256":_sha(cbytes),"source_sha256":_sha(source_bytes),
            "receipt":receipt,"receipt_sha256":_sha(receipt_bytes) if receipt_bytes is not None else None}
def _target_error(path:Path):
    path=Path(path); resolved=path.resolve()
    try: resolved.relative_to(ROOT.resolve())
    except ValueError: return None
    if path.absolute()!=DEFAULT_REGISTRY.absolute() or resolved!=DEFAULT_REGISTRY.resolve():
        return "repository writes are restricted to registry/edge_corrections.jsonl"
    if DEFAULT_REGISTRY.is_symlink() or DEFAULT_REGISTRY.parent.is_symlink(): return "edge correction registry path cannot be a symlink"
    return None
def _load_registry(path:Path):
    if not path.exists(): return [],{}
    rows=_jsonl(path.read_bytes(),"edge correction registry"); byid={}
    for n,row in enumerate(rows,1):
        correction=row.get("correction")
        if row.get("registry_schema_version")!="edge-correction-registry-v1" or not isinstance(correction,dict):
            raise ValueError(f"invalid correction envelope at line {n}")
        digest=_sha(_canonical(correction))
        if digest!=row.get("correction_sha256"): raise ValueError(f"correction hash mismatch at line {n}")
        cid=correction.get("correction_id")
        if not isinstance(cid,str) or not cid: raise ValueError(f"missing correction_id at line {n}")
        if cid in byid: raise ValueError(f"duplicate correction_id {cid}")
        byid[cid]=row
    return rows,byid
@contextlib.contextmanager
def _lock(path:Path):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("a+b") as stream:
        if os.name=="nt":
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
def _atomic_write(path:Path,rows:list[dict]):
    payload=b"".join(_canonical(row)+b"\n" for row in rows)
    fd,raw=tempfile.mkstemp(prefix=path.name+".tmp-",dir=path.parent); tmp=Path(raw)
    try:
        with os.fdopen(fd,"wb") as stream: stream.write(payload); stream.flush(); os.fsync(stream.fileno())
        os.replace(tmp,path)
        try:
            dfd=os.open(path.parent,os.O_RDONLY)
            try: os.fsync(dfd)
            finally: os.close(dfd)
        except OSError: pass
    finally: tmp.unlink(missing_ok=True)
def register_edge_correction(correction_path:Path,source_path:Path=DEFAULT_SOURCE,registry_path:Path=DEFAULT_REGISTRY,
 *,approval_receipt_path:Path|None=None,apply:bool=False)->dict:
    try: batch=_load_input(Path(correction_path),Path(approval_receipt_path) if approval_receipt_path else None,Path(source_path))
    except Exception as exc: return {"status":"REJECTED","reason":str(exc),"writes_performed":False}
    registry_path=Path(registry_path); error=_target_error(registry_path)
    if error: return {"status":"REJECTED","reason":error,"writes_performed":False}
    c=batch["correction"]
    if not apply: return {"status":"DRY_RUN_READY","correction_id":c["correction_id"],"status_to_record":c["status"],"writes_performed":False}
    registry_path.parent.mkdir(parents=True,exist_ok=True)
    with _lock(Path(source_path).with_name(Path(source_path).name+".lock")):
      with _lock(registry_path.with_name(registry_path.name+".lock")):
        try: current=_load_input(Path(correction_path),Path(approval_receipt_path) if approval_receipt_path else None,Path(source_path))
        except Exception as exc: return {"status":"REJECTED","reason":str(exc),"writes_performed":False}
        for key in ("correction_sha256","source_sha256","receipt_sha256"):
            if current[key]!=batch[key]: return {"status":"STALE_INPUT","reason":f"{key} changed before append","writes_performed":False}
        try: rows,byid=_load_registry(registry_path)
        except Exception as exc: return {"status":"CONFLICT","reason":str(exc),"writes_performed":False}
        prior=byid.get(c["correction_id"])
        if prior:
            if prior["correction_sha256"]!=batch["correction_sha256"]: return {"status":"CONFLICT","reason":"same correction_id has different content","writes_performed":False}
            return {"status":"ALREADY_REGISTERED","correction_id":c["correction_id"],"writes_performed":False}
        envelope={"registry_schema_version":"edge-correction-registry-v1","correction_id":c["correction_id"],
                  "correction_sha256":batch["correction_sha256"],"correction":c,
                  "approval_receipt_sha256":batch["receipt_sha256"],"source_registry_sha256":batch["source_sha256"],
                  "registered_at":datetime.now().astimezone().isoformat()}
        try: _atomic_write(registry_path,[*rows,envelope])
        except Exception as exc: return {"status":"WRITE_FAILED","reason":str(exc),"writes_performed":False}
        return {"status":"APPENDED","correction_id":c["correction_id"],"writes_performed":True}
def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("correction",type=Path)
    parser.add_argument("--source-registry",type=Path,default=DEFAULT_SOURCE,help=argparse.SUPPRESS)
    parser.add_argument("--registry-path",type=Path,default=DEFAULT_REGISTRY,help=argparse.SUPPRESS)
    parser.add_argument("--approval-receipt",type=Path)
    parser.add_argument("--apply",action="store_true",help="append validated correction; default is read-only")
    args=parser.parse_args(argv)
    result=register_edge_correction(args.correction,args.source_registry,args.registry_path,
      approval_receipt_path=args.approval_receipt,apply=args.apply)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0 if result["status"] in {"DRY_RUN_READY","APPENDED","ALREADY_REGISTERED"} else 2
if __name__=="__main__": raise SystemExit(main())
