# Raw chat-import read-back verifier — 2026-10-18

## Purpose

Continue the resumable raw-import work without repeating the PR #38/#39 integration audit. The existing importer already stages opaque conversation JSON into SQLite and supports durable batch checkpoints. This addition provides an independent, read-only check that the staged records still match the immutable source snapshot.

## Source files read

- `tools/resumable_chat_import.py` on `feature/experience-first-adaptive-analysis-20261017`: confirmed existing immutable snapshot hashing, SQLite staging, byte/ordinal checkpointing, process-level resume, and idempotent replay paths.
- `tests/test_resumable_chat_import.py`: confirmed existing synthetic coverage for interruption/resume, process crash rollback, replay, ZIP input, Unicode, duplicate source IDs, invalid and truncated JSON.
- `core/source_ingestion_protocol.md`: requires raw preservation before semantic extraction and says archive CRC/structure alone does not establish source completeness.

## Changes persisted

- Added `tools/verify_resumable_chat_import.py`.
  - Opens the existing import database read-only.
  - Verifies snapshot byte count and SHA-256.
  - Streams the immutable JSON/ZIP source and compares each staged conversation's locator, ID, identity method, serialized payload, payload hash, ordinal, and byte offset.
  - Checks the persisted checkpoint against staged rows.
  - Returns `PASS` only for a complete source-to-staging match, `PARTIAL` for an exact staged prefix of a non-complete import, and `FAIL` for mismatches.
  - Does not repair state, rewrite records, or promote semantic memory.
- Added `tests/test_verify_resumable_chat_import.py` with seven synthetic tests: complete read-back, resumable partial prefix, tampered payload, missing row under a complete status, modified snapshot, ambiguous multiple snapshots, and empty export.
- Read both new files back from GitHub; the exact contents are present on the PR #39 branch.

## Verification status

