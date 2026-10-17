# PRE_ACTION — 2026-10-17

## Task
Continue the existing raw chat-history ingestion work in `alexbotleh-oss/agent-knowledge-base` without requesting a new ChatGPT archive.

## Confirmed context
- PR #31 is Draft/open/unmerged on `feature/dialogue-stm-source-references-20261017`; exact HEAD before this step is `d179786c3df805e9bc6515bddcb10dcb8622b77d`.
- Exact-head CI run `39008178323` completed successfully.
- The branch already has `tools/resumable_chat_import.py`, `tools/archive_registry_staging.py`, `tools/source_ingestion_runner.py`, and a read-only archive audit tool with synthetic tests.
- The handoff says to audit and finish the existing partial pipeline, not restart importer design or repeat accepted agent-report analysis.
- Available Library materials include four `История_part00x.pdf` files and various project ZIPs. The enumerated Library ZIP inventory (266 files) did not contain `conversations.zip`, `export_manifest.json`, or `conversation_asset_file_names.json`. A ZIP named `archive-2026-10-07_16-01-58.zip` was inspected and contains Recipe Manager project documents, not a ChatGPT export. No raw ChatGPT archive is currently available in the working container or verified Library inventory.
- The current conversation contains only two text notes, not a raw archive. Do not ask the user to request a new archive at this stage.

## Scope for this step
Inspect the existing raw importer and its regression tests for a concrete correctness gap in interruption/resume, truncation handling, source immutability, or chronology. Make at most one narrowly scoped fix if the source and tests establish a defect. Do not alter `main`, merge any PR, delete source records, or claim real-archive acceptance.

## Verification
- Add or update a regression test that fails on the defect and passes after the fix.
- Verify read-back from GitHub at the exact resulting branch HEAD.
- Verify GitHub Actions for that exact HEAD before claiming CI success.
- Record source availability limits and any process deviation honestly in POST_ACTION.

## Process note
The initial read-only source inventory for this user request was performed before this PRE_ACTION record was written. This record governs the next inspection/edit phase and does not retroactively claim otherwise.
