# PRE_ACTION — 2026-10-17

## Active goal
Continue strengthening archive completeness checks using synthetic fixtures only. The attachment-marker boundary now passes; next cover messages whose export lacks a message ID.

## Why this matters
`archive_registry_staging.py` counts missing message IDs and builds stable source locators from archive/conversation/node identity. The importer must not invent a source message ID, and missing IDs must keep coverage partial instead of silently implying completeness.

## Plan
1. Add a focused roundtrip test with one missing message ID.
2. Verify the original bytes/hash remain intact, coverage is partial, the missing-ID count is explicit, and stable node-based provenance survives the sanitized adapter without inventing an ID.
3. Run CI on the exact head, read back the test/result, and record limits.

## Safety
No real archive import, no merge, and no `main` modification. Preserve the source as evidence and treat the missing ID as unknown rather than fabricating one.