- Initial code-under-test HEAD `05058571f2e2ed90e2af3d5ef8a581f43f818e4f` failed run #39070052586 before unit tests: four read-only SQLite `.execute()` calls lacked an explicit contract classification. Added the missing read-only contract entry in `tools/audit_write_contracts.py`.
- Follow-up code HEAD `2fa702cdbc551e0b3760a3d4cb14db0d7ddfc384` passed GitHub Actions run [#39070199971](https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/39070199971): **486 Python tests passed, 1 skipped; 4 Node tests passed; strict write audit 162 mutation sites / 0 unclassified; canonical temporal audit and project/stack validation passed.** All seven new verifier tests passed.
- The run's task-start smoke deliberately deferred because the live branch tip had code changes after the checkpoint's recorded code head. The changed paths included this report file, which is not in the current metadata-only allowlist. Therefore code/test CI is PASS, but a fresh task-start smoke on the latest branch tip is not established.
- The source files were read back from GitHub after writes, so persistence of the implementation and tests is verified.
- No full native ChatGPT export was available in this turn. Synthetic fixtures cannot establish real archive completeness, message chronology, or attachment mapping.


## Additional ZIP preflight tests — 2026-10-18

- Fixed the ZIP attachment test fixture to use the actual synthetic source key `node-0` (not the nonexistent `node-0-user`). Read-back confirmed the fix on branch commit `1c818f88dcd5d19cd2c6e152c3156dd17b6af9be`.
- Exact-head CI run [#39070970942](https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/39070970942) passed: 488 Python tests (1 skipped), 4 Node tests, repository validation, canonical event-log temporal audit, and restore/task-start smoke.
- Added two more fail-closed tests on code HEAD `c5845d235a9f89ee4517092dfc7a9941f2744e21`:
  - ZIP with more than one member named `conversations.json` is rejected and stages zero conversations.
  - Corrupt ZIP is rejected and stages zero conversations.
- Exact-head CI run [#39071042500](https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/39071042500) passed: **490 Python tests, 1 skipped; 4 Node tests; strict memory/write validation, canonical event-log temporal audit, project/stack validation, and restore/task-start smoke all passed.**
- The two new ZIP rejection tests, attachment-byte preservation test, and evidence-package-vs-native-export test all passed within this run.
- This closes the currently testable synthetic ZIP boundary for these cases; it does not establish the completeness or exact attachment-reference semantics of the not-yet-available native archive.

## Remaining preflight work before requesting the native archive

1. Add an explicit, read-only archive inventory report: member paths and sizes, duplicate paths, nested archive markers, CRC/read errors, and candidate attachment files. Keep this inventory separate from semantic interpretation and avoid assuming attachment formats from filenames alone.
2. Add a source-reference audit that reports candidate attachment references and unresolved/ambiguous matches without rewriting raw conversation payloads.
3. Verify the report and inventory against the actual archive only after its bytes arrive. Until then, preserve these as synthetic-test boundaries rather than claiming native-export compatibility.
4. Keep import, independent read-back, attachment inventory, and later semantic extraction as separate stages. Do not promote staged raw content into canonical memory.

No merge was performed and `main` was not changed. Approved semantic-memory registry availability and automatic ChatGPT-host invocation/writeback remain separate unresolved system boundaries.


## Read-only archive inventory preflight — 2026-10-18

- Added `tools/audit_chat_export_archive.py`: hashes the original ZIP, lists each member path/size/compressed size/CRC, detects duplicate member paths, counts candidate `conversations.json` members, records filename-only nested-archive hints, and checks every member CRC. It never extracts or changes the source and does not infer that non-conversation files are valid attachments.
- Added `tests/test_audit_chat_export_archive.py` with six synthetic cases: valid inventory and source immutability, duplicate paths, missing conversations JSON, member CRC corruption, non-ZIP input, and missing source.
- Exact-head CI run [#39071127180](https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/39071127180) passed on `47c337be6ab867c08bc297786a1e34e22b7e1a4d`: **496 Python tests, 1 skipped; 4 Node tests; strict write audit 162 mutation sites / 0 unclassified; memory, event-log, and project/stack validation passed.**
- Important boundary: the workflow's restore/task-start smoke step **deferred** because the current code checkpoint predates the new code/test/report paths. The job itself passed, but this run does not establish a fresh task-start smoke on this branch tip. The previous known smoke evidence remains historical; do not label this run as a new smoke PASS.
- Next: refresh the continuity checkpoint through the established checkpoint workflow using the exact verified code HEAD and CI run, then rerun the metadata-descendant restore/task-start smoke. After that, add the conservative message-reference-to-archive-member reconciliation. Full native archive completeness and attachment semantics remain unverified until the actual archive bytes are available.


## Conservative attachment-reference reconciliation preflight — 2026-10-18

- Added `tools/audit_chat_attachment_references.py`. It streams the raw conversation array, preserves each candidate reference's conversation ID/ordinal and JSON Pointer, and compares only exact source values to archive member paths. It deliberately does not infer matches from basenames, URI parsing, identifier substrings, or extensions.
- Results remain `SCAN_COMPLETE_REVIEW_REQUIRED` even when no candidate references are found: detection is heuristic, and an exact path match is only a path-level correspondence, not proof that the member is the intended attachment.
- Added six synthetic tests covering exact path matches, unresolved URI-like references, duplicate-path ambiguity, JSON Pointer escaping, missing conversations JSON, and the “zero candidates is not proof of no attachments” boundary.
- Exact-head CI run [#39071356427](https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/39071356427) passed on `1f12c4fc116df9bafc3f1f9e3857a65f137505aa`: **502 Python tests, 1 skipped; 4 Node tests; strict write audit 162 mutation sites / 0 unclassified; memory, event-log, and project/stack validation passed.**
- As expected, restore/task-start smoke deferred because these new source/test files are not metadata-only descendants of the currently recorded code SHA. Refresh the checkpoint to this exact code/test SHA and CI run, then rerun the smoke. The previous successful smoke remains valid for its recorded code head, but is not a smoke run on this new revision.
- Native-export completeness, exact message-to-attachment mapping, and live ChatGPT-host invocation/writeback remain unverified.


## Raw importer ambiguity guards — 2026-10-18

- Fixed a source-loss edge case in `tools/resumable_chat_import.py`: duplicate JSON object keys are rejected rather than silently keeping only the last value during decode/re-serialization.
- Added a second strictness guard: non-standard JSON numeric constants (`NaN`, `Infinity`, `-Infinity`) are rejected rather than staged as non-standard JSON.
- Aligned ZIP conversation-candidate selection with the inventory audit: directory entries named `conversations.json` are not treated as conversation payloads.
- Added `tests/test_import_edge_cases.py` covering duplicate-key rejection with zero staged rows, non-standard numeric constant rejection with zero staged rows, directory-entry filtering, and duplicate member-path agreement between inventory and importer.
- Exact code/test HEAD `c09e5a5d72f345fc534289981c9b12d971946c74` passed CI run [#39072044539](https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/39072044539): **506 Python tests, 1 skipped; 4 Node tests; strict write audit 162 mutation sites / 0 unclassified; memory/event-log/project validation passed.**
- Restore/task-start smoke correctly deferred on that run because the checkpoint still records the prior code HEAD; this run is not a fresh smoke PASS. The next checkpoint refresh must cite this exact code SHA and CI run before the metadata-descendant smoke is accepted.
- The source snapshot remains the byte-exact archive of record; the staged payload is decoded JSON and is not claimed to preserve whitespace/formatting byte-for-byte. Duplicate-key and non-standard-number cases now fail closed rather than silently changing semantics.


## Source-stability guards for read-only preflight — 2026-10-18

- Both `tools/audit_chat_export_archive.py` and `tools/audit_chat_attachment_references.py` now re-hash the source after scanning. If the final digest differs from the initial digest, or the source becomes unreadable, the audit returns `FAIL` instead of attaching results to a stale source hash.
- Added one synthetic regression test to each audit suite to verify fail-closed behavior on digest drift.
- Exact code/test HEAD `7417eb95fc1996e6eddfa43ee6c7505bb387060e` passed CI run [#39072317737](https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/39072317737): **508 Python tests, 1 skipped; 4 Node tests; strict write audit 162 mutation sites / 0 unclassified; memory/event-log/project validation passed.**
- Restore/task-start smoke deferred because the checkpoint still recorded the previous code SHA. Refresh the checkpoint to this exact code/test/report HEAD and CI run before accepting the next metadata-descendant smoke.
- Scope limit: the before/after digest check detects persistent source changes during the scan; it is not a filesystem snapshot and cannot prove that a source was not modified and restored between the two hashes. The importer itself stages from its verified immutable snapshot. The native archive is still required for real completeness and attachment reconciliation.


## ZIP member path safety and structured read failures — 2026-10-18

- `tools/audit_chat_export_archive.py` now flags absolute, drive-qualified, and parent-traversal member names, including traversal written with backslashes. The original member name is retained in the report; no extraction or path normalization of source data occurs. Any such entry makes the inventory `REVIEW_REQUIRED` via `UNSAFE_MEMBER_PATHS`.
- Both the ZIP inventory and attachment-reference audit now convert initial source-read failures into structured `FAIL / SOURCE_UNREADABLE` results rather than letting an `OSError` escape as an unstructured crash.
- Added synthetic regressions for POSIX absolute paths, parent traversal, Windows drive paths, backslash traversal, and unreadable-source behavior in both audits.
- Exact code/test HEAD `1bf53dce7a9dc7a149a01f624911e2548beddf69` passed CI run [#39092911318](https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/39092911318): **511 Python tests, 1 skipped; 4 Node tests; strict write audit 162 mutation sites / 0 unclassified; memory/event-log/project validation passed.**
- Restore/task-start smoke deferred on this code/test HEAD because the checkpoint still records the prior verified code SHA. Refresh the checkpoint to this exact HEAD and CI run before accepting a metadata-descendant smoke result.
- Scope boundary: this is a preflight flag, not proof that every downstream extractor is safe. The inventory itself does not extract any member.
