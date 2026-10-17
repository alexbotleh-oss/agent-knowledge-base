# Cluster integration audit — 2026-10-17

## Purpose and scope

This audit answers four operational questions:
1. Which memory/continuity mechanisms already exist and where?
2. Which can be composed now without duplicating authority?
3. Which contracts/adapters do not match the actual ChatGPT + GitHub workflow?
4. What is missing before the system becomes one coherent, verifiable working cluster?

This is a repository/branch inspection, not a claim that the current ChatGPT session automatically executes these tools. Branch and CI facts below are revision-scoped. Existing archive-transfer work remains deferred; this audit does not restart archive ingestion. Browser-extension implementation and integration remain deferred by project instruction.

## 1. Live repository and branch topology

- main: a0c12ba849a3416f50e1289d8f0dd20844e1e51f.
- PR #27 integration branch: integration/memory-core-clean-20261015, HEAD 9eb2ab86fb3cc99791c8803b5ac3564ce9b63b19, Draft/open/unmerged.
- PR #34: relocation-aware discovery, HEAD 2d661ee60da6981ad3d8ad150b7f86f0a5ae0cb7, Draft/open/unmerged, based on #27.
- PR #35: capability-aware local source search, HEAD c979abd99f0e525a94cbe31ea74bc3f9cc496e86, Draft/open/unmerged, based on #34.
- Exact-head CI for #35: run 39015228626 — SUCCESS; 315 Python tests (1 skipped), 4 Node tests, write-contract audit 127 mutation sites / 0 unclassified, memory/stack validation passed.
- More than 30 PRs are open. Many are historical project-memory transfers; they are not automatically components of the current runtime. Do not bulk-merge them or treat open as integrated.

Relevant parallel drafts checked:
- PR #33 identity/global-project instructions, HEAD 82ce508c6b77f6060e4674ecfe24830b61eb27c6, based on main; exact-head CI 39012907765 SUCCESS.
- PR #32 in-chat pre/post-action writeback protocol, HEAD e5016171ea25a129a45d243441635ebb1353f858, based on integration HEAD 9eb2ab86; exact-head CI 39005787842 SUCCESS.
- PR #31 rolling dialogue window / resumable archive and attachment adapters, HEAD 4b05e0bb3b69d32235c08497cd9a08282e0aa938; exact-head CI 39010720187 SUCCESS. Browser-extension changes in this branch remain deferred; do not activate or extend them in this task.
- PR #30 attention/return controller, HEAD 85137d13c40777ef9f48cf305a0811c1e26cb3f1, based on audit branch #29 rather than current #27 HEAD; exact-head CI 38999888341 SUCCESS.
- PR #29 implementation audit, HEAD 57aa847f0f0104625d6cb6104111c4ee66a9b0cd, based on older integration revision d3f9c610; CI 38899172605 SUCCESS.
- PR #28 applicability evaluator / decision frontier, HEAD b6d32a3c36aa5df8079f63aad20fd41a8f56c512, based on older integration revision d3f9c610; CI 38897881585 SUCCESS.
- PR #26 minimal candidate-retrieval loop remains a separate historical draft chain, although later versions of its tools are present on the integration branch.

All listed PRs remain unmerged. main has not been modified.

## 2. Existing mechanisms grouped by responsibility

### A. Durable import and approved-memory data pipeline

Existing implementation on the integration lineage:
- tools/resumable_chat_import.py — immutable source snapshot, incremental parsing/import state and resumable local import.
- tools/archive_registry_staging.py — archive inventory and source metadata staging.
- tools/adapt_archive_staging_to_intake.py, tools/plan_memory_intake.py, tools/validate_memory.py — convert/validate intake and propose routes.
- tools/source_ingestion_runner.py, tools/source_evidence_registry.py, tools/source_registry_contract.py — resumable metadata-only source registration with identity, hash-chain and replay protections.
- tools/semantic_memory_registry.py — separately approved semantic-memory promotion.
- tools/edge_correction_registry.py — append-only relation corrections/retractions.
- tools/canonical_memory_index.py — rebuildable, versioned index derived from canonical memory.
- tools/memory_pipeline_coordinator.py — composes ingestion, provenance validation, approved promotion, optional correction registration, index refresh and fresh restore when given required inputs and approval receipt.
- Tests include real synthetic ingestion-to-promotion/index/restore and real-stage checks.

