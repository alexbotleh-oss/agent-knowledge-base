# Platform, chat, project and shared-memory contract

**Status:** integration contract / design under implementation. This document defines how agents should route memory across ChatGPT platform instructions, project instructions, individual chats, project repositories and the shared knowledge base. It does not imply that ChatGPT automatically exposes every chat, instruction, attachment or repository to every session.

## 1. The problem this contract solves

The agent must not depend on a model spontaneously remembering where knowledge lives. Every session should follow an explicit route: identify the active goal and available access, restore local state, search relevant experience, verify applicability, act, and record the result. A route is successful only when the underlying source was actually read and its evidence supports the conclusion.

## 2. Authority and ownership boundaries

Use each layer for the job it can reliably perform:

1. **Platform/system instructions and platform settings** — universal safety, product-level behavior, and constraints that apply across chats. Repository files cannot override platform rules. Do not assume a repository can read or modify platform settings.
2. **Project instructions** — project identity, local scope, required repository/source locations, local acceptance criteria, and project-specific prohibitions. They point to canonical files; they should not duplicate long histories.
3. **Current chat / working memory** — current conversational intent, active subtask, temporary hypotheses, unresolved questions, and short-lived discoveries not yet safely promoted. It is not a durable source of truth.
4. **Project memory cell/repository** — project facts, decisions, event chronology, failures, tests, task state and handoff for that project. Project-specific facts stay here.
5. **Shared agent knowledge base** — reusable methods, skills, cross-project lessons, retrieval descriptors and links to evidence. It stores transferable knowledge, not a merged chronology of unrelated projects.
6. **Immutable source archive / RAW** — original chat exports, attachments, logs and artifacts retained for re-extraction and audit. Derived summaries never replace RAW.
7. **Indexes and retrieval caches** — rebuildable projections that point to source records. An index is not the authoritative record and must be refreshed from accepted/versioned data.

When these layers conflict, obey platform constraints first; then explicit user decisions and active task scope; then source-grounded project state/history; then universal repository procedures. Preserve and report conflicts rather than silently choosing the most convenient value.

## 3. Chat-local short-term memory and promotion lifecycle

Every durable candidate should have a stable ID, source references, timestamps with known precision, project/scope attribution, evidence status, confidence, lifecycle status, and links to related records.

Recommended lifecycle:

- `LOCAL_ACTIVE`: temporary context in the current chat; not yet durable.
- `CAPTURED`: a source-bound event/candidate has been written to a durable local log.
- `EXTRACTION_PENDING`: RAW/source parsing or chronology validation is incomplete.
- `CANDIDATE_SHARED`: a transferable lesson/method has been proposed, with source evidence and applicability limits.
- `APPROVED`: review accepted the exact candidate version and evidence set.
- `PROMOTED`: versioned record exists in the shared knowledge base and can be resolved by stable ID.
- `INDEX_PENDING` / `INDEXED`: canonical index refresh is pending / completed for that record version.
- `QUARANTINED` / `CONFLICTED`: source, attribution, duplicate identity, safety, or contradiction needs resolution.
- `SUPERSEDED`: a newer record changes the active interpretation; prior versions remain traceable.

Promotion is not a move. Local event history and RAW remain intact. If shared promotion or indexing fails, retain the candidate and retry safely; never report success based only on an attempted write. `IMPORT_READY` is not approval. Approval must bind the exact candidate bytes/version and provenance.

## 4. Retrieval route: shortest justified path, not broadest search

Use progressive widening and stop when evidence is sufficient:

1. **Goal and scope:** identify the active project/task and what decision/action needs support.
2. **Local restore:** read the current chat context and available project instructions, TASK_STATE/HANDOFF, latest events and accepted decisions. Verify current repository HEAD/CI if the task depends on code state.
3. **Cheap candidate filtering:** filter by source, project, date range, record type, stack/language/tool, event or failure category, status, and known applicability descriptors. These are retrieval hints, not proof of applicability.
4. **Context expansion:** inspect parent/child tasks, adjacent events, relevant decisions, linked source excerpts, failed attempts, tests, and negative lessons.
5. **Applicability check:** compare preconditions, environment, version, objective, constraints, and known non-applicability. Record why a memory item does or does not transfer.
6. **Contradiction/gap search:** widen to other project cells and shared memory when local evidence is insufficient, conflicting, stale, or reveals an unexplained failure. Search for counterexamples, not only confirming matches.
7. **Evidence packet:** return a compact set of claims with stable IDs, source links, status, relevant excerpts, applicability rationale, conflicts and unknowns.
8. **Decision and stop condition:** act only when the required evidence/permission threshold is met. If a key uncertainty remains, take safe independent steps and ask one targeted question only when the user's decision/access is genuinely required.

