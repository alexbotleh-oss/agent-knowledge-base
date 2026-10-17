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
- PR #35: capability-aware local source search and cluster audit, current observed HEAD 5ee3816d3d780cccd6124df85de733e9485fb273, Draft/open/unmerged, based on #34.
- PR #36: unified task-start cluster, stacked on #35; code integration checkpoint 9f89d5f2156ac34c862875f76bfcdab046c49454 passed exact-head CI run 39018028508 (429 Python tests, 1 skipped; write audit 143 mutation sites / 0 unclassified). Later documentation-only commits require their own final-head CI check.
- Exact-head CI for audit checkpoint f4d874c7a9bc3e81c5ebe29f5609d4b1c2055acd: run 39016798651 — SUCCESS; both memory-protocol/record validation and knowledge-base/stack validation passed. Earlier code checkpoint c979abd99f0e525a94cbe31ea74bc3f9cc496e86 passed run 39015228626 with 315 Python tests (1 skipped), 4 Node tests, write-contract audit 127 mutation sites / 0 unclassified.
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

At the audited PR #35 revision, these were not one task-start path. PR #36 now adds an explicit local composition that invokes memory-aware restore when a repository is configured, passes the same packet into the candidate/applicability path, and combines attention/reuse/branch-return mechanisms. This removes the duplicate task restore and connects the major local task-start capabilities. The composition remains an explicit CLI, not automatic ChatGPT startup; its final exact-head CI and end-to-end runtime bridge still require separate verification.

Direct call-graph check against the exact PR #30 source (HEAD 85137d13c40777ef9f48cf305a0811c1e26cb3f1) makes the boundary more specific:
- `agent_memory_cycle.run_cycle()` calls `build_task_start_experience_map()`, attention inspection, branch-return reconciliation, and (only on an explicit return request) the guarded parent-return path.
- `build_task_start_experience_map()` calls `run_minimal_agent_loop()`, attention inspection, and `evaluate_check_reuse()`; its candidate expansion verifies source file hashes and record IDs.
- Neither function calls `build_memory_aware_packet()` / `retrieve_approved_memory()`, `applicability_evaluator.evaluate_applicability()`, or `decision_frontier.reduce_decision_frontier()`. The trusted receipt verifier is used for signed parent-return acknowledgement, not as the missing applicability-verification bridge.
- Therefore the name/comment “single local entry point for the current connected memory cycle” is accurate only for the attention + event/lesson-candidate + branch-return subcycle. It is not yet the unified task-start orchestrator described above. This is a source-inspected call-graph finding, not an inference from filenames or CI.

Integration implication: PR #36 selectively ports the #28/#30 primitives and defines a shared packet flow: one memory-aware restore packet is injected into candidate retrieval, applicability and decision-frontier evaluation run within the minimal loop, and attention/reuse/optional parent return remain distinct gates. Parent-return authorization is still separate and cannot authorize a memory candidate.

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

At PR #35, the restore path supplied identity, lexical query and project ID but omitted source_type, format and required_capabilities. PR #36 now supplies source_type=semantic_memory, format=jsonl and required_capabilities=[approved_records, source_provenance] when searching after a partial memory-index no-match. Size constraints remain unused because this restore request does not know the source item's byte size. Other task/event discovery adapters still need to pass their own source constraints.

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
5. Finish retrieval routing: wire the bounded remote GitHub adapter into the partial-memory fallback, preserve branch/blob provenance, and test stale refs and partial access. PR #37 now implements this bounded step.
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

## 8. Audit self-check: documented lesson not applied to a new event

Direct inspection of `projects/AGENT_MEMORY_SYSTEM/events.jsonl` found that `EVT-AGMS-20261017-002` was appended after `EVT-AGMS-20261017-001`, yet its relation pointed backward using `followed_by`. The repository already contains lesson `L-AGMS-20261013-002` and prior correction events explaining this exact relation-direction failure.

- **Observed:** the new event violated an existing documented rule.
- **Correction:** the original event was left unchanged; `EVT-AGMS-20261017-003` was appended with an `edge_corrections` overlay changing the interpreted relation to `preceded_by`.
- **System implication:** this is direct evidence that a stored lesson did not reliably influence the next write. A pre-write temporal-relation validator and regression test are still missing. The current architecture audit can identify imports and declared paths, but does not check semantic consistency of event relations.
- **Status:** source discrepancy confirmed and corrected append-only; prevention is not implemented.

