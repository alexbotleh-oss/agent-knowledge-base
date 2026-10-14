# TASK_STATE — AGMS-2026-10-13-01

- **Project:** AGENT_MEMORY_SYSTEM / `alexbotleh-oss/agent-knowledge-base`.
- **User task:** continue developing the memory system and transfer verified experience from «Настройка Агента»; inspect the live repository and PR #22 before changing canonical memory.
- **Expected result:** evidence-backed memory of memory-system design and work history, with provenance, chronology, statuses, conflicts and coverage gaps preserved.
- **Acceptance criteria:** correct project scope; source and repository states checked; existing memory reconciled before additions; facts separated from hypotheses; duplicate report copies not confused with repeated incidents; path-level scope risks recorded; available validation run; current handoff recorded; PR remains Draft/open/unmerged.
- **Constraints:** no application code changes; do not transfer full histories of CARD111, ORGANISM, RECIPE_MANAGER or B77_HTML_PWA; no private full chat archive uploaded to public GitHub; no destructive cleanup without a verified preservation destination; no merge without explicit user permission.
- **Sources directly inspected:** task file `turn209file0`; Library `conversations.zip`, `export_manifest.json`, `conversation_asset_file_names.json`, `Отчеты о извлечении.txt`, and `Последние дествия в предидущем чате.txt`; PR #22 and changed-path list; relevant core protocols on the PR head.
- **Source facts:** ZIP contains only `conversations.json`; 37 conversation objects, 10,034 distinct message IDs (7,446 assistant / 2,588 user), time range 2026-09-21 to 2026-10-07 UTC. Separate manifest lists 1,374 entries; asset-name map has 876 mappings. Full attachment/payload coverage remains incomplete. Report contains 1,425 lines and near-identical large blocks around lines 206–503 and 765–1063; 94 repeated long paragraphs were detected by a whitespace-normalized heuristic.
- **Coverage gap:** the inspected archive does not contain a conversation with the exact title «Настройка Агента»; the available “last actions” file is a summary, not the full chat. The transfer must remain PARTIAL.
- **Last confirmed passing CI checkpoint before this state refresh:** HEAD `2b029b3886571c3d989c9274bf9efc852974d5aa`, 336 commits ahead, 0 behind, 81 changed paths; exact-head GitHub Actions run #38387381733 passed. This update advances the branch; re-fetch after it.
- **Scope audit:** of 81 changed paths, 7 are AGENT_MEMORY_SYSTEM records, 37 are detailed records under separate project directories, and 2 are dedicated application-history reconciliation reports. Those 39 paths are outside direct scope unless distilled to transferable memory-process lessons. `SOURCE_REPORTS_AUDIT_2026-10-13.md` is mixed and needs narrowing. No files were deleted or moved pending a verified destination.
- **Completed:** inspected the requested core protocols; enumerated all 81 changed paths; checked live PR metadata, compare, exact-head CI, reviews and review threads; directly materialized and inspected the archive/manifest/report; recorded events EVT-AGMS-20261013-001–006 and lesson candidate L-AGMS-20261013-002; updated PR description with source and scope findings.
- **Not completed/verified:** semantic matching of every source-report claim to all primary messages and attachments; manifest-to-payload reconciliation; safe separation of the 39 out-of-scope paths; final scope-clean PR; local test commands.
- **Checks:** exact-head CI PASS at the checkpoint above; JSONL event file read-back parsed 6/6 records with 6 unique IDs; local `tools/validate_memory.py` and `python3 -m unittest discover -s tests` not run locally; no application code or database tests were relevant or run.
- **Next steps:** 1) decide safe destinations/PRs for out-of-scope project records; 2) narrow mixed report; 3) reconcile primary-source claims against canonical AGENT_MEMORY_SYSTEM records; 4) update PR body with the final exact head and run; 5) repeat structural validation and record the result.
- **Status:** active / partial; not ready for merge. Temporal edge corrections are recorded in an append-only overlay; a validator that applies overlays automatically remains unimplemented.

## Continuity checkpoint — 2026-10-13, user-requested operating loop

