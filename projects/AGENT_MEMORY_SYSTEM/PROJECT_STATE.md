# PROJECT_STATE — AGENT_MEMORY_SYSTEM

- **Canonical project ID:** AGENT_MEMORY_SYSTEM
- **Object:** improvement of the agent's memory, context-recovery, source-ingestion, verification and cross-chat continuity system stored in alexbotleh-oss/agent-knowledge-base.
- **Updated:** 2026-10-13; current state confidence: partial.
- **Current task:** AGMS-2026-10-13-01; see TASK_STATE.md and HANDOFF.md.
- **Current priority:** recover experience from the «Настройка Агента» memory-system work, preserve chronology and provenance, reconcile existing memory, detect omissions and repeated incidents, and validate changes using available tools.
- **Scope boundary:** work on the memory repository and AGENT_MEMORY_SYSTEM only. CARD111, ORGANISM, RECIPE_MANAGER and B77_HTML_PWA remain distinct project chains. Project-specific details may be retained here only when they directly explain memory-system architecture, scope mistakes, context-transfer failures, or a verifiable lesson. Do not transfer full histories of other projects.
- **Current design direction:** immutable RAW sources; stable source locators and IDs; a linked, multi-dimensional registry; separate event time/source time/recorded time; evidence and lifecycle status; reversible revisions; bidirectional temporal retrieval; coverage, contradiction and recurrence audits.
- **Existing mechanisms to reuse:** core/repository_scope.md; core/universal_instructions.md; core/agent_runtime_protocol.md; core/source_ingestion_protocol.md; core/chronology_reconstruction.md; core/memory_model.md; core/memory_registry_and_multidimensional_index.md; core/session_handoff.md; tools/archive_temporal_index.py; tools/validate_memory.py; tools/validate_project.sh; tools/generate_report.sh; tests and GitHub Actions.
- **Known process failure to prevent:** previous work redirected a memory-system task to a Recipe Manager archive migration despite repository scope. The chat collection task now explicitly defaults to the current chat/project and prohibits scope switching based on incidental project mentions.
- **Latest repository audit:** PR #22 is open, Draft and unmerged. Baseline HEAD before this documentation update was f879e9c6ba4ae7931d31ae3f6ef043320785b1b0; compare reported 301 commits ahead of main, 0 behind, 75 changed paths. The PR description was stale (different HEAD and 60 paths). GitHub Actions Validate knowledge base passed on the baseline SHA, run #38382449482; this PASS does not validate later commits.
- **Scope risk requiring audit:** PR #22 includes project-specific records for B77_HTML_PWA, CARD111, ORGANISM and RECIPE_MANAGER. Their relevance to the memory-system task must be checked path by path before any claim that the PR is scope-clean. No merge is authorized.
- **Environment limitation:** local git clone failed with “Could not resolve host: github.com”. Local validators and unit tests were not run; rely only on the cited baseline CI until a later exact-SHA run is confirmed.
- **Source coverage:** PARTIAL. The uploaded task file turn209file0 was read; selected prior context and repository artifacts were reviewed. Full history of all «Настройка Агента» chats and all binary attachments is not confirmed as available in this session.
- **New continuity records:** TASK_STATE.md, EVENT_LOG.md, events.jsonl, DECISIONS.md, LESSONS.md, HANDOFF.md. Event EVT-AGMS-20261013-001 records the baseline PR audit.
- **Next step:** audit all changed PR paths against the user’s scope, retain only directly relevant memory-system evidence without destroying source history, correct the PR description against fresh metadata, and confirm CI for the final exact HEAD.
- **HEAD note:** latest known branch tip before this PROJECT_STATE update: 5d339c9dbde3f509afec7ef6d7c923c947afc210; obtain the post-update tip from live PR metadata rather than treating this value as self-referential.

## Обновление 2026-10-13 — PR topology and scope

- Live GitHub search returned 20 open PRs #3–#22; checked PRs are unmerged. Several use other unmerged PR branches as their base.
- PR #22 at HEAD 6becb0ac6f482750434afb9d598c7c7628a11aa3 was 308 commits ahead of main, 0 behind, with 81 changed paths. This is a dependency/scope risk, not proof that the paths are duplicates.
- PR #22 description now states current metadata, CI result for that SHA, partial source coverage, scope-review requirement, and no-merge rule.
- The exact current HEAD will move as these state/event updates are committed; retrieve live PR metadata before reporting it. CI must be checked again for the resulting final HEAD.
- **Next step:** path-by-path scope review and compare overlapping PR branches. Do not delete project history or merge without user review/permission.