## Previous checkpoint after PR #36 composition

- Implemented and narrowly tested: PR #36 ports the applicable #28/#30 modules into the #35 lineage; one explicit `agent_memory_cycle.py` entry point now composes verified task restore + approved semantic-memory retrieval + event/lesson candidate retrieval + applicability/frontier + attention/check-reuse + optional guarded parent return.
- Single-restore contract: the memory-aware packet is passed through to the candidate loop; a regression test rejects a second call to the local restore builder.
- Honest readiness: `cluster_readiness` is separate from legacy cycle status and marks missing repository/semantic-memory configuration as PARTIAL rather than complete.
- Exact code checkpoint `9f89d5f2156ac34c862875f76bfcdab046c49454` passed CI run 39018028508: 429 Python tests, 1 skipped; strict write audit 143 mutation sites / 0 unclassified. Final documentation/checkpoint HEAD still requires its own exact-head CI check.
- Still not one production runtime: ChatGPT does not automatically invoke this CLI; trusted local host/writeback bridge is absent; remote branch/commit search and external source adapters are not implemented; trusted applicability remains fail-closed without external pinned keyring configuration.
- PR #36 is Draft/open/unmerged, stacked on #35/#34/#27. main unchanged. Browser-extension integration and large archive transfer remain deferred.

## Current status after PR #37 remote source integration

- **Remote adapter implemented:** tools/github_source_discovery.py searches expected paths across explicit branch/commit refs, then known alternate paths. It records exact commit SHA, Git blob SHA, content SHA-256, size and identity evidence; it rechecks branch stability after a verified match.
- **Catalog added:** registry/remote_source_catalog.json lists known refs and source paths, including the exact blob for core/agent_bootstrap.md previously located in PR #33. The catalog is a bounded allowlist, not a claim that every branch or external source is covered.
- **Connected to recovery:** after a PARTIAL_NO_MATCH, memory_aware_session_restore first performs local capability-aware discovery. If no verified local identity is found and repository access is configured, it then searches the remote catalog. Remote matches/candidates are returned as evidence only; approved semantic memory status is not changed and no relocation/promotion occurs.
- **Tests:** remote exact match, alternate branch/path, text-only false positive, access denial, branch movement, invalid input, and restore integration without promotion are covered.
- **Code CI checkpoint:** PR #37 adapter/integration code checkpoint 0ada1a3db718ad09a050206cd1767681507bc1fe has a workflow run in progress at the time this note was drafted; fetch live exact-head CI before claiming final success. Prior standalone adapter checkpoint 9d2275ccf6e78b65742fd84f8aa7e12f972a57d5 passed run 39018402645 (435 Python tests, 1 skipped; write audit 143/0).
- **Still missing:** remote catalog does not enumerate all branches or search arbitrary paths/history; external archive/connector/device adapters are absent; ChatGPT does not automatically invoke the local CLI; local host writeback bridge is not connected; positive applicability remains fail-closed without external trusted-keyring configuration.
- **Branch safety:** PR #37 Draft/open/unmerged, stacked on #36 → #35 → #34 → #27. main unchanged. Archive transfer and browser-extension work remain deferred.


## Post-PR #37 source-routing hardening — 2026-10-17

