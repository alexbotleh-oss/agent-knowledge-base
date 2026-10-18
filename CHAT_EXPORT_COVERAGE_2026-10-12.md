# Cross-chat experience export — 2026-10-12

## Purpose and status
This is a consolidated memory-only export of project experience recovered from saved project summaries, accessible GitHub memory branches, and now a directly inspected user-provided source archive. It is not a claim that every raw chat and binary attachment has been fully exported. Overall source completeness: **PARTIAL**.

**Destination repository:** https://github.com/alexbotleh-oss/agent-knowledge-base  
**Consolidation branch:** `export/cross-project-experience-rollup-20261012`  
**Base:** `main` at `a0c12ba849a3416f50e1289d8f0dd20844e1e51f`  
**Scope:** memory, project-state, provenance, lessons and core documentation only. No application code, app database or APK was changed/built.

## Newly inspected source archive
- User supplied `conversations.zip`, containing `conversations.json` (about 43 MB uncompressed).
- Parsed **37 conversation objects** and **10,034 distinct message IDs** (7,446 assistant-role records and 2,588 user-role records in mappings).
- Conversation timestamps span **2026-09-21 through 2026-10-07 UTC**; latest update is 2026-10-07 UTC.
- 485 serialized user messages contain attachment markers, but the ZIP does not contain the referenced binary attachments.
- The ZIP does not contain the separate `chat.html`, `export_manifest.json`, `conversation_asset_file_names.json` or the other attachment files shown in the user's export folder.
- A previous ORGANISM note described a 74-chat / 10,034-message archive/search gap. The newly supplied JSON has 37 conversation objects but the same 10,034 distinct message IDs. This discrepancy is unresolved; neither count should be silently substituted for the other. Details and attribution rules: [SOURCE_ARCHIVE_AUDIT_2026-10-12.md](SOURCE_ARCHIVE_AUDIT_2026-10-12.md).

## Authoritative project identity boundary
The user explicitly clarified during this transfer:
- **N99 / «Что приготовить» = Android APK application** (the Flet/Python Android implementation).
- **B77 / «Что приготовить» = separate HTML/WMA prototype, UI/logic and web version intended for iPhone**, repository `alexbotleh-oss/LK`.

These are separate projects despite sharing a product name and recipe domain. Do not merge code histories, event IDs, release states or acceptance claims. The current rollup's earlier phrase “RECIPE_MANAGER — Flet/Android + historical HTML/SQLite” risks conflating the projects and must be reconciled.

### RECIPE_MANAGER — N99 Android APK
- Project memory: `projects/RECIPE_MANAGER/PROJECT_STATE.md`, `TASK_STATE.md`, `EVENT_LOG.md`, `DECISIONS.md`, `LESSONS.md`, `HANDOFF.md`, `events.jsonl`, `HTML_SQLITE_REGRESSION_2026-10-12.md`, `RECIPE_SEARCH_REQUIREMENTS.md`, `BUILD_PACKAGING_ATTEMPT_2026-09-22.md`, `CHAT_TRANSFER_RECONCILIATION_2026-10-12.md`, `SOURCE_COVERAGE.md`.
- Consolidated accessible PR #20 memory with parallel PR #19 camera-decode evidence and PR #17 historical Core Lite/JNI/WebView diagnostic history. Relevant ingredient-equivalence rules may be shared only as independently supported requirements; HTML/SQLite defects must not be described as Android APK defects.
- Event IDs: 20 current EVT-2026… records plus 6 historical EVT-RM-* records. L-RM-022 is camera decode; L-RM-023 is task-scope correction. The gap EVT-20261012-007 remains unexplained.
- Source status: PARTIAL. Exact current Android source/runtime, original build artifacts and several diagnostic logs remain unavailable.

### B77_HTML_PWA — separate HTML/WMA web contour in alexbotleh-oss/LK
- Existing project chain copied from PR #5: `PROJECT_STATE.md`, `TASK_STATE.md`, `EVENT_LOG.md`, `DECISIONS.md`, `LESSONS.md`, `HANDOFF.md`, plus `lessons/cross_project_review_20261012.md`.
- Keeps B77 separate from N99 / RECIPE_MANAGER. Scanner/theme/water, Shopping/Products, baseline preservation, archive verification and historical rollback evidence retain their confidence/status labels.
- The supplied source archive includes earlier HTML-specific incidents (recipe list/import, DB-path access, nutrition and delete controls, ingredient normalization, shopping flow) from September 22 onward. These must be audited as HTML-contour evidence and only assigned to B77 where message-level provenance supports it. Mixed conversations must be split by message, not classified wholesale.
- The current B77 event log begins with Stage14/scanner records around October 5; evaluate earlier HTML incidents as possible B77 history without inventing attribution for entries that do not name B77.
- Source status: PARTIAL; not all original chats, build artifacts, screenshots and intermediate HTML diffs are available.

