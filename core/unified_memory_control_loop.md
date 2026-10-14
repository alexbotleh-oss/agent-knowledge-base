# Unified dialogue–memory control loop

Status: integration contract for AGENT_MEMORY_SYSTEM. This document connects existing protocols; it does not claim that every runtime mechanism is deployed.

## 1. Purpose

Keep dialogue control and memory lifecycle in one feedback loop without making the knowledge base a task dispatcher. The active task controller owns the user's current goal. Shared memory supplies evidence, reusable methods and warnings; it may inform the task but cannot silently replace it.

## 2. Canonical inputs and ownership

Use existing artifacts; do not create a parallel source of truth:

- Active goal, acceptance criteria, constraints, blockers and next step: `projects/<PROJECT>/TASK_STATE.md`.
- Project status and accepted direction: `PROJECT_STATE.md` and `DECISIONS.md`.
- Append-only event history: `events.jsonl` plus its human-readable `EVENT_LOG.md`.
- Source provenance and intake status: source registry/intake manifest and immutable RAW source.
- Session transfer: `HANDOFF.md`.
- Ideas, alternatives and unresolved hypotheses: `IDEA_SANDBOX.md` linked to source/event IDs.
- Rules for interpretation, interruption and intake: `core/agent_runtime_protocol.md`, `core/session_handoff.md`, `core/source_ingestion_protocol.md`, `core/event_continuity_and_uncertainty.md`.

A current-state file is a projection, not a replacement for event history. If they disagree, preserve the discrepancy and reconcile from evidence; do not silently rewrite history.

## 3. One operational loop

### A. Start / restore

1. Resolve the active project and task from the current user request and the latest checkpoint. If unclear, ask one targeted question.
2. Read the project's TASK_STATE and HANDOFF, then directly linked decisions/events and only relevant shared-memory candidates.
3. Verify live repository/branch/commit/test state when those resources are available. A prior handoff is a claim to check, not proof of current runtime state.
4. Produce a compact recovery state: goal, acceptance criteria, constraints, confirmed facts and evidence, hypotheses, unresolved conflicts, pending/unknown side effects, deferred branches, and next safe action.
5. Do not repeat a completed check unless its evidence is stale, its inputs changed, or a new contradiction appeared.

### B. Interpret each turn

Classify the turn as one of: continuation, correction, side branch, deferred idea, new task, priority change, or return to the parent task. Preserve the current goal unless the user changes it or a real blocker requires a decision.

For a side branch, capture a lightweight linked checkpoint only when it has durable value. Record: parent task/checkpoint, reason for branch, original stopping point, findings, remaining questions, relation to parent goal, and return condition. A deferred idea is not an instruction to execute it now.

### C. Use shared knowledge safely

For every reused item that materially affects an action, retain its source ID, status, evidence and applicability rationale. Check technology/tool/problem descriptors and known limitations; do not assume that a lesson transfers merely because wording matches. Shared memory is a support resource, not authority over the current task.

If useful general knowledge is discovered incidentally, add a candidate linked to its evidence. Return to the active task unless the discovery blocks it or the user changes priority.

### D. Capture actions and results

Keep distinct records for intent, proposal, attempt, tool/external report, observation, independent verification, decision and handoff. Every consequential result should link to its source evidence and task/checkpoint. Use append-only correction/supersession links instead of silently changing past events.

If an action may have had an external side effect but its acknowledgement was lost, preserve UNKNOWN until authoritative state is checked or safe idempotent replay is established.

### E. Ingest new sources

1. Preserve immutable RAW bytes and source identity/hash.
2. Inventory and extract without semantic merging.
3. Validate schema, hashes, scope and references.
4. Stage records as candidates; unknown routes go to quarantine rather than guessed destinations.
5. Review duplicates and conflicts while retaining all independent provenance.
6. Promote only according to the existing lifecycle/approval rules.
7. Update derived indexes and task views only after the authoritative records are committed; record exactly which updates succeeded.
8. Return stable IDs/paths and an ingestion report to the originating task/checkpoint.

