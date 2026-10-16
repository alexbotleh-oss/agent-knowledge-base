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
| UMC-01 | PARTIAL | `tools/restore_session_packet.py` and `tests/test_restore_session_packet.py` build a source-backed packet from TASK_STATE/HANDOFF/events with hashes and linked events; automatic startup in a new ChatGPT chat and semantic goal verification remain unimplemented. |
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

## 12. Bounded restore and experience-candidate pass

Implemented prototype: `tools/minimal_agent_loop.py`; tests: `tests/test_minimal_agent_loop.py`.

### Two-tier review plus local evidence-source availability

The loop applies independent, non-authorizing review dimensions:
- **Scope filter:** explicit `--project-id` matching routes same-project candidates to review; mismatches remain `OUT_OF_PROJECT_SCOPE`; missing identity remains `PROJECT_SCOPE_UNKNOWN`.
- **Evidence-quality filter:** classifies the record's status metadata and whether recognized evidence pointers exist. A `verified` label is not proof of claim validity.
- **Local source-availability check:** when the caller explicitly supplies `--evidence-root`, each `evidence`/`evidence_refs` item with `kind: file` and a repository-relative `ref` is checked under that root for existence, regular-file type, non-empty content and a text-like UTF-8 sample (up to 8192 bytes). Empty files are classified `EMPTY_FILE`; samples containing a NUL byte or invalid UTF-8 are classified `BINARY_FILE`. An incomplete UTF-8 sequence only at the sample boundary is tolerated so a multibyte character split by the 8192-byte limit is not misclassified. Path traversal and absolute paths are not followed outside the root. URLs, commit IDs, test names and other non-file references are not fetched or validated.

#### Evidence source validation levels

| Level | Check | Per-reference / aggregate status | Review effect |
|---|---|---|---|
| 1. Root supplied | Is `--evidence-root` explicit? | `NOT_CHECKED_NO_EVIDENCE_ROOT` when absent | Not a pass; candidate remains review-only |
| 2. Path safety | Does the resolved path remain inside the root? | `OUTSIDE_EVIDENCE_ROOT` | Not followed outside root; routed to review, not treated as valid evidence |
| 3. Existence and type | Does the path exist and point to a regular file? | `MISSING` / `MISSING_SOURCE`; `NOT_A_FILE` / `INVALID_SOURCE_TYPE` | Blocks the same-project evidence-source review route |
| 4. Readability | Can the file be opened and the bounded sample read? | `UNREADABLE` / `UNREADABLE_SOURCE` | Blocks the same-project evidence-source review route |
| 5. Content sanity | Is the file non-empty, with a text-like UTF-8 sample within the first 8192 bytes? | `EMPTY_FILE` / `EMPTY_SOURCE`; `BINARY_FILE` / `BINARY_SOURCE` | Blocks the same-project evidence-source review route |
| 6. Claim support | Does the source actually support the event claim? | Not evaluated by this check; `claim_validated: false` | Requires a separate evidence-backed assessment |

Aggregate source statuses also include `ALL_LOCAL_FILES_READABLE` when all checked local file references pass the availability/format screen, and `NO_LOCAL_FILE_REFS` when no local file references are available to check. The check is local-only and runs only with an explicit evidence root.

Important limitations:
- A file passing the availability/format screen is only a suitable carrier for textual evidence; it is not proof that the file supports the claim or that the lesson transfers to the current task.
- Semantic validation of evidence content remains unimplemented.
- Every candidate remains `transfer_decision: UNASSESSED`; no gate authorizes use, promotion, writes or execution.
The command explicitly connects existing components in this order:
1. Build the source-backed restore packet from the supplied `TASK_STATE.md`, `HANDOFF.md` and canonical event log.
2. Extract semantic fields with source-hash freshness checks and preserve `UNKNOWN` / stale states.
3. Ask the existing trust gate whether the restored context is sufficient for planning.
4. Search explicitly supplied JSONL event logs for lexical experience candidates using the current request, restored active goal and explicit blockers as the query.
5. Return candidates with event ID, matched terms, source path/hash/line, evidence references, event/lifecycle status and time fields.