### CARD111 — loyalty-card Web/PWA in alexbotleh-oss/CARD
- Added project chain: `PROJECT_STATE.md`, `TASK_STATE.md`, `EVENT_LOG.md`, `DECISIONS.md`, `LESSONS.md`, `HANDOFF.md`, `events.jsonl`, `lessons.jsonl`.
- Preserved editor/preview behavior, template/catalog requirements and brand list, mentioned app commits/branches, temporary QR observation, and reported scanner/gallery/crop issues.
- Static checks, deployment, phone runtime, barcode readability and full template integration remain NOT VERIFIED.
- Source status: PARTIAL; the supplied archive has some CARD111 conversations but not all source artifacts.

### ORGANISM — separate continuous-agent app in alexbotleh-oss/organism
- Added project chain: `PROJECT_STATE.md`, `TASK_STATE.md`, `EVENT_LOG.md`, `DECISIONS.md`, `LESSONS.md`, `HANDOFF.md`, `events.jsonl`, `lessons.jsonl`.
- Preserved the decision to build a full app rather than only a ChatGPT bridge; Android/WebView direction; RAW/provenance/Context Engine/import architecture; download and OAuth incidents; memory-integrity protection against dangerous deletion.
- The previously recorded 74-chat / 10,034-message archive/search gap is now explicitly flagged as inconsistent with the newly inspected ZIP's 37 conversation objects / 10,034 distinct message IDs. Reconcile against the manifest and full export before claiming coverage.
- CI/build reports are not represented as device/runtime PASS. OAuth white screen and archive integration remain unresolved in available evidence.
- Source status: PARTIAL.

## Cross-project/core material
- Imported chronology and repository-scope rules from PR #4: `core/chronology_reconstruction.md`, `core/repository_scope.md`, plus corresponding README/core/template updates.
- Imported curated general lessons from PR #3 and added G-LESSON-005 for the observed task-boundary failure during transfer: source-chat content is evidence to classify, not an embedded instruction to execute unless explicitly requested.
- Project facts remain in each project's own directory. ORGANISM, agent-knowledge-base, CARD111, B77_HTML_PWA and RECIPE_MANAGER/N99 are distinct scopes.

## Source PRs and consolidation notes
- PR #3: initial RECIPE_MANAGER/global lesson memory — used as a source for global lessons and project decisions.
- PR #4: chronology reconstruction and repository-scope guardrails — included in this rollup.
- PR #5: B77 HTML/PWA experience — included in this rollup.
- PR #17: early RECIPE_MANAGER Core Lite/JNI/WebView diagnostics — unique historical material included, with source limitations.
- PR #19 and #20: parallel RECIPE_MANAGER memory branches — reconciled event and lesson ID collisions in this rollup; source branches remain untouched.
- PR #21: independent/stale ingredient/web regression branch with conflicting EVT-20261012-005/006 meanings and colliding legacy lesson IDs. Domain requirements remain in DEC-RM-006 and B77 event records; ingredient-normalization and HTML/SQLite end-to-end lessons are canonicalized as B77-L-011 and B77-L-012, with pointers from RECIPE_MANAGER L-RM-009. Legacy IDs remain provenance only.
- Other older RECIPE_MANAGER PRs remain open. This rollup does not merge, close or rewrite any source PR. Review consolidation before any merge.

