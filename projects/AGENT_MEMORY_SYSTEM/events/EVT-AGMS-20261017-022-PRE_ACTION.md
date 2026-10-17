# PRE_ACTION — 2026-10-17

## Active goal
Continue validating archive completeness without importing the user's real archive yet. Add a focused regression test for the known binary-attachment boundary.

## Current evidence
- The staging manifest explicitly states that binary attachment payloads are not extracted or verified.
- `archive_registry_staging.py` marks coverage `partial` when attachment markers are present and records `attachment_payloads_inspected=False` for those messages.
- The current synthetic E2E fixture does not include attachment markers, so it does not prove that this limitation is surfaced instead of falsely claiming complete coverage.

## Plan
1. Add one focused test to the existing source-ingestion roundtrip suite using a synthetic attachment marker.
2. Assert the raw source bytes/hash remain unchanged, coverage stays partial, the record retains an attachment marker, and payload inspection remains explicitly false.
3. Run CI on the exact resulting head, read back the test and result, and keep the scope limited to the known boundary.

## Safety
Do not request/import the user's real archive yet. Do not infer that binary payloads are complete or readable. No merge and no `main` modification.