- **Finding:** the first remote fallback implementation flattened every catalogued path into one candidate_paths list for a semantic-memory lookup. That meant a protocol/bootstrap file could be searched as if it were an alternative semantic-memory source, and source-specific expected_blob_sha metadata was not passed by this caller.
- **Correction:** registry/remote_source_catalog.json now classifies each profile with source_type and priority. tools/memory_aware_session_restore.py searches only compatible semantic_memory and event_history profiles for a partial approved-memory miss, in priority order, with each profile's own expected path and aliases. The protocol/bootstrap profile is excluded from that memory search instead of being treated as a generic fallback drawer. Per-source expected SHA/blob SHA fields are forwarded when a profile is selected.
- **Regression coverage:** test_remote_discovery_routes_by_source_type_and_excludes_bootstrap_from_memory_search verifies the memory registry is searched first, project event history second, and the incompatible bootstrap source is not queried. test_expected_blob_sha_verifies_registered_source checks exact Git blob identity for a registered source.
- **Exact-head verification:** commit fe232c4d6ee18308d93bebad801803c364f1e683; GitHub Actions run #39019051330 (https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/39019051330) completed SUCCESS. The run executed 438 Python tests with 1 skipped; strict write-contract audit reported 143 mutation sites and 0 unclassified.
- **Current status:** source-specific remote routing is implemented and narrowly tested. The bootstrap contract can be selected explicitly by source ID through the remote discovery CLI, but it is not part of approved-memory fallback. This is intentional capability filtering, not a claim that every source type is automatically queried.
- **Next step:** verify catalog branch-head drift and conflicting versions, then define the host/runtime bridge. The largest remaining system gap is still that this local CLI is not automatically invoked by the live ChatGPT conversation and the turn-writeback adapter has no connected host here.
- **Scope unchanged:** PR #37 remains Draft/open/unmerged, stacked on #36 → #35 → #34 → #27. main unchanged. Browser-extension integration and large archive transfer remain deferred.



 
## Full PR inventory and cross-branch reconciliation — live snapshot 2026-10-17

This section supersedes older PR-state snapshots above where they disagree. Metadata was fetched again for PR #1–#38, changed paths were enumerated, and workflow runs were queried by each current head SHA. No PR was merged, closed, deleted, or rebased during this audit.

