# PRE_ACTION — 2026-10-17

## Active goal
Continue improving continuity and memory writeback based on the successful importer-to-memory acceptance test. Investigate a concrete compatibility risk found during final verification before starting the next code change.

## Evidence prompting this action
- CI run `39007059758` passed for code/test head `d60ab7576dfba0264e0ec11308bb2cb9cbab870d`; it ran 324 Python unittest tests (1 skipped) and 13 Node tests (0 failed), and the new acceptance test reported `ok`.
- Latest PR head after recording the result is `e6f06f512e4d6cbf628f8a344c14d58893e7436a`; comparison with the tested head shows exactly one added file: `projects/AGENT_MEMORY_SYSTEM/events/EVT-AGMS-20261017-014-POST_ACTION.md`.
- `tools/verified_session_restore.py` currently treats only the flat `projects/AGENT_MEMORY_SYSTEM/events.jsonl` path as metadata-only; it does not allow event records under `projects/AGENT_MEMORY_SYSTEM/events/`. This may cause future restore to reject a branch whose only new commits are the append-only event records this workflow writes.

## Plan
1. Confirm the current allowlist and tests that enforce metadata-only descendant behavior.
2. Design the narrowest safe rule for recognized event records, without allowing arbitrary source/code files to bypass CI.
3. Add focused tests for recognized event records being allowed and unrelated files under the event directory being rejected.
4. Run CI on the resulting exact head, read back the changes, and report the remaining limits.

## Safety
Do not merge PRs or modify `main`. Preserve the successful acceptance test. Do not weaken code/CI freshness checks for arbitrary files. This PRE_ACTION entry is committed before the new code-editing work begins.