The raw importer, manifest validator and read-only route planner are separate capabilities. Do not describe the whole pipeline as end-to-end until staging, promotion, index update, result publication and recovery are connected and tested together.

### F. Checkpoint and return

After a meaningful milestone, update the owning task's current-state projection and handoff, linking new event IDs, evidence, commit/test results, unresolved questions and the next step. Child/side-branch work reports back to its parent by linked result; it must not overwrite the parent's historical checkpoint. Mark only the acceptance criteria actually met as resolved.

## 4. Required invariants

- **Goal continuity:** no silent goal replacement by a shared-memory finding or side branch.
- **Provenance:** every accepted claim can be traced to source evidence; generated summaries do not outrank their sources.
- **Chronology:** event time, source time, ingestion time and record time remain distinct.
- **Epistemic honesty:** reported, observed, inferred, verified and unknown remain distinguishable.
- **Append-only history:** corrections add linked records; they do not erase earlier beliefs/actions.
- **Idempotent intake:** replay of the same immutable source does not duplicate records or destroy revisions.
- **Safe authorization:** a valid manifest or IMPORT_READY marker is not permission to execute arbitrary code or accept knowledge.
- **Failure containment:** partial failure leaves an explicit recoverable status; no false COMPLETE/PASS.
- **No duplicate authority:** indexes and compact views are derived from canonical records and identify their source revision.
- **Portable access:** a chat/agent may claim that cross-chat restore works only after it has actually retrieved the current source/checkpoint in that environment.

## 5. Integration acceptance tests

The project is not ready for end-to-end testing until each row has an executable test or a clearly justified manual test with stored evidence.

| ID | Scenario | Required result |
|---|---|---|
| UMC-01 | New chat starts from a task checkpoint | Restores goal, constraints, current evidence, unresolved items and next step from repository sources; does not rely solely on a model summary |
| UMC-02 | Side topic appears during active work | Parent goal remains active; side branch is linked with return condition; completed parent checks are not repeated |
| UMC-03 | Shared lesson is relevant but not proven transferable | Used only as a candidate/limited method with provenance and applicability check; no silent promotion |
| UMC-04 | Same source batch arrives twice | Idempotent replay; stable IDs and no duplicate canonical records |
| UMC-05 | Source or manifest is tampered/incomplete | Reject or mark PARTIAL/quarantined; retain RAW and error evidence; no promotion |
| UMC-06 | Two sources disagree about a decision/result | Both claims and provenance survive; status becomes disputed/needs review; no silent overwrite |
| UMC-07 | Tool side effect occurs but response is lost | Status remains UNKNOWN until authoritative reconciliation; no unsafe replay |
| UMC-08 | Child chat completes one sub-question | Linked result returns to parent checkpoint; only matching acceptance criterion is resolved |
| UMC-09 | Crash after records commit but before index/checkpoint update | Resume detects committed records, avoids duplicates, finishes or reports failed projection update |
| UMC-10 | Knowledge is corrected later | Impact trace finds dependent decisions, lessons and handoffs for review; history remains recoverable |
| UMC-11 | An agent tries to write outside its scope | Protected path/branch policy or validation rejects it; folder naming alone is not counted as access control |
| UMC-12 | A chat has no repository connector/access | It explicitly reports restore BLOCKED and requests the minimum access/input; it does not pretend continuity is automatic |

## 6. Definition of done before test stage

All of the following are required:

1. Every invariant maps to a concrete component and owner.
2. Each component has status proposed/designed/implemented/verified/blocked, with evidence.
3. Critical transitions have executable tests, including failure injection and retry.
4. The happy path runs from source arrival through validation, staging, approved promotion, index/view refresh, result publication and a new-session restore.
5. Exact commit CI passes; important local tests are run where possible.
6. Permissions/branch protection are verified from actual repository settings, not inferred from docs.
7. A clean test matrix records PASS/FAIL/BLOCKED and evidence links.
8. Known limitations are explicit; no automatic cross-chat capture is claimed unless the capture path exists and has been tested.

Until these conditions are met, describe the architecture as partially implemented and in development, not complete.
