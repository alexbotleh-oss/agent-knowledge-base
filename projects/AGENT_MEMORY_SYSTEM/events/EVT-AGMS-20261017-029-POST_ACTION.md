# POST_ACTION — 2026-10-17

## Investigation result
The proposed read-only archive audit is paused before implementation because inspection exposed a more fundamental cross-stage identity defect that should be corrected first.

## Confirmed code mismatch
- `tools/resumable_chat_import.py::conversation_id(item, ordinal)` uses `source_id` when present; otherwise it generates an ordinal-scoped ID `ordinal-{ordinal}-{hash(canonical compact JSON)}` and labels it `snapshot_ordinal_fallback`.
- `tools/archive_registry_staging.py::_build_unlocked` currently uses a different fallback, `conversation-unknown-{hash(default JSON serialization)}`, and does not include the top-level conversation ordinal.
- Therefore a conversation with no ID does not have the same identity in the importer and staging layers. Two identical ID-less conversations can also collide in staging's `seen` locator check even though the importer can distinguish them by ordinal.

## Why this takes priority
An audit report should not paper over inconsistent identities. The importer and downstream staging must agree on source identity before the audit can reliably cross-check raw rows against derived message records.

## Scope adjustment
The audit-report task remains deferred at its first step (inventory/contract design); no audit tool has been created. Next action is to unify fallback identity generation and add a regression test for repeated ID-less conversations. After that passes CI, resume the read-only audit design.

## Safety
No code changed in this investigation. No merge and no `main` modification.