| PR | Scope / role | Base ref @ base SHA | Current HEAD SHA | State / head-associated CI |
|---|---|---|---|---|
| #1 | Initial knowledge-base structure and stack validators | main @ 952c079ad1a753e67db01ddec362bdebe4fd9e7d | a5a8e72c1c238ccce71ca9d1cd9383237386e2d5 | MERGED |
| #2 | Continuity and memory protocol foundation | main @ bbab1df5957c001a9f307418caada4fe0a9ea9e8 | f3d78033e4819c922169c5ea1cb42367ce2317be | MERGED |
| #3 | RECIPE_MANAGER initial memory transfer | main @ a0c12ba849a3416f50e1289d8f0dd20844e1e51f | fa07c811aaadeb6ba02553eee870815245c77e2e | OPEN/DRAFT; CI 38231989159 SUCCESS |
| #4 | Chronology reconstruction and repository scope | main @ a0c12ba849a3416f50e1289d8f0dd20844e1e51f | 72b90219ca44e765af0775d3d1260a14fdbf4a47 | OPEN/DRAFT; CI 38223127349 SUCCESS |
| #5 | B77 HTML/PWA memory transfer | main @ a0c12ba849a3416f50e1289d8f0dd20844e1e51f | e0fe2027daf57798ae47f25297d1667ff9d6475c | OPEN/DRAFT; CI 38230197018 SUCCESS |
| #6 | RECIPE_MANAGER history continuation | main @ a0c12ba849a3416f50e1289d8f0dd20844e1e51f | 8abf56a281fd55d94adf6444e65b58fefb500b01 | OPEN/DRAFT; CI 38237522214 SUCCESS |
| #7 | RECIPE_MANAGER category regression continuation | handoff/recipe-manager-chat-continuation-20261012 @ 8abf56a281fd55d94adf6444e65b58fefb500b01 | 19f1d9e6372cdd048864282bd239c837818103f4 | OPEN/DRAFT; CI 38240392254 SUCCESS |
| #8 | RECIPE_MANAGER UI/platform memory | main @ a0c12ba849a3416f50e1289d8f0dd20844e1e51f | 12059aab57ba1ceacc60b445c0a207553fe6ed28 | OPEN/DRAFT; CI 38243062861 SUCCESS |
| #9 | RECIPE_MANAGER HTML/SQLite UX and confidence lessons | handoff/recipe-manager-chat-continuation-20261012 @ 8abf56a281fd55d94adf6444e65b58fefb500b01 | 04f103f6599b15a77a4d5e1f0d8a2008d110b679 | OPEN/DRAFT; CI 38244650757 SUCCESS |
| #10 | RECIPE_MANAGER chat reconciliation note | main @ a0c12ba849a3416f50e1289d8f0dd20844e1e51f | 488087894ef7f6110f9734d0fd30e90318e546f7 | OPEN/DRAFT; CI 38253141990 SUCCESS |
| #11 | RECIPE_MANAGER unresolved packaging attempt | memory/recipe-manager-chat-scope-20261012 @ 468495782a5b0e1ba33a0caf493d3fd5fff77636 | ff54a3e6f2d361066841ffec262dee7710b5bf9d | OPEN/DRAFT; CI 38261292677 SUCCESS |
| #12 | RECIPE_MANAGER continuation transfer | main @ a0c12ba849a3416f50e1289d8f0dd20844e1e51f | ff54a3e6f2d361066841ffec262dee7710b5bf9d | OPEN/DRAFT; same HEAD and CI as #11 |
| #13 | Initial RECIPE_MANAGER memory package, alternate schema | main @ a0c12ba849a3416f50e1289d8f0dd20844e1e51f | fac7e8a9dfed8e158b923a43e79d4ddc886b31dc | OPEN, not draft; CI 38256471543 SUCCESS |
| #14 | RECIPE_MANAGER artifact-verification canon | main @ a0c12ba849a3416f50e1289d8f0dd20844e1e51f | 2f056046946bf1e5a16f54e858f71e7ee8ebd49a | OPEN/DRAFT; CI 38270958513 SUCCESS |
| #15 | RECIPE_MANAGER cross-cutting regressions | memory/recipe-manager-archive-verification-canon-20261012 @ 2f056046946bf1e5a16f54e858f71e7ee8ebd49a | 507a8aaeb84f740b1237a32be926293acdce2015 | OPEN/DRAFT; CI 38275805726 SUCCESS |
| #16 | RECIPE_MANAGER HTML/SQLite and ingredient rules | memory/recipe-manager-crosscutting-regressions-20261012 @ 507a8aaeb84f740b1237a32be926293acdce2015 | 800cd28dfa10601c8d06a2c2bfa9b0c295c2d6da | OPEN/DRAFT; CI 38282766101 SUCCESS |
| #17 | Initial RECIPE_MANAGER experience package, alternate schema | main @ a0c12ba849a3416f50e1289d8f0dd20844e1e51f | 32d80b8bcd99ebb59e17307c48f3337e0c7a4645 | OPEN, not draft; CI 38285618465 SUCCESS |
| #18 | RECIPE_MANAGER PWA products/shopping regressions | memory/recipe-manager-crosschat-html-db-kbju-20261012 @ 800cd28dfa10601c8d06a2c2bfa9b0c295c2d6da | b4fbbe90c5fa22368f54ea8e68a9929f0164635d | OPEN/DRAFT; CI 38288805527 SUCCESS |
| #19 | RECIPE_MANAGER HTTPS/PWA camera regression | memory/recipe-manager-pwa-shopping-products-regressions-20261012 @ b4fbbe90c5fa22368f54ea8e68a9929f0164635d | 3c0e3a5860f87126a6f85ca3d08ec57db38c34f5 | OPEN/DRAFT; CI 38292601680 SUCCESS |
| #20 | RECIPE_MANAGER task-boundary reconciliation | memory/recipe-manager-pwa-shopping-products-regressions-20261012 @ b4fbbe90c5fa22368f54ea8e68a9929f0164635d | 346ee9f4466e44b88bd3fc1ca5f1af2e2a548a31 | OPEN/DRAFT; CI 38297134150 SUCCESS |
| #21 | RECIPE_MANAGER web experience and ingredient rules | main @ a0c12ba849a3416f50e1289d8f0dd20844e1e51f | f847c282e01e1103e456752cfcf604fabe656027 | OPEN/DRAFT; CI 38300459937 SUCCESS |
| #22 | Broad cross-chat/project experience export | main @ a0c12ba849a3416f50e1289d8f0dd20844e1e51f | 52ff4df1c13f65bb33e5ec2a122b387071e973ce | OPEN/DRAFT; CI 38563107303 SUCCESS |
| #23 | ORGANISM OAuth return diagnostics | main @ a0c12ba849a3416f50e1289d8f0dd20844e1e51f | adbd68938539ff59bf67a0b451207d22d6b896de | OPEN/DRAFT; CI 38453917690 SUCCESS |
| #24 | ORGANISM architecture-chat transfer | memory/organism-current-chat-20261013 @ adbd68938539ff59bf67a0b451207d22d6b896de | 3250365cc7ca1ecb1838490c83e06f1122185fbb | OPEN/DRAFT; CI 38457796818 SUCCESS |
| #25 | Durable-write and real-API integration tests | archive-reconciliation/deferred-20261014 @ 5c7018d51e543394b3662af6576b00c4258f0ca3 | efd5de131be5c037373c8a61a6a5dbc02d2d8c1c | OPEN/DRAFT; CI 38710552384 SUCCESS |
| #26 | Bounded restore and experience-candidate loop | test/real-api-integration-20261014 @ efd5de131be5c037373c8a61a6a5dbc02d2d8c1c | 4830123fabc7d0a2835151eeba2ef6ceb06bb5ea | OPEN/DRAFT; CI 38739494738 SUCCESS |
| #27 | Memory-core integration line | main @ a0c12ba849a3416f50e1289d8f0dd20844e1e51f | 9eb2ab86fb3cc99791c8803b5ac3564ce9b63b19 | OPEN/DRAFT; CI 38999759832 SUCCESS |
| #28 | Applicability evaluator and decision frontier | integration/memory-core-clean-20261015 @ d3f9c610b7865793960dc652c2ccccc88afef732 | b6d32a3c36aa5df8079f63aad20fd41a8f56c512 | OPEN/DRAFT; CI 38897881585 SUCCESS |
| #29 | End-to-end implementation audit | integration/memory-core-clean-20261015 @ d3f9c610b7865793960dc652c2ccccc88afef732 | 57aa847f0f0104625d6cb6104111c4ee66a9b0cd | OPEN/DRAFT; CI 38899172605 SUCCESS |
| #30 | Attention, check reuse and branch-return controller | audit/agent-memory-e2e-20261016 @ 57aa847f0f0104625d6cb6104111c4ee66a9b0cd | 85137d13c40777ef9f48cf305a0811c1e26cb3f1 | OPEN/DRAFT; CI 38999888341 SUCCESS |
| #31 | Dialogue window, archive/attachment adapters and extension work | integration/memory-core-clean-20261015 @ 9eb2ab86fb3cc99791c8803b5ac3564ce9b63b19 | 4b05e0bb3b69d32235c08497cd9a08282e0aa938 | OPEN/DRAFT; CI 39010720187 SUCCESS |
| #32 | In-chat pre/post-action writeback protocol | integration/memory-core-clean-20261015 @ 9eb2ab86fb3cc99791c8803b5ac3564ce9b63b19 | e5016171ea25a129a45d243441635ebb1353f858 | OPEN/DRAFT; CI 39005787842 SUCCESS |
| #33 | Global/project instructions, identity contract and bootstrap | main @ a0c12ba849a3416f50e1289d8f0dd20844e1e51f | 82ce508c6b77f6060e4674ecfe24830b61eb27c6 | OPEN/DRAFT; CI 39012907765 SUCCESS |
| #34 | Local relocation-aware source discovery | integration/memory-core-clean-20261015 @ 9eb2ab86fb3cc99791c8803b5ac3564ce9b63b19 | 2d661ee60da6981ad3d8ad150b7f86f0a5ae0cb7 | OPEN/DRAFT; CI 39014044383 SUCCESS |
| #35 | Capability-aware adaptive local search and audit | feature/relocation-aware-memory-discovery-20261017 @ 2d661ee60da6981ad3d8ad150b7f86f0a5ae0cb7 | 5ee3816d3d780cccd6124df85de733e9485fb273 | OPEN/DRAFT; CI 39017002643 SUCCESS |
| #36 | Unified local task-start composition | feature/capability-aware-retrieval-planner-20261017 @ 5ee3816d3d780cccd6124df85de733e9485fb273 | 5ef5af23ca0f0f8f12f8ad31763f1980800b3529 | OPEN/DRAFT; CI 39018196597 SUCCESS |
| #37 | Bounded remote GitHub source discovery | feature/unified-task-start-cluster-20261017 @ 5ef5af23ca0f0f8f12f8ad31763f1980800b3529 | d1e36e70d07c2ebf0a2d1342377d64445e7f0fb8 | OPEN/DRAFT; CI 39019200129 SUCCESS |
| #38 | Pre-write temporal-relation validator | feature/remote-github-source-discovery-20261017 @ b52b5cf850ac03fc34c88f24cb5b3f2d0f8eeed0 | 9c52cefed05f3cabac6df04ae927d8a3a5a87027 | OPEN/DRAFT; CI 39019098457 FAILURE (446 tests, 21 errors, 1 skipped) |

