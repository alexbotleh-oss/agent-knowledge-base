# Memory repository write-path inventory and operation contracts

Status: initial static inventory, based on the implementation in this branch. This is not a claim that every path is safe, race-free, or fully integration-tested. Re-run `python tools/audit_write_contracts.py` after adding or changing persistence code.

## Trust and evidence model

- A recovery packet is a source-backed snapshot, not proof that all conversation history was captured.
- Semantic extraction must preserve UNKNOWN and provenance rather than infer a missing goal or next action.
- `context_trust_gate.authorize_next_step` is a policy decision, not an executor and not a cryptographic signature.
- Any canonical task-state mutation must validate the proposal, source revision, event evidence and current context; no-write outcomes may report conflicts/stale revisions before the gate, but a write must remain blocked unless the gate authorizes it.
- External trust verdict JSON is caller-supplied input, not independent proof of origin. Recompute the gate from canonical sources immediately before mutation.
- A lock must cover the final revision/evidence/trust checks and the write. Atomic replacement alone does not prevent lost updates or stale authorization.

## Known write paths

| Path / operation | Persisted target | Current contract / review notes |
| --- | --- | --- |
| `tools/guarded_task_state_update.py:apply_checkpoint` | `projects/*/TASK_STATE.md` | Append-only checkpoint; restricts target name/path; validates proposal, expected SHA-256, event ID; duplicate ID is idempotent or conflict; requires external authorized verdict and recomputes trust from canonical files; uses lock and temp-file + fsync + replace. The final trust/event recheck is intended to be under the task-state lock. Event-log writers use a separate lock; cross-file snapshot consistency remains a race to review. |
| `tools/branch_result_registry.py:publish_result` | `projects/*/events.jsonl` | Validates result envelope, stable event ID, exact replay no-op, same-ID/different-content conflict, append-only event representation, lock and atomic replacement. |
| `tools/branch_result_registry.py:acknowledge_result` | `projects/*/events.jsonl` | Requires an existing child-result event and explicit decision/reference; appends linked acknowledgement, does not edit task state. Replay identity uses result ID + owner reference. |
| `tools/archive_registry_staging.py:build` | staging record files and `archive_snapshot.json` | Reads export, hashes original bytes, generates source locators and staging records. It does not itself authorize canonical memory import. Review whether every manifest write is atomic and whether reruns safely reconcile existing staging output. |
| `tools/resumable_chat_import.py:immutable_snapshot` | import snapshot directory | Captures an immutable source snapshot and digest before parsing. Verify cleanup, concurrent invocation and existing-target collision behaviour. |
| `tools/resumable_chat_import.py:connect / _commit_batch / import_export` | SQLite import database | Uses SQLite as resumable storage. The database is not equivalent to canonical TASK_STATE; inspect transaction boundaries, uniqueness constraints, resume cursor and crash recovery when changing this code. |
| `tools/archive_temporal_index.py` | derived temporal index | Derived data must retain source provenance and be rebuildable; inspect actual target path before treating it as canonical. |
| `tools/reconcile_branch_returns.py` | reconciliation report | Intended as derived output. Report generation must not silently accept a child result or update canonical task state. |
| `tools/validate_memory.py` | validation output, if configured | Validation/reporting is distinct from authorization. Keep generated reports separate from canonical source files. |
| `tools/plan_memory_intake.py` | planning output, if configured | A plan/proposal is not permission to write canonical memory. |

## Operation contracts

### Canonical task checkpoint
Preconditions: canonical task state, HANDOFF and event journal exist; proposal schema and target path are valid; expected hash matches; supporting event exists; current source hashes are fresh; semantic goal and explicit next step are known; history-dependent operation has complete event linkage; trust gate returns `AUTHORIZED_FOR_PLANNING`.

Commit: lock, reread expected revision, recompute trust from current canonical sources, revalidate event evidence, append one idempotently marked checkpoint via same-directory temporary file and atomic replace.

No-write results: `REJECTED`, `STALE_REVISION`, `LOCKED`, `CONFLICT`, `ALREADY_APPLIED`, or `BLOCKED`. The caller must not reinterpret these as successful persistence.

### Child-result publication and acknowledgement
Publication records what a child reports; it does not mean the parent accepted it. Stable identity enables exact replay and conflict detection. Owner acknowledgement is a separate append-only event linked to the result. An acknowledgement is evidence of a decision, not proof that the parent task is complete. Parent state changes remain a separate gated checkpoint operation.

### Archive staging and resumable import
Staging is not canonical memory. Preserve source digest, stable source locators, original temporal metadata and uncertainty. Do not collapse messages from separate conversations into an untraceable summary. Import must be resumable and idempotent across process restart; batch commits must not advance a cursor past records that were not durably committed. Source snapshots and imported records should be auditable against the original digest.

### Derived reports and indexes
Derived output should be rebuildable from canonical sources and must not silently mutate task state or event history. Clearly distinguish report creation from source-of-truth changes.

## Audit limitations and next checks

The AST audit reports known mutation-shaped calls in `tools/*.py` and flags files without an explicit contract entry. It is a review tripwire, not a complete taint/path analysis: aliases, subprocesses, C extensions, dynamic dispatch and writes hidden in dependencies can evade it. A clean audit does not prove safe semantics.

Next integration checks:
1. Verify that a real subprocess restart can rebuild a packet and extract the same task identity, goal, next step and linked events.
2. Verify that changing TASK_STATE, HANDOFF or events between snapshot and commit refuses a write.
3. Verify two concurrent checkpoint writers cannot both apply against one expected hash.
4. Verify result/ack appenders reject malformed journals and survive interrupted writes without losing prior events.
5. Kill/restart the resumable importer at batch boundaries and compare imported identities/counts with a clean import.
6. Re-run this inventory after any persistence API or write target changes.