- **New user requirement:** when the user says to continue, recover the prior task, inspect source context and repository memory, compare current evidence with previous conclusions, record a checkpoint before risky/long work, maintain a verifiable plan, update progress during execution, resume safely after interruption, and report only verified outcomes. This is a desired operating protocol across the user, ChatGPT conversation/library, GitHub repository and LLM; it must not be described as fully automated until implementation and tests exist.
- **Required loop:** (1) recover goal/scope/constraints; (2) read project state/task/handoff and relevant source records; (3) fetch live branch/HEAD/PR/CI; (4) reconcile summaries against primary evidence; (5) create/update a compact task checkpoint with done/remaining/blockers/next action; (6) choose the smallest safe next operation; (7) perform and verify it; (8) update checkpoint after each substantial milestone; (9) update handoff before ending or when interruption risk is high; (10) report evidence, limitations and next step.
- **Anti-loop rule:** do not recreate indices/reports or rerun expensive matching when existing outputs can be inspected and compared. Repeat only when a defined check fails or a new hypothesis justifies it.
- **Current CARD111 evidence discovered during continuation:** branch `export/cross-project-experience-rollup-20261012`, prior reported HEAD `1afae2fe74f8919da13cf25d33de2a732ae5418c`. `projects/CARD111/source_history/attachment_index.jsonl` has 152 rows / 150 unique attachment IDs; one `attachment_id + message_id` pair appears twice with different `export_name`. The availability registry reports exact-ID matches for 150 unique IDs, while 106 rows in the attachment index have null `library_file_id`. A direct comparison confirmed 106 field mismatches between these files. This is an index-consistency defect, not evidence that another full-library matching pass is needed.
- **Scope conflict to resolve:** the current PR #22 description and AGENT_MEMORY_SYSTEM task instructions say full project histories (including CARD111) are outside the memory-system PR's direct scope, but the current branch now contains `projects/CARD111/source_history/` and other CARD111 paths. Do not silently treat this as approved or delete it. Before merge, establish whether the CARD111 source history belongs in a separate project-specific PR/branch or is intentionally included under an explicit revised scope; preserve recoverability either way. PR remains open/Draft/unmerged; no merge authorized.
- **Live state last fetched:** PR #22 is OPEN / DRAFT / UNMERGED; HEAD `1afae2fe74f8919da13cf25d33de2a732ae5418c`; 369 commits ahead of main according to PR metadata; 101 changed paths. The PR body is stale and still claims HEAD `a20279ef09609f437463d15b5b63ef4a74bf84c9`, 344 commits and 81 paths. Refresh description only after the intended scope and next verified changes are settled.
- **Immediate next actions:** (1) record/retain this checkpoint; (2) confirm the current source files and exact HEAD before writing; (3) decide/record scope separation for CARD111 without deleting files; (4) fix the 106 attachment-index references only from unambiguous exact-ID matches and retain an audit trail; (5) validate duplicate pair normalization without blindly deleting rows; (6) run targeted validation and exact-HEAD CI; (7) update task/handoff and report evidence.
- **Status:** PARTIAL / active. This checkpoint records a requested operating model and current evidence; it does not claim implementation of a durable automatic resume mechanism or completion of CARD111 transfer.


## Checkpoint 2026-10-13 — PRE-REPOSITORY GATE

