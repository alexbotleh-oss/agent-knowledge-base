# HANDOFF — AGENT_MEMORY_SYSTEM

Updated: 2026-10-18

## Active goal
Continue building a reliable, resumable raw-history intake pipeline while preserving source bytes, chronology, provenance, conflicts and unknowns. Raw import and semantic analysis remain separate phases.

## Live baseline
- Repository: `alexbotleh-oss/agent-knowledge-base`.
- Branch: `export/cross-project-experience-rollup-20261012`.
- PR #22: [open / Draft / unmerged](https://github.com/alexbotleh-oss/agent-knowledge-base/pull/22).
- `main` last verified at `a0c12ba849a3416f50e1289d8f0dd20844e1e51f`; do not modify or merge without explicit permission.
- Before the latest checkpoint-record commits, exact-head CI passed on `3d7aabfd266fc742a4bc1cd4355d54fd93178188` in [run #39124050309](https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/39124050309). The workflow ran 77 unittest tests and memory validation successfully. **Recheck CI for the current live HEAD** after the checkpoint updates.

## Current implementation state
- `tools/resumable_chat_import.py` is an existing local-first prototype, not a new/unimplemented proposal. It stores a hash-verified immutable source snapshot, incrementally parses one conversation object at a time, stages opaque payloads in SQLite, journals batches and checkpoints transactionally, supports JSON/ZIP input and resumable/idempotent runs.
- New integrity gate `_verify_staged_integrity()` validates staged payload JSON, payload SHA-256, and contiguous source ordinals before resume, before marking `RAW_COMPLETE`, and before returning `ALREADY_COMPLETE`. Corruption sets `FAILED`, appends `INTEGRITY_FAILED`, and raises.
- Regression tests now cover tampering after a completed import and tampering at a saved resume checkpoint. `core/source_ingestion_protocol.md` records this contract. The code and tests were committed; exact-head CI for the final checkpoint-record commits is pending.
- A real archive run was **not** possible in this session: the Library file service refused raw-byte materialization of the selected ZIP. Do not claim real-source verification.

## Remaining gaps
1. Obtain authorized local raw bytes for the intended export; run the importer and record source hash, archive structure, counts and any gaps without uploading private content to GitHub.
2. Add a single-writer/concurrency guard and failure-injection tests around SQLite commit/checkpoint boundaries.
3. Inventory manifest entries and attachment payload availability separately; this importer currently stages conversation JSON only and does not prove external attachment completeness.
4. Reconcile the PR's unrelated project-history paths and mixed reports safely; PR #22 is not scope-clean and is not merge-ready.

## Operating rules
- Preserve raw source separately from extracted/candidate/canonical memory.
- Never treat a summary as a replacement for source history; never infer event time from import time.
- A passed structural/CI test does not prove complete chat coverage, attachment coverage, multi-process safety or live ChatGPT auto-capture.
- Keep PR #22 Draft/open/unmerged. Do not modify `main`, delete history or merge without explicit user permission.
