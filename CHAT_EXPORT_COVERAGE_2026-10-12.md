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
- PR #21: independent/stale ingredient/web regression branch with conflicting EVT-20261012-005/006 meanings; unique requirements are preserved in DEC-RM-006/EVT-014/L-RM-008/009, not imported under conflicting IDs. Re-check web-specific event ownership in light of the N99/B77 clarification.
- Other older RECIPE_MANAGER PRs remain open. This rollup does not merge, close or rewrite any source PR. Review consolidation before any merge.

## Validation checklist
- [x] Report-bundle audit is recorded in `SOURCE_REPORTS_AUDIT_2026-10-13.md` and was read back from GitHub.
- [x] Retrieved and reviewed all 59 current PR paths individually for availability, structure/headings, unresolved-status markers, and change scope; PR file list confirms all changes are within memory/core documentation, templates, audits, and project-memory records. This is not equivalent to line-by-line semantic reconciliation of every claim against primary chat messages; that work remains open.
- [x] Parsed current JSONL files: RECIPE_MANAGER events 22/22 valid and unique; B77 HTML/PWA events 20/20 valid and unique; CARD111 events 15/15 and lessons 6/6 unique; ORGANISM events 7/7 and lessons 5/5 unique; global lessons 5/5 unique.
- [x] Reconciled original event/lesson ID collisions: EVT-20261012-017/018 are task-scope/transfer events, EVT-20261012-019 is PWA camera decode; L-RM-022 is camera decode, L-RM-023 is task boundary.
- [x] The initial compare recorded 46 changed paths, all memory/core documentation. The current PR API reports 59 changed files, and all 59 were individually retrieved and scope-reviewed. No app source, HTML/JS project code, databases, or APKs are reported among the changed paths.
- [x] Draft PR #22 remains open and unmerged: https://github.com/alexbotleh-oss/agent-knowledge-base/pull/22.
- [x] Historical CI runs #103/#104 and #120 passed on their stated older SHAs. Latest GitHub Actions Validate knowledge base passed on PR #22 HEAD `f4418338c7427596971b9de38667af14aadade99`, run #141: https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/38359389986. These are structural checks, not proof of historical-source completeness.
- [x] Moved clearly HTML/PWA-specific source events out of N99's event chain: early HTML/SQLite regressions, EVT-20261012-014, PWA Shopping/Products EVT-20261012-016 and browser camera decode EVT-20261012-019 now live under B77. Early September attribution to B77 remains medium confidence where the source conversation does not name the project.
- [x] Five additional B77 events were reconstructed directly from raw October 3–5 user messages and added with source conversation/message IDs; root causes remain unconfirmed without diffs.
- [x] CARD111 narrative and structured event parity is restored: 15 event headings in `EVENT_LOG.md` match 15 structured JSONL records; nine raw-source events were added and two lessons were synchronized across Markdown/JSONL.
- [x] B77 narrative and structured event parity is restored: 20 event headings in `EVENT_LOG.md` match 20 structured JSONL records; nine pre-existing narrative events were added without duplicates.
- [x] Structured reference audit found and repaired stale `EVT-20260922-001` references to canonical B77 event `EVT-B77-20260922-001`; re-read seven JSONL files: 64 events + 16 lessons parsed, no parse errors/duplicate IDs/unresolved structured event references. Details in `SOURCE_REPORTS_AUDIT_2026-10-13.md`.
- [ ] Continue message-by-message review of remaining mixed N99/B77 conversations before treating the project histories as complete.

## Known limitations
- The supplied ZIP contains exactly 37 conversation objects and 10,034 distinct message IDs. The older 74-chat note is not substantiated by this archive or the supplied report text; its origin remains unresolved. The ZIP does not prove full-export completeness and lacks the separate binary attachment bytes.
- Missing source files are not reconstructed from filenames alone. Unverified fixes remain unverified; hypotheses remain hypotheses.
- Source PRs may still show stale/conflicting content until separately reviewed. The consolidation branch is the candidate review surface, not evidence that main has been updated.
- Do not merge PR #22 without explicit user permission.
