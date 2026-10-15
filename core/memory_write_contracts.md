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
| `tools/guarded_task_state_update.py:apply_checkpoint` | `projects/*/TASK_STATE.md` | Append-only checkpoint; restricts target name/path; validates proposal, expected SHA-256, event ID; duplicate ID is idempotent or conflict; requires external authorized verdict and recomputes trust from canonical files. Acquires the shared `events.jsonl.lock` first, then `TASK_STATE.md.lock`, and holds both through final evidence/trust checks and atomic replacement. Lock contention fails closed. `HANDOFF.md` is not protected by this lock protocol and may still change externally; this is a residual race/limitation. |
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

## Verified lock protocol (branch implementation)

For `apply_checkpoint`, the required order is:

1. Acquire `events.jsonl.lock` using exclusive creation; if it exists, return `LOCKED` without writing.
2. Acquire `TASK_STATE.md.lock`; if it exists, return `LOCKED` and release the journal lock.
3. Re-read the task-state revision, rebuild the packet, recompute the trust verdict, and validate the supporting event while both locks are held.
4. Write to a same-directory temporary file, flush/fsync, then atomically replace `TASK_STATE.md`.
5. Release locks in reverse order.

`branch_result_registry.publish_result` and `acknowledge_result` acquire only `events.jsonl.lock`, so the observed lock graph has no reverse task-state → journal acquisition in these implementations. The regression test verifies that an existing journal lock blocks a checkpoint write. This is not yet a full multiprocess stress proof: direct/manual writers and any future writer that bypasses the shared lock remain outside the protocol. Stale locks are not auto-broken; inspect the recorded PID and process state before manual recovery. `HANDOFF.md` remains outside the shared lock.

## SQLite decision

`resumable_chat_import.py` already uses SQLite transactions for its import staging database, with each batch's rows, cursor/offset update and import event written in one transaction. That database is not the canonical task-state store. A migration of `TASK_STATE.md` plus `events.jsonl` to SQLite is **deferred**, not approved: it changes storage formats and reader/writer APIs, and would not remove the need to coordinate `HANDOFF.md` or other external files. First validate the shared-lock protocol, concurrent writers, crash recovery and every remaining write path; then compare a SQLite-backed canonical store against the operational cost of a single shared lock protocol.

## Write-path review checklist

For every persistence operation, verify and record:

- [ ] Exact target path and whether it is canonical, staging, or derived.
- [ ] Contract classification in `tools/audit_write_contracts.py` and this document.
- [ ] Source digest/revision checked immediately before commit.
- [ ] Trust/evidence gate is recomputed from current canonical inputs for canonical writes.
- [ ] Shared lock name/order is followed; lock contention fails closed.
- [ ] Duplicate/replay is idempotent; same identity with different payload is a conflict.
- [ ] Temp file is on the same filesystem; flush/fsync and atomic replace where applicable.
- [ ] SQLite rows, resume cursor and audit event share a transaction where applicable.
- [ ] Failure/restart leaves no cursor ahead of durable data and preserves prior records.
- [ ] A regression test asserts both status and no-write/file-preservation behaviour.
- [ ] Limitations, external writers and recovery procedure are documented.
- [ ] CI ran against the exact commit under review.

## Monitoring and stress-test status

Current protection is fail-closed lock contention and explicit operation statuses; there is no always-on monitor or automated stale-lock reaper. Do not auto-delete stale lock files without process-level verification. Independent-process checkpoint stress testing and controlled crash injection have CI evidence on the reviewed revisions below. Archive staging collision/rerun tests and importer interruption tests remain open. The AST audit is a tripwire and must not be treated as proof of complete write-path coverage.

## Audit limitations and next checks

The AST audit reports known mutation-shaped calls in `tools/*.py` and flags files without an explicit contract entry. It is a review tripwire, not a complete taint/path analysis: aliases, subprocesses, C extensions, dynamic dispatch and writes hidden in dependencies can evade it. A clean audit does not prove safe semantics.