What is already composable: the controlled source-to-approved-memory-to-index-to-restore path is the strongest existing end-to-end data pipeline. It has synthetic integration evidence.

Boundary: source registration alone is metadata-only and is not semantic-memory promotion. A route plan is not a writer. A successful synthetic fixture does not prove production archive completeness. The separate PR #31 tools/resumable_archive_pipeline.py composes raw export import → staging → metadata source registration, but it is not on the current #35 branch and does not itself perform semantic promotion/index refresh. Its interface should be reconciled with tools/memory_pipeline_coordinator.py before combining them.

### B. Session restoration and experience retrieval

Several valid but distinct paths currently coexist:
- tools/restore_session_packet.py builds a local source-backed task packet.
- tools/verified_session_restore.py compares local state with selected live GitHub revision/blob evidence and assembles a verified restore packet.
- tools/memory_aware_session_restore.py adds freshness-checked retrieval from the approved semantic-memory index and now invokes local adaptive discovery after PARTIAL_NO_MATCH.
- tools/minimal_agent_loop.py restores a task packet, extracts semantic context, searches explicitly supplied event logs for experience candidates and applies a trust gate. It is intentionally review-only: no planning authorization from unverified currentness, no writes and no action execution.
- PR #30 adds tools/task_start_experience_map.py and a broader tools/agent_memory_cycle.py composition candidate. PR #30 is based on the older audit branch and is not integrated into #35.
- PR #28 adds tools/applicability_evaluator.py and tools/decision_frontier.py. The evaluator is fail-closed; permissive judgments remain unknown until a trusted verifier is connected.

Main integration defect: these are not one task-start path. minimal_agent_loop and memory_aware_session_restore use different retrieval inputs and have different outputs. The current adaptive fallback is connected only to memory_aware_session_restore, not to the candidate-retrieval/applicability path. The task-start/attention cycle is on another branch. The system can therefore recover one kind of context without invoking the other.

Direct call-graph check against the exact PR #30 source (HEAD 85137d13c40777ef9f48cf305a0811c1e26cb3f1) makes the boundary more specific:
- `agent_memory_cycle.run_cycle()` calls `build_task_start_experience_map()`, attention inspection, branch-return reconciliation, and (only on an explicit return request) the guarded parent-return path.
- `build_task_start_experience_map()` calls `run_minimal_agent_loop()`, attention inspection, and `evaluate_check_reuse()`; its candidate expansion verifies source file hashes and record IDs.
- Neither function calls `build_memory_aware_packet()` / `retrieve_approved_memory()`, `applicability_evaluator.evaluate_applicability()`, or `decision_frontier.reduce_decision_frontier()`. The trusted receipt verifier is used for signed parent-return acknowledgement, not as the missing applicability-verification bridge.
- Therefore the name/comment “single local entry point for the current connected memory cycle” is accurate only for the attention + event/lesson-candidate + branch-return subcycle. It is not yet the unified task-start orchestrator described above. This is a source-inspected call-graph finding, not an inference from filenames or CI.

Integration implication: do not simply port PR #30 as the cluster entry point. First define the shared packet contract and adapt this cycle to accept/return the verified restore packet and candidate assessments, then call the applicability evaluator and decision frontier exactly once. Keep branch-return authorization as a separate optional operation so it cannot accidentally authorize use of a memory candidate.

Recommended composition contract: one outer task-start orchestrator should:
1. restore the authoritative task/checkpoint and verify live source freshness;
2. retrieve approved semantic memories;
3. retrieve event/lesson candidates from configured sources;
4. independently evaluate applicability/conflicts and retain provenance;
5. produce a decision frontier with KEEP-FOR-REVIEW / HOLD / EXCLUDE / CONFLICT / OUT-OF-SCOPE;
6. pass only a verified context packet to planning.
This is an integration target, not a claim that such a complete orchestrator exists today. Reuse agent_memory_cycle.py as a candidate only after reconciling its older base and checking that it also calls the approved-memory path; do not create a second coordinator by default.

