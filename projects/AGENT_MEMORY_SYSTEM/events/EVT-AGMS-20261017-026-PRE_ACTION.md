# PRE_ACTION — 2026-10-17

## Active goal
Strengthen the main importer-to-memory acceptance path so it exercises the actual ZIP export format, not only a bare `conversations.json` file.

## Current evidence
- Separate importer tests cover ZIP input and ZIP resume.
- Separate staging tests cover attachment markers and partial coverage.
- The main E2E test currently uses JSON, so it does not yet prove that one resumed ZIP snapshot flows through staging, sanitized intake, provenance, promotion, indexing, and restore as a single path.

## Plan
1. Convert the existing E2E fixture to a synthetic ZIP containing exactly one `conversations.json` and one fake binary attachment payload.
2. Add an attachment marker to a synthetic message and verify the immutable ZIP snapshot/hash remains the source identity, coverage remains partial, and the payload is not claimed as inspected.
3. Preserve existing assertions for resume, message order/timestamp ties, parent/child links, sanitized registry, task restore, and approved memory retrieval.
4. Run CI on the exact head, read back results, and report limits clearly.

## Safety
The archive and attachment are synthetic. This does not import the user's real archive or claim attachment completeness. No merge and no `main` modification.
