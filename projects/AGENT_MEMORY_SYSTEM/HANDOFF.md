# HANDOFF — AGENT_MEMORY_SYSTEM

- **Repository/project:** `alexbotleh-oss/agent-knowledge-base` / AGENT_MEMORY_SYSTEM.
- **Current task:** transfer verified experience about the memory system itself from available «Настройка Агента» materials; reconcile it with existing canonical memory without importing full histories of other projects.
- **Working PR branch:** `export/cross-project-experience-rollup-20261012`; PR [#22](https://github.com/alexbotleh-oss/agent-knowledge-base/pull/22), base `main`.
- **Last verified checkpoint before this handoff update:** HEAD `2b029b3886571c3d989c9274bf9efc852974d5aa`; 336 commits ahead, 0 behind, 81 changed paths; exact-head CI PASS run [#38387381733](https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/38387381733). After this commit, re-fetch PR metadata and CI for the new exact HEAD.
- **PR state:** open, Draft, unmerged; no review submissions or review threads returned. Do not merge without explicit permission.
- **Core protocols reviewed:** repository scope, universal instructions, runtime protocol, memory model, source ingestion, chronology reconstruction, session handoff, chat collection task, multidimensional registry, continuous-agent architecture.
- **Direct source results:** materialized and parsed `conversations.zip` (one member: `conversations.json`), separate manifest, asset-name index, report bundle and previous-session note. Archive: 37 conversations, 10,034 distinct message IDs, 7,446 assistant / 2,588 user, timestamps 2026-09-21—2026-10-07 UTC. Manifest: 1,374 entries; asset-name map: 876 mappings. Full payload reconciliation remains open.
- **Report duplicates:** near-identical large blocks at lines 206–503 and 765–1063; 94 long paragraphs repeat under whitespace normalization. Treat these as copied-report candidates, not incident counts.
- **History coverage:** no exact «Настройка Агента» conversation title appears in the inspected ZIP. The separate “Последние дествия в предидущем чате.txt” is a secondary summary. Source coverage is PARTIAL.
- **Scope finding:** 37 paths under B77_HTML_PWA/CARD111/ORGANISM/RECIPE_MANAGER plus two app-specific reconciliation reports are outside direct scope. `SOURCE_REPORTS_AUDIT_2026-10-13.md` mixes relevant methodology with app-history detail. No files were removed because a safe preservation destination has not been confirmed. The PR is not scope-clean.
- **Local validation:** not run locally; prior clone attempt was blocked by DNS. Use exact-head GitHub Actions as current automated evidence, then run local commands if a working clone becomes available.
- **Canonical memory:** `projects/AGENT_MEMORY_SYSTEM/EVENT_LOG.md`, `events.jsonl`, `PROJECT_STATE.md`, `TASK_STATE.md`, `DECISIONS.md`, `LESSONS.md`; latest recorded event EVT-AGMS-20261013-006. EVT-AGMS-005 documents reversed temporal edges in EVT-AGMS-002/003/004; EVT-AGMS-006 adds machine-readable `edge_corrections`. L-AGMS-20261013-002 captures the prevention rule. Keep event logs append-only.
- **Integrity note:** append-only event records 001–004 were not rewritten; EVT-AGMS-005 describes the relation-direction correction and EVT-AGMS-006 provides a machine-readable overlay. Consumers must apply `edge_corrections`; an automatic validator is not implemented yet. Before adding temporal edges, check whether the referenced event is earlier or later.
- **Next action:** preserve and safely separate the 39 out-of-scope paths; narrow the mixed source-report audit; semantically reconcile only memory-system claims; update PR description and confirm CI for the final exact HEAD. Do not change `main`, merge PR #22, or edit application code.

## Continuity checkpoint — 2026-10-13

- **User's operating expectation:** on “continue”, recover the chain rather than starting over: read prior task/context, consult project memory and primary sources, compare previous conclusions with live repository state, record a checkpoint, keep a progress plan, verify each material step, update state/handoff before interruption, and report evidence plus next action. Treat this as a protocol requirement, not a claim that ChatGPT/library/GitHub automatically synchronize themselves.
- **Current branch before this checkpoint:** `export/cross-project-experience-rollup-20261012`; PR #22 open, Draft, unmerged. Live PR metadata before this checkpoint: HEAD `1afae2fe74f8919da13cf25d33de2a732ae5418c`, 369 commits ahead, 101 changed files. The PR body is stale (it reports HEAD `a20279ef09609f437463d15b5b63ef4a74bf84c9`, 344 commits and 81 paths). Refresh after scope decisions and final verified changes.
- **Important scope conflict:** current PR instructions say full histories of CARD111/ORGANISM/RECIPE_MANAGER/B77_HTML_PWA are outside direct scope, but the branch contains CARD111 source-history files. Preserve them while deciding whether to separate into a project-specific PR/branch or explicitly revise scope. Do not silently delete, merge, or claim approval.
- **Attachment index evidence:** `attachment_index.jsonl` has 152 rows, 150 unique IDs and one duplicated `attachment_id + message_id` pair with differing `export_name`; 106 rows lack `library_file_id`. `attachment_availability.json` reports exact-ID matches for 150 unique IDs, and direct comparison shows 106 missing-field mismatches. This supports a targeted consistency repair, not a full-library rematch.
- **Next safe sequence:** resolve scope/preservation; repair only unambiguous missing `library_file_id` values using the exact-ID availability record; investigate the duplicated pair without deleting provenance; run targeted structural checks and exact-HEAD CI; refresh PR body/state; update this handoff again.
- **Completeness:** PARTIAL. The current checkpoint is recorded in TASK_STATE and HANDOFF; no claim is made that full conversation coverage, all attachment payloads, or an automatic interruption/resume mechanism is complete.


## Checkpoint 2026-10-13 — PRE-REPOSITORY GATE

- **User requirement:** before consulting the repository, the agent must already recover the task intent and constraints, establish the action order and verification criteria, and avoid returning to a disproven conclusion without new evidence or a documented reason.
- **Implemented on this branch:** added a mandatory `PRE-REPOSITORY GATE` to `core/universal_instructions.md` and a mandatory reference to it in `core/agent_runtime_protocol.md`. The gate requires goal/scope/permission recovery before repository calls; an explicit verification sequence; source-vs-hypothesis separation; a checkpoint before material edits; evidence-based revision of conclusions; read-back and status recording after each material step; and resumption from the last checkpoint after interruption.
- **Read-back:** both modified files were fetched again from the branch and the gate presence confirmed. Latest write commits: universal instructions `dfaba89607d120d4c9d1366b6e806392b859e402`; runtime protocol `3dc92fc62e6c392f49c228887b477467441fd8ed`. Subsequent read-back showed updated blob SHAs for both files.
- **Validation status:** exact-HEAD workflow lookup for `3dc92fc62e6c392f49c228887b477467441fd8ed` returned no associated PR workflow run at the time of lookup. Do not report CI PASS for this new head until a run is observed and its conclusion is successful.
- **Scope discipline:** only universal protocol files were changed in this step. No application code, project-specific source history, PR merge, or main-branch changes were made.
- **Next step:** re-fetch live PR/branch HEAD and check whether CI has started for the current head; then continue the existing scope-resolution work only after confirming live state. PR #22 remains intended to stay Draft/open/unmerged.


## Continuity checkpoint — 2026-10-13: resumable low-overhead chat import

- **Current task:** develop a safe, lightweight chat-history import mechanism that can resume after unstable network/long context interruption, while preserving chronology, source identity and causal evidence. The point is to stop repeating work after chat transitions and avoid losing errors/decisions.
- **Accepted finding — do not redo:** the user already provided reports from agents in other chats; reports and chat/archive information were compared, confirming that similar data/errors had been merged and distinct dialogue/incident provenance was obscured. Treat this as accepted for the current task unless new contradictory evidence appears.
- **Design direction:** first preserve raw source and exact ordering in bounded, resumable batches; later run a separate analysis pass for events, decisions, causal relations, semantic grouping and indexes. Do not perform semantic merging during initial import.
- **Change recorded:** extended `core/source_ingestion_protocol.md` with states (`REGISTERED`, `SNAPSHOTTED`, `INVENTORIED`, `STAGING`, `PAUSED`, `RAW_COMPLETE`, `PARTIAL`, `FAILED`), stable source-key/cursor rules, idempotent replay, lost-ack recovery, checkpoints, append-only import events, gap tracking and required tests.
- **Evidence:** commit `8c3490627f87fa85c4f1ecfa78d8ebd00ec843af`; read-back from the branch confirmed the new section and required clauses. This verifies that the protocol text was saved, not that a runtime implementation exists.
- **Current verification status:** protocol persistence/read-back PASS; executable import, network-interruption recovery, replay idempotency, local durable storage and performance target SKIP/not implemented. Exact-head CI not yet checked after the protocol commit.
- **Boundaries:** keep PR #22 open/Draft and unmerged; do not re-run accepted report reconciliation; do not claim the current ChatGPT interface itself can guarantee background/local persistence.
- **Next single action:** fetch the live PR/branch state and CI for the new exact head, then inventory existing parser/schema/tooling before selecting the smallest implementation path.


## Design correction — minimal continuity memory (2026-10-13)

- The user clarified that the goal is a practical memory workflow using only current chat (temporary), Project Library (archives/reports) and repository (persistent memory). Do not over-engineer or require a server/local agent/database for the first usable iteration.
- We need not copy every chat. Preserve only enough source-grounded material to recover significant event chronology, decisions and their rationale, failed attempts, lessons, current task state and next step. Keep source IDs/locators, event time and confidence/status.
- Keep event/incident, decision, task-state and source records linked. Generalize lessons only as an overlay linked to all distinct episodes; do not collapse separate incidents or lose provenance.
- First archive pass should be lightweight: inventory source, select/preserve relevant fragments and metadata, checkpoint progress. No full semantic analysis or indexing during import. Reconstruct chronology/causality and build search indexes in a later pass.
- During live work, record significant confirmed changes when they happen, and update/read back the checkpoint before likely limits/interruption and at stage completion. The current chat alone is not durable storage.
- Instruction changes were appended to `core/universal_instructions.md` and `core/agent_runtime_protocol.md`. Write commits returned successfully; read-back and exact-head CI still need checking.
- Accepted report finding remains accepted: supplied agent reports were reviewed and confirmed that similar information/errors had been merged, obscuring distinct source dialogue/episode provenance. Do not redo that reconciliation without new contradictory evidence.
- **Next action:** read back the instruction changes, check current PR/CI status, then test the smallest practical continuity path using existing repository structures before designing any additional machinery.


## Handoff update — 2026-10-13: instruction verification

- Re-read `core/universal_instructions.md` and `core/agent_runtime_protocol.md` on the active PR branch; the accepted minimal-continuity instructions are present.
- Live PR #22 head: `8112a41eea8cb7b03b403748567fb5faa60d8d3c`; exact-head CI run 38416426765 completed successfully. This is a CI PASS only, not proof of complete memory transfer or tested runtime recovery.
- PR #22 remains Draft/open/unmerged and is explicitly not scope-clean; preserve that boundary.
- ChatGPT Project instructions do not need editing for this correction: they already require context restoration and checkpoints. Keep the repository protocol as the detailed source, and read it at the start of relevant work rather than assuming it loads automatically.
- **Next single action:** inspect existing event/source/decision/task-state schemas and use the smallest existing format for a real continuity record; add a template only if none is suitable, then perform a new-context recovery test.


## Handoff — 2026-10-13: causal attention and return stack

- **Active goal:** develop persistent, evidence-backed continuity in `agent-knowledge-base`, not implement a separate application.
- **Accepted change:** return stack records must preserve the reason/context of the conversational detour, the branch's meaning and findings, its established or unknown relation to the original goal, new constraints, and the condition for return. On return, re-evaluate the goal and next step; do not jump back mechanically.
- **Written artifacts:** `core/continuous_agent_architecture.md` section 10; attention/return requirements in `core/universal_instructions.md`; decision `DEC-AGMS-20261013-003`; corresponding checkpoint appended to `TASK_STATE.md`.
- **Status at handoff creation:** write operations returned commit SHAs. Read-back, final PR head, and exact-head CI still require verification. Runtime mechanism and behavior tests remain NOT IMPLEMENTED / NOT TESTED.
- **Boundaries:** PR #22 remains Draft/open/unmerged and is not scope-clean per its own audit. No merge or main-branch changes. Do not claim this documentation provides automatic cross-chat persistence or background scheduling.
- **Next single action:** read back the changed artifacts and inspect CI for the final exact branch head; then provide the user a concise report and paste-ready ChatGPT Project instruction amendment.


## Resume point — executable temporal memory primitives — 2026-10-13

- Continue from PR #22 at live HEAD after the task-state checkpoint; fetch PR metadata again because each file update creates a new commit.
- Added `tools/temporal_memory_model.py`: snapshot validation, comparability gate using scope/counting/inclusion/exclusion identifiers, as-of assertion view, assertion provenance/time validation, and transitive dependent discovery. Added `tests/test_temporal_memory_model.py` with seven targeted cases.
- Current automated check at the time of writing: workflow run [#38464705063](https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/38464705063) was in progress for commit `484eacb048caa2c7c5a6d28c9c68d8bf2d93d308`. Re-check the run against the newest HEAD after these state updates; never infer PASS from a running job.
- Important limits: primitives are not yet connected to the canonical memory registry or import pipeline; no automatic downstream revalidation/migration is implemented. Local test commands were not run in this environment. Source coverage remains PARTIAL, PR scope remains unsafe to merge, and PR #22 must remain Draft/open/unmerged.
- Immediate next action: re-fetch exact PR HEAD and workflow run, inspect job/test result, repair if needed, then create a versioned fixture/schema and compatibility checks only after test baseline passes. Continue preserving rather than deleting out-of-scope histories until a destination is verified.


## Resume checkpoint — snapshot schema and fixture

- Added versioned snapshot schema `schemas/temporal_memory_snapshot.schema.json`, fixture `tests/fixtures/temporal_snapshots_37_vs_74.json`, and fixture-driven coverage in `tests/test_temporal_memory_model.py`.
- Key safety correction: unknown capture time for the historical “74 conversations” claim remains null; review date must not be substituted as if it were source capture time. The two snapshots are marked non-comparable because their scope and counting unit are not aligned. A numeric delta is not treated as proof of corruption or missing data.
- The temporal model remains an isolated additive module, not yet integrated into import/canonicalization. Schema is not yet wired into CI validation. Local tests not run.
- At the preceding check, CI run #38464883917 was queued for HEAD `88a7b5362d15366483c86c7c3be50c86bb9b1513`. Re-fetch PR #22 and the newest workflow run before claiming test status because subsequent checkpoint commits move HEAD.
- Continue with exact-head CI inspection; if green, wire JSON Schema and tests into CI with backward-compatibility coverage. Do not merge PR #22; the scope/preservation issue remains unresolved and source completeness is PARTIAL.
