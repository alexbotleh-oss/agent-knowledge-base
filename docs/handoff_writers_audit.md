# HANDOFF.md writer-path audit

Status: partial static audit on branch `test/real-api-integration-20261014`, HEAD `b285662c7601b4e12b56dc41b23589cc27863f81` (before this audit document). This is an implementation-path review, not proof that no external/manual writer exists.

## Findings

| Path and location | Classification | Lock / trust behavior | Invariant and disposition |
| --- | --- | --- | --- |
| `tools/guarded_task_state_update.py:153-159` | Reads `HANDOFF.md` while rebuilding the packet; does not write it | Holds `events.jsonl.lock` and `TASK_STATE.md.lock`, but neither protects HANDOFF from external mutation | Trust is recomputed against the packet before task-state write, but HANDOFF may change between read/check and `os.replace(TASK_STATE.md)`. Explicit residual race; do not describe the full source set as atomically locked. |
| `tools/restore_session_packet.py:45-87` | Reads HANDOFF and records its hash/excerpt in a derived packet | No lock; read-only operation | Snapshot provenance/freshness evidence, not a mutation path. |
| `tools/context_extractor.py:47-77, 111-130` | Consumes HANDOFF excerpt/hash and extracts semantic context | No lock; read-only operation | Preserves source linkage; not a mutation path. |
| `tools/plan_memory_intake.py:61-62` | Routes an intake artifact of kind `handoff` to a change proposal | Produces a plan; no direct HANDOFF write observed in this tool | Proposal is not authorization to mutate canonical state. |
| `tools/generate_report.sh:4-15` | Writes to caller-configurable `OUT` (default `$PROJECT/validation-report.md`) | Now rejects known canonical-memory basenames before creating directories or writing; no shared lock is needed for this explicit refusal path | Regression tests cover refusal for `HANDOFF.md` without modifying its bytes and continued creation of a derived report. This closes the direct report-generator overwrite route for the enumerated canonical basenames only after CI confirms the current HEAD. It does not protect against other writers or aliases/indirect paths. |
| `tools/install_into_repo.sh:9` | Runs `rsync -av --ignore-existing --exclude='.git' "$SRC/" "$DEST/"` | No shared lock; does not overwrite existing destination files because of `--ignore-existing` | Can create a missing HANDOFF.md in a destination repo, but should not replace an existing one. It is a broad copy/install path, not an update path for existing HANDOFF. |
| `tools/archive_registry_staging.py:99-124` | Writes staging records and `archive_snapshot.json` under caller-supplied output directory | No shared lock; temp replacement only for records file; manifest uses `write_text` | Targets are fixed staging filenames, not HANDOFF.md. Manifest write atomicity/rerun collision remains a separate staging concern. |
| `tools/resumable_chat_import.py:38-59, 177-...` | Writes immutable snapshots and SQLite import database | File replacement for snapshots; SQLite transactions for import state | No HANDOFF target found; not a canonical HANDOFF writer. |

## Search scope and limits

Inspected all listed `tools/*.py` and `tools/*.sh` files plus `.github/workflows/validate.yml` at the branch revision above for HANDOFF references and common write shapes (`write_text`, `write_bytes`, `open`, `os.replace`, `shutil.copy/move`, shell redirection, `cp`, `mv`, `tee`, and `rsync`). No dedicated function that updates an existing `HANDOFF.md` was identified in these files.

This does not cover manual edits, arbitrary external scripts, editor/IDE writes, commands run outside repository tools, dynamically constructed paths, dependency code, or every indirect process invocation. The AST audit is advisory and is not a complete data-flow analysis.

## Current disposition

- No dedicated in-repository HANDOFF update API was found in the inspected tools.
- `generate_report.sh` now rejects the known canonical-memory filenames (`HANDOFF.md`, `TASK_STATE.md`, `PROJECT_STATE.md`, `DECISIONS.md`, `LESSONS.md`, `EVENT_LOG.md`, `events.jsonl`, `lessons.jsonl`) as report targets. The new regression test must pass in CI before this path is considered verified; the basename guard does not replace a complete writer audit.
- `install_into_repo.sh` can populate a missing HANDOFF but is configured not to overwrite existing files.
- The guarded checkpoint's trust check does not make HANDOFF mutation atomic with TASK_STATE mutation. Until HANDOFF has a shared mutation protocol or immutable/versioned source reference, this remains an explicit limitation.
- Next audit step: review caller documentation and all invocation sites for `generate_report.sh` and `install_into_repo.sh`; confirm the target-guard regression in CI; then test importer/archive restart and collision behavior. Do not claim complete writer coverage based on this partial static audit.
