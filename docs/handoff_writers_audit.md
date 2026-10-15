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


## Import idempotency coverage (branch review)

Coverage was inspected in `tests/test_resumable_chat_import.py` and `tests/test_archive_registry_staging.py` before changing tests.

| Scenario | Existing coverage before this change | New/updated test | Status and boundary |
| --- | --- | --- | --- |
| Re-import the exact completed source with the same `archive_id` | `test_rerun_is_idempotent_and_preserves_original_snapshot` checks row counts and snapshot bytes; `test_completed_exact_source_is_not_reimported` checked run mode and selected event counts. Neither previously compared the complete event history and persisted row/checkpoint fields before and after replay. | Strengthened `test_completed_exact_source_is_not_reimported` to compare staged record identity/hash/import timestamp/byte offset, full event rows including `occurred_at`, and persisted import state before and after replay. | **Verified.** Test change committed as `bd4ff3f464e22fff8c61ff65b32e72fe5e39aa54`; GitHub Actions run [#548](https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/38690579785) passed on that exact test HEAD. The subsequent documentation update is committed as `9b46660936e33506fde61fe85a47ffc61d5ff5e8`; CI run [#549](https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/38690594334) passed on that exact documentation HEAD. The test compares the relevant persisted rows and checkpoint state before/after replay. Boundary: this is evidence for this scenario through `resumable_chat_import.py`, not for direct SQLite writes or arbitrary filesystem failures. |
| Same source bytes, different `archive_id` in staging | `test_same_bytes_with_different_archive_ids_keep_separate_generations` asserts distinct record filenames and preserves the first generation's bytes. | None. | Covered at staging-generation level. |
| Same source bytes, different `archive_id` in the SQLite importer | Previously no dedicated importer-level test existed. The schema keys records/imports by both `archive_id` and source digest, but schema shape alone is not behavioral evidence. | Added `test_same_source_bytes_with_different_archive_ids_are_independent`: identical bytes/digest; archive A pauses after one committed record, archive B completes independently, then A resumes. It asserts two import rows, distinct source locators, archive-scoped events, and independent checkpoint progress. Test commit `f68372756a05525d8925c63bff6a5e1c48647a0a`. | **Awaiting CI for exact test HEAD.** Do not call this scenario verified until the workflow succeeds on this commit or a later HEAD containing the test. |

### Principle: import idempotency (PRINCIPLE)

Re-running a completed import with the same `archive_id` and identical source bytes is a verification/no-op operation, not a rewrite. It must not change the committed event history, event timestamps, payload checksums, or persisted checkpoint state.

**Evidence:** `test_completed_exact_source_is_not_reimported`, test commit `bd4ff3f464e22fff8c61ff65b32e72fe5e39aa54`, confirmed by CI run [#548](https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/38690579785). The documentation follow-up on `9b46660936e33506fde61fe85a47ffc61d5ff5e8` also passed CI run [#549](https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/38690594334).

**Applicability boundary:** this guarantee is scoped to imports performed through `tools/resumable_chat_import.py` and the tested completed-source replay path. Direct writes to SQLite that bypass the importer, manual database edits, arbitrary filesystem/kernel failures, and untested paths are not covered.

The separate case “same source bytes, different `archive_id` in the SQLite importer” remains an open test gap; staging-generation coverage does not prove importer-level independence.

## Search scope and limits

Inspected all listed `tools/*.py` and `tools/*.sh` files plus `.github/workflows/validate.yml` at the branch revision above for HANDOFF references and common write shapes (`write_text`, `write_bytes`, `open`, `os.replace`, `shutil.copy/move`, shell redirection, `cp`, `mv`, `tee`, and `rsync`). No dedicated function that updates an existing `HANDOFF.md` was identified in these files.

This does not cover manual edits, arbitrary external scripts, editor/IDE writes, commands run outside repository tools, dynamically constructed paths, dependency code, or every indirect process invocation. The AST audit is advisory and is not a complete data-flow analysis.

## Current disposition

- No dedicated in-repository HANDOFF update API was found in the inspected tools.
- `generate_report.sh` now rejects the known canonical-memory filenames (`HANDOFF.md`, `TASK_STATE.md`, `PROJECT_STATE.md`, `DECISIONS.md`, `LESSONS.md`, `EVENT_LOG.md`, `events.jsonl`, `lessons.jsonl`) as report targets. The regression test passed in CI run #537 on the exact HEAD recorded in `core/memory_write_contracts.md`; the basename guard does not replace a complete writer audit.
- `install_into_repo.sh` can populate a missing HANDOFF but is configured not to overwrite existing files.
- The guarded checkpoint's trust check does not make HANDOFF mutation atomic with TASK_STATE mutation. Until HANDOFF has a shared mutation protocol or immutable/versioned source reference, this remains an explicit limitation.
- Next audit step: review caller documentation and all invocation sites for `generate_report.sh` and `install_into_repo.sh`; retain the target-guard regression in CI; then test importer/archive restart and collision behavior. Do not claim complete writer coverage based on this partial static audit.


## Caller / invocation audit (limited to files read at this revision)

| Source and line | Invocation / target | Classification | Evidence and limits |
| --- | --- | --- | --- |
| `README.md:65` | `tools/generate_report.sh /path/to/project` | Safe documented default invocation; no explicit `OUT` argument | The second positional argument is omitted, so the script uses `$PROJECT/validation-report.md`. |
| `.github/workflows/validate.yml` (validation steps) | No direct invocation of `generate_report.sh` or `install_into_repo.sh` in the workflow content inspected | No caller found in this workflow | The workflow invokes `validate_project.sh`, not the report generator or installer. This does not rule out indirect invocation by another script. |
| Repository documentation/scripts searched in this pass | No `install_into_repo.sh` invocation identified in the inspected content | No caller found in inspected content; coverage incomplete | The installer is a manually invoked utility taking only a destination repository argument. Its `rsync --ignore-existing` option protects existing destination files, but creation of a missing canonical file is still possible. |
| External/manual callers | Unknown | Outside repository-static scope | A local grep over the complete checked-out branch would be needed to establish a broader invocation inventory. GitHub code search used here indexes the default branch, so it is not sufficient evidence for all callers on this PR branch. |

This caller inventory is deliberately scoped: it records only source files actually read and does not claim repository-wide exhaustive search. Before declaring the invocation audit complete, run a branch-local search across tracked files for both script names, shell wrappers, and indirect `bash`/`sh` invocations; record exact line numbers and every explicit output target. CI run #540 passed on reviewed HEAD `165c39a69549af3c1f04ece75e7d930a8ee40f60`; the current documentation follow-up does not yet have a confirmed CI result.
