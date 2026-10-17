# Agent Bootstrap — canonical entry point

This file is the required starting point for work in `agent-knowledge-base`. It is a source map and execution order, not a claim that the mechanisms described below are automatically executed.

## 1. Recover the task before acting
1. State the user's current goal, active project, scope, constraints and permissions.
2. Read this repository's live branch/HEAD/PR/CI state before relying on old checkpoints.
3. Read the project's current `PROJECT_STATE.md`, `TASK_STATE.md`, `HANDOFF.md`, `DECISIONS.md`, `EVENT_LOG.md`, `LESSONS.md` and `events.jsonl` where present.
4. Compare current evidence with the last checkpoint. Keep facts, source claims, inferences, hypotheses, conflicts and unknowns distinct.
5. Choose the smallest safe, reversible next action. Read back every material change and validate its exact resulting revision.

## 2. Canonical instruction map
Read the sources relevant to the task in this order:

1. `core/repository_scope.md` — repository identity and project boundaries.
2. `core/guardrails.md` — permissions, safety and prohibited actions.
3. `core/universal_instructions.md` — universal operating rules.
4. `core/agent_runtime_protocol.md` — task execution, verification and handoff.
5. `core/source_ingestion_protocol.md` — source acquisition, coverage and resumable import.
6. `core/memory_model.md` and `core/memory_registry_and_multidimensional_index.md` — record identity, provenance, relationships and canonical memory.
7. `core/chronology_reconstruction.md` and `core/event_continuity_and_uncertainty.md` — temporal claims, uncertainty and corrections.
8. `core/continuous_agent_architecture.md` and `core/unified_memory_control_loop.md` — architecture and integration boundaries.
9. The active project's canonical state, decisions, event journal and handoff.

Do not assume that a referenced file exists on every branch: verify its presence at the selected revision. Report missing sources as a gap; do not silently substitute a similarly named document.

## 3. Canonical record roles
- `PROJECT_STATE.md`: compact current project state.
- `TASK_STATE.md`: active task plus detailed, dated checkpoints and evidence trail.
- `HANDOFF.md`: concise current resume instructions, not a second copy of the full checkpoint history.
- `DECISIONS.md`: decisions, scope and their status.
- `EVENT_LOG.md` / `events.jsonl`: event chronology and source references; corrections are append-only.
- `LESSONS.md` / structured lesson records: reusable conclusions with evidence, confidence, scope and status.
- Source archives and raw message payloads: evidence, not automatically verified lessons. Derived indexes must remain rebuildable from source records.

## 4. Chronology and duplicate rules
- Keep `event_time`, source/message time, and ingestion/recording time separate.
- Never fill a missing event timestamp with the import date, file modification time, current date or an inferred version order.
- A historical event without a traceable temporal basis is not part of the confirmed timeline.
- Match records by stable source identity first; semantic/text similarity only creates duplicate candidates.
- If a complete, evidenced duplicate exists and the untimed copy has no unique information, exclude the untimed copy from the canonical set. Keep one canonical record and retain source provenance/auditability.
- If one record has unique evidence, enrich the canonical record only when the meaning remains intact and every source remains traceable.
- Preserve conflicts and distinct episodes. Do not merge merely because terms, symptoms or summaries look alike.
- Do not count repeated report paragraphs as repeated real-world incidents without primary-source evidence.

## 5. Repository and verification boundaries
- Do not edit `main`, merge or close PRs, or force-update branches without explicit permission.
- Prefer existing relevant branches; do not create branches/PRs merely to document a plan.
- A CI PASS applies only to the exact tested SHA. Structural validation does not prove semantic completeness or live model behavior.
- Distinguish `CONTEXT_AVAILABLE`, `SOURCE_RETRIEVED` and `PERSISTENCE_VERIFIED`.
- Keep project-specific histories isolated. Cross-project material belongs in shared memory only as a directly evidenced transferable lesson with source references.
- After material work: read back changed files, verify exact HEAD, run available checks, record remaining gaps, and leave a concise actionable handoff.
