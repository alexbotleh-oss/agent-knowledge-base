# HANDOFF — AGENT_MEMORY_SYSTEM

Updated: 2026-10-18

## Active goal
Continue building a reliable, resumable raw-history intake pipeline. Preserve source bytes, chronology, provenance, conflicts and unknowns. Keep raw import separate from later semantic analysis.

## Live baseline
- Repository: `alexbotleh-oss/agent-knowledge-base`.
- Branch: `export/cross-project-experience-rollup-20261012`.
- PR #22: [open / Draft / unmerged](https://github.com/alexbotleh-oss/agent-knowledge-base/pull/22).
- `main` last verified at `a0c12ba849a3416f50e1289d8f0dd20844e1e51f`; do not modify or merge without explicit permission.
- Before the current code and checkpoint updates, exact-head CI passed on `3d7aabfd266fc742a4bc1cd4355d54fd93178188` in [run #39124050309](https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/39124050309). The workflow ran 77 unittest tests and memory validation successfully. **Re-fetch branch HEAD and verify CI for the newest commit before reporting current state as verified.**

## Current implementation state
- `tools/resumable_chat_import.py` is an existing local-first prototype, not an unimplemented proposal. It preserves a SHA-256-verified immutable source snapshot, incrementally parses one conversation object at a time, stages opaque payloads in SQLite, journals batches and checkpoints transactionally, and supports JSON/ZIP input with resumable/idempotent runs.
- `_verify_staged_integrity()` validates staged payload JSON, payload SHA-256 and contiguous source ordinals before resume, before marking `RAW_COMPLETE`, and before returning `ALREADY_COMPLETE`. Corruption sets `FAILED`, appends `INTEGRITY_FAILED`, and raises.
- `import_export()` now acquires an OS-managed exclusive lock for its output directory. A second writer should fail visibly; the OS releases the lock when the process exits. Linux/Unix `fcntl` is the CI path; Windows and network filesystems are not independently verified.
- Tests cover interruption/resume, ZIP resume, lost-ack replay, duplicate source IDs, truncated input, payload tampering at resume/completion and second-writer exclusion.
- `projects/AGENT_MEMORY_SYSTEM/events.jsonl` contains append-only events `EVT-AGMS-20261018-001..003`. Event 003 corrects the direction of a relation in event 002 via an overlay; do not rewrite either prior event. This is a concrete regression case for a future pre-write relation validator.

## Verification boundary
- A real archive run was not possible in this session: the Library file service refused raw-byte materialization of the selected ZIP. Do not claim real-source verification.
- The importer stages conversation JSON only. Manifest reconciliation, binary attachment inventory, full external chat coverage, power-loss/failure-injection tests, and automatic live ChatGPT capture remain unverified or unimplemented.
- The PR includes unrelated project-history paths and is not scope-clean or merge-ready.

## Immediate next actions
1. Verify exact-head CI after the latest implementation and checkpoint commits; read back the final changed files and check JSONL parsing/unique event IDs.
2. Obtain authorized local raw bytes for the intended export; run the importer and record its source hash, archive structure, counts and gaps without uploading private content to GitHub.
3. Add failure-injection around SQLite commit/checkpoint boundaries; test Windows lock behavior separately if Windows is a target.
4. Add/reuse a pre-write temporal relation-direction validator and regression-test it against `EVT-AGMS-20261018-003`.
5. Continue PR scope cleanup only with a verified preservation destination for out-of-scope history.

## Operating rules
- Preserve raw source separately from extracted/candidate/canonical memory.
- Never treat a summary as a replacement for source history or import time as event time.
- A passing CI run does not prove complete chat/attachment coverage, multi-process safety on every filesystem, or live ChatGPT integration.
- Keep PR #22 Draft/open/unmerged. Do not modify `main`, delete history or merge without explicit user permission.