Safety and interpretation:
- This is a read-only local command. It does not write memory, promote candidates, update TASK_STATE/HANDOFF, resolve conflicts or execute the next step.
- Disputed and apparently conflicting records remain separate candidates. The retriever does not decide which is true.
- Every candidate starts with `transfer_decision: UNASSESSED`. Tool/language tags are descriptive only; applicability to the current project requires a separate evidence-backed assessment.
- First conservative scope criterion: when the caller explicitly supplies `--project-id`, a candidate with the exact same `project_id` receives `SCOPE_MATCHED_REQUIRES_REVIEW`; a different project receives `OUT_OF_PROJECT_SCOPE`; missing candidate or current project identity receives `PROJECT_SCOPE_UNKNOWN`. A project match is necessary for this same-project path but is not sufficient for applicability or promotion.
- The candidate-level `evidence_quality` classifier distinguishes a `verified` status label with/without recognized evidence-reference pointers, observed records, reported/hypothesis-like states, disputed/conflicted states, rejected/quarantined states, and unknown metadata. It does not independently inspect or validate the cited source content.
- When `--evidence-root` is supplied, `evidence_source_validation` checks repository-relative `kind: file` pointers for local existence/readability and rejects empty or binary-like files using a bounded UTF-8 sample check; missing, unreadable, non-file, empty or binary-like sources are blocked from the review path. Without an explicit root the result remains `NOT_CHECKED_NO_EVIDENCE_ROOT`. This is source availability/format screening, not claim validation.
- `candidate_review_gate` combines explicit project scope with that evidence-metadata state. A project mismatch remains `OUT_OF_PROJECT_SCOPE`; unknown scope remains `PROJECT_SCOPE_UNKNOWN`; same-project candidates receive specific review/blocking routes such as `SCOPE_MATCHED_VERIFIED_LABEL_WITH_REFS_REVIEW_REQUIRED` or `SCOPE_MATCHED_DISPUTED_REQUIRES_CONFLICT_REVIEW`.
- A `verified` label alone is never sufficient: even a verified label plus a file that passes the local availability/format screen does not prove the file supports the claim or that the lesson transfers to the current task. Every candidate remains `transfer_decision: UNASSESSED`; these gates route review, not authorization or promotion.
- The current event schema does not guarantee a canonical `task_branch` field, so branch matching is deliberately `NOT_EVALUATED`, not guessed from paths or prose. This pass also does not treat an event's `type` or `status` alone as a trust verdict.
- Missing or malformed requested logs fail closed; partial results are not presented as a complete search.
- Even if the lower-level context trust gate returns `AUTHORIZED_FOR_PLANNING`, this coordinator blocks planning by default with `BLOCKED_CURRENTNESS_UNVERIFIED`. Source hashes prove byte freshness relative to packet creation; they do not prove that the checkpoint still matches the live user goal or current repository/PR state.
- Candidate review may still be offered, but the returned policy explicitly says `REVIEW_CANDIDATES_ONLY_NO_PLANNING`. A future currentness gate must compare a stable task/checkpoint identity and relevant live state against authoritative evidence before it can lift this block.

Limitations:
- Retrieval is lexical, not embedding/semantic retrieval, and it searches supplied event logs only; it is not yet a complete query over every canonical MemoryRecord, lesson, decision and relation.
- It does not classify dialogue turns, preserve parent goals across side branches, publish child results automatically, or run at new-chat startup.
- The prototype does not complete UMC-01, UMC-02 or UMC-03. The acceptance matrix above remains unchanged until end-to-end behavior is demonstrated.


## Implementation audit — 2026-10-15 (PR #27)

This status table is based on direct inspection of the implementation and tests at code HEAD `06ae31ed9aba9d6ce54b2ebfbf28adbb91958a6f`, plus exact-head CI run `38747989802` (success: 188 tests, one skipped; write audit: 67 mutation sites, zero unclassified). It distinguishes existing components from an integrated end-to-end workflow.

