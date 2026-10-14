# PR #22 scope audit — refreshed against current changed-path set (2026-10-14)

## Live evidence

- PR: https://github.com/alexbotleh-oss/agent-knowledge-base/pull/22
- Branch: `export/cross-project-experience-rollup-20261012`
- Fetched PR changed-path list: 134 paths.
- Commit `52ff4df1c13f65bb33e5ec2a122b387071e973ce`: GitHub Actions run 38563107303, “Validate knowledge base”, completed with conclusion `success`.
- Combined commit status API returned no status entries; the successful workflow run above is the concrete CI evidence. This says nothing about a later commit until its own workflow result is checked.
- A separate preservation branch `archive-reconciliation/deferred-20261014` exists and preserves the PR-head tree plus archive-reconciliation corrections. It is not a scope-clean PR branch.

## Important count correction

The older scope note refers to 81 paths and 39 out-of-scope paths. The live PR now reports 134 paths, so that older path-level count is stale and cannot be used as a deletion manifest. The exact changed-path list has been refreshed, but the older note did not preserve the names of all 39 paths. Do not guess which current paths correspond to them.

## Scope rule still in force

The active task is to transfer memory-system design/work history from «Настройка Агента» into `agent-knowledge-base`, not to publish full histories of B77, CARD111, ORGANISM or RECIPE_MANAGER. Transferable lessons may be retained with source provenance; full project history and raw chat exports must remain separately preserved and must not silently enter this PR.

The current PR contains 68 paths under project directories:
- `projects/AGENT_MEMORY_SYSTEM/`: 11
- `projects/B77_HTML_PWA/`: 8
- `projects/CARD111/`: 28
- `projects/ORGANISM/`: 8
- `projects/RECIPE_MANAGER/`: 13

These counts are a direct grouping of the current changed-path list. They are not, by themselves, a decision that all 68 paths must be removed: project-state summaries, append-only events, transferable lessons, and raw/source-history material have different purposes and scope risks.

## Required path-level disposition

Classify each changed path as one of:
1. `KEEP_CORE` — universal memory architecture, schemas, tools and tests.
2. `KEEP_AGMS` — direct memory-system project state, events, decisions, lessons and handoff.
3. `KEEP_TRANSFERABLE_LESSON` — concise cross-project lesson with source locator and no unnecessary project history.
4. `SEPARATE_PROJECT_MEMORY` — project-specific summary/events that belong in a separately scoped project-memory change, not this direct-scope PR.
5. `PRESERVE_RAW_OUT_OF_SCOPE` — raw conversations, source payload indexes, detailed project reports or supplementary source extracts. Preserve in the existing checkpoint branch or another verified destination before excluding from PR.
6. `REVIEW_MIXED` — mixed reports needing a narrower memory-process extract.

Do not delete source-only copies. Do not use the old count of 39 as a proxy for a path list. Do not update `main` or merge PR #22.

## B77/LK identity correction

User clarification (2026-10-14): `alexbotleh-oss/LK` is the repository for the whole B77 project, not only Lite Cook. Lite Cook is the simplified user-facing branch; the «Что приготовить» APK was a technical branch planned to be unfrozen and later integrated with B77/LK. That integration was planned, not confirmed as completed. Keep this distinction when classifying B77 and RECIPE_MANAGER memories; do not collapse them into one implemented application.

## Current status and next step

- Archive reconciliation documents and the LK/B77 correction have been committed and read back on `archive-reconciliation/deferred-20261014`.
- No path has been deleted. No merge or change to `main` has occurred.
- Next action: produce a complete path-by-path disposition manifest for all 134 current paths; use the checkpoint branch as preservation evidence; then create a scope-clean PR branch or adjust PR #22 only after the manifest is complete. Run validation and check CI on the exact resulting HEAD.