Do not search every repository for every trivial turn. Do search related memories proactively when the action is consequential, when a known failure pattern may recur, or when the local route detects a gap or contradiction.

## 5. Agent instructions: what each layer should say

**Platform-level instructions** should establish the general obligation to restore relevant available context, distinguish source-backed fact from inference, respect instruction hierarchy, and never claim access or persistence that was not verified.

**Project-level instructions** should identify the canonical project cell, current-state files, event log, decisions, handoff, test/CI sources, shared-memory entry point and explicit exclusions. They should tell the agent how to discover access and what to do when access is missing.

**Chat/session instructions** should preserve the current goal, constraints, active/deferred branches, return condition, temporary candidates and next step. They should point to durable files rather than attempt to contain the whole project history.

**Shared-memory records** should contain reusable experience with source links, preconditions, limits, negative evidence, confidence/status and feedback from actual application.

Instructions should be short operational entry points with links to canonical protocols. Do not copy whole architecture documents into every project or chat; duplication creates drift.

## 6. Evidence contract and truthful status

Use separate states for access and processing: `NOT_CHECKED`, `AVAILABLE`, `READ`, `EXTRACTED`, `ANALYZED`, `VERIFIED`, `BLOCKED`. “Found” is not “read”; “read” is not “verified”.

Use separate states for implementation: `SPEC_ONLY`, `IMPLEMENTED_PARTIAL`, `VERIFIED_SYNTHETIC`, `PROTOTYPE_NOT_ACCEPTED`, `BLOCKED`, `ACCEPTED_REAL_INPUTS`. Tests must name the exact revision, inputs and runtime. Skipped checks are not passes. A prior checkpoint is a claim to revalidate, not live proof.

Every consequential operation should distinguish intent, attempted action, tool acknowledgement, observed result and independent verification. If acknowledgement or side-effect status is unknown, preserve `UNKNOWN` until checked; do not blindly replay non-idempotent actions.

## 7. Experience-in-action feedback loop

For each meaningful reuse of memory, capture:
- candidate memory IDs and versions used;
- why each was applicable (or rejected);
- action taken and relevant environment/version;
- observed result and independent verification;
- whether the experience was confirmed, refined, limited, contradicted or not tested;
- resulting follow-up candidate and source evidence.

A memory record is not proven merely because it was retrieved. Failed application is valuable evidence and should refine applicability, not be converted automatically into a universal prohibition.

## 8. Cross-chat and cross-repository limitations

A new chat may not have direct access to another chat's transcript, project instructions, files, or repository. The agent must inspect what is actually available through the current platform/tools. If access is absent, record the missing source and continue with available evidence; request only the minimum necessary access or export. Never claim automatic cross-chat synchronization, automatic promotion, or startup restore until an executable mechanism and acceptance test demonstrate it.

Where project repositories have local memory cells, they should use the same schema/protocol version and expose compact manifests/links for shared retrieval. The shared repository should reference local evidence by stable repository/path/revision/source ID; it should not copy entire project histories by default.

## 9. Acceptance gates for the integrated system

The system is not end-to-end complete until tests demonstrate, against exact revisions:

1. A new session can restore the correct goal and local state without confusing separate projects.
2. A candidate remains local while incomplete and is safely retried after interrupted capture.
3. Approved experience is promoted with stable identity, immutable provenance and version history.
4. The canonical index refreshes after promotion and can be rebuilt without changing source records.
5. Ordinary session restore can retrieve promoted knowledge and follow its evidence links.
6. Retrieval filters reduce search cost but widen on missing context, contradiction or failed applicability.
7. Rejected, stale, duplicate and ambiguous candidates cannot silently overwrite accepted memory.
8. Experience-in-action feedback changes a candidate's status only with recorded evidence.
9. Cross-chat limitations are surfaced honestly when the necessary connector/source is unavailable.
10. CI reports the exact revision and clearly distinguishes PASS, FAIL, SKIP, BLOCKED and real-input acceptance.

Until each gate is evidenced, report the capability as partial or blocked rather than implying that the architecture is already operational.