## Validation checklist
- [x] Report-bundle audit is recorded in `SOURCE_REPORTS_AUDIT_2026-10-13.md` and was read back from GitHub.
- [x] Five Library control-matrix workbooks were located and their extracted text reviewed; summary preserved in `projects/RECIPE_MANAGER/MASTER_CONTROL_MATRIX_AUDIT_2026-10-13.md`.
- [x] Retrieved and reviewed all 60 current PR paths individually for availability, structure/headings, unresolved-status markers, and change scope; PR file list confirms all changes are within memory/core documentation, templates, audits, and project-memory records. This is not equivalent to line-by-line semantic reconciliation of every claim against primary chat messages; that work remains open.
- [x] Parsed current JSONL files: RECIPE_MANAGER events 25/25 valid and unique; B77 HTML/PWA events 22/22 valid and unique; CARD111 events 15/15 and lessons 6/6 unique; ORGANISM events 7/7 and lessons 5/5 unique; global lessons 5/5 unique.
- [x] Reconciled original event/lesson ID collisions: EVT-20261012-017/018 are task-scope/transfer events, EVT-20261012-019 is PWA camera decode; L-RM-022 is camera decode, L-RM-023 is task boundary.
- [x] The initial compare recorded 46 changed paths, all memory/core documentation. The current PR API reports 60 changed files, and all 60 were individually retrieved and scope-reviewed. No app source, HTML/JS project code, databases, or APKs are reported among the changed paths.
- [x] Historical checkpoints: PR #22 was 206 commits ahead with 59 changed files, then 230 commits ahead with 60 files. At the 206-commit checkpoint, 208 paginated commit entries contained 152 unique subjects reviewed as export/docs/memory-oriented. This is not a full historical diff review. Current live comparison is recorded in the 2026-10-13 checkpoint below. Keep Draft/open and do not merge without explicit permission.
- [x] Draft PR #22 remains open and unmerged: https://github.com/alexbotleh-oss/agent-knowledge-base/pull/22.
- [x] Historical CI runs #103/#104, #120 and #182 passed on their stated SHAs. The latest checkpoint and exact HEAD/CI result are recorded below; structural checks do not prove historical-source completeness.
- [x] Moved clearly HTML/PWA-specific source events out of N99's event chain: early HTML/SQLite regressions, EVT-20261012-014, PWA Shopping/Products EVT-20261012-016 and browser camera decode EVT-20261012-019 now live under B77. Early September attribution to B77 remains medium confidence where the source conversation does not name the project.
- [x] Five additional B77 events were reconstructed directly from raw October 3–5 user messages and added with source conversation/message IDs; root causes remain unconfirmed without diffs.
- [x] Global lesson `G-LESSON-004` source path corrected to canonical B77 event. HTML-specific rules in `L-RM-019/021/022` and HTML evidence in `L-RM-004` are now cross-project pointers; canonical B77 lessons `B77-L-008/009/010` hold the HTML-specific rules.
- [x] RECIPE_MANAGER EVENT_LOG duplicate heading `EVT-20261012-013` was deduplicated after merging its unique wording; the JSONL record remains. `EVT-20261012-014/016/019` are cross-project pointers to B77, while 10 structured RECIPE_MANAGER records remain without standalone narrative headings (not duplicated; see source audit).
- [x] CARD111 narrative and structured event parity is restored: 15 event headings in `EVENT_LOG.md` match 15 structured JSONL records; nine raw-source events were added and two lessons were synchronized across Markdown/JSONL.
- [x] B77 narrative and structured event parity is restored: 22 event headings in `EVENT_LOG.md` match 22 structured JSONL records; nine pre-existing narrative events were added without duplicates.
- [x] Lesson evidence-path audit passed: all structured lesson evidence refs that name a project event JSONL resolve to an event ID in that exact project file; all created_from_event_ids resolve to a known event. Global G-LESSON-004 now points to B77's canonical event file.
- [x] October 2 mixed-scope source split: B77/PWA IndexedDB and scanner failures are recorded as EVT-B77-20261002-001/002; the separate N99 expiry-edit/Add Product request is EVT-RM-20261002-001 and remains a pending design item, not an accepted implementation decision.
- [x] B77 event coverage is now 22/22 after the two additional October 2 source events; RECIPE_MANAGER is 25/25 after recovery of EVT-20261012-007 from PR #8.
- [x] Structured reference audit found and repaired stale `EVT-20260922-001` references to canonical B77 event `EVT-B77-20260922-001`; re-read seven JSONL files: 69 events + 16 lessons parsed, no parse errors/duplicate IDs/unresolved structured event references. Details in `SOURCE_REPORTS_AUDIT_2026-10-13.md`.
- [ ] Continue message-by-message review of remaining mixed N99/B77 conversations before treating the project histories as complete.

- [x] Historical checkpoint after adding the control-matrix audit: comparison reported 230 commits ahead of `main`, 0 behind, and 60 changed files. This is a dated checkpoint, not the latest branch count; see PR #22 for the current head and comparison. The earlier 208-entry/152-subject commit-message review predates later commits and is not a complete review of the current commit history.

