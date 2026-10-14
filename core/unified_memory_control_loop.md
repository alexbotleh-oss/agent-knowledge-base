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


## 7. First executable integration primitive: child-result publication

Implemented component: `tools/branch_result_registry.py`. Tests: `tests/test_branch_result_registry.py`.

- Writes a linked `cross_branch_result` event to the existing canonical `projects/AGENT_MEMORY_SYSTEM/events.jsonl`; it does not create a parallel journal or directly mark a parent question resolved.
- Requires child branch ID, parent checkpoint/task IDs, stable result key, explicit result status, summary, source references and report timestamp.
- Exact replay with the same stable identity/content is a no-op. Same identity with changed content is a conflict; a correction must use a new result key and link to the earlier event.
- Missing provenance, invalid state or reported success with unknown evidence is rejected without writing.
- Owner acknowledgement remains PENDING. Delivery is not acknowledgement; acknowledgement is not acceptance; acceptance of a child result is not completion of the parent task.
- The write uses a temporary file and atomic replacement for a single writer. Concurrent writers are NOT coordinated; use a single-writer constraint until a lock/transactional store is implemented.
- This component is a local repository primitive, not an automatic ChatGPT cross-chat message bus. The caller must have repository access and explicitly invoke it. Updating the human-readable EVENT_LOG, notifying the owner, recording acknowledgement, and refreshing TASK_STATE/HANDOFF are not automated by this primitive.

Release interpretation: this closes only one narrow part of UMC-08 (durable linked result publication). It does not make UMC-08 end-to-end PASS and does not satisfy the whole release gate.


### Explicit parent acknowledgement primitive

`tools/branch_result_registry.py` also exposes `acknowledge_result(...)`, which appends a separate `cross_branch_result_acknowledged` event referencing an existing child-result event. Allowed decisions are `accepted`, `needs_review`, and `rejected`; exact replay is idempotent, and changing a decision under the same acknowledgement identity is rejected as a conflict.

The acknowledgement is append-only and does not edit the child event or mutate TASK_STATE. Even an `accepted` acknowledgement means only that the owner accepted that child result; the parent task controller must separately check acceptance criteria and update the current-state projection. The owner reference is an evidence locator supplied by the caller; the primitive cannot authenticate the human or prove the reference's truth. The CLI currently publishes result envelopes only; acknowledgement is available as a Python API, not yet wired into a dedicated CLI command or automatic chat workflow.


### Writer coordination and command-line interface

The result registry now acquires a fail-closed exclusive lock file around read/validate/append. If a lock already exists, it returns `LOCKED` without changing the journal; it never automatically deletes a stale lock because doing so could race a live writer. Recovery from a stale lock requires checking that no writer remains active, then manual removal. A process crash may therefore require operator recovery.

CLI forms:
- `python3 tools/branch_result_registry.py <events.jsonl> publish <result-envelope.json>`
- `python3 tools/branch_result_registry.py <events.jsonl> ack --result-event-id <event-id> --decision accepted|needs_review|rejected --owner-ref <evidence-ref> --at <ISO-8601>`

These are explicit local operations. They do not dispatch chat messages, authenticate the owner reference, update task-state projections, or guarantee cross-host locking on every filesystem. Multi-process same-filesystem writes are guarded by exclusive lock-file creation; network/distributed filesystem behavior remains unverified.


## 8. Guarded task-state projection update

Implemented prototype: `tools/guarded_task_state_update.py`; tests: `tests/test_guarded_task_state_update.py`.

- Appends a new checkpoint block to an existing project `TASK_STATE.md`; it never replaces prior checkpoint text.
- Requires a caller-supplied expected SHA-256 of the exact current task-state file, a parent checkpoint ID, a stable update ID and a supporting event ID already present in a project `events.jsonl`.
- Re-reads the task state after acquiring an exclusive lock. If the file changed since the proposal was made, returns `STALE_REVISION` without writing.
- Exact replay is a no-op; reusing an update ID with changed content is a conflict; missing event evidence, invalid paths or an existing lock fail closed.
- The lock is removed after a normal handled operation; a hard process crash can leave a stale lock and requires verified manual recovery.
- This updates only the task-state checkpoint append. It does not regenerate HANDOFF or EVENT_LOG, authenticate the event's source, or determine that a parent acceptance criterion is satisfied. The caller remains responsible for recording truthful content and linking evidence.
- The tool is restricted by path/name checks to `TASK_STATE.md` and `events.jsonl` under `projects/`, but path checks are not a substitute for repository/OS permissions.

This is a guarded local projection primitive, not an automatic cross-chat restore mechanism. End-to-end integration and failure injection across event publication plus state update are still required.


