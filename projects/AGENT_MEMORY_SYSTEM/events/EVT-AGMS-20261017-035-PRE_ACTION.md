# PRE_ACTION — 2026-10-17

## Decision from importer review
The existing raw importer already has regression coverage for interruption/resume, process crash, ZIP member seeking, Unicode chunk decoding, truncated sources, duplicate IDs, source immutability, concurrent runs, and idempotent replay. No new defect in those parser paths is established by this read-only review, so do not rewrite the importer.

## Concrete integration gap
The handoff explicitly says the current source-ingestion runner starts from a staging `archive_snapshot.json` and does not invoke `resumable_chat_import.py`. The raw importer and staging/registry runner therefore exist as separate stages, and there is no single production CLI that begins with an original export and carries the same immutable snapshot through raw import → staging → metadata-only source registration. The E2E test covers the stages in a test harness, not as one user-invocable command.

## Planned minimal change
Add a small orchestration CLI that:
1. calls the existing resumable raw importer;
2. stops unless the raw import status is `RAW_COMPLETE` or exact-source `ALREADY_COMPLETE`;
3. builds staging from the importer's immutable snapshot path, never from a potentially changed original source path;
4. runs the existing source-ingestion runner in dry-run by default, with explicit opt-in for metadata-only registry apply;
5. emits each stage's result and preserves the existing honest downstream-pending boundary.

Do not duplicate parser logic, merge semantic memory, or alter existing tools. Add integration tests using a synthetic export for the happy path, resume/replay behavior, and a changed-source/truncated-source gate. No actual user archive is available; all new tests remain synthetic.

## Safety and verification
- Branch: `feature/dialogue-stm-source-references-20261017`; PR #31 stays Draft/open/unmerged.
- Do not change `main`, merge PRs, or write raw conversation text to the repository.
- Read back new files from GitHub and require CI success on the exact resulting HEAD.
