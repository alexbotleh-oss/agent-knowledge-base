#!/usr/bin/env python3
"""Compose verified task recovery with freshness-checked semantic-memory retrieval."""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
from typing import Any, Callable
from canonical_memory_index import DEFAULT_INDEX_ROOT, DEFAULT_REGISTRY, check_index_freshness
from verified_session_restore import build_verified_session_packet, request_json

def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")

def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def _registry(data: bytes) -> dict[tuple[str,str], dict]:
    try: lines=data.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc: raise ValueError("canonical memory registry is not UTF-8") from exc
    rows={}
    for n,line in enumerate(lines,1):
        if not line.strip(): raise ValueError(f"blank registry line {n}")
        try: row=json.loads(line)
        except Exception as exc: raise ValueError(f"invalid registry JSON at line {n}") from exc
        if not isinstance(row,dict) or not isinstance(row.get("record"),dict): raise ValueError(f"invalid registry envelope at line {n}")
        if row.get("lifecycle_status")!="accepted": raise ValueError(f"non-accepted registry envelope at line {n}")
        if _sha(_canonical(row["record"]))!=row.get("record_sha256"): raise ValueError(f"record hash mismatch at line {n}")
        key=(row.get("memory_id"),row.get("revision_id"))
        if not all(isinstance(v,str) and v for v in key): raise ValueError(f"invalid identity at line {n}")
        if key in rows: raise ValueError(f"duplicate memory revision at line {n}")
        rows[key]=row
    return rows

def retrieve_approved_memory(project_id:str,*,task_id:str|None=None,context_id:str|None=None,
 query:str|None=None,limit:int=20,registry_path:Path=DEFAULT_REGISTRY,index_root:Path=DEFAULT_INDEX_ROOT)->dict:
    if not isinstance(project_id,str) or not project_id.strip():
        return {"status":"AMBIGUOUS_SCOPE","coverage_status":"UNKNOWN","records":[],"reason":"project_id is required"}
    if isinstance(limit,bool) or not isinstance(limit,int) or not 1<=limit<=100:
        return {"status":"INVALID","coverage_status":"UNKNOWN","records":[],"reason":"limit must be between 1 and 100"}
    registry_path,index_root=Path(registry_path),Path(index_root)
    freshness=check_index_freshness(registry_path,index_root)
    if freshness.get("status") not in {"CURRENT","CURRENT_PARTIAL"}:
        return {"status":freshness.get("status","INVALID"),"coverage_status":"UNKNOWN","records":[],
                "reason":freshness.get("reason","index freshness is not established"),"index_freshness":freshness,
                "warnings":["No conclusion about memory absence is possible from a stale or unavailable index."]}
    try:
        source_bytes=registry_path.read_bytes(); live_sha=_sha(source_bytes)
        if live_sha!=freshness.get("source_registry_sha256"):
            return {"status":"STALE","coverage_status":"UNKNOWN","records":[],"reason":"registry changed during retrieval"}
        pointer=json.loads((index_root/"CURRENT.json").read_text(encoding="utf-8"))
        rel=pointer.get("generation_file")
        if not isinstance(rel,str) or not rel or Path(rel).is_absolute() or any(part==chr(46)*2 for part in Path(rel).parts):
            raise ValueError("unsafe generation path in CURRENT pointer")
        generation_path=(index_root/rel).resolve()
        if index_root.resolve() not in generation_path.parents: raise ValueError("generation path escapes index root")
        gen_bytes=generation_path.read_bytes()
        if _sha(gen_bytes)!=pointer.get("index_sha256"): raise ValueError("index generation hash mismatch")
        generation=json.loads(gen_bytes.decode("utf-8"))
        if generation.get("source_registry",{}).get("sha256")!=live_sha: return {"status":"STALE","coverage_status":"UNKNOWN","records":[],"reason":"index source hash is stale"}
        canonical_rows=_registry(source_bytes)
    except Exception as exc:
        return {"status":"INVALID","coverage_status":"UNKNOWN","records":[],"reason":str(exc),"index_freshness":freshness}
    current=generation.get("current_revision_by_memory_id"); indexed=generation.get("records")
    if not isinstance(current,dict) or not isinstance(indexed,list):
        return {"status":"INVALID","coverage_status":"UNKNOWN","records":[],"reason":"index lacks current-revision map or records"}
    candidates=[]
    for ref in indexed:
        if not isinstance(ref,dict) or not ref.get("current_revision"): continue
        if project_id not in ref.get("project_ids",[]): continue
        if task_id and task_id not in ref.get("task_ids",[]): continue
        if context_id and context_id not in ref.get("context_ids",[]): continue
        key=(ref.get("memory_id"),ref.get("revision_id"))
        if current.get(key[0])!=key[1]: continue
        row=canonical_rows.get(key)
        if row is None or row.get("record_sha256")!=ref.get("record_sha256"):
            return {"status":"INVALID","coverage_status":"UNKNOWN","records":[],"reason":f"index reference cannot be resolved: {key}"}
        record=row["record"]
        if query and query.casefold() not in json.dumps(record,ensure_ascii=False,sort_keys=True).casefold(): continue
        candidates.append((ref,row))
    candidates.sort(key=lambda pair:(pair[0]["memory_id"],pair[0]["revision_id"]))
    matches=len(candidates); result=[]; contradictions=[]
    for ref,row in candidates[:limit]:
        rec=row["record"]
        result.append({
            "memory_id":row["memory_id"],"revision_id":row["revision_id"],"record_sha256":row["record_sha256"],
            "lifecycle_status":row["lifecycle_status"],"record_lifecycle_status":rec.get("lifecycle_status","unknown"),
            "evidence_status":rec.get("evidence_status","unknown"),
            "confidence":rec.get("confidence",rec.get("classification",{}).get("confidence") if isinstance(rec.get("classification"),dict) else None),
            "provenance":rec.get("provenance",[]),"relations":rec.get("relations",[]),"record":rec,
        })
        for relation in rec.get("relations",[]) if isinstance(rec.get("relations"),list) else []:
            if isinstance(relation,dict) and relation.get("type")=="contradicts":
                contradictions.append({"memory_id":row["memory_id"],"revision_id":row["revision_id"],"relation":relation})
    correction=generation.get("coverage",{}).get("correction_overlay_status","unknown")
    partial=freshness.get("status")=="CURRENT_PARTIAL" or correction!="APPLIED" or matches==0
    status="PARTIAL_NO_MATCH" if matches==0 else ("PARTIAL" if partial else "AVAILABLE")
    return {
        "status":status,"coverage_status":"PARTIAL" if partial else "COMPLETE","project_id":project_id,
        "filters":{"task_id":task_id,"context_id":context_id,"query":query,"limit":limit},
        "retrieval_method":"exact multidimensional filters plus lexical substring; no embedding/semantic ranking",
        "index_generation_id":generation.get("generation_id"),"source_registry_sha256":live_sha,
        "index_sha256":pointer.get("index_sha256"),"index_freshness":freshness,"correction_overlay_status":correction,
        "total_current_project_matches":matches,"returned_count":len(result),"records":result,
        "unresolved_contradictions":contradictions,
        "warnings":[] if not partial else [
            "Memory index coverage is partial; no canonical correction-overlay source was available.",
            "No match in the current partial index does not prove that no relevant memory exists.",
        ],
        "writes_performed":False,
    }