### Local linked-return round-trip test

`tests/test_child_result_return_roundtrip.py` now exercises the connected local path: publish child result → replay without duplication → append owner acknowledgement → append a guarded task-state checkpoint linked to the acknowledgement. It also changes the parent state between proposal and apply to confirm that stale state is rejected, then re-plans against the new hash without losing the intervening parent update.

This proves a local two-step recovery path under the tested fixtures. It does not prove distributed atomicity: a crash can occur after the event is appended and before the task checkpoint is applied. Recovery currently relies on idempotent replay plus an explicit refreshed proposal; automatic reconciliation of all pending branch returns remains future work.


## 9. Read-only reconciliation of incomplete returns

Implemented prototype: `tools/reconcile_branch_returns.py`; tests: `tests/test_reconcile_branch_returns.py`.

It reads the canonical event log and explicitly supplied TASK_STATE files. It reports (without writing) child results that have no owner acknowledgement, and accepted acknowledgements whose event IDs are not linked from any supplied task-state file. Reports include source log hash and candidate task-state paths/hashes for a future guarded repair.

The report is intentionally conservative: it does not auto-acknowledge results, apply task-state updates, or declare the parent task complete. It cannot conclude that no checkpoint exists outside the files supplied by the caller. Repair remains a separate explicit operation requiring owner review and the expected-revision guard.


## 10. Current acceptance matrix — evidence-based status

Status meanings: **PARTIAL** means a component/test covers a narrow subcase but not the full scenario; **BLOCKED** means no executable end-to-end mechanism has been demonstrated.

| ID | Current status | Evidence / remaining gap |
|---|---|---|
| UMC-01 | BLOCKED | Raw export round-trip exists in `tests/test_current_session_roundtrip.py`; no new-session restore from TASK_STATE + linked decisions/events into a verified continuity packet. |
| UMC-02 | BLOCKED | Return rules are documented; no runtime dialogue controller classifying side branches and preserving/returning active goals. |
| UMC-03 | BLOCKED | Intake planner carries observed tool/language/task tags; no runtime applicability evaluator that gates use of shared lessons. |
| UMC-04 | PARTIAL | `tests/test_resumable_chat_import.py` covers replay/resume for immutable source snapshots; promotion and index refresh are not in that pipeline. |
| UMC-05 | PARTIAL | Manifest hash/path validation and importer incomplete-source tests exist; full staging-to-quarantine-to-promotion recovery is not end-to-end. |
| UMC-06 | PARTIAL | Disputed lifecycle and routing exist; end-to-end conflicting-source preservation and dependent-state impact review need stronger tests. |
| UMC-07 | PARTIAL | Unknown execution state is specified and idempotent child-result replay is tested; generic external side-effect reconciliation is not integrated. |
| UMC-08 | PARTIAL | `tests/test_child_result_return_roundtrip.py` covers local result → acknowledgement → guarded checkpoint; automatic chat delivery and pending-return reconciliation are absent. |
| UMC-09 | PARTIAL | Importer resume tests and stale TASK_STATE rejection exist separately; no single injected crash across canonical event commit, projection update and index refresh. |
| UMC-10 | PARTIAL | Temporal lineage/impact primitives exist; automated downstream impact review across every canonical record type is not proven. |
| UMC-11 | PARTIAL | Guarded updater path scope and exclusive locks are tested; actual GitHub permissions, branch protections and per-agent credentials are not verified. |
| UMC-12 | BLOCKED | Protocol says to report BLOCKED when access is unavailable; no executable session restore gate enforces this across environments. |

The current CI pass verifies the repository validators and unit tests on a specific commit. It does not upgrade PARTIAL/BLOCKED rows automatically. The end-to-end test stage remains blocked until the missing cross-component paths are implemented and evidenced.


## 11. Source-backed session restore packet

Implemented prototype: `tools/restore_session_packet.py`; tests: `tests/test_restore_session_packet.py`.

The tool reads TASK_STATE, HANDOFF and the canonical event log, records exact source hashes, includes recent checkpoint excerpts and linked events, and returns explicit status:
- `RESTORED_PACKET`: required sources parse and all referenced event IDs found in the inspected sources;
- `PARTIAL`: a referenced event is missing from the inspected event log;
- `BLOCKED`: a canonical source is missing or invalid.

It is read-only. It does not infer that all dialogue was captured, and it does not independently decide which excerpted statements are accepted facts. The agent must still interpret statuses, conflicts and next steps. This is a source-backed packet builder, not automatic session startup in every ChatGPT chat; callers must have access to the files and invoke it.