| Stage | Existing implementation / evidence | Status and boundary |
|---|---|---|
| Immutable raw export → staging records + snapshot manifest | `tools/archive_registry_staging.py`; crash/recovery tests in `tests/test_archive_registry_staging.py` | Implemented and tested for the covered cases. Coverage remains explicitly partial/unknown when attachments or source completeness are not verified. |
| Staging snapshot → sanitized intake batch | `tools/adapt_archive_staging_to_intake.py`; metadata-only, tamper, replay and concurrent-publisher tests in `tests/test_source_ingestion_write_contracts.py` | Implemented. Competing publishers must converge on one immutable batch; a losing publisher re-reads and verifies the winner. This does not make the whole pipeline transactional. |
| Intake manifest → route proposal | `tools/plan_memory_intake.py` | Read-only planner. `IMPORT_READY` and a route plan are not authorization and do not write canonical memory. |
| Candidate source records → canonical source registry | `tools/source_evidence_registry.py` | Implemented as metadata-only append with dry-run, revalidation, locking, idempotent replay and conflict rejection. It deliberately does not assign project scope or promote semantic knowledge. Stale-lock recovery is manual. |
| Semantic candidate review / promotion into canonical event, lesson, decision or memory records | The planner can describe logical views, but no matching promotion executor was found in the inspected `tools/*.py` implementation set. | **Not implemented as a connected executable stage.** Do not mark intake complete or accepted memory merely because source metadata was registered. |
| Rebuild/refresh a derived index from canonical memory records | `tools/archive_temporal_index.py` reads and searches an export; it is not a writer that rebuilds a canonical-memory index from promoted records. No connected canonical index-refresh executor was found in the inspected tool set. | **Not connected / not verified.** |
| Restore next session from the updated authoritative state | `tools/restore_session_packet.py` reads same-project `TASK_STATE.md`, `HANDOFF.md` and `events.jsonl`; it validates scope and source hashes. | Restore component exists, but source-registry ingestion does not automatically update these authoritative project-state files or prove that a new session can restore the just-ingested batch end-to-end. |
| Orchestrate stages and resume after an interruption | Components are separate commands; no single run ledger currently coordinates staging, registry append, semantic promotion, index refresh, result publication and restore verification. | **End-to-end orchestration remains open.** A future runner must persist per-stage intent/result, reconcile uncertain outcomes against authoritative outputs, and resume idempotently. |

### Acceptance boundary

The currently verified chain ends at **metadata-only source registration**. It does not end at accepted semantic memory, refreshed derived indexes, or a verified next-session restore. Keep these stages separate until an executable orchestration and crash-injection tests demonstrate the full chain. Preserve raw source provenance and existing project boundaries throughout.


## Implementation status update — 2026-10-16

This section supersedes the stage-status conclusions in the 2026-10-15 audit above; that earlier table remains as a historical snapshot.

| Stage | Current evidence | Current status and boundary |
|---|---|---|
| Semantic candidate promotion | `tools/semantic_memory_registry.py`, `schemas/semantic_memory_approval.schema.json`, `tests/test_semantic_memory_registry.py`; exact-head CI [38851184392](https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/38851184392) passed. | Implemented as a separate approval-bound append-only writer. Receipt hashes bind the exact manifest/artifact, but do not authenticate the receipt author. No production batch was promoted during implementation. |
| Canonical multidimensional index | `tools/canonical_memory_index.py`, `tests/test_canonical_memory_index.py`; exact-head CI [38851553475](https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/38851553475) passed for the index implementation before the additional lifecycle regression test. | Deterministic immutable generation plus atomic `CURRENT.json` pointer and freshness checker implemented. The index retains all revisions and derives views without duplicate canonical records. Coverage is deliberately `PARTIAL`: no canonical correction-overlay source/contract exists in this revision, and the index reports that explicitly. |
| Normal session restore from semantic memory | `tools/restore_session_packet.py` and `tools/verified_session_restore.py` | Still open. Current restore composes task/handoff/events and code/CI revision evidence; it does not yet load accepted memory records or validate canonical memory-index coverage/freshness as part of the restore packet. |
| End-to-end orchestration/recovery | Source ingestion, promotion, and index refresh remain separate commands. | Still open. Need a durable stage ledger that reconciles registry commit, index publication, and fresh-session restore after interruption. Do not claim the full pipeline is complete. |

The canonical index uses the shared source-registry advisory lock while reading and publishing, and the index lock while publishing. A failed pointer replacement preserves the prior pointer; a newly written but unreferenced generation may remain safely orphaned. The next stage is restore integration with explicit `CURRENT_PARTIAL|STALE|INVALID|UNAVAILABLE` handling, not an assertion that a successful index build means full coverage.


## Implementation status update — 2026-10-16, session restore integration

This status supersedes the earlier statement that no semantic-memory restore consumer existed. The full pipeline is still not end-to-end verified against a production registry/archive.