def build_memory_aware_packet(task_state:Path,handoff:Path,event_log:Path,repository:str,ref:str|None=None,
 *,fetch_json:Callable[[str],dict]=request_json,task_id:str|None=None,context_id:str|None=None,
 query:str|None=None,limit:int=20,registry_path:Path=DEFAULT_REGISTRY,index_root:Path=DEFAULT_INDEX_ROOT)->dict:
    packet=build_verified_session_packet(task_state,handoff,event_log,repository,ref,fetch_json=fetch_json)
    if packet.get("status") in {"BLOCKED","REVISION_CHECK_BLOCKED"}:
        packet["semantic_memory"]={"status":"NOT_ATTEMPTED","coverage_status":"UNKNOWN","records":[],"reason":"base restore is blocked","writes_performed":False}
        return packet
    scope=packet.get("project_scope",{})
    projects=[scope.get(k) for k in ("task_project_id","handoff_project_id","event_log_project_id")]
    if not all(isinstance(v,str) and v for v in projects) or len(set(projects))!=1:
        memory={"status":"AMBIGUOUS_SCOPE","coverage_status":"UNKNOWN","records":[],"reason":"task, handoff and event log do not establish one matching project scope","writes_performed":False}
    else:
        memory=retrieve_approved_memory(projects[0],task_id=task_id,context_id=context_id,query=query,limit=limit,
                                        registry_path=registry_path,index_root=index_root)
    packet["semantic_memory"]=memory
    if packet.get("status")=="PARTIAL": packet["status"]="PARTIAL_WITH_SEMANTIC_MEMORY"
    elif memory.get("status")=="AVAILABLE": packet["status"]="RESTORED_PACKET_WITH_SEMANTIC_MEMORY"
    elif memory.get("status")=="PARTIAL": packet["status"]="RESTORED_PACKET_WITH_PARTIAL_MEMORY"
    elif memory.get("status")=="PARTIAL_NO_MATCH": packet["status"]="RESTORED_PACKET_WITH_PARTIAL_MEMORY_NO_MATCH"
    else: packet["status"]="RESTORED_PACKET_WITH_MEMORY_UNAVAILABLE"
    packet.setdefault("warnings",[]).append("Semantic-memory retrieval is a separate layer; read its status and coverage independently from task/event restoration.")
    return packet

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task_state",type=Path); parser.add_argument("handoff",type=Path); parser.add_argument("event_log",type=Path)
    parser.add_argument("--repository",required=True,help="GitHub owner/repository")
    parser.add_argument("--ref"); parser.add_argument("--task-id"); parser.add_argument("--context-id")
    parser.add_argument("--query",help="literal lexical substring; not semantic ranking")
    parser.add_argument("--limit",type=int,default=20)
    parser.add_argument("--registry-path",type=Path,default=DEFAULT_REGISTRY,help=argparse.SUPPRESS)
    parser.add_argument("--index-root",type=Path,default=DEFAULT_INDEX_ROOT,help=argparse.SUPPRESS)
    args=parser.parse_args(argv)
    packet=build_memory_aware_packet(args.task_state,args.handoff,args.event_log,args.repository,args.ref,
      task_id=args.task_id,context_id=args.context_id,query=args.query,limit=args.limit,
      registry_path=args.registry_path,index_root=args.index_root)
    print(json.dumps(packet,ensure_ascii=False,indent=2))
    return 0 if packet.get("status") in {"RESTORED_PACKET_WITH_SEMANTIC_MEMORY","RESTORED_PACKET_WITH_PARTIAL_MEMORY","RESTORED_PACKET_WITH_PARTIAL_MEMORY_NO_MATCH","PARTIAL_WITH_SEMANTIC_MEMORY"} else 2

if __name__=="__main__": raise SystemExit(main())