## Known limitations
- The supplied ZIP contains exactly 37 conversation objects and 10,034 distinct message IDs. The older 74-chat note is not substantiated by this archive or the supplied report text; its origin remains unresolved. The ZIP does not prove full-export completeness and lacks the separate binary attachment bytes.
- Missing source files are not reconstructed from filenames alone. Unverified fixes remain unverified; hypotheses remain hypotheses.
- Source PRs may still show stale/conflicting content until separately reviewed. The consolidation branch is the candidate review surface, not evidence that main has been updated.
- Do not merge PR #22 without explicit user permission.


## Follow-up reconciliation — 2026-10-13

- [x] Re-read the current canonical RECIPE_MANAGER and B77 `events.jsonl` files from the consolidation branch: 24 and 22 records respectively; no JSON parse errors or duplicate event IDs in either file.
- [x] Reconciled the narrative traceability gap: ten of the 25 RECIPE_MANAGER structured events did not have standalone headings. Added a concise ID-to-summary index to `projects/RECIPE_MANAGER/EVENT_LOG.md`; no duplicate event payloads were created.
- [x] Current project event totals: RECIPE_MANAGER 25 + B77 22 + CARD111 15 + ORGANISM 7 = 69 structured events. CARD111 lessons 6, ORGANISM lessons 5 and global lessons 5 = 16 structured lessons. RECIPE_MANAGER intentionally has no `lessons.jsonl`; its Markdown lesson index remains canonical until schema-aligned source mapping is available.
- [ ] Continue primary-message reconciliation of remaining mixed N99/B77 conversations and inspect older PR branches for unique evidence not yet represented in the consolidation branch.
- [ ] Semantic completeness remains PARTIAL; no merge into `main` without explicit user permission.


## Chunked read-back checkpoint — 2026-10-13

To reduce loss of progress during intermittent connectivity, the PR was inspected in bounded batches and the results consolidated here.

- All 60 paths listed by the current PR API were fetched from the consolidation branch, including the source archive audit, report audit, all core protocols, project-state documents, handoffs, and machine-readable records.
- First-pass scope review: all changed paths are memory, core protocol, source-audit, project-state, lesson, template, or event-log artifacts. No application source, HTML/JS app code, database, or APK files are in the changed-path list.
- JSONL checks: RECIPE_MANAGER events 25/25 parseable with unique IDs; B77_HTML_PWA events 22/22 parseable with unique IDs; CARD111 events 15/15 and lessons 6/6 parseable with unique IDs; ORGANISM events 7/7 and lessons 5/5 parseable with unique IDs; global lessons 5/5 parseable with unique IDs. Total: 69 structured events and 16 structured lessons. These are structural checks, not proof of semantic completeness.
- Confirmed project boundary: early HTML/SQLite events are filed under B77_HTML_PWA with medium confidence for exact B77 attribution where the original messages do not name the project. Do not treat them as evidence of an N99 Android/APK defect.
- Source-coverage finding: the inspected archive contains 37 conversation objects and 10,034 distinct message IDs; the earlier “74 chats” count remains unsupported/unresolved. The archive lacks separate binary attachment bytes and later transfer-chat coverage, so overall completeness remains PARTIAL.
- Newly inspected control-matrix audit preserves the v1.2 workbook as a dated requirements snapshot, not proof that those functions are implemented or pass runtime tests.
- Remaining work: compare report claims and older PR branches event-by-event, resolve or preserve each possible omission/recurrence, then run CI on the final checkpoint. Do not merge PR #22 without explicit user permission.


## Additional lesson reconciliation checkpoint — 2026-10-13

Direct read-back of PR #21's legacy `lessons.jsonl` and `LESSONS.md` exposed two distinct lessons whose old IDs conflicted with canonical RECIPE_MANAGER lesson meanings: ingredient normalization (`LESSON-RM-008` / `L-RM-008`) and HTML/SQLite end-to-end regression (`LESSON-RM-009`). Both are now preserved under non-colliding canonical IDs `B77-L-011` and `B77-L-012`, with provenance and uncertainty preserved, and cross-linked from RECIPE_MANAGER `L-RM-009`. This adds no new JSONL lesson records and does not claim application fixes. The branch remains memory-only; merge is still not authorized.

## Current live checkpoint — 2026-10-13 07:42 UTC

