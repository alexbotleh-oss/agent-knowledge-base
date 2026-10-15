# HANDOFF.md writer-path audit

Status: partial static audit on branch `test/real-api-integration-20261014`; initial implementation review was based on HEAD `b285662c7601b4e12b56dc41b23589cc27863f81`. Caller-inventory follow-up commit: `d1e3a5024d8dfc803e157033ba5b147e479b42b0` (CI status not yet confirmed at the time of this edit). This is an implementation-path review, not proof that no external/manual writer exists.

## Findings

| Path and location | Classification | Lock / trust behavior | Invariant and disposition |
| --- | --- | --- | --- |
| `tools/guarded_task_state_update.py:153-159` | Reads `HANDOFF.md` while rebuilding the packet; does not write it | Holds `events.jsonl.lock` and `TASK_STATE.md.lock`, but neither protects HANDOFF from external mutation | Trust is recomputed against the packet before task-state write, but HANDOFF may change between read/check and `os.replace(TASK_STATE.md)`. Explicit residual race; do not describe the full source set as atomically locked. |
| `tools/restore_session_packet.py:45-87` | Reads HANDOFF and records its hash/excerpt in a derived packet | No lock; read-only operation | Snapshot provenance/freshness evidence, not a mutation path. |
| `tools/context_extractor.py:47-77, 111-130` | Consumes HANDOFF excerpt/hash and extracts semantic context | No lock; read-only operation | Preserves source linkage; not a mutation path. |
| `tools/plan_memory_intake.py:61-62` | Routes an intake artifact of kind `handoff` to a change proposal | Produces a plan; no direct HANDOFF write observed in this tool | Proposal is not authorization to mutate canonical state. |
| `tools/generate_report.sh:4-15` | Writes to caller-configurable `OUT` (default `$PROJECT/validation-report.md`) | Now rejects known canonical-memory basenames before creating directories or writing; no shared lock is needed for this explicit refusal path | Regression tests cover refusal for `HANDOFF.md` without modifying its bytes and continued creation of a derived report. GitHub Actions run [#537](https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/38680620394) passed on exact HEAD `a01c6523cf2ba10eda7b1787e3d4b516cf3c8a77`, including this regression test. The direct report-generator overwrite route is verified as blocked for the enumerated canonical basenames in the tested CI environment. It does not protect against other writers or aliases/indirect paths. |
| `tools/install_into_repo.sh:9` | Runs `rsync -av --ignore-existing --exclude='.git' "$SRC/" "$DEST/"` | No shared lock; does not overwrite existing destination files because of `--ignore-existing` | Can create a missing HANDOFF.md in a destination repo, but should not replace an existing one. It is a broad copy/install path, not an update path for existing HANDOFF. |
| `tools/archive_registry_staging.py` (current branch implementation) | Writes versioned staging record generations and `archive_snapshot.json` under caller-supplied output directory | Uses `.archive_registry_staging.lock`; records and manifest are written via temporary files and replacement | Regression tests cover failed manifest publication preserving the previous generation and identical bytes under different archive IDs retaining separate record generations. This is staging-only; it does not authorize canonical-memory import. CI on the previous importer HEAD passed, but the current follow-up HEAD must be checked separately. |
| `tools/resumable_chat_import.py:38-59, 177-...` | Writes immutable snapshots and SQLite import database | File replacement for snapshots; SQLite transactions for import state | No HANDOFF target found; not a canonical HANDOFF writer. |


## Stable import contracts (verified)

This section is the quick-reference contract surface. Each claim is tied to a behavioral test and a successful CI run; its scope is intentionally narrower than a general claim of importer or filesystem reliability.

### PRINCIPLE 1 — Idempotency of a completed import

Re-running a completed import with the same `archive_id` and identical source bytes is a verification/no-op operation, not a rewrite. It must not change the committed event history, event timestamps, payload checksums, or persisted checkpoint state.

- **Behavioral evidence:** `test_completed_exact_source_is_not_reimported`.
- **Test commit:** `bd4ff3f464e22fff8c61ff65b32e72fe5e39aa54`.
- **CI:** [run #548](https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/38690579785) passed on the exact test commit; [run #549](https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/38690594334) passed on the subsequent documentation commit.
- **Boundary:** applies to the tested completed-source replay through `tools/resumable_chat_import.py`. Direct SQLite writes, manual edits, arbitrary filesystem/kernel failures, and untested paths are outside this evidence.

### PRINCIPLE 2 — Separation of logical sources

Identical source bytes with different `archive_id` values represent different logical sources. Their event histories, checkpoints, and progress must remain independent and must not be mixed.

- **Behavioral evidence:** `test_same_source_bytes_with_different_archive_ids_are_independent`. The test pauses archive A, completes archive B using the same bytes/digest, then resumes A and verifies independent records, events, and checkpoints.
- **Test commit:** `f68372756a05525d8925c63bff6a5e1c48647a0a`.
- **CI:** [run #551](https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/38691451002) passed on the exact test commit; [run #552](https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/38691490708) passed on the subsequent documentation commit.
- **Boundary:** applies to the tested importer entry point and scenario. It does not establish safety for direct database mutations or untested failure modes.

### PRINCIPLE 3 — Recovery after an abrupt process crash

If a process exits after writing part of a batch but before the SQLite transaction commits, the uncommitted batch must roll back. A subsequent cooperating importer must recover from the last durable checkpoint without duplicating records or changing the previously committed prefix and event history.

- **Behavioral evidence:** `test_process_crash_mid_batch_rolls_back_uncommitted_rows_and_resumes`.
- **Test commit:** `52fd5f693f8649504f167c959b9cb71e0f5b1a2c`.
- **CI:** [run #556](https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/38692448056) passed on the exact test commit.
- **Boundary:** verified for the injected process-exit point and SQLite transaction path on Ubuntu 24.04 in GitHub Actions. This is not evidence for power loss, disk failure, arbitrary filesystem/kernel faults, or all operating systems.

## Dependencies and prohibitions for future changes

Every future importer logic change and every new interruption/recovery test must preserve all three verified principles above:

1. **Idempotency:** a completed-source replay must not rewrite committed records, event history/timestamps, payload checksums, or persisted checkpoint state.
2. **Logical-source separation:** different `archive_id` values retain independent records, event histories, and progress even when the source bytes and digest are identical.
3. **Crash recovery:** uncommitted batch work must not survive as partial rows or advance the durable checkpoint; retry must resume without duplicates or mutation of the previously committed prefix.

**Critical-defect rule:** violating any one of these principles is a critical defect, even if the importer eventually reports `RAW_COMPLETE` or appears to have read all source records. A successful final status does not override a failed invariant.

These are test-backed constraints, not a claim that every failure mode is covered. Each new guarantee must name its behavioral test, exact test commit, CI run on that commit, and explicit applicability boundary.

## Recovery dependencies (verified invariants)

The recovery test suite must collectively verify recovery **and** preservation of all three stable import contracts above. Not every scenario exercises every principle independently; the scenario-specific assertions and boundaries below define exactly what each test proves. Reaching `RAW_COMPLETE` is not sufficient if previously committed records, event timestamps, checksums, source identity, or checkpoint state were changed.

- **PRINCIPLE 1 — idempotency:** previously committed rows and their payload checksums/import timestamps remain unchanged; previously committed event rows and timestamps remain unchanged; a failed uncommitted batch does not advance the durable cursor or duplicate records when retried.
- **PRINCIPLE 2 — logical-source separation:** different `archive_id` values must retain independent event histories, records, and checkpoints even when source bytes/digests match and one process is interrupted.
- **PRINCIPLE 3 — crash recovery:** an uncommitted batch rolls back after abrupt process exit; retry resumes from the last durable checkpoint without changing the committed prefix or duplicating records.
- **Critical-defect rule:** any recovery path that violates any of these three invariants is a critical defect, even if the importer eventually reports `RAW_COMPLETE`.

### Scenario 1 — abrupt process exit inside a batch transaction

- **Behavioral evidence:** `test_process_crash_mid_batch_rolls_back_uncommitted_rows_and_resumes`. The test first commits a prefix, then a child process exits abruptly after SQLite executes the first raw-row insert of the next batch but before that batch can commit. It checks that the committed prefix and prior event history remain exact, the partial batch is rolled back, the durable cursor stays at the prior checkpoint, and a subsequent run completes without duplicate ordinals.
- **Test commit:** `52fd5f693f8649504f167c959b9cb71e0f5b1a2c`.
- **CI:** [run #556](https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/38692448056) passed on the exact test commit.
- **Boundary:** verified in the Ubuntu 24.04 GitHub Actions environment for this injected process-exit point and SQLite transaction path. It is not proof of power-loss durability, arbitrary filesystem/kernel failures, hardware faults, or every platform's SQLite/locking behavior.

### Scenario 2 — concurrent same-source launch with lock-holder crash

- **Behavioral evidence:** `test_concurrent_same_source_recovers_after_lock_holder_crashes`. Archive A first commits a prefix. A child process resumes and pauses after an insert inside an uncommitted batch while holding the output-directory lock; a second cooperating process attempts the same source. The first process exits abruptly, the waiting process completes the import, and the test checks the unchanged committed prefix/event history, unique ordinals, final checkpoint, and independent progress for identical bytes under a second `archive_id`.
- **Test commit:** `6df75bc59409c22d6dd924c6466d10184f1236d5`.
- **CI:** [run #559](https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/38692838537) passed on the exact test commit.
- **Boundary:** verifies cooperating processes using the importer entry point and its output-directory OS advisory lock in Ubuntu 24.04 GitHub Actions. The test's short wait confirms the second process has not exited while the first holds the lock; it does not establish behavior for non-cooperating writers, every OS/filesystem, or machine/power failure.

### Scenario 3 — independent-process restart at a committed batch boundary

- **Behavioral evidence:** `test_fresh_process_restarts_from_committed_checkpoint_without_rewriting_prefix`. The first importer invocation commits a two-record prefix and returns `PAUSED`. The test snapshots every persisted field of the committed rows, the event history, and the checkpoint. It then invokes the actual importer CLI using `subprocess.run` in a new Python interpreter, passing only the source path, output directory, and `archive_id`—not an in-memory cursor. The new process must report `RESUME`, finish at `RAW_COMPLETE`, preserve the committed prefix byte-for-byte at the selected field level and preserve all pre-existing event rows, and finish with six unique ordered records and a checkpoint at ordinal 6.
- **Test commit:** `b7d61d5f59cb0622e6d317e2f1303429128ff9c4` (contains the final test-file repairs as well as the test).
- **CI:** [run #565](https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/38694472142) passed on that exact HEAD; both validation steps succeeded.
- **Boundary:** verifies restart in a fresh Python process on the GitHub Actions runner using the importer's CLI and persisted SQLite checkpoint. It does not establish recovery from machine/power loss, disk corruption, arbitrary filesystem/kernel faults, or behavior on every OS/filesystem. The test checks the selected persisted row fields and all prior event fields; it is not a proof against direct external database mutation.

## Import idempotency coverage (branch review)

Coverage was inspected in `tests/test_resumable_chat_import.py` and `tests/test_archive_registry_staging.py` before changing tests.

| Scenario | Existing coverage before this change | New/updated test | Status and boundary |
| --- | --- | --- | --- |
| Re-import the exact completed source with the same `archive_id` | `test_rerun_is_idempotent_and_preserves_original_snapshot` checks row counts and snapshot bytes; `test_completed_exact_source_is_not_reimported` checked run mode and selected event counts. Neither previously compared the complete event history and persisted row/checkpoint fields before and after replay. | Strengthened `test_completed_exact_source_is_not_reimported` to compare staged record identity/hash/import timestamp/byte offset, full event rows including `occurred_at`, and persisted import state before and after replay. | **Verified.** Test change committed as `bd4ff3f464e22fff8c61ff65b32e72fe5e39aa54`; GitHub Actions run [#548](https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/38690579785) passed on that exact test HEAD. The subsequent documentation update is committed as `9b46660936e33506fde61fe85a47ffc61d5ff5e8`; CI run [#549](https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/38690594334) passed on that exact documentation HEAD. The test compares the relevant persisted rows and checkpoint state before/after replay. Boundary: this is evidence for this scenario through `resumable_chat_import.py`, not for direct SQLite writes or arbitrary filesystem failures. |
| Same source bytes, different `archive_id` in staging | `test_same_bytes_with_different_archive_ids_keep_separate_generations` asserts distinct record filenames and preserves the first generation's bytes. | None. | Covered at staging-generation level. |
| Same source bytes, different `archive_id` in the SQLite importer | Previously no dedicated importer-level test existed. The schema keys records/imports by both `archive_id` and source digest, but schema shape alone is not behavioral evidence. | Added `test_same_source_bytes_with_different_archive_ids_are_independent`: identical bytes/digest; archive A pauses after one committed record, archive B completes independently, then A resumes. It asserts two import rows, distinct source locators, archive-scoped events, and independent checkpoint progress. Test commit `f68372756a05525d8925c63bff6a5e1c48647a0a`. | **Verified.** GitHub Actions run [#551](https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/38691451002) passed on exact test HEAD `f68372756a05525d8925c63bff6a5e1c48647a0a`. The documentation follow-up is committed as `e66d89196bc6b7774b58b413fa2cf1643e023ab0`; CI run [#552](https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/38691490708) passed on that exact documentation HEAD. |

### Principle: import idempotency (PRINCIPLE)

Re-running a completed import with the same `archive_id` and identical source bytes is a verification/no-op operation, not a rewrite. It must not change the committed event history, event timestamps, payload checksums, or persisted checkpoint state.

**Evidence:** `test_completed_exact_source_is_not_reimported`, test commit `bd4ff3f464e22fff8c61ff65b32e72fe5e39aa54`, confirmed by CI run [#548](https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/38690579785). The documentation follow-up on `9b46660936e33506fde61fe85a47ffc61d5ff5e8` also passed CI run [#549](https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/38690594334).

**Applicability boundary:** this guarantee is scoped to imports performed through `tools/resumable_chat_import.py` and the tested completed-source replay path. Direct writes to SQLite that bypass the importer, manual database edits, arbitrary filesystem/kernel failures, and untested paths are not covered.

The importer-level identical-byte/different-`archive_id` scenario is now covered by `test_same_source_bytes_with_different_archive_ids_are_independent`; the exact test commit and subsequent documentation commit both have successful CI evidence above. The claim remains limited to this scenario and the tested importer entry point.

## Search scope and limits

Inspected all listed `tools/*.py` and `tools/*.sh` files plus `.github/workflows/validate.yml` at the branch revision above for HANDOFF references and common write shapes (`write_text`, `write_bytes`, `open`, `os.replace`, `shutil.copy/move`, shell redirection, `cp`, `mv`, `tee`, and `rsync`). No dedicated function that updates an existing `HANDOFF.md` was identified in these files.

This does not cover manual edits, arbitrary external scripts, editor/IDE writes, commands run outside repository tools, dynamically constructed paths, dependency code, or every indirect process invocation. The AST audit is advisory and is not a complete data-flow analysis.

## Current disposition

- No dedicated in-repository HANDOFF update API was found in the inspected tools.
- `generate_report.sh` now rejects the known canonical-memory filenames (`HANDOFF.md`, `TASK_STATE.md`, `PROJECT_STATE.md`, `DECISIONS.md`, `LESSONS.md`, `EVENT_LOG.md`, `events.jsonl`, `lessons.jsonl`) as report targets. The regression test passed in CI run #537 on the exact HEAD recorded in `core/memory_write_contracts.md`; the basename guard does not replace a complete writer audit.
- `install_into_repo.sh` can populate a missing HANDOFF but is configured not to overwrite existing files.
- The guarded checkpoint's trust check does not make HANDOFF mutation atomic with TASK_STATE mutation. Until HANDOFF has a shared mutation protocol or immutable/versioned source reference, this remains an explicit limitation.
- Next audit step: run a branch-local search across all tracked files for `generate_report.sh`, `install_into_repo.sh`, wrappers, indirect `bash`/`sh` calls, and explicit output targets. Importer restart, source-collision, changed-source, and concurrent-lock scenarios are now covered by the tests listed above, within their stated boundaries. Do not claim complete writer coverage based on this partial static audit.


## Caller / invocation audit (limited to files read at this revision)

| Source and line | Invocation / target | Classification | Evidence and limits |
| --- | --- | --- | --- |
| `README.md:65` | `tools/generate_report.sh /path/to/project` | Safe documented default invocation; no explicit `OUT` argument | The second positional argument is omitted, so the script uses `$PROJECT/validation-report.md`. |
| `.github/workflows/validate.yml` (validation steps) | No direct invocation of `generate_report.sh` or `install_into_repo.sh` in the workflow content inspected | No caller found in this workflow | The workflow invokes `validate_project.sh`, not the report generator or installer. This does not rule out indirect invocation by another script. |
| Repository documentation/scripts searched in this pass | No `install_into_repo.sh` invocation identified in the inspected content | No caller found in inspected content; coverage incomplete | The installer is a manually invoked utility taking only a destination repository argument. Its `rsync --ignore-existing` option protects existing destination files, but creation of a missing canonical file is still possible. |
| External/manual callers | Unknown | Outside repository-static scope | A local grep over the complete checked-out branch would be needed to establish a broader invocation inventory. GitHub code search used here indexes the default branch, so it is not sufficient evidence for all callers on this PR branch. |

This caller inventory is deliberately scoped: it records only source files actually read and does not claim repository-wide exhaustive search. Before declaring the invocation audit complete, run a branch-local search across tracked files for both script names, shell wrappers, and indirect `bash`/`sh` invocations; record exact line numbers and every explicit output target. CI run #540 passed on reviewed HEAD `165c39a69549af3c1f04ece75e7d930a8ee40f60`. The later documentation HEAD `f6ec021e7d99f49ac6b9e75e692fe2eb0cf58f22` passed validation in CI run [#566](https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/38695331178). This validates the repository's configured checks at that exact HEAD; it does not make the caller inventory exhaustive.


## Scope of guarantees for `tools/resumable_chat_import.py`

The importer provides the following **verified, scenario-scoped guarantees** through its own entry point:

1. **Idempotency:** replaying a completed import with the same `archive_id` and identical source bytes does not rewrite the tested committed records, payload checksums, import timestamps, event history/timestamps, or persisted checkpoint.
2. **Logical-source separation:** identical source bytes under different `archive_id` values retain independent records, event histories, and progress in the tested importer scenarios.
3. **Recovery integrity:** an injected process exit before a batch transaction commits rolls back that uncommitted batch; a cooperating retry or fresh-process CLI invocation resumes from the persisted checkpoint without duplicating records or changing the tested committed prefix/history.

These guarantees are supported by the named behavioral tests and CI runs in the sections above. They apply to the tested importer paths, SQLite transaction behavior, and cooperating processes using the importer's lock protocol. They are **not** a universal durability guarantee.

**Out of scope / not established by this importer contract:**

- Direct SQLite writes, manual database edits, or non-cooperating writers that bypass the importer and its lock protocol.
- Power loss, disk failure, WAL/database corruption, and arbitrary operating-system, filesystem, or kernel faults.
- Cross-platform locking/recovery behavior beyond the CI environment explicitly named by each test.
- Coordination across distinct canonical state files, including the known `HANDOFF.md` versus `TASK_STATE.md` race. That belongs to a separate shared-writer protocol; importer guarantees do not resolve it.

A successful `RAW_COMPLETE` status is necessary but not sufficient evidence of correctness: the scenario's persisted-state invariants must also hold. Do not extend these claims beyond the tests and boundaries cited here.

## Remaining-risk audit at HEAD `f6ec021e7d99f49ac6b9e75e692fe2eb0cf58f22`

This is a scoped audit of evidence available in the current branch, not a claim of complete system reliability.

| Area | Disposition | Evidence / reason |
| --- | --- | --- |
| Completed-source replay with the same `archive_id` and bytes | **Covered** | `test_completed_exact_source_is_not_reimported`; CI #548 passed on its exact test commit. The test compares persisted rows, event history/timestamps, and checkpoint state before and after replay. |
| Identical bytes under different `archive_id` values | **Covered** | `test_same_source_bytes_with_different_archive_ids_are_independent`; CI #551 passed on its exact test commit. |
| Abrupt process exit during an uncommitted SQLite batch | **Covered** | `test_process_crash_mid_batch_rolls_back_uncommitted_rows_and_resumes`; CI #556 passed on its exact test commit. |
| Concurrent same-source import after lock-holder crash | **Covered** | `test_concurrent_same_source_recovers_after_lock_holder_crashes`; CI #559 passed on its exact test commit. Scope: cooperating importer processes on the tested Ubuntu runner. |
| Restart in a fresh interpreter from a committed checkpoint | **Covered** | `test_fresh_process_restarts_from_committed_checkpoint_without_rewriting_prefix`; CI #565 passed on the exact test HEAD. The documentation update then passed CI #566 on the current HEAD. |
| Source bytes change between import passes | **Covered for the tested behavior** | `test_same_operation_with_changed_source_is_new_snapshot_not_resume` exists in the current test file. This is not a guarantee for arbitrary external edits to the SQLite database or snapshot files. |
| Stale/replayed batch attempting to move the cursor backwards | **Covered for the tested path** | `test_stale_replayed_batch_does_not_regress_checkpoint` exists in the current test file. |
| Direct SQLite writes, manual database edits, non-cooperating writers | **Intentionally outside the importer contract** | They bypass the importer entry point and its lock/transaction protocol. Do not describe importer tests as protecting against these actors. |
| Power loss, disk failure, database/WAL corruption, arbitrary OS/filesystem/kernel faults | **Intentionally not covered** | Current tests inject process termination at controlled points; they do not simulate hardware or storage failure. Add such testing only if these failure modes become explicit product requirements and can be tested meaningfully. |
| Windows/macOS and other filesystem locking semantics | **Not established by current CI evidence** | The documented crash/concurrency evidence is from Ubuntu 24.04. If cross-platform support is a release requirement, add a platform matrix and targeted lock/recovery checks; otherwise retain this as a stated boundary. |
| `HANDOFF.md` changing between trust re-check and `TASK_STATE.md` replacement | **Known open race; requires design decision** | The current lock protocol does not lock or version `HANDOFF.md`. A test can demonstrate the race, but a durable fix likely needs a shared mutation protocol or immutable/versioned source reference. Do not claim atomicity across these files. |
| Complete inventory of report/installer callers and indirect invocation paths | **Audit still required** | The current caller inventory is explicitly partial. Run a branch-local search over tracked files and record all call sites/targets before declaring the writer audit complete. |

### Audit conclusion

The current importer recovery evidence is sufficient to document the five named recovery/idempotency/source-identity scenarios within their boundaries. **No additional importer crash scenario is justified solely to increase the test count.** The next meaningful action is to close the branch-local caller inventory and decide whether the known `HANDOFF.md`/ `TASK_STATE.md` race is in scope for this PR. Hardware/storage failures and direct database mutation remain explicit exclusions unless the requirements change.