### C. Attention, branch return, reuse of checks and trusted evidence

PR #30 contains:
- dialogue_attention_controller.py — deterministic turn classification and a return stack reconstructed from the AGENT_MEMORY_SYSTEM event log; ambiguous turns remain review-needed.
- branch_result_registry.py and reconcile_branch_returns.py — linked child results, explicit owner acknowledgement and parent return checks.
- check_reuse_policy.py — reuse of a prior check only when input/source/candidate fingerprints still match.
- trusted_receipt_verifier.py — signed receipt verification against a keyring whose hash is pinned outside the repository.
- task_start_experience_map.py / agent_memory_cycle.py — intended composition.

These mechanisms are useful and should be integrated selectively, not copied into parallel variants. Their current CI is on PR #30's older branch lineage. Before inclusion, re-run tests against the current integration head and reconcile event schemas, imports and dependencies. A keyring file or a verified label alone is not trust; the external pinned keyring and actual verifier call are part of the contract.

### D. Turn lifecycle, dialogue memory and writeback

On the current integration lineage:
- tools/turn_lifecycle_ledger.py stores local turn lifecycle states and exact turn text in a private default path; it requires a caller to record the turn.
- tools/turn_lifecycle_adapter.py exposes a loopback HTTP API with bearer authentication. It does not inspect ChatGPT or infer that a response was delivered.
- clients/turn_lifecycle_client.js is a client SDK for a trusted wrapper; it does not scrape ChatGPT or run by itself.
- projects/AGENT_MEMORY_SYSTEM/events.jsonl is the append-only project event history; TASK_STATE.md, HANDOFF.md and CONTINUITY_CHECKPOINT.json are state/checkpoint views with guarded writers and recovery tests.

PR #32 adds core/in_chat_memory_writeback_protocol.md and projects/AGENT_MEMORY_SYSTEM/TURN_JOURNAL.jsonl. The protocol specifies pre-action intent and post-action evidence recording, but its own journal records that the first pre-action write was retrospective. It explicitly says the protocol is not automatic platform behavior.

PR #31 adds tools/dialogue_window.py, a rolling message-pair view builder, plus private attachment-library/adapters and extension-side work. The design correctly distinguishes a canonical private message ledger, derived windows, project state and long-term memory. The extension branch is deferred and is not a current runtime dependency.

Main integration defect: the turn lifecycle ledger, project event log and PR #32 TURN_JOURNAL have overlapping but not identical purposes. They should not become three competing sources of truth. Define one canonical contract:
- turn lifecycle ledger: received/started/progress/report/submitted/delivery-acknowledged/failed states;
- project events.jsonl: task decisions, actions, verified outcomes and cross-branch links;
- optional private message ledger: full user/assistant message pairs and attachment references;
- TASK_STATE/HANDOFF/checkpoint: derived current-state projections.
Each event should carry stable IDs and cross-references. TURN_JOURNAL.jsonl should either become a thin projection/reference to canonical turn events or be retired from the active path; do not append the same lifecycle event independently to both journals.

### E. Instructions, identity and bootstrap

PR #33 contains core/agent_bootstrap.md, core/chatgpt_global_instructions.md, core/identity_and_continuity_contract.md and projects/AGENT_MEMORY_SYSTEM/CHATGPT_PROJECT_INSTRUCTIONS.md. Exact-head CI passed on PR #33, but the branch is separate from #27/#35 and based on main.

Important correction to the previous component-map finding: core/agent_bootstrap.md is absent from main, current #27 integration and #35, but it is present on PR #33's branch. This is a branch-location discrepancy, not global absence. Its global instruction currently links to a feature-branch URL. After deliberate integration, the entry point must be changed to a stable canonical ref; until then, don't assume #35 can read it at its own branch path.