### Findings confirmed by file-level comparison

1. **PR #11 and #12 are duplicate submissions of the same branch tip.** Both point to HEAD ff54a3e6f2d361066841ffec262dee7710b5bf9d and the same CI run, but use different bases. Their diff ranges differ; do not merge both as if they were independent updates.
2. **RECIPE_MANAGER transfer branches contain real record conflicts.** PRs #3, #6, #8 and #21 independently modify the same event/lesson files from main. EVT-20261012-005 and EVT-20261012-006 have different meanings in #21 versus #6/#8. LESSON-RM-008 and LESSON-RM-009 also have different meanings in #21 versus #6/#8. The shared earlier event/lesson IDs were byte-identical in the inspected files. PRs #13 and #17 are further parallel initial packages with overlapping project-state files but different event-ID formats (EVT-RM-20260922-01 versus EVT-RM-20260922-001; the #3/#6/#8/#21 lineage uses EVT-20260922-001). Treat this as record reconciliation work, not a bulk merge.
3. **PR #4 is partly superseded by the current integration lineage.** core/chronology_reconstruction.md has the exact same blob SHA in #4, #22 and #27. In contrast, core/memory_model.md and core/universal_instructions.md differ between #4 and the later #22/#27 version. Preserve the useful newer versions rather than merging older file variants independently.
4. **PR #25/#26 are code-source branches for PR #27, not separate runtime clusters.** All 23 changed paths from #25 and all 26 changed paths from #26 are present among #27's changed paths. Blob checks confirmed exact reuse of several important implementations, including minimal_agent_loop.py, context_extractor.py, context_trust_gate.py, archive_registry_staging.py and resumable_chat_import.py; other files were further changed in #27. Compare unique behavior before any closure, but do not merge these PRs separately into the integration line.
5. **PR #28/#30/#36 share implementations rather than three independent applicability systems.** applicability_evaluator.py and its main test file have the same blob SHA across all three branches. decision_frontier.py in #30 and #36 has the same newer blob, while #28 has an older version. minimal_agent_loop.py evolved across the branches. #36 is the current composition candidate; #28/#30 are source branches whose unique behavior must be checked against #36, not bulk-merged.
6. **PR #22 is not part of the runtime cluster.** It has 134 changed paths and includes raw conversation history and project-specific memory payloads; its current head is 542 commits ahead of main. PR #27 and #22 diverge in history and share 75 changed path names, but #27 does not include the raw conversation paths or project-specific CARD111/ORGANISM/RECIPE_MANAGER/B77 history directories. Keep #22 separate and unmerged because archive transfer remains deferred.
7. **PR #27 has a scope mismatch that must be handled deliberately.** Its 161 changed paths include clients/chatgpt-web-extension files, extension contract tests and turn-lifecycle adapters even though browser-extension implementation/integration is explicitly deferred. These files are not evidence of a live host connection and must not be activated as a prerequisite for the current cluster.
8. **PR #31/#32/#27 have overlapping but non-identical turn stores.** The project events.jsonl, the local turn_lifecycle_ledger and PR #32's TURN_JOURNAL.jsonl serve related but different roles. The current integration must not append the same authoritative lifecycle event independently to three journals. Keep the project event history canonical; specify whether the other stores are private lifecycle ledgers or derived/reference views before integration.
9. **PR #33 bootstrap is a branch-location discrepancy, not global absence.** core/agent_bootstrap.md is absent from main and the #27/#37 integration line but present in #33 at blob 170972deabf4ccbd072a38c1400eac490c4da348, matching the exact hash in registry/remote_source_catalog.json. Its instructions point to a feature-branch URL; replace that only when the bootstrap is deliberately integrated at a stable canonical location.
10. **PR #34/#35/#37 search layers are complementary.** #34 performs bounded local relocation discovery; #35 orders local sources by capability/format/scope; #37 searches an explicit allowlist of GitHub refs and preserves branch HEAD and file blob identity. Do not collapse them into one untyped candidate list. The local and remote catalog files have distinct scopes and schemas; align shared source-profile semantics without pretending either catalog is exhaustive.
11. **PR #36 is the strongest current task-start composition candidate.** Its actual call graph invokes memory_aware_session_restore once when repository access is configured, passes that packet into task_start_experience_map/minimal_agent_loop, and reaches applicability_evaluator and decision_frontier. The same packet is reused, avoiding a second restore. Exact-head CI #39018196597 passed. The path remains an explicit CLI, not automatic ChatGPT startup.
12. **The live restore checkpoint is stale.** CONTINUITY_CHECKPOINT.json on #37 still records code HEAD 1fd9c91ae8bb8662a3cb1a1cea3d63452064fc40 and CI run 38852493391. Comparing that SHA with #37 HEAD d1e36e70d07c2ebf0a2d1342377d64445e7f0fb8 shows 169 commits and 56 changed paths, including source code. Since verified_session_restore.py fails closed on non-allowlisted changes after the recorded SHA, the configured live restore is expected to return CODE_REVISION_DRIFT until the checkpoint is refreshed. This is a code-path inference from the current implementation and GitHub metadata, not a live execution result.
13. **PR #38 is not integration-ready.** dialogue_attention_controller.py calls validate_event_append but does not import it; branch_result_registry.py already imports it. The exact-head CI fails with NameError and 21 test errors. The branch's events.jsonl also reuses EVT-AGMS-20261017-006 for a different event than #37. PR #38 reports mergeable=false and its base SHA b52b5cf850ac03fc34c88f24cb5b3f2d0f8eeed0 is 10 commits behind #37 HEAD d1e36e70d07c2ebf0a2d1342377d64445e7f0fb8. Do not merely add the import: reconcile the base and event ID first. The validator currently gates two writers, not every event-log writer, and the whole-log audit is not a dedicated workflow step.
14. **Passing individual CI runs does not establish a unified runtime.** PRs #3–#37 have successful workflow runs associated with their current heads, but many are memory-only drafts or isolated component tests. The actual ChatGPT host does not automatically invoke these Python tools, and the current stale checkpoint blocks the configured verified restore path. PR #38 is the only current-head failure in this inventory.

