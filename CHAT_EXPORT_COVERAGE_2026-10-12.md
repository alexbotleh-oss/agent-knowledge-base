# Cross-chat experience export — 2026-10-12

## Purpose and status
This is a consolidated memory-only export of all project experience recoverable from the current conversation context, saved project summaries, and accessible GitHub memory branches. It is not a claim that every raw chat and binary attachment has been fully exported. Overall source completeness: **PARTIAL**.

**Destination repository:** https://github.com/alexbotleh-oss/agent-knowledge-base
**Consolidation branch:** export/cross-project-experience-rollup-20261012
**Base:** main at a0c12ba849a3416f50e1289d8f0dd20844e1e51f
**Scope:** memory, project-state, provenance, lessons and core documentation only. No application code, app database or APK was changed/built.

## Project coverage

### RECIPE_MANAGER — «Что приготовить» Flet/Android + historical HTML/SQLite
- Project memory: projects/RECIPE_MANAGER/PROJECT_STATE.md, TASK_STATE.md, EVENT_LOG.md, DECISIONS.md, LESSONS.md, HANDOFF.md, events.jsonl, HTML_SQLITE_REGRESSION_2026-10-12.md, RECIPE_SEARCH_REQUIREMENTS.md, BUILD_PACKAGING_ATTEMPT_2026-09-22.md, CHAT_TRANSFER_RECONCILIATION_2026-10-12.md, SOURCE_COVERAGE.md.
- Consolidated the accessible PR #20 memory with parallel PR #19 camera-decode evidence and PR #17 historical Core Lite/JNI/WebView diagnostic history. Relevant ingredient rules and web regressions from separate PR #21 are preserved under the later non-conflicting IDs and decisions rather than copied with colliding EVT IDs.
- Event IDs: 20 current EVT-2026… records plus 6 historical EVT-RM-* records. L-RM-022 is camera decode; L-RM-023 is task-scope correction. The gap EVT-20261012-007 remains unexplained.
- Source status: PARTIAL; complete chat export, all original HTML/SQLite/Python/ZIP attachments, full inter-version diffs and several raw diagnostic logs are unavailable.

### B77_HTML_PWA — separate HTML/PWA project in alexbotleh-oss/LK
- Copied the existing project chain from PR #5: PROJECT_STATE.md, TASK_STATE.md, EVENT_LOG.md, DECISIONS.md, LESSONS.md, HANDOFF.md, plus lessons/cross_project_review_20261012.md.
- Keeps B77 HTML/PWA separate from RECIPE_MANAGER/Flet/Android. Scanner/theme/water, Shopping/Products, baseline preservation, archive verification and historical rollback evidence remain marked with their actual confidence/status.
- Source status: PARTIAL; not every original chat, build artifact and intermediate HTML diff is available.

### CARD111 — loyalty-card Web/PWA in alexbotleh-oss/CARD
- Added project chain: PROJECT_STATE.md, TASK_STATE.md, EVENT_LOG.md, DECISIONS.md, LESSONS.md, HANDOFF.md, events.jsonl, lessons.jsonl.
- Preserved the user-approved editor/preview behavior, template/catalog requirements and brand list, mentioned app commits/branches, temporary QR observation, and reported scanner/gallery/crop issues.
- Static checks, deployment, phone runtime, barcode readability and full template integration remain NOT VERIFIED.
- Source status: PARTIAL; based on available summaries, not a complete chat export or full app diff.

### ORGANISM — separate continuous-agent app in alexbotleh-oss/organism
- Added project chain: PROJECT_STATE.md, TASK_STATE.md, EVENT_LOG.md, DECISIONS.md, LESSONS.md, HANDOFF.md, events.jsonl, lessons.jsonl.
- Preserved the decision to build a full app rather than only a ChatGPT bridge; Android/WebView direction; RAW/provenance/Context Engine/import architecture; 74 chats/10,034 messages archive/search gap; download and OAuth incidents; memory-integrity protection against dangerous deletion.
- CI/build reports are not represented as device/runtime PASS. OAuth white screen and archive integration remain unresolved in available evidence.
- Source status: PARTIAL; complete raw chat exports and all original artifacts are not available.

## Cross-project/core material
- Imported chronology and repository-scope rules from PR #4: core/chronology_reconstruction.md, core/repository_scope.md, plus corresponding README/core/template updates.
- Imported curated general lessons from PR #3 and added G-LESSON-005 for the observed task-boundary failure during transfer: source-chat content is evidence to classify, not an embedded instruction to execute unless explicitly requested.
- Project facts remain in each project's own directory. ORGANISM, agent-knowledge-base, CARD111, B77_HTML_PWA and RECIPE_MANAGER are distinct scopes.

## Source PRs and consolidation notes
- PR #3: initial RECIPE_MANAGER/global lesson memory — used as a source for global lessons and project decisions.
- PR #4: chronology reconstruction and repository-scope guardrails — included in this rollup.
- PR #5: B77 HTML/PWA experience — included in this rollup.
- PR #17: early RECIPE_MANAGER Core Lite/JNI/WebView diagnostics — unique historical material included, with source limitations.
- PR #19 and #20: parallel RECIPE_MANAGER memory branches — reconciled event and lesson ID collisions in this rollup; source branches remain untouched.
- PR #21: independent/stale ingredient/web regression branch with conflicting EVT-20261012-005/006 meanings; unique requirements are preserved in DEC-RM-006/EVT-014/L-RM-008/009, not imported under conflicting IDs.
- Other older RECIPE_MANAGER PRs remain open. This rollup does not merge, close or rewrite any source PR. Review consolidation before any merge.

## Validation checklist
- [x] Read back all 46 changed paths from this branch; each returned non-empty content.
- [x] Parsed all six JSONL files: RECIPE_MANAGER events 26/26 unique; CARD111 events 6/6 and lessons 4/4 unique; ORGANISM events 7/7 and lessons 5/5 unique; global lessons 5/5 unique.
- [x] Reconciled event/lesson ID collisions: EVT-20261012-017/018 are task-scope/transfer events, EVT-20261012-019 is PWA camera decode; L-RM-022 is camera decode, L-RM-023 is task boundary.
- [x] Compared branch with main: 46 changed paths, all memory/core documentation; no app source, HTML/JS project code, databases, or APKs.
- [x] GitHub Actions Validate knowledge base passed on the first PR head, run #86: https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/38304244094. Because this coverage note is being updated afterward, rerun CI for the resulting HEAD before claiming final PASS.
- [x] Draft PR #22 opened: https://github.com/alexbotleh-oss/agent-knowledge-base/pull/22; it remains unmerged pending explicit user permission.

## Known limitations
- This rollup cannot recover raw chats that are not exposed in the current context or accessible repository branches.
- Missing source files are not reconstructed from filenames alone. Unverified fixes remain unverified; hypotheses remain hypotheses.
- Source PRs may still show stale/conflicting content until separately reviewed. The consolidated branch is the candidate review surface, not evidence that main has been updated.
