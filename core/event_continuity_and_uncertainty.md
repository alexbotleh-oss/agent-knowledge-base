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


## Checkpoint ownership and cross-chat branches

A checkpoint belongs to the task/project/chat context that created it. Ownership identifies the authoritative origin and the context responsible for advancing that line of work; it does not grant exclusive rights to read or reference the checkpoint.

When another chat or project uses an existing checkpoint as a basis for reasoning or action, create a child-branch record linked to the source checkpoint. Do not copy the source checkpoint as if the child created it, and do not mutate the source history in place.

Each branch record should preserve, where available:
- source checkpoint ID and owner scope (project/task/chat/session);
- consuming branch ID and its owner scope;
- the exact source revision/hash and the time it was read;
- what was reused: facts, decision, method, hypothesis, constraint, or open question;
- applicability assessment: accepted, adapted, rejected, or unresolved, with rationale;
- new evidence, actions, decisions, outcomes, and links to their own event records;
- whether the child result should be reported back to the source owner, and whether that report was delivered/acknowledged.

A read/reference alone does not mean the child has solved the original question. Record branch states distinctly, for example: REFERENCED, IN_PROGRESS, RESULT_REPORTED, SOURCE_OWNER_ACKNOWLEDGED, and NEEDS_REVIEW. The source question is marked resolved only when there is evidence that its required outcome was achieved or the original owner explicitly accepts the result. A child branch may resolve a reusable sub-question while leaving the parent task open.

### Returning knowledge to the source owner

When a child branch reaches a meaningful result, append a cross-branch event pointing to the source checkpoint and report:
1. which original question/decision it relates to;
2. what the child did with the inherited material;
3. the evidence-backed result and any limitations;
4. whether the result confirms, extends, contradicts, or is inapplicable to the source decision;
5. what, if anything, the source owner should update.

The source history remains append-only. The parent task's *current view* may incorporate the child result through a linked event or derived projection, but the original checkpoint and historical state remain available. If new evidence changes a previously accepted conclusion, append a correction/supersession event; never rewrite the old event as though the new information had always been known.

### Resume behavior in the originating chat

On reopening the originating task, retrieve branch notifications/results attached to its checkpoint before deciding the next step. If the original question is now resolved, do not repeat the investigation: mark that subtask resolved with a link to the child evidence, then continue the original plan or respond to the user's new request using the updated state. Reopen/reassess only if the child result is unverified, conflicts with stronger evidence, has narrower scope, or new data changes the premises.

This is not a global scan of every project on each turn. Use direct reverse links/indexes from checkpoint ID to its child branches and returned results. Updating the source task's current view should be proportional to the known related branches.

### Ownership, resolution, and synchronization are separate

- **Ownership:** who maintains the authoritative source task/checkpoint.
- **Reference/lineage:** which child branches rely on that checkpoint.
- **Resolution:** whether the specific question's acceptance criteria are satisfied.
- **Propagation:** whether the source owner has received and incorporated a child result.
- **Current view:** the latest derived state after applying linked events, without erasing historical states.

Do not conflate these dimensions into one boolean such as DONE. A child may have finished its work while the parent has not yet received the result; a result may be received but require review; a sub-question may be resolved while the parent goal continues.

## Required cross-branch recovery tests

1. A child reads a source checkpoint; the source owner and source content/hash remain unchanged.
2. A child completes a sub-question and records a result; the source task receives a linked result event without rewriting source history.
3. The originating chat resumes and discovers the result, skips duplicate investigation, and advances to the next plan step.
4. A child references a checkpoint but produces no result; the source question remains unresolved.
5. A child result conflicts with the source decision; both histories remain, and the source becomes NEEDS_REVIEW rather than silently adopting either conclusion.
6. A child adapts an idea to another project; applicability and new assumptions are explicit, and the source project is not mutated.
7. The result is recorded but its delivery/acknowledgement is interrupted; propagation remains pending and is retried idempotently.
8. Multiple child branches report results; source task state is derived from their distinct evidence and acceptance criteria, not from whichever report arrived last.

These semantics are a design contract until the branch registry, result-return path, and recovery tests are implemented.
