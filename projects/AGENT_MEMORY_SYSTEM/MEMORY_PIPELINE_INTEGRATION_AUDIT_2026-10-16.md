# Memory pipeline integration audit — 2026-10-16

## Scope and revision

This audit follows P1 revision-restore completion. It inspects the repository at branch `integration/memory-core-clean-20261015`, audited HEAD `95524a90a4e1b024e237e7a49e1d4be9c795a433`, with exact-head workflow run [38849636651](https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/38849636651) completed successfully. This is a read-only code/contract audit; it does not claim that the local CLI was executed against GitHub from this session.

Target path:

`immutable source → staging/intake → source registry → approval/review → semantic promotion → canonical index refresh → normal session restore`

## Findings by stage

| Stage | Evidence at audited revision | Status |
|---|---|---|
| Immutable source snapshot / staging | `tools/resumable_chat_import.py`, `tools/archive_registry_staging.py`; snapshot and extracted records retain source hashes/IDs and structural context. | Implemented; archive coverage and attachment payload completeness remain separate reconciliation concerns. |
| Intake adaptation and validation | `tools/adapt_archive_staging_to_intake.py`, `tools/validate_memory.py`, `schemas/memory_intake_manifest.schema.json`. Manifest validates artifact paths/hashes/counts, lifecycle/evidence/approval enums and approval evidence for accepted artifacts. | Implemented for intake contract. `IMPORT_READY` is explicitly not approval. |
| Route planning | `tools/plan_memory_intake.py` maps memory artifacts to candidate/disputed/historical logical views, but returns a dry-run proposal and explicitly says canonical records/indexes are not changed. | Planner only; no writer for memory artifacts. |
| Metadata-only source registration | `tools/source_ingestion_runner.py` routes one `source_records` artifact to `tools/source_evidence_registry.py`. The runner's event ledger is hash-chained and its state projection is recoverable. Tests cover dry-run, replay, registry-commit crash recovery, projection rebuild and tampered-ledger blocking. | Implemented through `SOURCE_REGISTERED_DOWNSTREAM_PENDING`. The writer deliberately does not assign project ownership or promote semantic memory. |
| Candidate approval | Intake schema has `not_requested/pending/user_approved/user_rejected`; accepted lifecycle requires `user_approved` and `approval_evidence`. Planner routes an approved+accepted memory artifact to `prepare_approved_record_for_review`. | **No complete approval workflow/executor verified.** A field value and route label are not proof of a user decision, review event, or promotion. |
| Semantic promotion / canonical memory registry | At this revision, tracked paths include the source registry contract but no tracked `registry/source_records.jsonl` or `registry/memory_records.jsonl` data file was found; README says source registry is created only by explicit `--apply`. No promotion writer/executor was found in the repository tree. | **Not implemented as an end-to-end path.** Existing schemas/templates define shapes, not a durable approved-record commit protocol. |
| Canonical multidimensional index | `core/memory_registry_and_multidimensional_index.md` defines a target architecture and explicitly warns that it is a data contract, not proof that indexers exist. `tools/archive_temporal_index.py` is a read-only index over a ChatGPT export, not a rebuildable index over canonical approved memory records. | **Canonical memory index refresh not implemented/verified.** No duplicate per-view copies should be created; views should be derived from one linked registry. |
| Normal session restore | `tools/restore_session_packet.py` restores TASK_STATE/HANDOFF and explicitly linked events; `tools/verified_session_restore.py` adds live branch/CI evidence. Neither loads approved semantic memory records or queries a canonical memory index. | **Task/event recovery exists; ingestion-to-semantic-memory session restore is not verified.** |

## Confirmed invariants to preserve

