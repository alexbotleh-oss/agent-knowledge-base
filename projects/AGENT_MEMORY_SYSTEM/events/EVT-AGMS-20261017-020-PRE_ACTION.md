# PRE_ACTION — 2026-10-17

## Active goal
Strengthen archive-history fidelity after the successful chronology/causal-link acceptance run. Specifically, ensure equal message timestamps do not cause arbitrary source reordering.

## Evidence
- The archive staging builder iterates conversations and their `mapping` entries in source order, but then sorts records by `(timestamp missing, timestamp, source_locator)`.
- `source_locator` is derived from node IDs, not chronology. When two messages have equal timestamps, lexical node IDs can reorder them against the original export order.
- The existing E2E fixture has unique timestamps, so it does not detect this case.

## Plan
1. Make the staging sort stable for equal timestamps by removing the non-chronological locator tie-breaker while retaining known timestamps before missing timestamps.
2. Extend the existing synthetic E2E fixture with a third message inserted after another message but carrying the same timestamp and a lexically earlier node ID.
3. Assert source order, timestamp order, and parent/child links survive sanitized intake and canonical source registration.
4. Run CI on the exact resulting head, read back changes, and record results.

## Safety
No real archive import, no merge, and no `main` modification. Do not infer ordering from IDs; source order is the tie-breaker when timestamps are equal.
