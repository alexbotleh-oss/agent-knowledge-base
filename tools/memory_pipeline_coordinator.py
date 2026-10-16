#!/usr/bin/env python3
"""Resumable coordinator for source ingestion → approved memory → index → fresh restore."""
from __future__ import annotations
import argparse, contextlib, hashlib, json, os, tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from source_ingestion_runner import run_ingestion
from semantic_memory_registry import promote_memory_records
from edge_correction_registry import register_edge_correction
from canonical_memory_index import DEFAULT_INDEX_ROOT, DEFAULT_REGISTRY as DEFAULT_MEMORY_REGISTRY, refresh_canonical_index
from source_evidence_registry import DEFAULT_REGISTRY as DEFAULT_SOURCE_REGISTRY
from memory_aware_session_restore import build_memory_aware_packet
from validate_memory import validate_intake_manifest

ROOT=Path(__file__).resolve().parents[1]
DEFAULT_RUN_ROOT=ROOT/".runtime"/"memory_pipeline_runs"

def _canonical(value:Any)->bytes:
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")
def _sha(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()
def _now()->str:
    return datetime.now().astimezone().isoformat()
def _atomic_write(path:Path,payload:bytes):
    path.parent.mkdir(parents=True,exist_ok=True)
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

def _load_ledger(path:Path,run_id:str)->list[dict]:
    if not path.exists(): return []
    try: lines=path.read_text(encoding="utf-8").splitlines()
    except Exception as exc: raise ValueError(f"pipeline ledger cannot be read: {exc}") from exc
    events=[]; previous=None
    for n,line in enumerate(lines,1):
        if not line.strip(): raise ValueError(f"pipeline ledger has blank line {n}")
        try: event=json.loads(line)
        except Exception as exc: raise ValueError(f"pipeline ledger invalid JSON at line {n}") from exc
        if not isinstance(event,dict): raise ValueError(f"pipeline ledger event {n} must be an object")
        if event.get("sequence")!=n or event.get("run_id")!=run_id: raise ValueError(f"pipeline ledger sequence/run mismatch at line {n}")
        if event.get("previous_event_sha256")!=previous: raise ValueError(f"pipeline ledger chain broken at line {n}")
        recorded=event.get("event_sha256"); payload={k:v for k,v in event.items() if k!="event_sha256"}
        if not isinstance(recorded,str) or _sha(_canonical(payload))!=recorded: raise ValueError(f"pipeline ledger hash mismatch at line {n}")
        events.append(event); previous=recorded
    return events

def _projection(path:Path,events:list[dict]):
    latest={}
    for event in events:
        stage=event.get("stage")
        if stage: latest[stage]={"event_type":event.get("event_type"),"status":event.get("status"),"sequence":event.get("sequence")}
    value={"schema_version":"memory-pipeline-state-v1","run_id":events[-1]["run_id"] if events else None,
           "latest_event_sha256":events[-1]["event_sha256"] if events else None,"event_count":len(events),"stages":latest}
    _atomic_write(path,_canonical(value)+b"\n")

def _append_event(run_dir:Path,run_id:str,event_type:str,stage:str,status:str,details:dict)->dict:
    path=run_dir/"pipeline_events.jsonl"
    with _lock(run_dir/".pipeline.lock"):
        events=_load_ledger(path,run_id)
        event={"sequence":len(events)+1,"run_id":run_id,"event_type":event_type,"stage":stage,"status":status,
               "recorded_at":_now(),"details":details,
               "previous_event_sha256":events[-1]["event_sha256"] if events else None}
        event["event_sha256"]=_sha(_canonical(event))
        with path.open("ab") as stream: stream.write(_canonical(event)+b"\n"); stream.flush(); os.fsync(stream.fileno())
        events.append(event)
        try: _projection(run_dir/"pipeline_state.json",events)
        except OSError: pass
        return event

def _source_rows(path:Path)->list[dict]:
    if not path.is_file(): raise ValueError("source registry is unavailable")
    rows=[]
    for n,line in enumerate(path.read_text(encoding="utf-8").splitlines(),1):
        if not line.strip(): raise ValueError(f"source registry has blank line {n}")
        try: row=json.loads(line)
        except Exception as exc: raise ValueError(f"source registry invalid JSON at line {n}") from exc
        if not isinstance(row,dict) or not isinstance(row.get("source_record_id"),str): raise ValueError(f"invalid source record at line {n}")
        rows.append(row)
    return rows

def validate_provenance_links(manifest_path:Path,source_registry_path:Path)->dict:
    errors=validate_intake_manifest(Path(manifest_path))
    if errors: return {"status":"REJECTED","errors":errors,"resolved_refs":0}
    try:
        manifest=json.loads(Path(manifest_path).read_text(encoding="utf-8"))
        artifacts=[a for a in manifest.get("artifacts",[]) if a.get("kind")=="memory_records"]
        if len(artifacts)!=1: raise ValueError("exactly one memory_records artifact is required")
        artifact=artifacts[0]; artifact_path=(Path(manifest_path).resolve().parent/artifact["path"]).resolve()
        if Path(manifest_path).resolve().parent not in artifact_path.parents or not artifact_path.is_file(): raise ValueError("memory artifact path is invalid")
        raw=artifact_path.read_bytes()
        if _sha(raw)!=artifact.get("sha256"): raise ValueError("memory artifact hash differs from manifest")
        records=[json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
        sources=_source_rows(Path(source_registry_path))
    except Exception as exc: return {"status":"BLOCKED","errors":[str(exc)],"resolved_refs":0}
    resolved=0; missing=[]; ambiguous=[]
    for record in records:
        mid=record.get("memory_id","unknown"); revision=record.get("revision",{}).get("revision_id","unknown")
        refs=record.get("provenance")
        if not isinstance(refs,list) or not refs:
            missing.append({"memory_id":mid,"revision_id":revision,"reason":"provenance is empty"}); continue
        for ref in refs:
            if isinstance(ref,str): criteria={"source_record_id":ref} if ref.startswith("SRC-") else {"source_locator":ref}
            elif isinstance(ref,dict):
                criteria={k:ref[k] for k in ("source_record_id","source_locator","source_node_id","message_id") if isinstance(ref.get(k),str) and ref[k].strip()}
                if "message_id" in criteria: criteria["source_message_id"]=criteria.pop("message_id")
                for field in ("archive_id","conversation_id"):
                    if isinstance(ref.get(field),str) and ref[field].strip(): criteria[field]=ref[field]
            else: criteria={}
            primary=[k for k in ("source_record_id","source_locator","source_node_id","source_message_id") if k in criteria]
            if len(primary)!=1:
                missing.append({"memory_id":mid,"revision_id":revision,"reference":ref,"reason":"provenance needs exactly one stable source ID/locator"}); continue
            matches=[s for s in sources if all(s.get(k)==v for k,v in criteria.items())]
            content_hash=ref.get("content_hash") if isinstance(ref,dict) else None
            if content_hash not in (None,"unknown",""):
                if len(matches)==1 and matches[0].get("text_sha256")!=content_hash:
                    missing.append({"memory_id":mid,"revision_id":revision,"reference":ref,"reason":"content_hash does not match source text hash"}); continue
            if len(matches)==1: resolved+=1
            elif len(matches)==0: missing.append({"memory_id":mid,"revision_id":revision,"reference":ref,"reason":"source reference did not resolve"})
            else: ambiguous.append({"memory_id":mid,"revision_id":revision,"reference":ref,"match_count":len(matches)})
    status="RESOLVED" if not missing and not ambiguous else "BLOCKED"
    return {"status":status,"resolved_refs":resolved,"missing_refs":missing,"ambiguous_refs":ambiguous,
            "source_registry_sha256":_sha(Path(source_registry_path).read_bytes()) if Path(source_registry_path).is_file() else None,
            "memory_artifact_sha256":artifact.get("sha256")}

def _summary(result:dict,keep:tuple[str,...])->dict:
    return {k:result[k] for k in keep if k in result}

def run_memory_pipeline(
 snapshot_path:Path,run_root:Path,semantic_manifest:Path,semantic_approval_receipt:Path,
 *,repository:str,task_state:Path,handoff:Path,event_log:Path,ref:str|None=None,
 correction_input:Path|None=None,correction_approval_receipt:Path|None=None,
 intake_root:Path|None=None,source_registry_path:Path=DEFAULT_SOURCE_REGISTRY,
 memory_registry_path:Path=DEFAULT_MEMORY_REGISTRY,correction_registry_path:Path|None=None,
 index_root:Path=DEFAULT_INDEX_ROOT,apply:bool=False,fetch_json:Callable|None=None,
)->dict:
    snapshot_path,semantic_manifest,semantic_approval_receipt=map(Path,(snapshot_path,semantic_manifest,semantic_approval_receipt))
    correction_registry_path=Path(correction_registry_path) if correction_registry_path else Path(memory_registry_path).with_name("edge_corrections.jsonl")
    required=[snapshot_path,semantic_manifest,semantic_approval_receipt]
    if any(not p.is_file() for p in required): return {"status":"BLOCKED","reason":"snapshot, semantic manifest and approval receipt are required","writes_performed":False}
    if correction_input is not None and not Path(correction_input).is_file(): return {"status":"BLOCKED","reason":"correction input was supplied but is missing","writes_performed":False}
    if correction_approval_receipt is not None and not Path(correction_approval_receipt).is_file(): return {"status":"BLOCKED","reason":"correction approval receipt was supplied but is missing","writes_performed":False}
    try:
        fingerprint={
            "snapshot_sha256":_sha(snapshot_path.read_bytes()),
            "semantic_manifest_sha256":_sha(semantic_manifest.read_bytes()),
            "semantic_approval_sha256":_sha(semantic_approval_receipt.read_bytes()),
            "correction_input_sha256":_sha(Path(correction_input).read_bytes()) if correction_input and Path(correction_input).is_file() else None,
            "correction_approval_sha256":_sha(Path(correction_approval_receipt).read_bytes()) if correction_approval_receipt and Path(correction_approval_receipt).is_file() else None,
            "repository":repository,"ref":ref or "checkpoint-default",
            "source_registry_path":str(Path(source_registry_path).resolve()),
            "memory_registry_path":str(Path(memory_registry_path).resolve()),
            "correction_registry_path":str(Path(correction_registry_path).resolve()),
            "index_root":str(Path(index_root).resolve()),
        }
    except Exception as exc: return {"status":"BLOCKED","reason":str(exc),"writes_performed":False}
    run_id="PIPE-"+_sha(_canonical(fingerprint))[:24]
    run_dir=Path(run_root).resolve()/run_id
    run_dir.mkdir(parents=True,exist_ok=True)
    ledger_path=run_dir/"pipeline_events.jsonl"
    try: events=_load_ledger(ledger_path,run_id)
    except Exception as exc: return {"status":"BLOCKED_LEDGER_INVALID","run_id":run_id,"reason":str(exc),"writes_performed":False}
    if events:
        try:
            state=json.loads((run_dir/"pipeline_state.json").read_text(encoding="utf-8"))
        except Exception: state={}
        if state.get("latest_event_sha256")!=events[-1]["event_sha256"]:
            try: _projection(run_dir/"pipeline_state.json",events)
            except OSError: pass
    _append_event(run_dir,run_id,"PIPELINE_STARTED","pipeline","RUNNING",{"apply":apply,"input_fingerprint":fingerprint})
    results={}; canonical_writes=False
    if apply:
        missing_restore_files=[str(p) for p in (Path(task_state),Path(handoff),Path(event_log)) if not Path(p).is_file()]
        correction_approval_missing=False
        if correction_input is not None:
            try:
                correction_data=json.loads(Path(correction_input).read_text(encoding="utf-8"))
                correction_approval_missing=correction_data.get("status")=="accepted" and correction_approval_receipt is None
            except Exception:
                correction_data={}
        preflight_ok=True
        if missing_restore_files:
            _append_event(run_dir,run_id,"STAGE_RESULT","preflight","BLOCKED",{"missing_restore_files":missing_restore_files})
            preflight_ok=False
        elif correction_approval_missing:
            _append_event(run_dir,run_id,"STAGE_RESULT","preflight","BLOCKED",{"reason":"accepted correction requires --correction-approval-receipt"})
            preflight_ok=False
        else:
            preflight_ok=execute("semantic_preflight",lambda:promote_memory_records(semantic_manifest,semantic_approval_receipt,memory_registry_path,apply=False),
                {"DRY_RUN_READY"},("status","candidate_count","error","writes_performed"))
        if not preflight_ok:
            final={"status":"BLOCKED_AT_PREFLIGHT","run_id":run_id,"run_dir":str(run_dir),"ledger_path":str(ledger_path),
                   "staging_writes_performed":False,"canonical_writes_performed":False,"ledger_writes_performed":True,"writes_performed":False}
            _append_event(run_dir,run_id,"PIPELINE_RESULT","pipeline",final["status"],{"stages":{name:result.get("status","UNKNOWN") for name,result in results.items()}})
            final["stages"]={name:result.get("status","UNKNOWN") for name,result in results.items()}
            return final
    def execute(stage:str,func:Callable,success:set[str],summary_fields:tuple[str,...]):
        _append_event(run_dir,run_id,"STAGE_STARTED",stage,"RUNNING",{"apply":apply})
        try: result=func()
        except Exception as exc: result={"status":"ERROR","reason":str(exc),"writes_performed":False}
        status=str(result.get("status","UNKNOWN"))
        _append_event(run_dir,run_id,"STAGE_RESULT",stage,status,{"result":_summary(result,summary_fields)})
        results[stage]=result
        return status in success
    source_ok=execute("source_ingestion",lambda:run_ingestion(snapshot_path,Path(run_root)/"source_ingestion",
        intake_root=intake_root,registry_path=source_registry_path,apply=apply),
        {"SOURCE_REGISTERED_DOWNSTREAM_PENDING"} if apply else {"READY_FOR_SOURCE_REGISTRATION"},
        ("status","batch_id","registration_status","latest_event_sha256","writes_performed","error"))
    source_stage_writes=bool(results["source_ingestion"].get("writes_performed"))
    if not source_ok:
        final={"status":"BLOCKED_AT_SOURCE_INGESTION"}
    elif not apply:
        promotion_ok=execute("semantic_promotion",lambda:promote_memory_records(semantic_manifest,semantic_approval_receipt,memory_registry_path,apply=False),
            {"DRY_RUN_READY"},("status","candidate_count","error","writes_performed"))
        promotion=results["semantic_promotion"]
        if correction_input:
            execute("edge_correction",lambda:register_edge_correction(correction_input,memory_registry_path,correction_registry_path,
                approval_receipt_path=correction_approval_receipt,apply=False),
                {"DRY_RUN_READY"},("status","correction_id","reason","writes_performed"))
        correction_ok=not correction_input or results["edge_correction"].get("status")=="DRY_RUN_READY"
        final={"status":"DRY_RUN_READY" if promotion_ok and correction_ok else "BLOCKED_AT_SEMANTIC_PREFLIGHT"}
        final["index_status"]="NOT_RUN_IN_DRY_RUN"
    else:
        provenance=validate_provenance_links(semantic_manifest,source_registry_path)
        results["provenance_validation"]=provenance
        _append_event(run_dir,run_id,"STAGE_RESULT","provenance_validation",provenance.get("status","UNKNOWN"),{"result":_summary(provenance,("status","resolved_refs","missing_refs","ambiguous_refs","errors","source_registry_sha256","memory_artifact_sha256"))})
        if provenance.get("status")!="RESOLVED":
            final={"status":"BLOCKED_AT_PROVENANCE_VALIDATION","provenance_validation":provenance}
        else:
            promotion_ok=execute("semantic_promotion",lambda:promote_memory_records(semantic_manifest,semantic_approval_receipt,memory_registry_path,apply=True),
                {"PROMOTED","ALREADY_PROMOTED"},("status","batch_id","decision_id","promoted_count","already_present","error","writes_performed"))
            canonical_writes=bool(results["semantic_promotion"].get("writes_performed"))
            if not promotion_ok:
                final={"status":"BLOCKED_AT_SEMANTIC_PROMOTION"}
            else:
                correction_ok=True
                if correction_input:
                    correction_ok=execute("edge_correction",lambda:register_edge_correction(correction_input,memory_registry_path,correction_registry_path,
                        approval_receipt_path=correction_approval_receipt,apply=True),
                        {"APPENDED","ALREADY_REGISTERED"},("status","correction_id","reason","writes_performed"))
                    canonical_writes=canonical_writes or bool(results["edge_correction"].get("writes_performed"))
                else:
                    results["edge_correction"]={"status":"NOT_REQUESTED","writes_performed":False}
                    _append_event(run_dir,run_id,"STAGE_RESULT","edge_correction","NOT_REQUESTED",{"reason":"no correction input supplied"})
                if not correction_ok:
                    final={"status":"BLOCKED_AT_EDGE_CORRECTION"}
                else:
                    index_ok=execute("canonical_index",lambda:refresh_canonical_index(memory_registry_path,index_root,
                        corrections_path=correction_registry_path,apply=True),
                        {"BUILT_PARTIAL","BUILT"},("status","generation_id","records_indexed","correction_overlay_status","reason","writes_performed"))
                    canonical_writes=canonical_writes or bool(results["canonical_index"].get("writes_performed"))
                    if not index_ok:
                        final={"status":"BLOCKED_AT_CANONICAL_INDEX"}
                    else:
                        kwargs={}
                        if fetch_json is not None: kwargs["fetch_json"]=fetch_json
                        packet=build_memory_aware_packet(task_state,handoff,event_log,repository,ref,
                            registry_path=memory_registry_path,index_root=index_root,**kwargs)
                        results["session_restore"]=packet
                        mem=packet.get("semantic_memory",{})
                        restore_summary={"status":packet.get("status"),"task_restore_status":packet.get("task_restore_status",packet.get("status")),
                            "semantic_memory_status":mem.get("status"),"coverage_status":mem.get("coverage_status"),
                            "index_generation_id":mem.get("index_generation_id"),"returned_count":mem.get("returned_count"),
                            "repository_revision_evidence":packet.get("repository_revision_evidence")}
                        _append_event(run_dir,run_id,"STAGE_RESULT","session_restore",packet.get("status","UNKNOWN"),{"result":restore_summary})
                        if packet.get("status") in {"RESTORED_PACKET_WITH_PARTIAL_MEMORY","RESTORED_PACKET_WITH_PARTIAL_MEMORY_NO_MATCH","RESTORED_PACKET_WITH_SEMANTIC_MEMORY","PARTIAL_WITH_SEMANTIC_MEMORY","PARTIAL_WITH_SEMANTIC_MEMORY_NO_MATCH"}:
                            final={"status":"PIPELINE_COMPLETE_WITH_PARTIAL_MEMORY","restore":restore_summary}
                        elif packet.get("status")=="RESTORED_PACKET_WITH_MEMORY_UNAVAILABLE":
                            final={"status":"PIPELINE_RESTORE_MEMORY_UNAVAILABLE","restore":restore_summary}
                        else:
                            final={"status":"PIPELINE_RESTORE_NOT_VERIFIED","restore":restore_summary}
    final.update({"run_id":run_id,"run_dir":str(run_dir),"ledger_path":str(ledger_path),
                  "source_stage_writes_performed":source_stage_writes,"canonical_writes_performed":canonical_writes,
                  "ledger_writes_performed":True,"writes_performed":source_stage_writes or canonical_writes})
    _append_event(run_dir,run_id,"PIPELINE_RESULT","pipeline",final["status"],
        {"stages":{name:result.get("status","UNKNOWN") for name,result in results.items()},
         "source_stage_writes_performed":source_stage_writes,"canonical_writes_performed":canonical_writes})
    final["stages"]={name:result.get("status","UNKNOWN") for name,result in results.items()}
    return final

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot",type=Path); parser.add_argument("--run-root",type=Path,required=True)
    parser.add_argument("--semantic-manifest",type=Path,required=True); parser.add_argument("--semantic-approval-receipt",type=Path,required=True)
    parser.add_argument("--repository",required=True); parser.add_argument("--task-state",type=Path,required=True)
    parser.add_argument("--handoff",type=Path,required=True); parser.add_argument("--event-log",type=Path,required=True)
    parser.add_argument("--ref"); parser.add_argument("--correction-input",type=Path); parser.add_argument("--correction-approval-receipt",type=Path)
    parser.add_argument("--intake-root",type=Path); parser.add_argument("--source-registry",type=Path,default=DEFAULT_SOURCE_REGISTRY,help=argparse.SUPPRESS)
    parser.add_argument("--memory-registry",type=Path,default=DEFAULT_MEMORY_REGISTRY,help=argparse.SUPPRESS)
    parser.add_argument("--correction-registry",type=Path,default=None,help=argparse.SUPPRESS)
    parser.add_argument("--index-root",type=Path,default=DEFAULT_INDEX_ROOT,help=argparse.SUPPRESS)
    parser.add_argument("--apply",action="store_true",help="execute canonical writes; default performs preflight/dry-run")
    args=parser.parse_args(argv)
    result=run_memory_pipeline(args.snapshot,args.run_root,args.semantic_manifest,args.semantic_approval_receipt,
        repository=args.repository,task_state=args.task_state,handoff=args.handoff,event_log=args.event_log,ref=args.ref,
        correction_input=args.correction_input,correction_approval_receipt=args.correction_approval_receipt,
        intake_root=args.intake_root,source_registry_path=args.source_registry,memory_registry_path=args.memory_registry,
        correction_registry_path=args.correction_registry,index_root=args.index_root,apply=args.apply)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0 if result.get("status") in {"DRY_RUN_READY","PIPELINE_COMPLETE_WITH_PARTIAL_MEMORY"} else 2
if __name__=="__main__": raise SystemExit(main())