### Minimal integration disposition

- Preserve main and all PRs unchanged until the branch-level record conflicts and scope are reconciled.
- Use #27 → #34 → #35 → #36 → #37 as the current code integration lineage; refresh the audit/checkpoint against the live #37 code and CI.
- Reuse the already-present #25/#26 and #28/#30 mechanisms through the current lineage; do not merge those source PRs separately.
- Reconcile #3/#6/#8/#21 and #13/#17 at record level before any project-memory consolidation. Keep #22 and #31's deferred archive/extension work out of the current runtime integration.
- Integrate #32/#33 selectively only after deciding journal ownership and aligning global/project instructions and bootstrap location.
- Repair #38 only after its base is synchronized and its event ID is unique; then wire the temporal validator into the intended writer and repository-validation paths and rerun exact-head CI.
- The next proof is a real invocation of the #37 configured restore path after the checkpoint is refreshed, followed by the #36 task-start path using that same packet. Do not call this a live ChatGPT end-to-end test until an actual host invokes it.


## Correction after PR #38 branch reconciliation — 2026-10-17

The previous inventory records PR #38 as failing and based on a stale revision; that was the verified state before the following repair. The existing PR branch was updated without force-pushing or creating a new PR.

- Merge commit: 258b11610bd57d8c4b1ff051a36b74dd75c741b6. Parents: previous PR #38 HEAD 9c52cefed05f3cabac6df04ae927d8a3a5a87027 and the then-current PR #37 HEAD 429d939ee0d2225d673dea709b12fd25f8fc9c8e.
- At merge commit 258b11610bd57d8c4b1ff051a36b74dd75c741b6, PR #38 compared against base HEAD 429d939ee0d2225d673dea709b12fd25f8fc9c8e with 7 commits ahead, 0 behind and five code/event paths. Subsequent audit/state updates on the same branch expanded the current PR diff to nine paths: those five code/event paths plus CLUSTER_INTEGRATION_AUDIT, TASK_STATE, HANDOFF and PROJECT_STATE. A refreshed PR metadata response reports mergeable=true.
- The #37 event EVT-AGMS-20261017-006 was preserved. The validator correction was appended as EVT-AGMS-20261017-007; the resulting events.jsonl has 32 records and 32 unique event IDs.
- tools/dialogue_attention_controller.py now imports validate_event_append. The existing branch_result_registry integration and the new validator/test files are preserved.
- **Verification at the time of the first branch reconciliation was PENDING.** No workflow run/check-run was associated with merge HEAD 258b11610bd57d8c4b1ff051a36b74dd75c741b6. After the PR metadata update, exact-head CI run 39022785538 passed for HEAD 566e90f746f702c0a5ca5abd1cd7f6e163f765df: 446 Python tests (1 skipped), 4 Node tests, strict write audit 143 mutation sites / 0 unclassified, memory validation PASS and project/stack validation PASS. The audit-document correction in this commit changes the HEAD again, so run 39022785538 must not be attributed to the new SHA; obtain exact-head CI before refreshing the checkpoint. A local clone attempt failed because the execution environment could not resolve github.com; no local test run is claimed.
- Do not merge PR #38. After an exact-head CI result is available, update the continuity checkpoint only with the SHA/run pair that actually passed. The validator is still wired to two writer paths; broad writer coverage and a dedicated whole-log workflow audit remain open.


