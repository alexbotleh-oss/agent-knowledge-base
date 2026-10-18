# HANDOFF — AGENT_MEMORY_SYSTEM

Updated: 2026-10-18

## Active goal
Continue building a reliable, resumable raw-history intake and memory-evolution pipeline. Preserve source bytes, chronology, provenance, conflicts and unknowns. Keep raw import separate from later semantic analysis.

## Live baseline
- Repository: `alexbotleh-oss/agent-knowledge-base`.
- Branch: `export/cross-project-experience-rollup-20261012`.
- PR #22: [open / Draft / unmerged](https://github.com/alexbotleh-oss/agent-knowledge-base/pull/22).
- `main` last verified at `a0c12ba849a3416f50e1289d8f0dd20844e1e51f`; do not modify or merge without explicit permission.
- Earlier exact-head CI passed at `825f71bda46078ef9e0864b55af094784eb29b4b` in [run #39124375760](https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/39124375760). Later changes include temporal validation, append-only writer, tests, docs and event/task checkpoints. **Verify CI for the current exact HEAD before reporting current state as verified.**

## Current implementation state
- `tools/resumable_chat_import.py` is an existing local-first prototype. It preserves a SHA-256-verified immutable source snapshot, incrementally parses one conversation object at a time, stages opaque payloads in SQLite, journals batches/checkpoints transactionally, and supports JSON/ZIP input with resumable/idempotent runs. New fault-injection tests now exercise rollback inside a batch transaction, commit-success/lost-ack recovery, and rollback/retry of `RAW_COMPLETE` finalization.
- `_verify_staged_integrity()` validates staged payload JSON, payload SHA-256 and contiguous source ordinals before resume, before marking `RAW_COMPLETE`, and before returning `ALREADY_COMPLETE`. Corruption sets `FAILED`, appends `INTEGRITY_FAILED`, and raises.
- `import_export()` acquires an OS-managed exclusive lock for its output directory. A second writer should fail visibly; the OS releases the lock when the process exits. Linux/Unix `fcntl` is the CI path; Windows and network filesystems are not independently verified.
- `immutable_snapshot()` fsyncs copied file contents before publishing the final content-addressed name, then attempts directory fsync where supported. A failure-injection test checks that file-fsync failure does not publish the final name.
- `tools/temporal_memory_model.py::validate_temporal_relations(records, trusted_order)` supports coarse calendar order plus evidence-backed `verified_precedence` paths for partial ordering. It never infers chronology from row position, event IDs or ingestion time. Correction overlays apply in memory; partial old-edge selectors are accepted only when they match exactly one edge.
- `tools/append_memory_event.py::append_event_record()` provides a pre-write append path: read existing JSONL, reject duplicate IDs, validate the full temporal graph against the supplied trusted order, then append under an OS-managed lock and fsync. Validation failures leave the journal unchanged. CLI accepts `--journal`, `--event`, `--trusted-order`.
- `tools/validate_event_journal.py` is a read-only preflight CLI for existing JSONL. It reports `PASS` or `NEEDS_RECONCILIATION` and explicitly reports `writes_performed: false`.
- Tests cover wrong edge direction, correction overlay replacement and null-removal without source mutation, missing/boolean chronology, invalid append rejection without mutation, valid append, duplicate IDs, and read-only preflight.
- **Read-only preflight has been run against the live journal in CI.** It reported 18 records, 15 raw temporal edges, `NEEDS_RECONCILIATION`, five unresolved same-day edges and `writes_performed: false`. The report artifact from run #39129738684 is available at https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/39129738684/artifacts/12137990330. The append writer has not been run against the live journal.
- Append-only events `EVT-AGMS-20261018-001..010` document importer integrity/locking, snapshot durability, temporal validation, the actual read-only preflight result, and independent verification of the supplied partial transfer package. Do not rewrite historical events or remove overlays.

## Verification boundary
- Exact-head CI run #39129738684 passed on code/test HEAD `2b9f6096483d6a18f5eb24f3b50f8aa1af9893c1` (98 unittest tests, memory validation, project validation, and report artifact upload). Later event/doc checkpoint commits require rechecking CI for the live HEAD.
- The newly supplied `EXPORT_EXPERIENCE_NASTROYKA_AGENTA_2026-10-18(1).zip` was independently verified: ZIP integrity passed, all 32 `SHA256SUMS.txt` entries and all 32 manifest entries matched. It is a partial evidence package and contains no native `conversations.json`; it does not unblock a real native-export import. Do not claim real-source verification.
- The importer stages conversation JSON only. Manifest reconciliation, binary attachment inventory, full external chat coverage, SQLite commit-boundary failure injection and automatic live ChatGPT capture remain unverified or unimplemented.
- PR #22 has accumulated unrelated project-history scope and is not scope-clean or merge-ready; re-fetch live changed-file count rather than relying on old counts.

## Immediate next actions
1. Re-fetch branch HEAD, `main`, PR metadata and Actions; verify exact-head CI. Read back changed code and check JSONL parseability, unique event IDs and correction overlays.
2. Resolve the five same-day edges only from independent source chronology: EVT-AGMS-20261013-002→001, 003→002, 004→003, 006→005, and EVT-AGMS-20261014-002→001. Otherwise preserve them as unresolved. Do not run the append writer against the live journal until all effective temporal edges validate.
3. Add failure injection around SQLite commit/checkpoint boundaries; test Windows lock behavior separately if Windows is a target.
4. Obtain authorized local raw bytes for the intended export; run the importer and record source hash, archive structure, counts and gaps without uploading private content to GitHub.
5. Reconcile manifest entries and attachment payload availability separately. The importer does not prove attachment completeness.
6. Continue PR scope cleanup only with a verified preservation destination for out-of-scope history.

## Operating rules
- Preserve raw source separately from extracted/candidate/canonical memory.
- Never treat a summary as a replacement for source history or import time as event time.
- A passing CI run does not prove complete chat/attachment coverage, multi-process safety on every filesystem, or live ChatGPT integration.
- Keep PR #22 Draft/open/unmerged. Do not modify `main`, delete history or merge without explicit user permission.


## Checkpoint 2026-10-18 — SQLite boundary fault injection

- Added tests in `tests/test_resumable_chat_import.py` for three failure boundaries:
  1. An SQLite trigger aborts the batch's event insert after row/checkpoint writes begin; the transaction rolls back, the prior cursor/count remain intact, and resume completes without loss.
  2. The batch commit succeeds but an injected exception simulates lost acknowledgement; the persisted cursor resumes after the committed batch and the final ordinals remain unique/contiguous.
  3. An SQLite trigger aborts the `RAW_COMPLETE` event insert; finalization rolls back, staged data and cursor remain durable, and a retry finalizes the import.
- These tests passed in CI run #39130123876 (101 unittest tests) at SHA `b0e2b892e52a50a28c8ee2fbe6146f346da7d9bc`. This result applies only to that SHA; the current branch has later event/checkpoint commits and must be checked again.
- The live event-journal preflight still reports five unresolved same-day edges. The append writer remains blocked from the live journal.
- The user-provided 18 October package is checksum-clean but partial; native chat export, platform message IDs/timestamps, and complete attachment lineage remain unavailable.