- **User requirement:** before consulting the repository, the agent must already recover the task intent and constraints, establish the action order and verification criteria, and avoid returning to a disproven conclusion without new evidence or a documented reason.
- **Implemented on this branch:** added a mandatory `PRE-REPOSITORY GATE` to `core/universal_instructions.md` and a mandatory reference to it in `core/agent_runtime_protocol.md`. The gate requires goal/scope/permission recovery before repository calls; an explicit verification sequence; source-vs-hypothesis separation; a checkpoint before material edits; evidence-based revision of conclusions; read-back and status recording after each material step; and resumption from the last checkpoint after interruption.
- **Read-back:** both modified files were fetched again from the branch and the gate presence confirmed. Latest write commits: universal instructions `dfaba89607d120d4c9d1366b6e806392b859e402`; runtime protocol `3dc92fc62e6c392f49c228887b477467441fd8ed`. Subsequent read-back showed updated blob SHAs for both files.
- **Validation status:** exact-HEAD workflow lookup for `3dc92fc62e6c392f49c228887b477467441fd8ed` returned no associated PR workflow run at the time of lookup. Do not report CI PASS for this new head until a run is observed and its conclusion is successful.
- **Scope discipline:** only universal protocol files were changed in this step. No application code, project-specific source history, PR merge, or main-branch changes were made.
- **Next step:** re-fetch live PR/branch HEAD and check whether CI has started for the current head; then continue the existing scope-resolution work only after confirming live state. PR #22 remains intended to stay Draft/open/unmerged.


## Checkpoint 2026-10-13 — lightweight resumable chat import

- **User correction / accepted prior finding:** reports from other chat agents were already supplied, reviewed and accepted. The comparison confirmed that similar data/errors were merged in reports, obscuring distinct source dialogues/episodes. Do not restart this verification absent new contradictory evidence.
- **Current goal:** design a low-overhead, interruption-safe import path that preserves raw chat data, source order, timestamps, stable message IDs, and links needed to reconstruct chronology and causal chains. Avoid long 10–15 minute in-context semantic processing.
- **Architecture decision for the proposal:** separate (1) raw acquisition/inventory/staging from (2) later semantic extraction, chronology/causality analysis and search indexing. Initial import must not merge similar errors or build semantic indexes.
- **Protocol change:** appended “Быстрый возобновляемый импорт (без смыслового анализа на лету)” to `core/source_ingestion_protocol.md`. It specifies import states, stable cursors, bounded batches, transactional staging, idempotent replay, recovery after lost acknowledgement, checkpoint/event log/gap register, completeness conditions and five failure/resume tests.
- **Read-back:** fetched the modified protocol after write; the new section, `RAW_COMPLETE` state, lost-ack test and separation of import from later analysis were confirmed present. Commit: `8c3490627f87fa85c4f1ecfa78d8ebd00ec843af`; content blob: `c6bca94b919fd68d285781526940150e58d7b58b`.
- **Status:** protocol proposal recorded and read-back verified (PASS for persistence/read-back only). Runtime importer is **not implemented or tested**; resilience/latency claims remain unverified. CI for the new commit has not yet been checked.
- **Constraints:** no re-audit of accepted agent reports; no merge to `main`; PR #22 remains Draft/open/unmerged; do not claim an automatic local save mechanism exists in the current ChatGPT session.
- **Next action:** inspect live branch/PR HEAD and exact-head CI; then check existing schemas/tools to decide the smallest executable importer implementation (prefer streaming parser + local transactional staging/SQLite if runtime allows) and define measurable interruption/idempotency tests.


## Design correction 2026-10-13 — minimal continuity memory

- **User clarified the intended scope:** use current chat as temporary workspace, Project Library for source archives/reports, and repository as persistent structured memory. Do not make servers, a local agent, or a separate database prerequisites for the first usable version.
- **Primary purpose:** prevent context loss across chats and preserve the chronology/causal chain of important project events, decisions, failed attempts and lessons with minimal necessary context and stable source locators—not copy every conversation wholesale.
- **Accepted workflow:** restore latest state → continue the nearest unfinished action → record significant confirmed events/decisions/errors during work → save/read back a checkpoint before likely interruption and at stage completion. No need to create a record for every message.
- **Memory model:** linked event/incident, decision, task state and source records. Keep distinct episodes distinct; an aggregated lesson links to its supporting episodes and must not replace them.
- **Import scope correction:** first pass is lightweight source inventory and selective preservation of relevant source fragments with timestamps/IDs; no full semantic analysis, index building, or error-merging during ingestion. A later pass reconstructs chronology and causal links; uncertainty remains explicit.
- **Documentation updated:** added “Минимальная непрерывная память между чатами” to `core/universal_instructions.md` and “Минимальная непрерывность: восстановить → работать → зафиксировать” to `core/agent_runtime_protocol.md`.
- **Verified so far:** GitHub Contents API returned commits for both files; read-back still required. This is a protocol/instruction update, not a runtime feature or evidence that chat-level auto-save exists.
- **Next action:** read back both updated files, fetch latest branch/PR head and CI, then test whether the present repo mechanisms can support the smallest practical source-fragment/event record and reliable handoff without adding unnecessary infrastructure.


