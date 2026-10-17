# Raw chat-import read-back verifier — 2026-10-18

## Purpose

Continue the resumable raw-import work without repeating the PR #38/#39 integration audit. The existing importer already stages opaque conversation JSON into SQLite and supports durable batch checkpoints. This addition provides an independent, read-only check that the staged records still match the immutable source snapshot.

## Source files read

- `tools/resumable_chat_import.py` on `feature/experience-first-adaptive-analysis-20261017`: confirmed existing immutable snapshot hashing, SQLite staging, byte/ordinal checkpointing, process-level resume, and idempotent replay paths.
- `tests/test_resumable_chat_import.py`: confirmed existing synthetic coverage for interruption/resume, process crash rollback, replay, ZIP input, Unicode, duplicate source IDs, invalid and truncated JSON.
- `core/source_ingestion_protocol.md`: requires raw preservation before semantic extraction and says archive CRC/structure alone does not establish source completeness.

## Changes persisted

- Added `tools/verify_resumable_chat_import.py`.
  - Opens the existing import database read-only.
  - Verifies snapshot byte count and SHA-256.
  - Streams the immutable JSON/ZIP source and compares each staged conversation's locator, ID, identity method, serialized payload, payload hash, ordinal, and byte offset.
  - Checks the persisted checkpoint against staged rows.
  - Returns `PASS` only for a complete source-to-staging match, `PARTIAL` for an exact staged prefix of a non-complete import, and `FAIL` for mismatches.
  - Does not repair state, rewrite records, or promote semantic memory.
- Added `tests/test_verify_resumable_chat_import.py` with seven synthetic tests: complete read-back, resumable partial prefix, tampered payload, missing row under a complete status, modified snapshot, ambiguous multiple snapshots, and empty export.
- Read both new files back from GitHub; the exact contents are present on the PR #39 branch.

## Verification status

- Code-under-test HEAD: `05058571f2e2ed90e2af3d5ef8a581f43f818e4f`.
- First exact-head workflow run #39070052586 for code-under-test SHA `05058571f2e2ed90e2af3d5ef8a581f43f818e4f` **FAILED before unit tests ran**: the strict write-contract audit classified four SQLite `.execute()` calls as `UNCLASSIFIED`. The calls are SELECT-only against a database opened with `mode=ro`; the audit's contract registry had no entry for this new tool. Added an explicit read-only contract entry in `tools/audit_write_contracts.py` at follow-up code HEAD `2fa702cdbc551e0b3760a3d4cb14db0d7ddfc384`. Exact-head CI for that follow-up SHA is **NOT YET VISIBLE**; tests remain unverified.
- The source files were read back from GitHub after writes, so persistence of the implementation and tests is verified.
- No full native ChatGPT export was available in this turn. Synthetic fixtures cannot establish real archive completeness, message chronology, or attachment mapping.

## Next action

Obtain exact-head CI for `2fa702cdbc551e0b3760a3d4cb14db0d7ddfc384`, inspect whether the strict audit now passes and whether the seven new tests pass, then fix any remaining failures before acceptance. After that, run the importer and read-back verifier against the actual native ChatGPT export when its bytes are available. Keep semantic extraction and memory promotion as later stages. Do not merge PR #39 or change `main` without explicit user authorization.