1. Keep the immutable raw snapshot separate from source metadata and semantic interpretations.
2. Keep raw source records project-neutral until project attribution has explicit evidence.
3. Preserve stable source/message/node IDs, source hashes, parser versions, parent/child relations, and distinct `source_time`, `event_time`, and `recorded_at`.
4. Candidate, approved, rejected, disputed, superseded and deprecated states must remain distinguishable. An `IMPORT_READY` manifest is not authorization.
5. Promotion must be append-only/versioned: retain previous interpretations and rejection/conflict history; do not overwrite source evidence.
6. Preserve relations/provenance to primary source records. Missing/ambiguous references must remain explicit, not be guessed from text similarity.
7. Indexes are derived/rebuildable views over canonical linked records, never the only copy of knowledge.
8. Restore must state what was actually loaded and whether coverage is complete/partial/unknown. Do not equate a valid task checkpoint with complete semantic memory.
9. Consume append-only correction overlays such as `edge_corrections` in any graph/index consumer; current event records warn that consumers must apply them, and no universal overlay consumer was verified in this audit.
10. Keep the existing branch/PR boundary: PR #27 Draft/open/unmerged; do not change `main`.

## Integration gaps and required contracts

### A. Approval evidence contract
An approval decision needs a stable decision/event ID, explicit actor/source, timestamp (with precision/timezone), exact candidate batch/artifact/record revision hashes, decision (`approve|reject|request_changes`), scope, and rationale/evidence reference. A manifest's `user_approved` string alone is insufficient unless the referenced decision can be resolved and verified. Approval must be bound to exact candidate bytes; changed hashes return a stale-candidate result, not approval.

### B. Semantic promotion contract
A guarded promotion operation should:
- validate the manifest and every referenced artifact against hashes/schema/counts;
- require a resolvable approval decision bound to those exact bytes;
- preserve project-neutral raw records and only set project/task/topic relations when evidence supports them;
- write canonical memory record revisions and provenance/relation edges append-only;
- be idempotent for exact replay and fail closed on identity/hash conflicts;
- record a durable promotion event before reporting success, with recoverable status if registry/index projection is interrupted;
- keep candidate/rejected/disputed/historical records queryable without presenting them as accepted current knowledge.

### C. Canonical index refresh contract
Build deterministic, versioned indexes from canonical records rather than staging artifacts. Record source registry revision/hash, indexer/schema version, generation ID, record/relation counts, and validation result. Publish atomically (generation plus one commit pointer); preserve the prior good generation if rebuild fails. Rebuild must apply correction overlays and preserve multi-dimensional views without duplicate canonical records. Index freshness must be checked against canonical registry revision, not a manually asserted flag.

### D. Restore integration contract
A normal restore should compose, not replace, the existing task/event packet with a memory retrieval section:
- select only eligible accepted records by project/task/context and bounded relevance;
- include stable memory IDs, revision IDs, evidence status, confidence, source refs, and unresolved contradictions;
- report index generation and source registry revision used;
- report `COMPLETE|PARTIAL|AMBIGUOUS|UNAVAILABLE` coverage and why;
- fail closed or degrade explicitly if the index is stale/missing; never silently imply no memory exists;
- retain the existing live GitHub revision check as a separate code/CI trust dimension.

## Recommended next implementation boundary

Do **not** build one monolithic pipeline or let the current source-registration writer promote records. First implement and test the approval-bound semantic registry writer as a separate guarded stage with append-only revisions, replay/conflict behavior, and crash recovery. Then add deterministic canonical-index generation from that registry. Only after both have stable contracts should the normal restore packet consume approved memory and expose coverage/freshness.

This ordering keeps the source ingestion boundary intact and makes each transition independently auditable. It is a recommendation derived from the code audit, not a claim that these stages already exist.

## Evidence limitation

This audit is based on tracked code, schemas, documentation, tests, and GitHub metadata at the stated revision. It did not process a real user archive through the full pipeline because the pipeline stops before semantic promotion. It did not prove completeness of any private/local runtime registry or archive payload. The current exact-head CI pass validates the repository checks, not the missing downstream stages.