PR #32 and PR #31 also edit core/universal_instructions.md, and PR #33 edits it from a separate base. These changes must be reconciled into one ordered contract rather than merged as independent text patches. The current project instruction explicitly defers browser-extension work; that constraint remains in force.

## 3. What can be connected now, and what needs adaptation

| Area | Existing usable pieces | Integration status | Required adaptation |
|---|---|---|---|
| Import → source registry | Resumable importer, staging, intake validator, source-ingestion runner | Components exist; source pipeline has resumable stages | Bring PR #31 archive pipeline in selectively after API/schema reconciliation; prove raw export → source registry in one current-head test |
| Source registry → approved memory → index → restore | Pipeline coordinator, semantic registry, correction overlay, canonical index, memory-aware restore | Strongest connected pipeline; synthetic E2E exists | Keep approval as a separate gate; add full source-catalog search and result publication to the same run record |
| Task-start restore | Verified restore, local restore packet, minimal loop, semantic-memory restore | Parallel paths | Choose one outer orchestrator and explicit subcontracts; remove duplicate restore work without losing capabilities |
| Experience reuse | Candidate retrieval, applicability evaluator, decision frontier, reuse policy | Split across #27/#28/#30 lineages | Wire candidate output → evaluator → frontier → task planner; connect trusted verifier through actual receipt validation |
| Attention/return | Dialogue attention controller, branch result registry, reconciliation, signed acknowledgement | PR #30 separate branch | Rebase/selectively port onto current #27 HEAD; ensure it writes the canonical event log and cannot override parent state without accepted child result |
| Per-turn persistence | Turn lifecycle ledger/adapter/client; writeback protocol | Local adapter exists; protocol exists in #32 | Make the current ChatGPT host able to call an actual persistence interface, or explicitly classify writeback as unavailable. Do not imply instructions themselves execute writes |
| Short-term dialogue | Dialogue window builder and message ledger design in #31 | Separate draft; extension deferred | Keep full messages in private storage; link windows to message/turn IDs; do not make the extension a dependency |
| Instructions/bootstrap | PR #33 global/project contract | Separate main-based draft | Reconcile edits to universal instructions with #31/#32; replace branch-pinned bootstrap URL only after a stable integration location exists |
| Remote source discovery | Local source catalog + relocation/adaptive search | Local-only | Add GitHub branch/revision adapter with access/coverage/freshness, branch HEAD SHA, file blob SHA and conflict handling |
| Current ChatGPT execution | GitHub connector can inspect/write repository files and CI validates commits | No live caller for repository Python tools | Add a supported callable runtime/connector bridge or explicitly run the tools in an external local environment. Current loopback adapter is not directly callable from this chat |
| Production archive acceptance | Raw importer and source/semantic pipeline; historical audits | Synthetic evidence only; full archive coverage remains unresolved | Keep deferred until the retrieval/restore cluster is coherent; then run exact immutable source acceptance with coverage manifest |

## 4. Search and source-catalog findings

tools/adaptive_source_search.py supports preferred/fallback/emergency tiers and correctly treats unknown metadata as fallback rather than exclusion. It stops early only after verified identity/hash evidence and does not move or promote files.

However, its current integration in tools/memory_aware_session_restore.py supplies stable identity, lexical query and project ID, but does not populate request source_type, format, required_capabilities or size_bytes. Therefore the general capability-aware ranking engine exists, but the integrated restore path currently exercises only a subset of its capability filters.

registry/source_catalog.json covers configured local roots in the current checkout. It does not enumerate remote branches or other open PR heads. PR #33 demonstrates why branch-aware lookup is required: a source absent from the active integration branch exists on a known separate PR branch. A future remote adapter must preserve exact ref/HEAD/blob identity and distinguish:
- not found at this ref/path;
- found at another ref;
- multiple/conflicting revisions;
- access denied/unavailable;
- incomplete scan;
- not found within all actually searched refs.
No global-absence claim is allowed from a partial branch list.

## 5. The communication/runtime boundary

