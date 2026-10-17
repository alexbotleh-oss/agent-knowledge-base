# HANDOFF — AGENT_MEMORY_SYSTEM

Updated: 2026-10-17

## Active goal
Reconcile the existing memory records in `agent-knowledge-base`: one canonical record for a shared lesson, project-specific source evidence retained, no invented chronology, and no unsupported merging of distinct incidents.

## Live baseline
- Branch: `export/cross-project-experience-rollup-20261012`.
- Last verified HEAD before this consolidation: `fe88a27cb8e1aeda3baf90207aaf9fd4531a0ef9`.
- PR #22: open / Draft / unmerged; 135 changed paths before this commit.
- Exact-head CI passed for `fe88a27cb8e1aeda3baf90207aaf9fd4531a0ef9` in run #39024118077.
- `main` was not changed; no PR was merged.

## Canonical source map
- `core/agent_bootstrap.md`: required entry point and source map.
- `projects/AGENT_MEMORY_SYSTEM/TASK_STATE.md`: detailed checkpoint chronology and evidence trail.
- `projects/AGENT_MEMORY_SYSTEM/EVENT_LOG.md` / `events.jsonl`: event chronology and corrections.
- `projects/AGENT_MEMORY_SYSTEM/DECISIONS.md`: accepted decisions and scope.
- `projects/AGENT_MEMORY_SYSTEM/LESSONS.md`: memory-system lessons.
- This file is the concise operational handoff; do not duplicate the entire checkpoint history here.

## Completed in the latest bounded pass
- Added the canonical bootstrap entry point and linked it from README.
- Reduced the active handoff from a second long history log to a concise resume pointer.
- Consolidated the shared verification-stages lesson into `G-LESSON-001`, with evidence refs from RECIPE_MANAGER, CARD111 and ORGANISM.
- Removed standalone structured duplicates `L-CARD111-002` and `L-ORGANISM-003`; their project Markdown indexes now point to G-LESSON-001 and retain distinct source events and unresolved incident causes.
- Earlier exact-head CI passed for the bootstrap/handoff cleanup. CI for the new lesson-consolidation commit remains to be checked.

## Governing rules
- No missing event time is filled from import/review time, file timestamps or guessed version order.
- Exact, evidenced duplicate → one canonical active record; preserve source provenance and auditability.
- Similar wording only generates candidates. Preserve separate incidents when source, outcome or causal context differs.
- A shared lesson's validation status does not prove every referenced project's implementation/runtime is verified.
- PR #22 remains Draft/open/unmerged; do not merge or change `main` without explicit permission.

## Immediate next actions
1. Read back all changed records and project pointers; verify the superseded IDs are absent from active structured lesson files and the canonical record links all source events.
2. Check CI on the exact new HEAD.
3. Update PR #22's description with exact live HEAD, changed-path count and CI result.
4. Continue one evidence-backed duplicate cluster at a time; keep the PR scope issue and archive coverage explicitly PARTIAL.

## Status
One cross-project lesson cluster has been consolidated and read-back/CI are pending for that new commit. Repository-wide semantic deduplication and PR scope cleanup are **not complete**.
