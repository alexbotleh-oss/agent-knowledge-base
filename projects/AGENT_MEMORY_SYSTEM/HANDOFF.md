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


## Resume point — chat-history importer implementation — 2026-10-14

- Active task is a real, fast, safe, resumable import of chat history. Do not repeat the accepted investigation of agent reports. Preserve source identity, raw source, chronology and provenance; semantic analysis is a separate later pass.
- `tools/archive_registry_staging.py` was confirmed not resumable: it reads the entire export into memory and rewrites derived output as a whole. A new isolated tool `tools/resumable_chat_import.py` was added instead, with tests in `tests/test_resumable_chat_import.py` and invocation/limitations documented in `core/source_ingestion_protocol.md`.
- Importer capabilities: SHA-256 snapshot copy/verification; incremental top-level JSON-array decode; ZIP support when exactly one `conversations.json` exists; SQLite local staging of full opaque conversation payloads; per-batch transaction that commits payloads, ordinal checkpoint and append-only event together; rerun/resume and unique source locator protection. It does not send private source content to GitHub.
- CI passed on commit `d5bbb7a21e0e280c5fc6aa11ff4cc546bcac9774` (run [#38519218588](https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/38519218588)). A subsequent small payload-order fix and documentation/state updates created newer commits, so re-check exact HEAD CI before calling the current tree green.
- Limitation to carry forward honestly: resume rescans the immutable source from the beginning to the saved ordinal; byte-offset/position index optimization remains future work. Source archive is byte-preserved, staged conversation payloads retain nested messages and parent/child links, but binary attachments are not extracted and no semantic analysis is performed.
- Next action: check exact current HEAD and CI. Then add lost-ack/duplicate-ID recovery tests and optimize seek position only after tests remain green. PR #22 stays open/Draft/unmerged due to unresolved unrelated project-history preservation/scope concerns; never touch main.


## Resume checkpoint — recovery tests added — 2026-10-14

- Added tests for replaying a committed batch after a simulated lost acknowledgement (no duplicate), duplicate conversation IDs (must end FAILED, not silently lose a record), and UTF-8 streaming across tiny chunk boundaries.
- Test commit: `31272906f2b2a904c230225249fd930e8c0c0cf4`; CI run [#38519357924](https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/38519357924) was in progress when this note was created. Verify conclusion before claiming pass.
- Most recent prior exact code/docs commit `466f68801eb7fd8b75bdbc8171f4bae5ce213d32` passed run #38519320849. Later test additions are not covered by that pass.
- Continue from the importer task, not the temporal-model tangent. Main remaining implementation trade-off: resume scans earlier conversation objects to reach the checkpoint ordinal. Improve this with a snapshot-bound position index after green test evidence. Preserve private source content locally; never commit exports.
- PR #22 remains OPEN/DRAFT/UNMERGED; do not merge or touch main because unrelated project histories still require safe preservation and scope resolution.


## Resume checkpoint — offset-based import verified — 2026-10-14

- The resumable importer now saves the next conversation ordinal, byte offset after the last committed JSON object, and last source locator. The offset is scoped to the source snapshot SHA-256 and committed atomically with each batch and append-only event. Resume seeks to the saved offset; legacy zero-offset checkpoints fall back to scanning from the start.
- The first offset patch had a CI-detected bookkeeping error and was corrected. Code + protocol documentation passed CI at SHA b7344e351c260dab55f24a03e1c355f953124988 (run #38519573230). Tests include interruption/resume, seek from saved offset, idempotent repeat, lost-ack batch replay, duplicate source IDs, ZIP source, malformed JSON, and small-chunk UTF-8 decoding.
- Re-fetch live PR metadata and workflow after this checkpoint commit; current commit updates only this handoff/state documentation. Do not say the newest HEAD passed until its own workflow finishes.
- Remaining production hardening: ZIP resume seek behaviour at scale, concurrent invocation lock, injected process crash around transaction boundaries, benchmark on a real large archive, attachment completeness and source-scope reconciliation. Private exports stay local and must not be committed.
- Continue the importer task. PR #22 remains Draft/open/unmerged because the broader PR has unrelated project histories without a verified preservation destination. Do not touch main.


## Handoff checkpoint — ZIP resume test pending — 2026-10-14

- A dedicated test now pauses a ZIP export after a committed batch and resumes from the stored byte offset inside conversations.json. This is specifically to validate ZIP-member seek behavior.
- Test commit f100e40e9d68cbdbf4a9a2099beb2afc7a2c8133; workflow run #38519660453 was in progress at checkpoint. Check its conclusion before claiming this test passed.
- Previous importer + offset implementation passed exact-head CI at b7344e351c260dab55f24a03e1c355f953124988. That result does not cover the later ZIP-specific test.
- Next: inspect run #38519660453 and repair if needed; then decide on a concurrent-import lock and crash-injection test before production claims. Keep PR #22 Draft/open/unmerged; no changes to main.


## Handoff — memory pipeline concept and audit — 2026-10-14

- **Active goal:** apply the user's new concept to AGENT_MEMORY_SYSTEM in stages: a shared, multi-chat memory pipeline where working agents submit structured material and independent infrastructure preserves, routes, links, indexes, and exposes it without requiring the source agent to remain active.
- **Important distinction:** chat/session interruption and GitHub workflow interruption are separate failure modes. GitHub automation cannot recover material that was never successfully exported/uploaded. Checkpoints for the pipeline do not imply ChatGPT auto-save or background synchronization.
- **Audit artifact:** `projects/AGENT_MEMORY_SYSTEM/MEMORY_PIPELINE_GAP_ANALYSIS_2026-10-14.md`, created in commit `70422903e899521ad6eca93d07395098787f7581`. It records existing components, evidence boundaries, gaps, invariants, staged plan, and acceptance criteria.
- **Existing reusable components found:** `core/memory_model.md`; `core/stack_registry.json`; event/lesson templates; `tools/validate_memory.py`; `.github/workflows/validate.yml`; `core/agent_runtime_protocol.md`; `core/session_handoff.md`. The current stack registry is a useful starting point for observed language/tool attributes, not proof of semantic lesson applicability.
- **Runtime boundary:** `tools/resumable_chat_import.py` is only an isolated raw-chat import prototype. It preserves/stages conversation payloads and checkpoint state, but does not perform the full route-to-libraries → update-indexes → publish result addresses workflow. Do not describe it as the complete memory pipeline. Do not delete it automatically; decide after intake contract/schema compatibility review.
- **Current phase:** Stage 1 (inventory/gap map) documented. Still needed: inspect all actual write/index consumers and CI triggers; map each library's canonical format and update path; then define the smallest compatible versioned intake manifest and lifecycle before adding routing code.
- **Next action:** continue the factual inventory of indexing/write paths and workflow permissions/triggers. Do not start a new router before this is complete. Do not touch `main`.
- **CI:** run #38519704988 passed for the preceding HEAD `b43f404034450f718f18e002356cdb926fd702ba`; the new audit/checkpoint commits require a fresh exact-HEAD CI result.
- **PR #22:** keep OPEN/DRAFT/UNMERGED; existing unrelated project histories and preservation/scope issue remain unresolved.


## Handoff — stage 2 intake manifest contract — 2026-10-14

- Additional repository inventory found existing target contract `core/memory_registry_and_multidimensional_index.md`, memory-record example, local source-record staging, read-only temporal query tool and snapshot/assertion primitives. These are not yet wired into one end-to-end ingestion flow.
- Stage 2 adds a versioned intake envelope, not a replacement memory model: `schemas/memory_intake_manifest.schema.json`, `templates/memory_intake_manifest.json.example`, synthetic fixture under `tests/fixtures/memory_intake_batch/`, dependency-free validation in `tools/validate_memory.py`, and tests in `tests/test_memory_intake_contract.py`.
- Routing is by a closed allowlist of artifact kinds; paths are relative to the manifest directory and SHA-256 is checked. No arbitrary target path, executable payload, automatic promotion to accepted memory, or guessed future-project applicability.
- `IMPORT_READY` is a processing signal only, not authorization. A future workflow must have separate trusted trigger/permissions and must not run write-capable processing on untrusted PR input.
- The repository is public; raw private chat exports must not be committed. Use sanitized structured records or private-reference-only metadata.
- **Next action:** verify read-back and exact-head CI for this contract. If green, implement a dry-run route planner that reports intended logical views/updates from the existing registry, without writing canonical memory or rebuilding indexes yet. Keep PR #22 Draft/open/unmerged and do not touch `main`.


## Handoff — dry-run router — 2026-10-14

- Stage 1 inventory/gap map is documented in `projects/AGENT_MEMORY_SYSTEM/MEMORY_PIPELINE_GAP_ANALYSIS_2026-10-14.md`.
- Stage 2 adds `schemas/memory_intake_manifest.schema.json`, an example, synthetic manifest/artifact fixtures, and dependency-free validation for schema version, status, source metadata, path containment and SHA-256. Exact-head CI passed for preceding checkpoint HEAD `258f6895e144b160fb82cd5a6d990fc294506a3d` in run [#38521126820](https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/38521126820).
- Stage 3 adds `tools/plan_memory_intake.py` and `tests/test_memory_intake_planner.py`. The tool validates the batch then emits a read-only JSON route plan. It never writes to canonical memory or indexes; unknown artifact types go to quarantine; task-state and handoff changes are proposal-only.
- **Next:** run exact-head CI for the planner; add relationship-endpoint and schema-version rejection cases. Do not create the writer or trigger workflow until dry-run routing and record-format compatibility are verified.
- PR #22 remains open/Draft/unmerged; no changes to `main`.


## CI checkpoint — dry-run planner — 2026-10-14

- `tools/plan_memory_intake.py` and `tests/test_memory_intake_planner.py` passed workflow run [#38521279153](https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/38521279153) on exact implementation commit `799d438f664e7792af0d402c858a7a0a0d038e55`.
- The workflow validated memory records/protocol and detected stacks. It does not prove production-scale behavior or integration with canonical write/index paths.
- Follow-up checkpoint changes are documentation/state-only; verify live PR head and any associated run before claiming exact-head CI.
- Next architecture gate: inspect the actual on-disk canonical record collections and relation formats before any writer/index updater. Keep the current route planner read-only until that mapping is complete.


## Resume checkpoint — intake compatibility audit — 2026-10-14

- User chose to defer repository visibility changes until the memory mechanism is fully tested. No visibility setting was changed.
- Recovered active goal: finish the staged memory-intake pipeline, not repeat the already accepted report-agent reconciliation. Keep PR #22 OPEN/DRAFT/UNMERGED and do not change main.
- Live inspection: PR #22 was at HEAD `fa382dab2cce0b01caf7fdf292ace80432c649b7`, 116 changed paths; Validate knowledge base was successful for that exact pre-correction HEAD. The PR description still has stale HEAD/path-count metadata and is not ready for merge.
- Important inventory correction written and read back in `projects/AGENT_MEMORY_SYSTEM/MEMORY_PIPELINE_GAP_ANALYSIS_2026-10-14.md` (commit `4113fc2121c85c4d52d7751b97498f5225597463`): `core/memory_registry_and_multidimensional_index.md` and `templates/memory_record.json.example` exist on the PR branch, but not on `main`; they are proposed target-contract files, not deployed canonical storage.
- Reused components: main-branch memory model, stack registry, event/lesson examples, validator and PR/push validation workflow; branch-only local staging, temporal model primitives, versioned intake manifest and read-only planner.
- Remaining compatibility gap: no canonical writer/index updater or intake-triggered workflow; manifest validation does not validate every artifact payload by kind or resolve relation endpoints. Existing event relations are nested and use `event_id`; the proposed registry contract uses typed source/target relations; decisions are Markdown. Do not implement a generic writer until per-kind adapters and endpoint-resolution policy are tested.
- Latest verification after the correction: read-back PASS; PR head moved to `4113fc2121c85c4d52d7751b97498f5225597463`; CI for that exact head was QUEUED at last check, so no current-head PASS claim.
- Next action: define and test a compatibility map for source records, events, lessons, decision proposals, memory candidates and relations; distinguish in-batch IDs, existing IDs and unresolved endpoints. Keep the route planner read-only until that contract passes.

## User-requested self-history round-trip audit — 2026-10-14

- **User requirement:** apply the developing memory mechanism to the agent's own work history; test export and reverse recovery; preserve chronology, decisions and context so omissions can be discovered without user hints. After the mechanism is reliable, return to older chats and export their histories.
- **Truthful current status:** the agent does not automatically persist every live message or tool event between turns. Earlier updates to TASK_STATE/HANDOFF were manual checkpoints, not evidence of continuous capture.
- **Regression test added:** `tests/test_current_session_roundtrip.py`, commit `b7fbafe6757182300e106ce8180af8938929dc41`. It uses a redacted reconstructed ChatGPT-style tree from the visible timeline and checks payload equality, SHA-256, IDs, roles, ordering, parent links, unknown timestamps, and replay idempotency.
- **Do not overstate coverage:** this is not a native export of the still-active live chat. Native export of this active conversation is not available to the agent in-session. The test checks importer behavior on a reconstructed fixture, not completeness of live capture or semantic recall of every event.
- **Local execution:** clone attempt failed because the container could not resolve github.com. Check GitHub Actions for the exact latest branch HEAD before claiming test PASS.
- **Next:** inspect exact-head CI; fix failures; then test missing messages/parents, duplicate IDs, truncated source and interruption/resume; produce a read-back report with counts/IDs/order/hashes; then blind-test semantic reconstruction against source evidence without user hints. Only after these gates pass should older chats be exported.
- **Keep separate:** raw export integrity, chronology/relation restoration, semantic recovery, and automatic ongoing capture are four separate acceptance gates. Do not claim one from another.

- **Self-history audit update:** added `tests/test_current_session_roundtrip.py` using a redacted reconstructed timeline (not a native live-chat export). It checks payload round-trip equality, payload SHA-256, IDs, roles, ordering, parent links, unknown timestamps and idempotent replay. GitHub Actions run [38523204585](https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/38523204585) passed at exact HEAD `f4f1c8acaaf7cc67af2853580dadf91964935116`, including the full unittest suite.
- **Important self-detected defect:** while recording EVT-AGMS-20261014-001, the agent initially reversed a temporal relation to EVT-AGMS-20261013-006. It caught this on review and preserved an append-only correction in EVT-AGMS-20261014-002. The validator for temporal edge direction is still missing; do not treat this as solved by manual review.
- **Latest known change after the passing CI:** TASK_STATE was updated in commit `0b57475aca9628f1d8a4e6fcff3f02126b073afe`; CI for the resulting exact HEAD must be checked before claiming the latest head passes.
- **Remaining acceptance gates:** native source export/read-back of the live chat; verified counts/IDs/order/hashes; interruption/resume and malformed-source cases; semantic recovery against a blind source-derived checklist; automatic ongoing capture. Current test only proves behavior on the reconstructed fixture.

## Handoff — продолжить с последней подтверждённой контрольной точки (2026-10-14)

**Явная директива следующему заходу:** CONTINUE_FROM_LAST_CONFIRMED_CHECKPOINT.

- Цель: проверить двухзаходное восстановление после намеренно неполной обработки и закрепить явные инструкции агента.
- Состояние ветки до read-back/CI: export/cross-project-experience-rollup-20261012; последняя известная ранее HEAD 55cb3a50ad338dccc80b5ca968942618349b377d. После последних записей необходимо получить живой HEAD повторно.
- Изменён тест tests/test_resumable_chat_import.py: test_explicit_second_pass_resumes_from_last_confirmed_checkpoint создаёт паузу после одного подтверждённого пакета, читает durable checkpoint из SQLite, затем запускает второй проход с теми же идентификаторами и проверяет RESUME, source SHA-256, ordinal, byte offset, locator, уникальность/порядок записей и RAW_COMPLETE только после финальной сверки.
- Добавлены правила явного resume в core/universal_instructions.md, core/agent_runtime_protocol.md, core/source_ingestion_protocol.md. На втором заходе агент обязан проверить фактическую контрольную точку и использовать тот же исходник, archive ID и state path.
- Важно: обработка остановлена ≠ сама выгрузка усечена. Для усечённой выгрузки нужен отдельный тест и статус FAILED/PARTIAL; нельзя объявлять RAW_COMPLETE или переносить offset на новый снимок.
- Коммиты записи: test f97f1a57462a3a2672ec7c243246eb528274f527; universal aafd760661dc387a54ffeb94bdc212ff699d1011; runtime ce86fc578482a3cb31db7ad466eeb9d970478e2c; source protocol be5c95a964cdff40ef7f432c98eb650594477de1.
- **Статус сейчас: PARTIAL.** Файлы были записаны, но exact-HEAD read-back/CI ещё не подтверждены; локальный тест не запускался. Не называть это PASS до доказательств.
- **Следующий шаг:** read-back всех четырёх изменённых файлов и этого handoff, получить фактический HEAD, найти workflow run для точного SHA и прочитать итог. При зелёном CI выполнить/добавить отдельный тест усечённой выгрузки. PR #22 оставлять Draft/open/unmerged; main не менять.