## Writer inventory and verified smoke update — 2026-10-17

Scope is the canonical project journal `projects/AGENT_MEMORY_SYSTEM/events.jsonl`, not every file with an `events.jsonl` name.

| Writer / mechanism | Target | Temporal validator | Lock contract | Assessment |
|---|---|---|---|---|
| `branch_result_registry.py` (result + acknowledgement) | Canonical project `events.jsonl` | Yes, before append | Exclusive `events.jsonl.lock` | Gated |
| `check_reuse_policy.py` | Canonical project `events.jsonl` | Yes, before append | Exclusive `events.jsonl.lock` | Gated |
| `dialogue_attention_controller.py` | Canonical project `events.jsonl` | Yes, before append | Exclusive `events.jsonl.lock` | Gated |
| `experience_outcome_capture.py` (verified candidate + observed failure; PR #39 sibling) | Project `events.jsonl` | Yes, before append | Advisory lock on `.capture.lock` | **Not concurrency-safe with the other writers; fix before integration** |
| `guarded_task_state_update.py` | `TASK_STATE.md` plus paired checkpoint metadata | No event append; validates supporting event evidence | Journal lock + task-state lock | Not a journal writer |
| `turn_lifecycle_ledger.py` | User-local turn lifecycle ledger | Separate event schema | Advisory lock | Separate authority; cross-reference only |
| `source_ingestion_runner.py` | Per-run `run_events.jsonl` | Separate ingestion ledger contract | Run lock + atomic projection | Separate authority |
| `memory_pipeline_coordinator.py` | Per-run `pipeline_events.jsonl` | Hash-chained pipeline ledger | Run lock + append/fsync | Separate authority |
| `edge_correction_registry.py`, `semantic_memory_registry.py`, `source_evidence_registry.py` | Dedicated registries | Registry-specific validation | Registry-specific locks | Not canonical project-event appenders |

### Exact-head evidence

- Code HEAD `4a2ee4499e11b8ff8fb02292d1320ad8b20e2160`: CI run `39068720335` PASS — 448 Python tests (1 skipped), 4 Node tests, strict write audit 143 mutation sites / 0 unclassified, memory validation and project/stack validation PASS.
- Metadata-only branch tip `460ba6ab859d1aae906e716b8173c618486edafe`: run `39068855181` PASS — verified restore and task-start smoke both pass; `READY_FOR_REVIEW`, `RESTORED_PACKET`, readiness `PARTIAL` because approved semantic memory is unavailable.
- This proves the repository CLI path under GitHub Actions only. Automatic ChatGPT-host invocation/writeback remains unverified. Do not merge either PR or modify `main`.
