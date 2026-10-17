# PRE_ACTION — 2026-10-17

## Active goal
Fix the confirmed importer/staging conversation-identity mismatch before resuming archive-scope audit work.

## Confirmed defect
The importer and staging layer use different fallback IDs for conversations without `id`/`conversation_id`. The staging fallback omits ordinal scope and can collide for identical ID-less conversations.

## Plan
1. Reuse the importer's canonical `conversation_id(item, ordinal)` identity function from archive staging rather than maintaining a second fallback algorithm.
2. Enumerate top-level conversations in source order and use the same ordinal when deriving IDs.
3. Add a regression test with two identical ID-less conversations, proving importer ordinals and staged source locators remain distinct and consistent.
4. Run CI on the exact code head, read back the change, and record the result.
5. Only after this is stable, resume the deferred read-only archive audit design.

## Safety
Do not invent conversation identity from non-unique content alone; retain ordinal scope. No real archive import, no merge, and no `main` modification.
