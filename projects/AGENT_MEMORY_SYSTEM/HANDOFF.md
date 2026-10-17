# HANDOFF — AGENT_MEMORY_SYSTEM

Updated: 2026-10-17

## Active goal
Consolidate genuinely shared lessons into one canonical global record while retaining project-specific evidence, chronology, uncertainty and source links. Do not merge merely similar symptoms or summaries.

## Live baseline
- Branch: `export/cross-project-experience-rollup-20261012`.
- Last verified HEAD before the current API-lesson consolidation: `c85ffe55bc25235aa8f3d06074b4a27a4f5b9502`.
- PR #22: open / Draft / unmerged; 135 changed paths before this commit.
- Exact-head CI passed for `c85ffe55bc25235aa8f3d06074b4a27a4f5b9502` in run #39024266434.
- `main` was not changed; no PR was merged.

## Canonical source map
- `core/agent_bootstrap.md`: required entry point/source map.
- `projects/AGENT_MEMORY_SYSTEM/TASK_STATE.md`: detailed checkpoint chronology and evidence.
- `projects/AGENT_MEMORY_SYSTEM/EVENT_LOG.md` / `events.jsonl`: event chronology and corrections.
- `projects/AGENT_MEMORY_SYSTEM/DECISIONS.md`: accepted decisions and scope.
- `projects/AGENT_MEMORY_SYSTEM/LESSONS.md`: lessons about the memory system itself.
- This file is the concise operational handoff, not a duplicate historical log.

## Completed bounded consolidations
1. **G-LESSON-001:** unified the shared rule for separating syntax/build/deployment/install/runtime/visual/regression checks. Evidence now links RECIPE_MANAGER, CARD111 and ORGANISM. Standalone CARD111/ORGANISM copies were replaced by pointers; distinct incidents and unknown root causes remain separate.
2. **G-LESSON-002:** unified the API-version/signature rule. RECIPE_MANAGER's L-RM-002 is now a pointer; EVT-20260927-001 remains the evidence anchor. Exact version/root cause/final fix remain unverified.
3. **Bootstrap/handoff:** added `core/agent_bootstrap.md`, linked it from README, and reduced the active handoff to a concise resume note. Detailed checkpoints remain in TASK_STATE.

## Governing rules
- Never invent event time or replace it with import/review time.
- Exact, evidenced duplicate → one canonical active record; keep provenance/audit trail.
- Similar wording is only a candidate. Preserve distinct episodes and unresolved causes.
- A validated shared process lesson does not prove every referenced app's runtime is verified.
- PR #22 remains Draft/open/unmerged; do not merge or change `main` without explicit permission.

## Immediate next actions
1. Read back the current consolidation and verify JSONL parsing, unique IDs, canonical links and preserved source event IDs.
2. Check CI on the exact new HEAD.
3. Continue with other evidence-backed duplicate clusters; reject false positives such as the already-correct B77-L-010 / L-RM-022 cross-project pointer.
4. Resolve PR scope drift and archive coverage gaps without silently deleting unique project history.

## Status
Two cross-project lesson clusters have been consolidated in bounded passes. Repository-wide semantic reconciliation and PR scope cleanup remain **PARTIAL**.
