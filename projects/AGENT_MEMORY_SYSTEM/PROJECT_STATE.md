# PROJECT_STATE — AGENT_MEMORY_SYSTEM

## Current identity — РИМА

- **Имя:** РИМА.
- **Расшифровка:** Развивающаяся Интеллектуальная Модель Агента.
- **Род:** женский.
- **Статус:** имя принято пользователем 2026-10-16; событие `EVT-AGMS-20261016-009` хранит состояние до и после присвоения имени.
- **Принцип непрерывности:** имя должно восстанавливаться из постоянной памяти вместе с историей присвоения; краткое резюме чата не является единственным носителем идентичности.
- **Ограничение:** глобальное автоматическое восстановление во всех runtime-клиентах ещё не подтверждено.

- **Canonical project ID:** AGENT_MEMORY_SYSTEM.
- **Repository:** `alexbotleh-oss/agent-knowledge-base`.
- **Updated:** 2026-10-13; confidence: partial.
- **Current task:** AGMS-2026-10-13-01; see `TASK_STATE.md` and `HANDOFF.md`.
- **Goal:** improve the memory system itself—source ingestion, provenance, chronology, context recovery, conflict/duplicate handling, linked registry, verification and cross-chat continuity.
- **Scope boundary:** do not transfer full histories of CARD111, ORGANISM, RECIPE_MANAGER or B77_HTML_PWA into this memory-system task. Keep only evidence that directly explains memory architecture, scope/context-transfer failures or transferable lessons. These remain distinct project chains.
- **Current design direction:** immutable RAW snapshots; explicit inventory; extracted source records; candidate vs canonical memory; stable IDs and locators; separate event/source/recorded times; evidence and lifecycle statuses; append-only revisions; reversible imports; bidirectional temporal retrieval; source-to-memory coverage and recurrence audits.
- **Protocols reviewed from PR #22 head:** `core/repository_scope.md`, `core/universal_instructions.md`, `core/agent_runtime_protocol.md`, `core/memory_model.md`, `core/source_ingestion_protocol.md`, `core/chronology_reconstruction.md`, `core/session_handoff.md`, `core/chat_memory_collection_task.md`, `core/memory_registry_and_multidimensional_index.md`, and `core/continuous_agent_architecture.md`. Some of these paths are newly introduced on the PR branch and are not present on `main`.
- **Direct source audit:** materialized and parsed Library files `conversations.zip`, `export_manifest.json`, `conversation_asset_file_names.json`, and `Отчеты о извлечении.txt`. The ZIP contains only `conversations.json` (42,997,976 bytes uncompressed): 37 conversation objects, 10,034 unique message IDs, 7,446 assistant and 2,588 user messages, timestamps from 2026-09-21T11:06:33.535Z to 2026-10-07T14:24:53.051577Z. Separate manifest: 1,374 entries; asset-name map: 876 mappings. Full manifest-to-payload reconciliation is incomplete.
- **Report duplication:** large near-identical blocks around lines 206–503 and 765–1063; whitespace-normalized scan found 94 repeated long paragraphs. These are report-copy candidates, not independent incident counts.
- **Coverage limitation:** the inspected ZIP has no conversation with the exact title «Настройка Агента» and ends on 2026-10-07. The separate “Последние дествия в предидущем чате.txt” is a secondary summary, not a full primary transcript. Overall source coverage remains PARTIAL.
- **Live PR audit checkpoint:** PR #22 is open, Draft, unmerged. Last confirmed passing checkpoint before this state refresh: HEAD `2b029b3886571c3d989c9274bf9efc852974d5aa`, 336 commits ahead of `main`, 0 behind and 81 changed paths; GitHub Actions passed on that exact SHA, run [#38387381733](https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/38387381733). This update advances the branch; re-fetch live metadata and exact-head CI before reporting current status.
- **Scope finding:** 7 paths belong to `projects/AGENT_MEMORY_SYSTEM/`; 37 changed paths contain project-specific records under B77_HTML_PWA, CARD111, ORGANISM and RECIPE_MANAGER; two additional reports focus on application-specific histories. These 39 paths are outside direct scope unless reduced to transferable memory-process lessons. `SOURCE_REPORTS_AUDIT_2026-10-13.md` is mixed and needs narrowing. They were not deleted because a verified preservation destination has not been established. PR is not scope-clean.
- **No merge authorized:** keep PR #22 Draft/open/unmerged. Do not alter `main` or application code.
- **Local checks:** local validators and unit tests were not run in this session; prior local clone attempt was blocked by DNS. Exact-head CI is the available automated evidence.
- **Data-integrity correction:** temporal edge directions in EVT-AGMS-002/003/004 were found reversed; EVT-AGMS-005 documents the correction and EVT-AGMS-006 adds machine-readable `edge_corrections`. Lesson candidate L-AGMS-20261013-002 was appended. Older records remain in the append-only log; an automatic overlay-applier/validator is not implemented.
- **Canonical records:** `EVENT_LOG.md` and `events.jsonl` contain events EVT-AGMS-20261013-001 through EVT-AGMS-20261013-006. Historical events remain append-only; this file is a current-state snapshot.
- **Next step:** decide a safe preservation/separation strategy for the 39 out-of-scope paths; narrow the mixed report; continue semantic reconciliation only for AGENT_MEMORY_SYSTEM and transferable memory lessons; rerun exact-head CI after final scope changes.

## Checkpoint — actionable cross-chat checkpoint instructions (2026-10-14)

- User identified a practical gap: agents may see a checkpoint owned by another chat/project but lack explicit instructions for how to act on it.
- Added `core/cross_chat_checkpoint_agent_instructions.md` with an eight-step procedure: identify source and owner; preserve source history; assess applicability; avoid repeating evidence-backed work; record child work separately; return results with evidence; reconcile linked results on source resume; safely handle interrupted delivery.
- Wired the instruction into `core/universal_instructions.md` and `core/agent_runtime_protocol.md` so it is part of the normal agent instructions, not an isolated design note.
- Read-back confirmed the instruction file and both references are present on the working branch.
- **Implementation boundary:** this is an actionable behavioral instruction plus runtime reference. It does not implement the branch registry, automated cross-chat retrieval/result delivery, acknowledgement tracking, or derived-state updates. Do not claim those mechanisms are automatic.
- **Next:** run/check CI for the exact latest HEAD and record the result. Keep PR #22 Draft/open/unmerged; do not change `main`.
