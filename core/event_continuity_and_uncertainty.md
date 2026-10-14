# Event Continuity and Uncertainty Protocol

Status: proposed protocol on the cross-chat experience branch; not yet a deployed runtime guarantee.

## Purpose

Prevent loss of event continuity across interrupted turns, dropped connections, context switches, and separate chats. The agent must distinguish what was intended, what it attempted, what an external system reported, what was independently verified, and what remains unknown.

The target is continuity of evidence-backed state, not identical wording or identical regenerated reasoning. Model outputs may vary; durable event records and explicit provenance must not silently vary with them.

## Core invariant

**Absence of a record is not evidence that an event did not happen. A generated claim is not evidence that an action happened. An attempted action is not a confirmed result.**

Never silently convert UNKNOWN into NOT_DONE or DONE.

## Event record

Each meaningful event should be append-only and carry, where available:

- event_id: stable unique identifier.
- operation_id and task_id: scope the event to a concrete operation and goal.
- occurred_at and recorded_at: distinguish event time from capture time; preserve unknown timestamps as unknown.
- source: chat/turn, tool, user, repository, external system, or inferred source.
- event_type: intent, proposal, command, attempt, tool result, observation, verification, interruption, decision, correction, or handoff.
- payload_ref or concise payload: what was actually said, sent, returned, or observed.
- status: epistemic/execution state, not a vague success boolean.
- caused_by / related_event_ids: links to prior events and affected goals.
- evidence_refs: exact outputs, commits, files, logs, or user confirmations supporting the record.
- confidence and uncertainty_reason when the event is inferred or incomplete.
- supersedes / corrects: append a correction rather than silently rewriting history.

Do not fabricate missing fields. Unknown values remain explicitly unknown.

## Separate execution state from evidence state

Use distinct lifecycle states, selected to fit the operation:

- INTENDED: planned or requested; not yet attempted.
- PREPARED: inputs/action assembled; not yet sent or executed.
- ATTEMPTED: execution was initiated; outcome may be unknown.
- REPORTED_SUCCESS: a tool or external system reported success; independent verification may still be absent.
- VERIFIED: the specified postcondition was checked against evidence.
- FAILED: failure is evidenced.
- UNKNOWN: execution may have occurred, but available evidence does not resolve the outcome.
- CANCELLED: cancellation is evidenced before completion.
- SUPERSEDED: a later event changes the active plan or state; preserve the prior event.

A status should be accompanied by its source and evidence. Do not treat a model's own natural-language assertion as independent verification.

## Interruption and recovery

At a boundary where an external side effect may occur, persist the intent and operation identifier before dispatch when technically possible. Record the attempt and tool response as separate events. If the connection breaks between dispatch and response, write/retain UNKNOWN and resume by checking the operation's authoritative state.

On resume, restore in this order:
1. Active goal and scope.
2. Last durable checkpoint and its exact source/version.
3. Events after that checkpoint, including pending/unknown operations.
4. Evidence needed to resolve those operations.
5. Only then continue the next safe step.

Do not replay an operation with possible side effects merely because its response was lost. First query its outcome or compare the resulting state. Use idempotency keys for external operations when supported. If neither outcome lookup nor safe idempotent replay is available, stop at UNKNOWN and ask for the minimum necessary human decision.

## Checkpoints and append-only corrections

A checkpoint is a snapshot of the current interpreted state plus the event-log position and evidence references that justify it. It is not a replacement for the event log. Checkpoints should identify what is confirmed, inferred, pending, disputed, and unknown.

Never silently overwrite a prior decision or event. Append a correction/retraction event with a reason and a link to the event being corrected. Keep chronology and provenance so another chat can reconstruct what was believed at the time and what changed later.

## Cross-chat continuity

A new chat should be able to retrieve a task by stable identifiers and semantic links, not rely on the user repeating context. Retrieval should return a compact continuity packet containing:
- goal and scope;
- confirmed facts and exact evidence;
- decisions, rationale, alternatives rejected, and constraints;
- chronological event chain;
- current checkpoint;
- pending and unknown actions;
- contradictions or superseding events;
- next safe action and its preconditions.

Keep project boundaries explicit. Reuse an idea from another project by linking to its source event and explaining the relationship; do not copy it as an established fact for the new project without checking applicability.

## First pass versus resume

An intake operation must declare its mode at entry:
- FIRST_PASS: no prior record for this operation and exact source; begin initial processing.
- RESUME: same operation and immutable source, with a valid checkpoint.
- RETRY_FROM_START: prior operation record exists but no valid checkpoint.
- ALREADY_COMPLETE: exact source was completed; do not reprocess as new work.
- NEW_SNAPSHOT: operation/archive identifier matches but source hash differs; treat as a distinct snapshot, not a resume.

Do not issue a resume instruction during a first pass. Do not run broad duplicate searches on every entry; exact operation/source identity is the fast path. Broader reconciliation is a separate audit task.

## Minimum recovery tests

Test deliberately interrupted workflows at each boundary:
1. Before action dispatch.
2. After dispatch but before response.
3. After tool response but before recording it.
4. After recording the response but before verifying the postcondition.
5. After verification but before checkpoint publication.
6. During handoff to another chat.
7. When the same event is encountered again.
8. When later evidence contradicts an earlier event.
9. When source material changes after a checkpoint.
10. When the only available evidence is a model-generated statement.

Expected behavior: preserve chronology, never invent completion, avoid unsafe duplicate side effects, resolve uncertainty from authoritative evidence when possible, and clearly report remaining uncertainty.

## Scope and limitations

This document defines a protocol proposal. It does not itself implement durable storage, atomic writes, automatic capture of every chat/tool event, cross-chat retrieval, distributed locking, idempotency support, or network-resumable export. Those capabilities require implementation and fault-injection tests before they may be described as operational.