- PR #22 HEAD at the time of verification: e3557497f757b8377a4c01a5e7d1f7ab4fbbafba; GitHub Actions Validate knowledge base PASS, run #38364347001: https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/38364347001.
- Live compare: 263 commits ahead of main, 0 behind, 60 changed paths. All changed paths remain within memory/core documentation, project-state/event/lesson records, source audits, and templates; no app source, HTML/JS application code, database, or APK was included.
- All 60 paths have been fetched and scope-reviewed in bounded batches. Detailed semantic matching of every source claim remains incomplete; source completeness remains PARTIAL.
- Additional collision repair: PR #21 ingredient and HTML/SQLite lessons are preserved as B77-L-011 and B77-L-012, with pointers from RECIPE_MANAGER L-RM-009. B77 event EVT-20261012-014 now references the canonical B77 lessons, not the conflicting legacy N99 lesson ID.
- PR #22 remains Draft/open/unmerged. Do not merge without explicit user permission.

## Live recheck — 2026-10-13 07:43 UTC

- Branch ref at the last live compare resolved to eca56274378f54dfecedb52d301cce7e0b5c65f7; compare showed 266 commits ahead of main, 0 behind, and 60 changed paths. PR #22 remained Draft/open/unmerged.
- Exact-head CI caution: the last confirmed run matching a live branch ref was run #38364347001 on e3557497f757b8377a4c01a5e7d1f7ab4fbbafba. A later completed run for 82b96bc5ee29ca6d65ebd7322cb4f9ca0bcc450f did not match the branch ref eca56274378f54dfecedb52d301cce7e0b5c65f7. The newer head's status must be verified against its own SHA.
- Source audit was updated to record this mismatch rather than treating a pass on a different SHA as current proof. This checkpoint is append-only; after this file update, re-read the branch ref and CI run for the resulting commit.
- Source completeness remains PARTIAL. The PR #21 lesson-ID conflict is now preserved under B77-L-011/B77-L-012, with canonical cross-links and source limitations.


## Bounded full-path read-back — 2026-10-13 08:10 UTC

- [x] Re-fetched all 60 paths returned by the current PR #22 changed-file listing in bounded batches. The 60-path list includes the newly added `projects/RECIPE_MANAGER/MASTER_CONTROL_MATRIX_AUDIT_2026-10-13.md`; older 59-file checkpoints are superseded by this check.
- [x] Confirmed every listed path is a memory, protocol, source-audit, lesson, template, or project-state/event/decision/handoff artifact. No application source, HTML/JS implementation, database, or APK is included in the changed-path list.
- [x] Re-read the control-matrix audit and the source/coverage audit files from the branch. They explicitly distinguish artifact requirements from implemented or runtime-verified behavior and retain the source-completeness status as PARTIAL.
- [x] Confirmed the latest observed PR head at this checkpoint was `a801eeb324e1f480c246fcb5418b33351a3c5dbf`; GitHub Actions run #38366773680 passed on that exact SHA: https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/38366773680.
- [ ] Semantic, message-by-message reconciliation of all claims and missing binary/source artifacts remains incomplete. File read-back and successful CI do not prove historical completeness.
- PR #22 remains Draft/open/unmerged. Do not merge without explicit user permission.

 
## Current structured-record reconciliation — 2026-10-17

This is a new read-back checkpoint; the historical counts above are retained as historical observations and are superseded for current totals by this section.

- Read the four project event journals from this branch again: RECIPE_MANAGER = 25 records; B77_HTML_PWA = 22; CARD111 = 16; ORGANISM = 7. Total = **70 structured events**.
- All 70 JSONL lines parse successfully. Every project journal has unique event IDs, and no event ID is duplicated across the four project journals.
- The current CARD111 count is 16, not 15, because the existing journal includes `EVT-CARD111-20261013-001`, recording the six selected source conversations and their index. This record was already present; this checkpoint did not add or re-import it.
- Structured lesson files remain: CARD111 = 6, ORGANISM = 5, global = 5, total = **16**. RECIPE_MANAGER intentionally retains its Markdown lesson index rather than a parallel `lessons.jsonl`.
- This verifies parseability and ID uniqueness only. It does not prove full semantic reconciliation, completeness of all chats, attachment-byte coverage, or completeness of the 2026-10-05/07 export relative to later development. The archive remains a 37-conversation / 10,034-message-ID snapshot ending 2026-10-07 UTC; the separate historical count of 74 remains a different, unresolved snapshot/scope claim.
- No raw archive was re-imported. No source PR was merged, closed, deleted, or force-updated. PR #22 remains open/Draft/unmerged.