The current working arrangement is ChatGPT conversation + GitHub connector. The connector can read files, inspect PRs/commits/CI and write repository files; it does not execute arbitrary Python from the checkout inside this chat. GitHub Actions executes validation after repository events, not as an automatic handler for each user turn.

The existing loopback HTTP adapter requires a trusted client on the same machine and explicit calls before/after work. It does not by itself connect this ChatGPT conversation to local disk. The client SDK is not a host. The extension could become such a host in a future scope, but it remains deferred.

Thus, the missing connection is not another memory format: it is an explicit runtime bridge between the actual conversation host and the existing persistence/restore tools. That bridge must provide:
- pre-action request receipt with stable turn/task IDs;
- post-action results and evidence;
- idempotent writes and read-back acknowledgement;
- a safe, authenticated invocation of restore/search/checks;
- explicit unavailable/partial status if the host cannot call it.
Until the bridge is available, the agent must use the GitHub connector for the operations it supports and must not claim automatic per-turn capture, local tool execution or cross-chat restore.

## 6. Recommended integration order

1. Freeze the inventory, not the repository. Keep all PRs open; no bulk merge. Treat this report as the revision-scoped map.
2. Reconcile contracts first: PR #33 bootstrap/identity + PR #32 writeback + current #27 runtime protocol. Resolve edits to universal_instructions.md, event IDs and journal ownership; do not create duplicate authoritative logs.
3. Choose one task-start orchestrator: use agent_memory_cycle.py from PR #30 as a candidate, not an automatic winner. Compare its actual call graph with memory_aware_session_restore.py and minimal_agent_loop.py; ensure approved-memory retrieval, candidate retrieval, applicability, attention state and trust gates are all reached exactly once.
4. Integrate the import front-end: selectively bring resumable_archive_pipeline.py and its tests from PR #31 only after matching interfaces with the current memory_pipeline_coordinator.py. Keep the browser extension and attachment integration out of scope.
5. Finish retrieval routing: add the remote GitHub source adapter and pass real source-type/capability constraints into adaptive search.
6. Define one host/runtime bridge for this ChatGPT + GitHub operating method. Do not assume a local HTTP server or instructions are callable from the chat.
7. Run cross-path end-to-end tests on the final integrated head: source import → approved memory/index → restore; task start → experience candidates → applicability/trust gate → decision frontier; side branch → accepted result → parent return; turn receipt → result writeback → restart recovery; missing expected source → alternate branch discovery.
8. Only then return to production archive completeness. Preserve the raw archive and prior findings; don't repeat already completed source-report reconciliation without a new evidence-based reason.

## 7. Acceptance definition for one working cluster

The cluster is not accepted merely because every module imports or CI passes. Acceptance requires one explicit entrypoint and observable evidence that:
- the active task and return point are restored from current sources;
- approved memory and candidate experience are both retrieved without confusing their authority;
- applicability and trust gates actually influence the next action;
- a failed local lookup expands to configured alternative sources, including remote refs when implemented;
- turn results are persisted and read back through the supported host connection;
- partial failure stays PARTIAL/BLOCKED rather than false PASS/COMPLETE;
- the next process can resume from the stored state;
- the user-visible report is derived from verified outcomes, not only from the plan or a prior summary.

## Current status

- Implemented: multiple robust components; a connected synthetic source-to-approved-memory/index/restore pipeline; local adaptive source discovery; turn lifecycle service/ledger; candidate retrieval and trust-gate primitives.
- Verified in separate drafts: identity/bootstrap (#33), writeback protocol (#32), dialogue window/archive adapter (#31), attention/return and signed receipt cycle (#30), applicability/decision frontier (#28).
- Not yet one integrated cluster: these drafts have different bases, schemas and entrypoints.
- Main missing capability: a single orchestrated task lifecycle connected to the actual ChatGPT host, with one event/state contract and cross-branch source discovery.
- Safety: PR #35 remains Draft/open/unmerged; main unchanged. Browser-extension integration and large archive transfer remain deferred.
