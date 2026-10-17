# Target architecture: durable event memory and incident learning

Status: **target architecture / design constraints**. This document records intended behavior; it does not claim that these guarantees are implemented or tested. Keep the current persistence/import audit as the active task. Do not begin the EXPERIENCE/PRINCIPLE implementation until the archive-staging and concurrent-import checks have been completed and their results recorded.

## Core model

The memory system must preserve the chronology of events and the history of how the agent's knowledge about those events changes. Re-importing or reinterpreting old source material must not silently rewrite established event facts.

### Distinct times

Where applicable, keep separate:

- `event_time`: when the event actually happened, as supported by its source.
- `registered_time`: when the event/source record was registered in memory.
- `confirmed_time`: when a relationship, hypothesis, or cause was confirmed or revised.

Also preserve source provenance and, where useful, the time an import or analysis run occurred. Never substitute import time for event time. Unknown timestamps remain unknown; do not infer them merely to fill a field.

### Append and correct by linked history

- Treat RAW source material and established EVENT records as immutable in their established facts.
- New evidence adds linked records or assertions; corrections and reinterpretations must be recorded as new, traceable changes rather than silent overwrites.
- Preserve original events and their timestamps even when later evidence changes their interpretation.
- Keep provenance, uncertainty, contradictory evidence, failed attempts, and superseded conclusions.
- Distinguish the fact that an event occurred from a hypothesis about why it occurred.

## Re-import and identity

- Re-importing the same source/event must not create a second occurrence or inflate incident counts.
- Import activity and event occurrence are different entities: a repeated import can be recorded as an import/reconciliation event without counting the old incident again.
- Use stable source/event identity and provenance to detect exact replays. Text similarity alone is not sufficient to declare two records duplicates.
- Two distinct occurrences with identical or similar descriptions must remain separate events until their identity is established; they may be linked to the same incident class.
- When an existing identity has different content, do not silently overwrite it. Record a conflict or a versioned correction and preserve both provenance and audit history.

## Event, class, experience, principle

Use the following conceptual separation:

- **RAW** — original source material, immutable snapshot/digest, and provenance.
- **EVENT** — an individually identified occurrence with its own time, source, evidence, and outcome.
- **CLASS** — a relationship/grouping of potentially related events. A class is not a replacement for its member events.
- **EXPERIENCE** — a revisable interpretation or lesson supported by one or more events.
- **PRINCIPLE** — a broader rule whose evidence, scope, verification status, and known limitations are traceable.

Similar symptoms do not prove a common cause. Class membership may begin as a candidate relationship and must be confirmable, revisable, or rejectable without deleting the underlying events.

## Recurrence-triggered investigation

- Repeated incidents are a signal to investigate, not proof of a shared root cause.
- Investigation triggers may include a configurable recurrence count/window, a sharp frequency increase, recurrence after a claimed fix, or one critical incident.
- The threshold should depend on incident severity and class; do not require multiple occurrences for every critical failure.
- The agent should compare evidence and alternative explanations, document a hypothesis and its confidence/status, and propose or execute only permitted checks.
- A cause becomes confirmed only under explicit evidence/verification criteria; an agent-generated explanation alone is not confirmation.
- A fix is not successful merely because a rule was written. Preserve the test/result evidence and, where possible, check whether the incident recurs under relevant conditions.
- Known relevant incidents and verified principles should be retrieved before a risky action so memory can prevent errors, not only explain them afterward.

## Traceability and revision

For every material hypothesis, relationship, or principle, preserve:

- supporting and contradicting event IDs;
- source provenance and relevant times;
- status (for example: candidate, under investigation, supported, confirmed under stated criteria, rejected, superseded);
- checks performed and their results;
- who/what produced the conclusion and when;
- the reason for any status change.

Never erase an earlier hypothesis merely because a later conclusion replaces it. Preserve the path by which the conclusion changed.

## Relation to current implementation

The current PR #25 work is focused on persistence/trust gates, write-path auditing, archive staging, and resumable import. Passing checkpoint-lock tests does **not** prove that every RAW/EVENT fact is globally immutable: direct/external writers, the HANDOFF/TASK_STATE cross-file race, and import/archive paths have separate boundaries.

Before implementing higher memory layers, finish and record the outstanding checks for:

1. staging archive rerun/interruption consistency, including records plus manifest;
2. concurrent import behavior for the same source and archive identity;
3. safe resume and conflict behavior, with exact CI evidence for the reviewed HEAD;
4. the remaining HANDOFF writer/synchronization limitations.

This document is a durable design constraint, not evidence that the above guarantees are already implemented.
