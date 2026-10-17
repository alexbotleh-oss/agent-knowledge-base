# PRE_ACTION — 2026-10-17

## Active goal
Build the next useful layer after synthetic E2E acceptance: a reusable, non-semantic audit of an imported archive so an eventual real export can be checked for byte integrity, record counts, ordinal continuity, missing metadata, and known coverage gaps before any semantic extraction.

## Evidence
- The ZIP-based importer → staging → sanitized intake → approved memory E2E test passes in CI.
- Separate tests now cover equal-timestamp source ordering, causal links, attachment markers staying partial/uninspected, and missing message IDs staying explicit.
- These are fixture tests; there is not yet a single user-facing audit report that can be run against an actual local import directory and its staging manifest.

## Plan
1. Inspect existing audit/validation tools to avoid duplication.
2. Define a read-only report that verifies immutable snapshot SHA/size, importer status/count/ordinal sequence, per-payload hashes, and optional staging manifest/record hash/count.
3. Report known limitations separately from integrity failures; do not infer semantic completeness or attachment completeness.
4. Add focused tests using temporary synthetic JSON/ZIP data, run CI, read back changes, and verify latest HEAD.

## Safety
No real archive import or upload. The tool must be read-only, must not rewrite/repair source data, and must never mark semantic memory approved. No merge and no `main` modification.