| Stage | Current evidence | Status |
|---|---|---|
| Approved semantic promotion | `tools/semantic_memory_registry.py`; exact-head CI #38851184392. | Implemented and tested; no real production batch was promoted. |
| Canonical memory index | `tools/canonical_memory_index.py`; tests cover deterministic generations, multidimensional views, revision history, freshness and failed pointer publication. | Implemented. Exact source freshness is checked. Coverage remains PARTIAL because no canonical correction-overlay source exists. |
| Session restore consumes approved semantic memory | `tools/memory_aware_session_restore.py`; tests in `tests/test_memory_aware_session_restore.py` and `tests/test_memory_aware_restore_partial_status.py`; exact-head CI [#38851785241](https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/38851785241) passed. | Implemented as a read-only composition over the verified task/event restore and a fresh canonical index. It filters by exact project/task/context IDs and optional lexical substring, resolves records back to the canonical registry, returns provenance/evidence/conflicts, and marks partial/stale/unavailable states explicitly. |
| Live production acceptance / full pipeline crash recovery | Current tests use synthetic registry envelopes and mocked remote API for the base restore. No production registry/archive was run through ingestion → approval → promotion → index → restore as one transaction. | Still open. Do not claim end-to-end production acceptance or a complete index while correction overlays remain unavailable. |

Restore statuses distinguish task/event recovery from semantic-memory coverage. A stale or missing index is not interpreted as an empty memory store; an empty search in the current partial index does not prove that no relevant memory exists. The wrapper does not auto-refresh an index or mutate canonical records.


## Implementation status update — 2026-10-16, correction overlays

This section supersedes the earlier statement that no correction-overlay contract existed.

- Added `schemas/edge_correction.schema.json` and `schemas/edge_correction_approval.schema.json`, plus `tools/edge_correction_registry.py` for guarded append-only correction registration. Accepted corrections require a separate receipt bound to the exact correction input; candidate/rejected/disputed/superseded entries are preserved but not applied.
- `tools/canonical_memory_index.py` now validates the correction registry and applies accepted `add|retract|replace` operations to derived relation views only. It does not mutate source MemoryRecords. Relation targets use canonical relation fingerprints, not list positions.
- The correction-registry hash is part of generation identity and freshness. If either canonical records or corrections change, the index becomes stale until rebuilt.
- The source tree has a correction contract/writer now, but no production `registry/edge_corrections.jsonl` has been populated. Until approved correction data exists and archive/source coverage is proven, the index remains PARTIAL. The receipt hash does not cryptographically authenticate its author.
- Tests use synthetic source records and corrections. They do not establish that any real project memory is fully reconciled or that all source archives were imported.

Next: validate the exact integrated code HEAD, then add a durable pipeline coordinator that reconciles ingestion, explicit approval, semantic promotion, correction registration, index publication and fresh-session restore after crashes/replays.


## Implementation status update — 2026-10-16, durable pipeline coordinator

This section supersedes the earlier statement that ingestion, approval, promotion, correction registration, index generation and restore were only independent manual stages.

- Added `tools/memory_pipeline_coordinator.py`. It preflights approval/restore inputs, invokes source ingestion, resolves every memory provenance reference against schema-valid canonical SourceRecords, then promotes semantic memory, optionally registers a correction, refreshes the index and composes verified restore.
- The coordinator maintains a deterministic input-bound run ID and a hash-chained append-only stage ledger. Its state JSON is a rebuildable projection. If interrupted after a stage effect but before the result event, rerunning the same input fingerprint replays the idempotent stage; the coordinator does not roll back earlier append-only writes.
- Provenance validation uses stable source IDs/locators and optional archive/conversation/content-hash constraints. Missing or ambiguous references block semantic promotion. Raw provenance locators are not copied into the durable pipeline ledger.
- CI exact-head tests cover provenance resolution/ambiguity, preflight stops, ledger integrity/projection rebuild, dry-run replay and a mocked apply-stage sequence. The coordinator has **not** been run against a production archive as one transaction; production acceptance remains open.
- A partial-memory result remains partial. No source archive completeness is inferred from a successful stage chain or CI pass.

Next: verify the full coordinator against a controlled end-to-end synthetic fixture with the real stage executors, including crash points after source registration, promotion, correction append, index pointer publication and restore. Then perform a separately authorized archive acceptance/coverage audit.

## 13. UMC-03 applicability assessment — specification and first read-only implementation

**Status: UMC-03 remains `BLOCKED` in the acceptance matrix (section 10).** The current implementation is in draft PR #28 and includes the applicability evaluator, trusted-verifier injection seam, and staged S1/S2 retrieval. CI evidence must be checked against the exact head commit; this draft is not merged. Items marked "not implemented" below remain open.
Basis revision of the specification: `d3f9c610b7865793960dc652c2ccccc88afef732` (branch `integration/memory-core-clean-20261015`). PR #27 remains Draft, unmerged.

### 13.0 Terms

`APPLICABLE`, `APPLICABLE_WITH_ADAPTATION`, `NOT_APPLICABLE`, `INSUFFICIENT_DATA`, `CONFLICT` are **designed evaluator outcomes**. They are not existing repository statuses and must not be written into `lifecycle_status`, `evidence_status` or `decision_status`.

### 13.1 Facts about the current code that constrain the design

1. `retrieve_experience_candidates` searches **event-log rows** (`event_id`, `type`, `status`, `evidence_refs`, `relations`) and does not read lesson records; lesson records are read by the separate `retrieve_lesson_candidates` added with this section. The fields `trigger`, `applicability`, `exceptions` exist in `templates/lesson_record.jsonl.example`, not in the event schema. The evaluator therefore cannot assume those fields for every candidate (see rule R7).
2. `run_minimal_agent_loop` does not plan. It returns `next_action_policy: REVIEW_CANDIDATES_ONLY_NO_PLANNING` and always sets `checkpoint_currentness_gate: BLOCKED_CURRENTNESS_UNVERIFIED`. So "influence on the decision" cannot mean "influences the plan"; it must mean the fields defined in 13.4.
3. Every candidate currently carries `transfer_decision: UNASSESSED`. The evaluator is the only component that may replace it, and only in its own output, never in the source record.

### 13.2 Evaluator contract (as implemented in the current patch)

`evaluate_applicability(candidates, judgments=None) -> dict` in `tools/applicability_evaluator.py`.

- Pure and read-only: no file access, no writes, no execution; inputs are not mutated (`writes_performed: false`, `grants_planning_permission: false`).
- Inputs: the candidate list from event retrieval (`candidate_type: "event"`) and lesson retrieval (`candidate_type: "lesson"`, `retrieve_lesson_candidates`), plus explicit judgments. Conditions are **not** an input and are never extracted from free text: every criterion result is a recorded judgment.
- Judgment: `{candidate_id, candidate_type (default "lesson"), criterion, result, judged_by: rule|user|agent, basis_ref, adaptation_note?, with_candidate_id?}`. Criteria and allowed results: `problem_similarity`, `trigger`, `applicability`, `evidence_support`, `circumstances_unchanged` → `MATCH | MISMATCH | UNKNOWN`; `exceptions` → `NOT_TRIGGERED | TRIGGERED | UNKNOWN`; `compatibility` → `COMPATIBLE | CONFLICT | UNKNOWN` (`CONFLICT` requires `with_candidate_id`). Malformed judgments are listed in `judgment_issues` and never used.
- Restrictive results (`MISMATCH`, `TRIGGERED`, `CONFLICT`) are always honoured, because they only narrow use. A non-empty `basis_ref` is only a locator, not proof. Without an explicitly injected trusted rule/source verifier, all permissive judgments remain `UNKNOWN`; their claims are retained for review. The verifier is a programmatic dependency, never a field in the judgments JSON, and must independently verify the claim and source.
- Output: `assessments[]` (per candidate: `outcome`, `reason`, `criteria`, `evidence_assessment`, `needs`, `adaptation_notes`, `caps`), `usable_as_rationale[]`, `excluded[]`, `not_evaluated[]`, `needs[]`, `blocked_dependent_decisions[]`, `judgment_issues[]`, `restrictive_policy`.
- The evaluator does not read evidence files. Local source availability is screened at retrieval time (`--evidence-root`); claim support is a judgment (`evidence_support`), never inferred from a label or a pointer.
- CLI: `tools/minimal_agent_loop.py ... --lesson-log FILE (repeatable) --judgments FILE.json`.

### 13.3 Decision rules (first match wins)

In the first patch every criterion named below is a recorded judgment (13.2); a criterion without a judgment with basis is `UNKNOWN`. Rule numbers follow the order of the design discussion, not the evaluation order; the order of evaluation is R0, R1, R7, R10–R13, R2, R4, then criteria checks, R8/R12 caps.

- R0 (pre-filter, not an outcome). Candidate gate `OUT_OF_PROJECT_SCOPE` → `NOT_EVALUATED_OUT_OF_SCOPE`. The candidate is listed in `not_evaluated[]` with its original `project_id`/`scope` and is **not** assigned any of the five outcomes. Out of the current search scope does not mean inapplicable in general. In particular the existing `scope: global` lessons are retained untouched and unjudged.
- R1. `PROJECT_SCOPE_UNKNOWN` or any `*_BLOCKED` gate → `INSUFFICIENT_DATA`. The evaluator never loosens an existing gate.
- R2. A listed exception holds in the current state → `NOT_APPLICABLE`.
- R3. An exception refers to a condition whose current value is `UNKNOWN` → `INSUFFICIENT_DATA`.
- R4. Two non-superseded candidates give incompatible recommendations for the same decision → `CONFLICT` for both; the conflict is reported, not resolved.
- R5. All trigger/applicability criteria `MATCH`, no exception holds, evidence `SUPPORTS_CLAIM` → `APPLICABLE`.
- R6. Principle matches but some stated conditions differ and the difference is explicit → `APPLICABLE_WITH_ADAPTATION`.
- R7. The candidate is an event without `applicability`/`exceptions` fields, or the only conditions are free text nobody has judged → `INSUFFICIENT_DATA`. Free-text conditions are never matched by shared words.
- R10. Lesson `status` (see 13.3.1): `superseded` or `deprecated` → excluded from active rationale, reason recorded, link to the replacement kept when `supersedes`/a replacement is known (otherwise `replacement: UNKNOWN`). They are not deleted and not scored.
- R11. Lesson `disputed` → `INSUFFICIENT_DATA` with `needs: resolve dispute` (UMC-06: both claims survive, status needs review).
- R12. Lesson `candidate` → never `APPLICABLE`; ceiling `APPLICABLE_WITH_ADAPTATION` (see 13.3.1 for what the contract does and does not say). Lesson `validated` → no ceiling from status alone; other rules still apply.
- R13. A status value not listed in 13.3.1 → `INSUFFICIENT_DATA` with `needs: status semantics undefined`. The evaluator does not guess a meaning.
- R8. A criterion judged by `agent` has evidence status `inferred`. An outcome that depends on an `agent`-judged criterion cannot be `APPLICABLE`; it is at most `APPLICABLE_WITH_ADAPTATION` until a `rule` or `user` judgment is recorded.
- R8b. A `rule` or `user` judgment is accepted only with a `basis_ref` that names what exactly was confirmed (which criterion, against which current condition, which source). A judgment without `basis_ref`, or one that cites only the candidate itself, is treated as `UNKNOWN`. A `user` judgment is a statement by the user, not proof of the underlying fact; it is recorded as such.
- R9. `evidence_refs` present, a `verified` label, or a readable file never alone yield `SUPPORTS_CLAIM`. Support requires that the recorded coverage of the source includes the claim; otherwise `UNASSESSED`, and R5 cannot fire.

### 13.3.1 Status semantics — what the existing contracts define and what they do not

Lesson records use `status` ∈ `candidate | validated | disputed | superseded | deprecated` (`templates/lesson_record.jsonl.example`). The repository's lifecycle vocabulary (`tools/validate_memory.py`) is `candidate | accepted | disputed | superseded | deprecated | not_applicable`. These are two different vocabularies and must not be silently equated (`validated` ≠ `accepted`).

| Value | Defined by | What is defined | What is NOT defined |
|---|---|---|---|
| `superseded`, `deprecated` | `core/memory_model.md` | Outdated lessons are marked and linked to a replacement; never auto-deleted | How a consumer must treat them; spec rule R10 is the proposal |
| `disputed` | UMC-06 matrix row | Both claims and provenance survive; needs review; no silent overwrite | Lesson-specific handling; R11 is the proposal |
| `candidate` | `lessons/global/README.md`, UMC-03 row | Promote candidate lessons only after confirming evidence and limits; shared lessons are "used only as a candidate/limited method" | An explicit usage ceiling for a `candidate` lesson; R12 is a **new rule of this spec**, not an existing contract |
| `validated` | enum in the lesson template only | Nothing beyond its existence | Its meaning and relation to `accepted` and to evidence checks; the evaluator grants no trust from the label |

Existing-code gap to preserve in the implementation: `_evidence_quality` detects disputed/rejected/quarantined only in `decision_status` and `lifecycle_status`, not in `status`. Lesson records carry `status` only, so a `disputed` lesson would not be recognized as disputed by that classifier. The lesson path must read `status` explicitly and must not rely on the event classifier for it.

Naming: outcome `NOT_APPLICABLE` (evaluator output) is distinct from the lifecycle value `not_applicable` (stored record status). The evaluator never writes the former into a record field.

### 13.4 How the outcome affects the loop

New output fields of `run_minimal_agent_loop` (all additive):

- `assessments[]` — the results above.
- `usable_as_rationale[]` — `APPLICABLE` and `APPLICABLE_WITH_ADAPTATION` only (the latter with its adaptation notes).
- `excluded[]` — `NOT_APPLICABLE`, `superseded`, `deprecated`, with reason.
- `not_evaluated[]` — candidates outside the current search scope (R0), with their own `project_id`/`scope`; no outcome assigned.
- `needs[]` — from `INSUFFICIENT_DATA`; drives "search further or ask one question".
- `blocked_dependent_decisions[]` — from `CONFLICT`.

`next_action_policy` may gain only **more restrictive or more specific** values: `ASK_OR_SEARCH_MORE` (insufficient data), `STOP_RESOLVE_CONFLICT` (conflict). It never gains a value that permits planning.

**Authority boundaries.** The evaluator can narrow what memory may justify; it can never grant permission. Planning requires, independently: `context_trust_gate` = `AUTHORIZED_FOR_PLANNING` **and** a currentness gate that is not `BLOCKED_CURRENTNESS_UNVERIFIED` **and** autonomy limits. An `APPLICABLE` result changes none of these.

### 13.5 Progressive search and provisional experience

This generalizes the "temporary experience" idea: a wrong or incomplete claim made on the way to an answer is useful evidence, as long as it cannot silently become knowledge.

**13.5.1 Progressive search (S1/S2 implemented; S3 deferred).** The loop first searches the same project by explicit structured markers (S1: problem type, tools, languages, environment). If no verified `APPLICABLE` lesson is found, it falls back to same-project lexical expansion (S2). S1/S2 only retrieve and rank candidates; markers and lexical overlap do not prove applicability. A verified `APPLICABLE` result stops expansion. If explicit markers are absent, S1 reports `NO_MARKERS` and S2 runs. S3 (other projects) remains deferred and is never entered implicitly.
- S1: same project, structured match on tool/language/problem fields.
- S2: same project, lexical expansion (current behavior), then evaluated by 13.3.
- S3 (other projects, `scope: global` lessons): **deferred; not part of the first implementation.** No `allow_cross_project` flag is implemented. Such candidates are reported as `NOT_EVALUATED_OUT_OF_SCOPE` (R0) and retained unchanged. A later, separate decision must define a mechanism for global applicability.
Each stage records its query, source hashes and result counts. Widening beyond the project boundary is never silent.

**13.5.2 Provisional ledger.** While working, claims are recorded as provisional entries: `claim`, `origin` (step or candidate), `status: unconfirmed`, `confirmation_needed` (the concrete check that would settle it), `recorded_at`. Wrong or partial claims are recorded too, not only plausible ones.
- Scope: this run only. It is returned in the loop output; it is **not** written to canonical records and is not retrievable as experience by other tasks (if exposed at all, it is labelled `provisional`).
- First implementation is read-only. Persisting the ledger needs its own write contract and classification under `audit_write_contracts.py --strict`; this block does not authorize that.

**13.5.3 Resolution.** Each entry is resolved by an independent check with evidence, not by the final answer being accepted:
- `confirmed` → generates a **promotion proposal** (a candidate lesson record with `created_from_event_ids`, `evidence_refs`, `applicability`, `exceptions`). It enters the existing user-approval path (`semantic_memory_approval`, `decision: approve`, `actor_type: user`). No silent promotion.
- `refuted` → kept as negative experience (`approach_that_failed` plus the refuting evidence). Never deleted.
- `unresolved` → not promoted; listed in the handoff as `UNKNOWN` with its `confirmation_needed`.

A correct final claim does **not** confirm the intermediate claims that led to it. If the final claim is a generalization of what was observed, the proposal states the observed scope separately and marks the extra reach `inferred`.

### 13.6 Acceptance scenarios and what the current patch tests

Implemented in `tests/test_applicability_evaluator.py`; integration scenarios run through `run_minimal_agent_loop`.

- **T1 (revised)** (`test_t1_unverified_assertions_do_not_enter_rationale`): user/rule/agent labels plus non-empty basis references remain unverified and cannot enter `usable_as_rationale`; a restrictive mismatch can still exclude a candidate. Unverified positive assertions remain blocked; a separate integration test proves the positive path only with an injected verifier test double, not a production verifier.
- **T1b**: a `scope: global` lesson is reported in `not_evaluated`, no outcome, source file hash unchanged.
- **T1c**: `superseded`/`deprecated` excluded (replacement named when another candidate supersedes it, otherwise `UNKNOWN`); `disputed` → `INSUFFICIENT_DATA`; `candidate` capped at `APPLICABLE_WITH_ADAPTATION`; unknown status value → `INSUFFICIENT_DATA`.
- **T2**: a triggered exception → `NOT_APPLICABLE`, excluded, even with a positive lexical score and otherwise complete judgments.
- **T3a**: no judgments → `INSUFFICIENT_DATA` with named needs, `next_action_policy: ASK_OR_SEARCH_MORE`.
- **T3b**: declared incompatibility → both `CONFLICT`, `blocked_dependent_decisions` non-empty, `next_action_policy: STOP_RESOLVE_CONFLICT`.
- **T4 (revised)**: even when all supplied judgments are permissive, they remain unverified; no lesson enters `usable_as_rationale`, `checkpoint_currentness_gate` stays `BLOCKED_CURRENTNESS_UNVERIFIED`, and untrusted context stays refused. Blocked sources keep `STOP_AND_RECONCILE_SOURCES`.
- Fail-closed retrieval: invalid lesson JSONL, a lesson without `lesson_id` and a missing lesson file block the pass; malformed `evidence_refs` are flagged, not reinterpreted.

The lesson records in these tests are fixtures. They demonstrate the mechanism; they are not evidence that any real repository lesson, including the existing `scope: global` records, is applicable. **T5 (provisional ledger) is not implemented.**

### 13.7 Unchanged

`context_trust_gate` still decides only trust in restored context. Storage, promotion and index mechanisms, registry contracts and schemas are not extended. No new status values are added to existing records.

### 13.8 Condition for leaving BLOCKED

`UMC-03` changes from `BLOCKED` to `PARTIAL` only when: the evaluator is called from `run_minimal_agent_loop`; T1–T4 pass; and CI is green on the exact commit that contains them. It cannot be `PASS` while the loop has no consumer that actually plans or acts on `usable_as_rationale` and `blocked_dependent_decisions`; until then the matrix row must say so. T5 gates the provisional-ledger part separately and does not affect the T1–T4 condition.

### 13.9 Decisions recorded (owner: user, 2026-10-16)

1. Retrieval searches **both** event logs and lesson-record files, as **separate candidate types** (`candidate_type: event | lesson`); they are not merged. Events carry history (actions, results, errors); lesson records carry trigger/applicability/exceptions. An event without structured conditions stays `INSUFFICIENT_DATA` (R7) and is history, not a rule.
2. S3 is deferred. S1 uses explicit same-project marker overlap; S2 is the same-project lexical fallback. The five existing `scope: global` lessons stay as they are and are marked out of scope; this says nothing about their applicability in general.
3. Tests for the evaluator use project-lesson **fixtures**. Their results are not evidence that any real global lesson is applicable.

### 13.10 Not implemented by the first patch

The provisional-experience ledger (13.5.2) and its scenario T5; S3 / `allow_cross_project`; a production trusted verifier implementation and its trust configuration; writing any ledger to disk; automatic promotion of lessons; automatic extraction of conditions from free text; any change to record schemas, status vocabularies or registry contracts. If a record's status or scope cannot be determined from existing contracts, the evaluator reports the uncertainty (R13) rather than supplying a meaning.