Next integration checks:
1. Verify that a real subprocess restart can rebuild a packet and extract the same task identity, goal, next step and linked events.
2. Verify that changing TASK_STATE, HANDOFF or events between snapshot and commit refuses a write.
3. Verify two concurrent checkpoint writers cannot both apply against one expected hash.
4. Verify result/ack appenders reject malformed journals and survive interrupted writes without losing prior events.
5. Kill/restart the resumable importer at batch boundaries and compare imported identities/counts with a clean import.
6. Re-run this inventory after any persistence API or write target changes.

## Crash-injection evidence (HEAD `85f6867668c1884ed8a43f6a6d379a77200e720b`)

GitHub Actions validation run [#528](https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/38679138314) completed successfully on this exact HEAD. The crash-injection tests in `tests/test_checkpoint_crash_injection.py` exercise two controlled termination points:

- **Killed before `os.replace`:** the prior `TASK_STATE.md` bytes remain unchanged; the temporary file and both lock files may remain because the killed process cannot execute cleanup. The test confirms those markers, then removes locks only after verifying the worker has exited and retries the operation.
- **Killed after `os.replace`:** the complete new checkpoint is present; lock files remain; replay returns `ALREADY_APPLIED` before attempting lock acquisition. The test removes the locks only after confirming the worker is dead.

These are verified test outcomes for the tested Linux CI environment and the injected boundaries, not a universal durability guarantee. They do not prove behavior under power loss, filesystem/controller failure, kernel panic, storage hardware faults, or every possible instruction-level interruption. Atomic replacement protects readers from a partially replaced target under the tested filesystem semantics; it does not by itself prove the directory entry is durable across sudden power loss.

Stale-lock cleanup is intentionally not automatic. A lock may represent a live or stalled writer, and guessing that it is stale can reintroduce concurrent mutation. Recovery remains an explicit operator action after checking that the owning process is no longer active. The tests' manual cleanup is test-fixture recovery, not production lock-reaping behavior.


## Multiprocess checkpoint stress evidence (HEAD `98138f32f0495570917acd4846fc5c4b7416c6d4`)

GitHub Actions validation run [#530](https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/38679829211) completed successfully on this exact HEAD. The workflow's `validate` job completed successfully, including the repository validation/test steps. The added `tests/test_checkpoint_multiprocess_stress.py` exercises the shared `apply_checkpoint` lock protocol with 32 independent Python processes by default (configurable with `CHECKPOINT_STRESS_WORKERS`, 2–100) released against the same expected task-state revision.

The test asserts: exactly one `APPLIED`; all other outcomes are `LOCKED` or `STALE_REVISION`; exactly one checkpoint marker and one reported write; no lock files remain after all workers exit normally; and worker/barrier timeouts surface as failures. The test passed as part of run #530 on the exact HEAD above.

Scope: this is evidence for concurrent callers using `apply_checkpoint` and the shared lock protocol in the tested GitHub Actions Linux environment. It does not establish race-freedom for manual/direct writers, external mutation of `HANDOFF.md`, other persistence paths, all filesystem failures, or every possible process interleaving. The HANDOFF write-path audit and archive/import stress tests remain open; this result does not close those items.


## Proven checkpoint-write invariants and current boundaries

**Verified stress-test evidence:** CI run [#530](https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/38679829211) passed on exact test HEAD `98138f32f0495570917acd4846fc5c4b7416c6d4`. The test uses 32 independent processes by default against one expected task-state revision and asserts exactly one `APPLIED`, all other outcomes `LOCKED` or `STALE_REVISION`, one checkpoint marker/write, no remaining locks after normal worker completion, and failure on worker/barrier timeouts. This is evidence for the tested Linux CI environment and the `apply_checkpoint` shared-lock path only; it does not cover bypass writers, external `HANDOFF.md` mutation, or other persistence operations.

## Known bypass paths and mitigations

Audit reference: `docs/handoff_writers_audit.md` (partial static audit; external/manual/dynamic writers are not proven absent).

- `tools/generate_report.sh` previously accepted any caller-supplied output path and could overwrite a canonical file such as `HANDOFF.md`. The current branch adds a fail-closed basename guard for `HANDOFF.md`, `TASK_STATE.md`, `PROJECT_STATE.md`, `DECISIONS.md`, `LESSONS.md`, `EVENT_LOG.md`, `events.jsonl`, and `lessons.jsonl`, plus a regression test that checks refusal and byte preservation. GitHub Actions run [#537](https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/38680620394) passed on exact HEAD `a01c6523cf2ba10eda7b1787e3d4b516cf3c8a77`, including the regression test. The direct report-generator mitigation is therefore verified for the tested CI environment and enumerated basenames. The guard covers this report generator and these names, not every writer or indirect path.
- `tools/install_into_repo.sh` uses `rsync --ignore-existing`: it may populate a missing file, but is not intended to overwrite an existing `HANDOFF.md`.
- `HANDOFF.md` remains outside the `apply_checkpoint` lock protocol. Therefore trust-check plus `TASK_STATE.md` replacement is not an atomic transaction over all input sources. The target guard above does not close that separate race.


## Canonical-file protection status (reviewed HEAD `165c39a69549af3c1f04ece75e7d930a8ee40f60`)

GitHub Actions run [#540](https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/38681349393) completed successfully on exact HEAD `165c39a69549af3c1f04ece75e7d930a8ee40f60`. The workflow includes memory validation, the write-contract audit, the unit-test suite, and project validation. This confirms the repository checks for that revision; individual guarantees below retain their own test scope.

### Verified within the named mechanisms

- **`TASK_STATE.md` checkpoint writes:** `apply_checkpoint` uses the documented journal-then-task lock order and atomic replacement. CI run [#530](https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/38679829211) passed the multiprocess stress test on exact test HEAD `98138f32f0495570917acd4846fc5c4b7416c6d4`: one `APPLIED`, all competing writers `LOCKED` or `STALE_REVISION`, one checkpoint marker/write, and no leftover locks after normal completion. This evidence applies to concurrent writers using that protocol in the tested Linux CI environment.
- **`tools/generate_report.sh`:** the script rejects the enumerated canonical basenames (`HANDOFF.md`, `TASK_STATE.md`, `PROJECT_STATE.md`, `DECISIONS.md`, `LESSONS.md`, `EVENT_LOG.md`, `events.jsonl`, `lessons.jsonl`) before creating the output directory or writing. CI run [#537](https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/38680620394) passed on exact test HEAD `a01c6523cf2ba10eda7b1787e3d4b516cf3c8a77`; its regression test confirms refusal preserves the target file bytes and a normal derived report is still created.
- **`tools/install_into_repo.sh`:** the inspected implementation invokes `rsync -av --ignore-existing`, so it is configured not to replace files already present at the destination. It can still create a missing file, including a missing `HANDOFF.md`; this behavior is an implementation-level finding, not a separately reported integration test.

### Not established

- Exhaustive coverage of all callers and indirect invocations of `generate_report.sh` and `install_into_repo.sh`. The current caller audit is explicitly partial; a complete branch-local search over tracked files and indirect shell wrappers remains outstanding.
- Absence of external, manual, editor-driven, or dynamically constructed writes to `HANDOFF.md`.
- Atomicity of the sequence `read HANDOFF.md → recompute trust → replace TASK_STATE.md`. `HANDOFF.md` is not protected by the checkpoint's lock protocol, so it may change after the final read and before task-state replacement.
- Protection against all aliases, symlinks, path tricks, or indirect writes merely because `generate_report.sh` checks the output basename. The guard is a targeted mitigation for that script and the listed names, not a repository-wide access-control boundary.

**Boundary:** these guarantees apply only to the named mechanisms, exact tested revisions, and stated CI environment. They do not establish that all canonical-file writers have been found or that `HANDOFF.md` and `TASK_STATE.md` participate in one atomic transaction. Keep the HANDOFF race open until writer discovery and a synchronization/source-version contract are decided and tested.
