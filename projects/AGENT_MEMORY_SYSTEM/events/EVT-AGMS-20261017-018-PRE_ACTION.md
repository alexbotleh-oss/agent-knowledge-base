# PRE_ACTION — 2026-10-17

## Active goal
Continue from the passing synthetic importer-to-memory pipeline test and strengthen the acceptance criteria that matter to the archive-import project: preserve chronology, causal links, and recoverable task state, not merely successful ingestion and indexing.

## Current evidence
- The current importer-to-memory acceptance test passes in CI on code/test commit `25277bea0d0cce7b49a10199e30084eb4103f6b0`; the latest branch head after event logging also has successful run `39007236303`.
- The test currently checks importer pause/resume, snapshot/payload hashes, sanitized intake, provenance, semantic promotion, index and restore.
- It does not yet explicitly assert that the staged/registered user and assistant nodes retain their source chronology and parent/child graph, nor that the task recovery portion of the restore packet remains present.

## Plan
1. Extend the existing synthetic fixture assertions only; do not create a duplicate pipeline test.
2. Assert source message order/timestamps and parent/child edges survive staging, sanitized intake, and registry registration.
3. Assert the restore packet contains the task-state recovery result alongside approved memory retrieval.
4. Read back the test, run exact-head CI, and record results with limits.

## Safety
No merge and no `main` modification. Use the existing synthetic fixture; do not request or import the user's real archive yet. This PRE_ACTION record is written before the test edit.
