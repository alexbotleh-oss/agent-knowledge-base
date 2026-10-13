# Architecture gap: from source audit to evolving memory — 2026-10-13

## Why this note exists

The current repository already specifies RAW → INVENTORY → EXTRACTED → CANDIDATE → CANONICAL, provenance, timestamps, conflict preservation, reversible deletion/quarantine, and cross-chat handoff. These are important safeguards, but they do not by themselves constitute a complete architecture of continuously evolving memory. The 37-versus-74 discussion exposed a gap between documenting provenance rules and modeling the temporal evolution and scope of knowledge as first-class data.

This is a gap analysis, not a claim that the system already implements the mechanisms below.

## Existing foundations to preserve

- core/source_ingestion_protocol.md: source layers, source IDs/timestamps, counting-method distinctions, conflicts, confidence/evidence statuses, completeness reporting.
- core/universal_instructions.md: continuity lifecycle, event/lesson/state/handoff updates, verification gates.
- core/session_handoff.md: recoverable goals, decisions, verified outcomes, open questions, blockers, and next action.
- Prior continuity-core decisions in project history: identity/state must persist across chats, models, interfaces, and devices; experience chains from event/problem/hypothesis/action/result/conclusion/principle; old conclusions must not be erased when understanding changes; memory integrity must be protected with reversible quarantine and retained links.

These foundations must not be discarded or rewritten as if they were new discoveries.

## Architectural gap exposed

The current practice can record a timestamp on a fact and still compare two datasets that represent different temporal snapshots as if they were equivalent. Therefore, temporal metadata must describe not only when an event happened, but also which snapshot/collection a count or claim belongs to and how knowledge evolved between snapshots.

## Required conceptual model (not yet implemented/validated)

1. **Source snapshot / collection** — immutable identity for each archive, export, report, chat extraction, workbook batch, or merged-memory snapshot. Record capture/start/end times when known, received-at time, scope definition, inclusion/exclusion rules, counting units, content hashes where available, and completeness status.
2. **Atomic assertion / observation** — a claim or observation with stable identity, exact provenance, event-time interval, source-message time, ingestion time, evidence status, confidence rationale, project scope, and links to the snapshot(s) in which it appears.
3. **Knowledge lineage** — explicit links such as supports, contradicts, refines, supersedes, derived-from, duplicates, and independently-corroborates. Repeated copied text must not be mistaken for independent evidence.
4. **Temporal views** — ability to ask what the system believed at a given cutoff, what it believes now, and what changed between those states. A later merged memory must not be expected to equal an earlier archive.
5. **Revision without historical erasure** — when a new source changes interpretation, retain the prior assertion and its evidence; append a revision/relationship with reason, author/source, and time. Correcting a conclusion must not silently rewrite what was previously observed.
6. **Scoped reconciliation** — compare counts and claims only after aligning temporal cutoff, collection scope, and counting unit. If these cannot be aligned, report the difference as not directly comparable / unresolved, not as proof of corruption or incompleteness.
7. **Impact propagation** — when an assertion is revised or a source snapshot is found incomplete, identify downstream conclusions, lessons, summaries, and handoffs that depend on it; mark them for review rather than silently treating them as current.
8. **Memory integrity and recovery** — preserve immutable raw evidence, append-only history for meaningful changes, reversible quarantine, link integrity checks, and explicit recovery points. Capacity management must not delete potentially significant knowledge merely because it is old or rarely accessed.
9. **Decision and action traceability** — connect recalled knowledge to decisions/actions/results and record whether the recalled principle applied successfully, failed, or remains untested in that context.
10. **Operational validation** — define tests that prove snapshot-aware comparisons, temporal queries, provenance traversal, contradiction handling, revision impact discovery, cross-chat recovery, and recovery from partial ingestion. File/schema lint alone is not sufficient.

## Reinterpretation of the 37 / 74 discrepancy

User-provided timeline: archive submitted for archiving on 2026-10-05, returned on 2026-10-07, and development continued afterward. The archive's 37 conversation objects and a separate historical reference to 74 conversations may describe different cutoffs and/or scopes. The timeline makes that explanation plausible; it does not yet establish the exact membership or counting method behind 74. Keep both claims and their provenance; do not label the discrepancy as a defect unless snapshot-aligned evidence supports that conclusion.

## Next implementation sequence

1. Audit the current schemas and event/state/handoff formats against the conceptual model above; identify actual fields and missing capabilities, not just prose rules.
2. Specify a minimal versioned data model for snapshots, assertions, lineage edges, and temporal views without breaking existing records.
3. Create a small fixture containing at least two snapshots of the same evolving source set, with a known 37-versus-later-count scenario, and tests for non-comparability, temporal cutoff, and provenance.
4. Add validation and migration strategy; do not mass-rewrite existing memory until backward compatibility and rollback are demonstrated.
5. Update task state/handoff with the exact implementation status and unresolved decisions.

## Scope and status

- Status: ARCHITECTURE GAP IDENTIFIED; implementation NOT YET STARTED.
- This document is a proposed analysis derived from existing repository protocols and user-provided clarification, not proof that any new mechanism exists.
- Memory-system work only. Do not change application code, databases, or APKs. Keep N99 / RECIPE_MANAGER, B77_HTML_PWA, CARD111, and ORGANISM as distinct project chains.
- PR #22 remains open and must not be merged without explicit user permission.