## Checkpoint 2026-10-13 — instruction read-back and CI refresh

- **Read-back:** `core/universal_instructions.md` and `core/agent_runtime_protocol.md` were fetched from this branch. The minimal continuity workflow is present: existing resources only; linked event/decision/task/source records; preserve separate incidents and provenance; lightweight archive pass first; checkpoints during work and before interruption; honest limits and test statuses.
- **Live PR state:** PR #22 is OPEN / DRAFT / UNMERGED. Current head reported by GitHub: `8112a41eea8cb7b03b403748567fb5faa60d8d3c`. Do not merge; the PR's own scope audit says it is not scope-clean.
- **CI:** workflow run 38416426765 (“Validate knowledge base”, run #318) for that exact head completed with conclusion `success` (PASS for that CI workflow only). This does not prove source-history completeness or the runtime interruption/resume behavior.
- **ChatGPT Project instructions:** no change is required for this correction: the active project instructions already require context recovery, source verification, checkpointing, honest statuses, and a concrete next step before repository work. Repository protocols remain the detailed implementation reference; they are not automatically loaded in every chat, so the start gate must continue to direct the agent to read them.
- **Next action:** inspect existing memory schemas/registries and reuse them if suitable; only add a compact event/checkpoint template if a real gap is confirmed. Then test a real handoff/recovery path. No new runtime importer or automatic chat autosave is claimed.


## Checkpoint 2026-10-13 — accepted attention/return-stack architecture

- **User-approved requirement:** preserve context when conversation branches away from the current goal; on return, account for why the branch occurred and what it changed, so returning to the old task does not itself derail the conversation again.
- **Architecture recorded:** section 10 in `core/continuous_agent_architecture.md` defines intent classes, separate active task/return stack/deferred ideas/switch history, required causal fields, context-aware return protocol, pre-response attention check and minimum verification tests.
- **Instruction updated:** `core/universal_instructions.md` now requires context-aware branching and return, separate deferred ideas, checking whether the original goal remains current, and honest limits where no persistent scheduler/storage is available.
- **Decision recorded:** DEC-AGMS-20261013-003 in `DECISIONS.md`.
- **Status:** documentation changes written; read-back and exact-head CI are pending. This is an architecture/instruction change only. Runtime implementation and behavior tests are not claimed.
- **Project instruction for ChatGPT:** a paste-ready amendment will be returned to the user; the live ChatGPT Project instruction itself has not been edited by repository changes.
- **Constraints unchanged:** PR #22 stays Draft/open/unmerged; no main-branch changes; do not claim automatic background return/notifications.
- **Next step:** read back each changed file, check exact current PR head and CI, then report verified status and provide the proposed ChatGPT Project instruction amendment.


## Implementation checkpoint — 2026-10-13 23:40 local

- User instruction: continue the existing work; architecture feedback is that repeated principles-only documentation is insufficient. Prefer small executable capabilities with tests and evidence over another prose-only restatement.
- Live PR #22 rechecked after writes: OPEN / DRAFT / UNMERGED; current HEAD `484eacb048caa2c7c5a6d28c9c68d8bf2d93d308`; 103 changed files. Do not merge. PR description is known to lag live metadata and still needs refresh after scope work.
- Added `tools/temporal_memory_model.py` (commit `d9d1c498b7152f21e84d60f01303cc053a59b1f6`) with dependency-free primitives for snapshot validation, scope-aware snapshot comparison, assertion validation, as-of views and transitive downstream impact discovery.
- Added `tests/test_temporal_memory_model.py` (commit `484eacb048caa2c7c5a6d28c9c68d8bf2d93d308`) with seven targeted tests covering: 37→74 count delta without calling it corruption; incomparable counting units; missing scope; temporal as-of views; preserving superseded claims; transitive/cycle-safe impact; and timezone/provenance validation.
- These primitives are additive and are not yet integrated into the canonical registry, migration flow, or automatic revision/overlay application. They do not prove end-to-end memory continuity.
- Exact-HEAD CI run #38464705063 was observed for this SHA and was `in_progress` at last check. No PASS claim yet. Local test execution has not been performed in this step.
- Scope audit remains blocking: project-specific histories and two application-history reports are present in PR #22 contrary to its direct memory-system scope; do not delete them without a verified preservation destination. Full source reconciliation remains PARTIAL.
- Next: check exact-head CI conclusion and test logs; fix any failures; add a small versioned schema/fixture and compatibility checks only after this baseline is green; then continue scope/preservation work and refresh task/handoff/PR metadata.


## Snapshot model increment — 2026-10-13

- Extended the first implementation increment with `schemas/temporal_memory_snapshot.schema.json` (version 1.0) and `tests/fixtures/temporal_snapshots_37_vs_74.json`. The fixture preserves 37 as directly observed in the inspected archive and 74 as a historical reported claim; it deliberately leaves the capture time for the 74 claim unknown and records the evidence needed for a valid comparison.
- Added a fixture-driven test that asserts the two snapshots are not comparable because scope and counting unit are not aligned. The test also asserts that unknown capture time remains null rather than being replaced with the date of review.
- Corrected the Python validator so an unknown capture time is permitted instead of being treated as missing. Known times still require an ISO-8601 timezone.
- Read-back confirmed the new files are present on the PR branch. Current live PR HEAD at checkpoint: `88a7b5362d15366483c86c7c3be50c86bb9b1513`, 105 changed paths, open/Draft/unmerged. GitHub Actions run [#38464883917](https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/38464883917) was queued for this exact HEAD; outcome not yet known. No local test execution has been performed, so tests are pending CI evidence.
- This is an initial vertical slice, not a complete evolving-memory architecture. Still absent: source-snapshot registry integration, assertion-revision persistence, impact propagation into state/lesson/handoff, migration/rollback, schema validation in CI, and end-to-end temporal recovery tests. Do not claim these are implemented.


## Active task checkpoint — resumable chat import prototype — 2026-10-14

- **Active goal restored from the previous chat:** implement fast, safe, resumable import of chat history; do not repeat the already accepted reconciliation of agent reports. Preserve original source messages, source identity, chronology and links; import first, analyze later. Keep PR #22 Draft/open/unmerged; do not touch `main`.
- **Existing implementation gap confirmed:** `tools/archive_registry_staging.py` loads the whole export into memory, derives a sorted source-record list, and atomically replaces the output; it has no transaction-level checkpoint or resume cursor. Therefore it is not the required resumable importer.
- **New runtime implementation:** added `tools/resumable_chat_import.py` and `tests/test_resumable_chat_import.py`. The tool stores an immutable SHA-256-verified source snapshot, incrementally decodes a top-level JSON array one conversation at a time, supports ZIP exports containing exactly one `conversations.json`, stages opaque conversation payloads in SQLite, commits data + cursor + append-only event in the same transaction, and supports resume/idempotent rerun. No private export content is uploaded by this tool.
- **Coverage:** tests exercise interruption after a committed batch and resume, idempotent rerun/source snapshot preservation, ZIP payload structure, and malformed source state. The new tests and full repository validation passed in CI run [#38519218588](https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/38519218588) for commit `d5bbb7a21e0e280c5fc6aa11ff4cc546bcac9774`.
- **Post-CI change:** a follow-up commit `5acfb5b7734c8ff6ce9ac59e42e5a0309ee94f9e` stopped sorting JSON keys in staged payloads to better preserve source mapping order. Subsequent documentation/checkpoint commits move HEAD again; exact latest-head CI must be rechecked before reporting final PASS.
- **Docs:** `core/source_ingestion_protocol.md` now documents invocation, behaviour and limitations.
- **Known limitation:** resume currently rescans prior conversations from the immutable snapshot until it reaches the saved ordinal. It is correct for a fixed snapshot but not optimal for very large exports; next optimization is a snapshot-bound byte-offset/position index tied to the last committed source locator. Payloads are staged at conversation granularity with full nested message structures; binary attachments are not extracted, and message-level semantic indexing is deferred.
- **Next:** verify CI for exact current HEAD; inspect failure logs if needed. Then improve resume seek efficiency only after correctness baseline remains green, add a test for simulated lost acknowledgement/transaction recovery and duplicate source IDs, and update PR description/hand-off. Do not merge because PR #22 remains scope-unsafe and includes unrelated project histories without a verified preservation destination.


## Resumable import test expansion — 2026-10-14

- Expanded `tests/test_resumable_chat_import.py` with a simulated lost acknowledgement/replayed committed batch, duplicate source conversation IDs (must fail visibly rather than silently drop one), and incremental UTF-8 decoding with tiny chunks/non-ASCII text.
- New exact-head workflow run [#38519357924](https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/38519357924) is running for commit `31272906f2b2a904c230225249fd930e8c0c0cf4`; result is not yet known at this checkpoint.
- Previous implementation + documentation changes have PASS on run [#38519320849](https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/38519320849) for commit `466f68801eb7fd8b75bdbc8171f4bae5ce213d32`. Do not extend that PASS to the new test commit until its own run completes.
- Next: inspect run #38519357924 and job logs if it fails; then optimize cursor seek only after tests are green. Current known limitation remains re-scanning from the start of the immutable snapshot on resume.


## Checkpoint — offset-based resume and CI verification — 2026-10-14

- Optimized tools/resumable_chat_import.py so a checkpoint stores both the next conversation ordinal and a byte offset immediately after the last committed conversation, plus the last source locator. The offset is bound to the immutable source snapshot SHA-256 and is advanced in the same SQLite transaction as the batch and event journal. Resume seeks to the offset rather than re-parsing earlier conversations; older DBs with zero/missing offset safely fall back to scanning from the beginning.
- Added additive SQLite column migration, offset emission from the incremental JSON-array decoder, and a test asserting that resume starts from the saved offset. Small-chunk UTF-8 test covers non-ASCII text; lost-ack replay and duplicate-ID tests remain in the suite.
- During this change CI caught a real bookkeeping bug (last was an ordinal but was indexed like a record). It was fixed in commit baf9240895b94d308b7f1f88d1f9ddb95a85535c; the subsequent exact-head run passed. The final code+docs HEAD at this checkpoint is b7344e351c260dab55f24a03e1c355f953124988, and workflow #38519573230 completed SUCCESS for that exact SHA.
- PASS means repository validation and all unittest discovery checks passed on the exact code/docs SHA. This is not yet a production-scale performance benchmark, attachment completeness audit, or proof that every external conversation is present.
- Next: inspect exact live PR head and run after checkpoint writes; add ZIP-resume test if needed; consider concurrent-run locking and crash injection around SQLite commit boundaries before treating the importer as production-ready. Keep PR #22 Draft/open/unmerged; scope/preservation issue still blocks merge.


## ZIP resume verification — 2026-10-14

- Added test coverage that pauses an import of a ZIP export after one committed conversation and resumes using the saved offset inside conversations.json. This validates the real ZipExtFile seek path rather than assuming it works.
- Exact test HEAD is f100e40e9d68cbdbf4a9a2099beb2afc7a2c8133. GitHub Actions run #38519660453 was in progress at the time of this checkpoint. Do not claim this added test passed until that run completes.
- Previous exact code/docs state b7344e351c260dab55f24a03e1c355f953124988 passed run #38519573230; the additional ZIP test is beyond that evidence.
- Continue from safe resumable importer; next inspect the exact-head run, fix any ZIP seek failure, then decide whether a concurrent-import guard is necessary before calling the prototype production-ready.


## Новая концепция общей памяти — аудит и этапы внедрения — 2026-10-14

- **Возврат к исходной цели:** пользователь передал концепцию независимого приёма и маршрутизации памяти из рабочих чатов. Обычный агент подготавливает маркированную выгрузку по общей инструкции; дальнейшая обработка должна идти независимо от исходного агента. Не сводить выгрузку только к «опыту» и «событиям»: возможны хронология, рабочий/краткосрочный контекст, кандидаты, утверждённые записи, связи и другие существующие библиотеки.
- **Ключевая поправка:** не требовать заранее определять все будущие проекты применимости. На входе фиксировать наблюдаемые признаки (язык/стек, инструменты, тип задачи/операции, условия, симптом/результат, provenance и статус). Применимость к другому проекту выявляется позднее и должна оставаться проверяемой.
- **Аудит выполнен:** добавлен `projects/AGENT_MEMORY_SYSTEM/MEMORY_PIPELINE_GAP_ANALYSIS_2026-10-14.md`. Проверены модель памяти, реестр стеков, шаблоны событий/уроков, валидатор, workflow, протокол сессий, протокол приёма источников и прототип импортёра.
- **Подтверждено существующее:** `core/memory_model.md`, `core/stack_registry.json`, event/lesson templates, `tools/validate_memory.py`, `.github/workflows/validate.yml`, runtime/session handoff protocols. Это фундамент, но не доказательство сквозной автоматической маршрутизации.
- **Статус импортёра исправлен концептуально:** `tools/resumable_chat_import.py` — изолированный прототип сохранения сырой истории и checkpoint, не готовый общий конвейер памяти. Его не считать согласованной конечной архитектурой; не удалять автоматически, не интегрировать дальше до сопоставления с контрактом входящей выгрузки.
- **PR/CI:** перед изменением HEAD `b43f404034450f718f18e002356cdb926fd702ba` имел CI PASS, run [#38519704988](https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/38519704988). Новый audit document создан коммитом `70422903e899521ad6eca93d07395098787f7581`; CI для нового HEAD нужно перепроверить отдельно.
- **Следующий шаг:** продолжить инвентаризацию фактических механизмов записи/индексации и workflow, сверить совместимость существующих форматов, затем определить минимальный versioned intake contract. Пока не писать новый маршрутизатор и не менять main.
- **Безопасность:** PR #22 остаётся Draft/open/unmerged; ранее обнаруженный scope/preservation конфликт остаётся нерешённым. Этот аудит не разрешает merge.


## Second-pass inventory and intake contract — 2026-10-14

- **Additional existing code checked:** `core/memory_registry_and_multidimensional_index.md`, `templates/memory_record.json.example`, `tools/archive_registry_staging.py`, `tools/archive_temporal_index.py`, `tools/temporal_memory_model.py`, existing tests and the actual branch workflow.
- **Findings:** the canonical design already calls for one linked registry with multidimensional views and rebuildable indexes. The archive staging tool is whole-file/non-resumable; temporal index is read-only/transient; temporal model primitives are not integrated into the ingestion write path; current workflow validates PRs and pushes to main but does not route incoming batches.
- **Stage 2 started:** added a versioned `memory_intake_manifest` contract, a synthetic fixture, and dependency-free validation tests. The manifest points to hash-checked relative artifacts; routing hints use allowlisted artifact kinds rather than arbitrary destination paths. Technology/tool/task labels retain evidence status and source refs; there is no field claiming universal future applicability.
- **Approval boundary:** `IMPORT_READY` means “this batch is ready for processing,” not “approve all records.” An artifact with lifecycle status `accepted` requires explicit user-approval evidence. The intake validator never executes artifact content and rejects path traversal, hash mismatch, unknown fields, duplicate artifact IDs and unsupported status values.
- **Privacy boundary:** the manifest contract forbids treating raw private chat exports as normal repository artifacts. Use sanitized structured memory or private-reference-only metadata; the GitHub repository is not a safe default destination for private raw history.
- **Next:** read back all changed files, run CI on exact HEAD, fix any validation issues, then define a dry-run route plan against the existing registry without writing canonical memory. Do not build automatic writes/index publication until the dry-run contract is tested.
