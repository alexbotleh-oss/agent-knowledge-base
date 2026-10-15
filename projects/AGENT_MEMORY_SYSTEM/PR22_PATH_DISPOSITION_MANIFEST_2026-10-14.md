# PR #22 path disposition manifest — 2026-10-14

> Historical disposition record. This clean integration branch copies KEEP_CORE, KEEP_AGMS and KEEP_TRANSFERABLE_LESSON items only. Out-of-scope project histories and raw-source artifacts remain on `archive-reconciliation/deferred-20261014`; their absence here is not deletion or merge authorization.

Source: live GitHub changed-path list for PR #22, fetched 2026-10-14. This is a first-pass scope disposition, not a deletion script. Each path must be preserved before exclusion; no path is deleted by this manifest.

Statuses: KEEP_CORE; KEEP_AGMS; KEEP_TRANSFERABLE_LESSON; SEPARATE_PROJECT_MEMORY; PRESERVE_RAW_OUT_OF_SCOPE; REVIEW_MIXED.

| # | Path | Proposed status | Rationale / required handling |
|---:|---|---|---|
| 1 | `ARCHIVE_TEMPORAL_ROUNDTRIP_AND_RECURRENCE_PROBE_2026-10-13.md` | KEEP_AGMS | Temporal round-trip fixture evidence and recurrence-probe caveats; retain as memory-system validation evidence, not as independent incident counts. |
| 2 | `BIDIRECTIONAL_TEMPORAL_CONTEXT_RETRIEVAL_2026-10-13.md` | KEEP_AGMS | Memory-system design for bidirectional temporal retrieval, lineage, causal/impact traces, and a proposed test plan; do not overstate requirements as implementation. |
| 3 | `CHAT_EXPORT_COVERAGE_2026-10-12.md` | KEEP_AGMS | Source coverage/provenance audit for memory-transfer task; verify no unnecessary app history. |
| 4 | `MEMORY_ARCHITECTURE_GAP_EVOLVING_KNOWLEDGE_2026-10-13.md` | KEEP_AGMS | Direct analysis of evolving-memory gaps; distinguishes partial vertical slices from missing end-to-end integration. |
| 5 | `README.md` | KEEP_CORE | Repository entrypoint; review links against files retained in scope. |
| 6 | `SOURCE_ARCHIVE_AUDIT_2026-10-12.md` | KEEP_AGMS | Source coverage/provenance audit for memory-transfer task; verify no unnecessary app history. |
| 7 | `SOURCE_RECONCILIATION_APK_BUILD_2026-10-13.md` | PRESERVE_RAW_OUT_OF_SCOPE | Full report preserved at `projects/RECIPE_MANAGER/source_history/SOURCE_RECONCILIATION_APK_BUILD_2026-10-13.md`; retain original root copy until a separately validated PR candidate excludes it. |
| 8 | `SOURCE_RECONCILIATION_B77_HTML_REGRESSIONS_2026-10-13.md` | PRESERVE_RAW_OUT_OF_SCOPE | Full report preserved at `projects/B77_HTML_PWA/source_history/SOURCE_RECONCILIATION_B77_HTML_REGRESSIONS_2026-10-13.md`; retain original root copy until a separately validated PR candidate excludes it. |
| 9 | `SOURCE_REPORTS_AUDIT_2026-10-13.md` | KEEP_AGMS | Direct audit methodology: copied report text vs incidents, chronology, evidence grading, source coverage, and structural vs semantic completeness. Preserve its limitations; no broad re-audit without contradictory evidence. |
| 10 | `SOURCE_TIMELINE_RECONCILIATION_37_VS_74_2026-10-13.md` | KEEP_AGMS | Source coverage/provenance audit for memory-transfer task; verify no unnecessary app history. |
| 11 | `UNIFIED_MEMORY_REGISTRY_AND_SAFE_ENRICHMENT_2026-10-13.md` | KEEP_AGMS | Memory architecture for snapshots, provenance, lineage, staging, idempotence, retrieval and integrity; does not establish that all runtime integration/rollback is implemented. |
| 12 | `core/agent_runtime_protocol.md` | KEEP_CORE | Universal memory architecture, implementation, schema, fixture or test; confirm dependencies before scope removal. |
| 13 | `core/chat_lifecycle_protocol.md` | KEEP_CORE | Universal memory architecture, implementation, schema, fixture or test; confirm dependencies before scope removal. |
| 14 | `core/chat_memory_collection_task.md` | KEEP_CORE | Universal memory architecture, implementation, schema, fixture or test; confirm dependencies before scope removal. |
| 15 | `core/chronology_reconstruction.md` | KEEP_CORE | Universal memory architecture, implementation, schema, fixture or test; confirm dependencies before scope removal. |
| 16 | `core/continuous_agent_architecture.md` | KEEP_CORE | Universal memory architecture, implementation, schema, fixture or test; confirm dependencies before scope removal. |
| 17 | `core/cross_chat_checkpoint_agent_instructions.md` | KEEP_CORE | Universal memory architecture, implementation, schema, fixture or test; confirm dependencies before scope removal. |
| 18 | `core/event_continuity_and_uncertainty.md` | KEEP_CORE | Universal memory architecture, implementation, schema, fixture or test; confirm dependencies before scope removal. |
| 19 | `core/external_change_control.md` | KEEP_CORE | Universal memory architecture, implementation, schema, fixture or test; confirm dependencies before scope removal. |
| 20 | `core/external_change_registry_template.md` | KEEP_CORE | Universal memory architecture, implementation, schema, fixture or test; confirm dependencies before scope removal. |
| 21 | `core/memory_model.md` | KEEP_CORE | Universal memory architecture, implementation, schema, fixture or test; confirm dependencies before scope removal. |
| 22 | `core/memory_registry_and_multidimensional_index.md` | KEEP_CORE | Universal memory architecture, implementation, schema, fixture or test; confirm dependencies before scope removal. |
| 23 | `core/repository_scope.md` | KEEP_CORE | Universal memory architecture, implementation, schema, fixture or test; confirm dependencies before scope removal. |
| 24 | `core/skill_catalog.md` | KEEP_CORE | Universal memory architecture, implementation, schema, fixture or test; confirm dependencies before scope removal. |
| 25 | `core/skill_spec_template.md` | KEEP_CORE | Universal memory architecture, implementation, schema, fixture or test; confirm dependencies before scope removal. |
| 26 | `core/source_ingestion_protocol.md` | KEEP_CORE | Universal memory architecture, implementation, schema, fixture or test; confirm dependencies before scope removal. |
| 27 | `core/stepwise_verification_protocol.md` | KEEP_CORE | Universal memory architecture, implementation, schema, fixture or test; confirm dependencies before scope removal. |
| 28 | `core/unified_memory_control_loop.md` | KEEP_CORE | Universal memory architecture, implementation, schema, fixture or test; confirm dependencies before scope removal. |
| 29 | `core/universal_instructions.md` | KEEP_CORE | Universal memory architecture, implementation, schema, fixture or test; confirm dependencies before scope removal. |
| 30 | `core/visual_diagnostics.md` | KEEP_CORE | Universal memory architecture, implementation, schema, fixture or test; confirm dependencies before scope removal. |
| 31 | `lessons/cross_project_review_20261012.md` | KEEP_TRANSFERABLE_LESSON | Retain only general prevention rules and explicit project-boundary distinctions; full B77 and RECIPE_MANAGER event histories remain in their own project memories. |
| 32 | `lessons/global/LESSONS.md` | KEEP_TRANSFERABLE_LESSON | Shared lessons; retain only entries with source provenance and no project-only detail. |
| 33 | `lessons/global/README.md` | KEEP_TRANSFERABLE_LESSON | Shared lessons; retain only entries with source provenance and no project-only detail. |
| 34 | `lessons/global/records.jsonl` | KEEP_TRANSFERABLE_LESSON | Shared lessons; retain only entries with source provenance and no project-only detail. |
| 35 | `projects/AGENT_MEMORY_SYSTEM/CENTRAL_CHAT_CHECKPOINT_2026-10-14.md` | KEEP_AGMS | Direct memory-system project state/events/decisions/handoff; in scope. |
| 36 | `projects/AGENT_MEMORY_SYSTEM/DECISIONS.md` | KEEP_AGMS | Direct memory-system project state/events/decisions/handoff; in scope. |
| 37 | `projects/AGENT_MEMORY_SYSTEM/EVENT_LOG.md` | KEEP_AGMS | Direct memory-system project state/events/decisions/handoff; in scope. |
| 38 | `projects/AGENT_MEMORY_SYSTEM/HANDOFF.md` | KEEP_AGMS | Direct memory-system project state/events/decisions/handoff; in scope. |
| 39 | `projects/AGENT_MEMORY_SYSTEM/IDEA_SANDBOX.md` | KEEP_AGMS | Direct memory-system project state/events/decisions/handoff; in scope. |
| 40 | `projects/AGENT_MEMORY_SYSTEM/LESSONS.md` | KEEP_AGMS | Direct memory-system project state/events/decisions/handoff; in scope. |
| 41 | `projects/AGENT_MEMORY_SYSTEM/MEMORY_PIPELINE_GAP_ANALYSIS_2026-10-14.md` | KEEP_AGMS | Direct memory-system project state/events/decisions/handoff; in scope. |
| 42 | `projects/AGENT_MEMORY_SYSTEM/PROJECT_STATE.md` | KEEP_AGMS | Direct memory-system project state/events/decisions/handoff; in scope. |
| 43 | `projects/AGENT_MEMORY_SYSTEM/SOURCE_AND_GOAL_PREFLIGHT_INCIDENT_2026-10-14.md` | KEEP_AGMS | Direct memory-system project state/events/decisions/handoff; in scope. |
| 44 | `projects/AGENT_MEMORY_SYSTEM/TASK_STATE.md` | KEEP_AGMS | Direct memory-system project state/events/decisions/handoff; in scope. |
| 45 | `projects/AGENT_MEMORY_SYSTEM/events.jsonl` | KEEP_AGMS | Direct memory-system project state/events/decisions/handoff; in scope. |
| 46 | `projects/B77_HTML_PWA/DECISIONS.md` | SEPARATE_PROJECT_MEMORY | Project-specific history/state; review for concise transferable lessons, but do not merge full project history into direct-scope PR. |
| 47 | `projects/B77_HTML_PWA/EVENT_LOG.md` | SEPARATE_PROJECT_MEMORY | Project-specific history/state; review for concise transferable lessons, but do not merge full project history into direct-scope PR. |
| 48 | `projects/B77_HTML_PWA/HANDOFF.md` | SEPARATE_PROJECT_MEMORY | Project-specific history/state; review for concise transferable lessons, but do not merge full project history into direct-scope PR. |
| 49 | `projects/B77_HTML_PWA/HTML_SQLITE_REGRESSION_2026-09-22.md` | SEPARATE_PROJECT_MEMORY | Project-specific history/state; review for concise transferable lessons, but do not merge full project history into direct-scope PR. |
| 50 | `projects/B77_HTML_PWA/LESSONS.md` | SEPARATE_PROJECT_MEMORY | Project-specific history/state; review for concise transferable lessons, but do not merge full project history into direct-scope PR. |
| 51 | `projects/B77_HTML_PWA/PROJECT_STATE.md` | SEPARATE_PROJECT_MEMORY | Project-specific history/state; review for concise transferable lessons, but do not merge full project history into direct-scope PR. |
| 52 | `projects/B77_HTML_PWA/TASK_STATE.md` | SEPARATE_PROJECT_MEMORY | Project-specific history/state; review for concise transferable lessons, but do not merge full project history into direct-scope PR. |
| 53 | `projects/B77_HTML_PWA/events.jsonl` | SEPARATE_PROJECT_MEMORY | Project-specific history/state; review for concise transferable lessons, but do not merge full project history into direct-scope PR. |
| 54 | `projects/CARD111/DECISIONS.md` | SEPARATE_PROJECT_MEMORY | Project-specific history/state; review for concise transferable lessons, but do not merge full project history into direct-scope PR. |
| 55 | `projects/CARD111/EVENT_LOG.md` | SEPARATE_PROJECT_MEMORY | Project-specific history/state; review for concise transferable lessons, but do not merge full project history into direct-scope PR. |
| 56 | `projects/CARD111/HANDOFF.md` | SEPARATE_PROJECT_MEMORY | Project-specific history/state; review for concise transferable lessons, but do not merge full project history into direct-scope PR. |
| 57 | `projects/CARD111/LESSONS.md` | SEPARATE_PROJECT_MEMORY | Project-specific history/state; review for concise transferable lessons, but do not merge full project history into direct-scope PR. |
| 58 | `projects/CARD111/PROJECT_STATE.md` | SEPARATE_PROJECT_MEMORY | Project-specific history/state; review for concise transferable lessons, but do not merge full project history into direct-scope PR. |
| 59 | `projects/CARD111/TASK_STATE.md` | SEPARATE_PROJECT_MEMORY | Project-specific history/state; review for concise transferable lessons, but do not merge full project history into direct-scope PR. |
| 60 | `projects/CARD111/events.jsonl` | SEPARATE_PROJECT_MEMORY | Project-specific history/state; review for concise transferable lessons, but do not merge full project history into direct-scope PR. |
| 61 | `projects/CARD111/lessons.jsonl` | SEPARATE_PROJECT_MEMORY | Project-specific history/state; review for concise transferable lessons, but do not merge full project history into direct-scope PR. |
| 62 | `projects/CARD111/source_history/README.md` | PRESERVE_RAW_OUT_OF_SCOPE | Detailed source-history material; preserve outside this direct-scope PR. |
| 63 | `projects/CARD111/source_history/attachment_availability.json` | PRESERVE_RAW_OUT_OF_SCOPE | Detailed source-history material; preserve outside this direct-scope PR. |
| 64 | `projects/CARD111/source_history/attachment_index.jsonl` | PRESERVE_RAW_OUT_OF_SCOPE | Detailed source-history material; preserve outside this direct-scope PR. |
| 65 | `projects/CARD111/source_history/index.md` | PRESERVE_RAW_OUT_OF_SCOPE | Detailed source-history material; preserve outside this direct-scope PR. |
| 66 | `projects/CARD111/source_history/message_index.jsonl` | PRESERVE_RAW_OUT_OF_SCOPE | Detailed source-history material; preserve outside this direct-scope PR. |
| 67 | `projects/CARD111/source_history/raw/conversations/6ac37f12-5b7c-83eb-bcee-b7cc20d48046.json` | PRESERVE_RAW_OUT_OF_SCOPE | Detailed source-history material; preserve outside this direct-scope PR. |
| 68 | `projects/CARD111/source_history/raw/conversations/6ac3c8f4-c55c-83ed-8f87-61017faf4c9d.json` | PRESERVE_RAW_OUT_OF_SCOPE | Detailed source-history material; preserve outside this direct-scope PR. |
| 69 | `projects/CARD111/source_history/raw/conversations/6ac4e22f-1174-83ed-921f-467bf4a31b7d.json` | PRESERVE_RAW_OUT_OF_SCOPE | Detailed source-history material; preserve outside this direct-scope PR. |
| 70 | `projects/CARD111/source_history/raw/conversations/6ac51760-2c30-83eb-9311-3f229c67f3ee.json` | PRESERVE_RAW_OUT_OF_SCOPE | Detailed source-history material; preserve outside this direct-scope PR. |
| 71 | `projects/CARD111/source_history/raw/conversations/6ac51c82-4b70-83eb-a16b-b7085d95daeb.json` | PRESERVE_RAW_OUT_OF_SCOPE | Detailed source-history material; preserve outside this direct-scope PR. |
| 72 | `projects/CARD111/source_history/raw/conversations/6ac613a6-d118-83ed-a2ea-b85f766a18ee.json` | PRESERVE_RAW_OUT_OF_SCOPE | Detailed source-history material; preserve outside this direct-scope PR. |
| 73 | `projects/CARD111/source_history/reports/CARD111_FULL_REPORT_2026-10-06.md` | PRESERVE_RAW_OUT_OF_SCOPE | Detailed source-history material; preserve outside this direct-scope PR. |
| 74 | `projects/CARD111/source_history/source_index.json` | PRESERVE_RAW_OUT_OF_SCOPE | Detailed source-history material; preserve outside this direct-scope PR. |
| 75 | `projects/CARD111/source_history/supplementary/CARD111_визуальные_требования_редактор_и_кошелёк.md` | PRESERVE_RAW_OUT_OF_SCOPE | Detailed source-history material; preserve outside this direct-scope PR. |
| 76 | `projects/CARD111/source_history/supplementary/CARD111_диалог_2026-10-08.md` | PRESERVE_RAW_OUT_OF_SCOPE | Detailed source-history material; preserve outside this direct-scope PR. |
| 77 | `projects/CARD111/source_history/supplementary/CARD111_чат_экспорт_2026-10-08.md` | PRESERVE_RAW_OUT_OF_SCOPE | Detailed source-history material; preserve outside this direct-scope PR. |
| 78 | `projects/CARD111/source_history/supplementary/CARD_TRANSFER_STATE_2026-10-05.txt` | PRESERVE_RAW_OUT_OF_SCOPE | Detailed source-history material; preserve outside this direct-scope PR. |
| 79 | `projects/CARD111/source_history/supplementary/EXPERIMENT_3_REQUEST_FULL_CHAT_EXTRACTION.md` | PRESERVE_RAW_OUT_OF_SCOPE | Detailed source-history material; preserve outside this direct-scope PR. |
| 80 | `projects/CARD111/source_history/supplementary/EXPERIMENT_4_TASK_MEMORY_TRANSFER.txt` | PRESERVE_RAW_OUT_OF_SCOPE | Detailed source-history material; preserve outside this direct-scope PR. |
| 81 | `projects/CARD111/source_history/supplementary/initial_project_proposal.md` | PRESERVE_RAW_OUT_OF_SCOPE | Detailed source-history material; preserve outside this direct-scope PR. |
| 82 | `projects/ORGANISM/DECISIONS.md` | SEPARATE_PROJECT_MEMORY | Project-specific history/state; review for concise transferable lessons, but do not merge full project history into direct-scope PR. |
| 83 | `projects/ORGANISM/EVENT_LOG.md` | SEPARATE_PROJECT_MEMORY | Project-specific history/state; review for concise transferable lessons, but do not merge full project history into direct-scope PR. |
| 84 | `projects/ORGANISM/HANDOFF.md` | SEPARATE_PROJECT_MEMORY | Project-specific history/state; review for concise transferable lessons, but do not merge full project history into direct-scope PR. |
| 85 | `projects/ORGANISM/LESSONS.md` | SEPARATE_PROJECT_MEMORY | Project-specific history/state; review for concise transferable lessons, but do not merge full project history into direct-scope PR. |
| 86 | `projects/ORGANISM/PROJECT_STATE.md` | SEPARATE_PROJECT_MEMORY | Project-specific history/state; review for concise transferable lessons, but do not merge full project history into direct-scope PR. |
| 87 | `projects/ORGANISM/TASK_STATE.md` | SEPARATE_PROJECT_MEMORY | Project-specific history/state; review for concise transferable lessons, but do not merge full project history into direct-scope PR. |
| 88 | `projects/ORGANISM/events.jsonl` | SEPARATE_PROJECT_MEMORY | Project-specific history/state; review for concise transferable lessons, but do not merge full project history into direct-scope PR. |
| 89 | `projects/ORGANISM/lessons.jsonl` | SEPARATE_PROJECT_MEMORY | Project-specific history/state; review for concise transferable lessons, but do not merge full project history into direct-scope PR. |
| 90 | `projects/RECIPE_MANAGER/BUILD_PACKAGING_ATTEMPT_2026-09-22.md` | SEPARATE_PROJECT_MEMORY | Project-specific history/state; review for concise transferable lessons, but do not merge full project history into direct-scope PR. |
| 91 | `projects/RECIPE_MANAGER/CHAT_TRANSFER_RECONCILIATION_2026-10-12.md` | SEPARATE_PROJECT_MEMORY | Project-specific history/state; review for concise transferable lessons, but do not merge full project history into direct-scope PR. |
| 92 | `projects/RECIPE_MANAGER/DECISIONS.md` | SEPARATE_PROJECT_MEMORY | Project-specific history/state; review for concise transferable lessons, but do not merge full project history into direct-scope PR. |
| 93 | `projects/RECIPE_MANAGER/EVENT_LOG.md` | SEPARATE_PROJECT_MEMORY | Project-specific history/state; review for concise transferable lessons, but do not merge full project history into direct-scope PR. |
| 94 | `projects/RECIPE_MANAGER/HANDOFF.md` | SEPARATE_PROJECT_MEMORY | Project-specific history/state; review for concise transferable lessons, but do not merge full project history into direct-scope PR. |
| 95 | `projects/RECIPE_MANAGER/HTML_SQLITE_REGRESSION_2026-10-12.md` | SEPARATE_PROJECT_MEMORY | Project-specific history/state; review for concise transferable lessons, but do not merge full project history into direct-scope PR. |
| 96 | `projects/RECIPE_MANAGER/LESSONS.md` | SEPARATE_PROJECT_MEMORY | Project-specific history/state; review for concise transferable lessons, but do not merge full project history into direct-scope PR. |
| 97 | `projects/RECIPE_MANAGER/MASTER_CONTROL_MATRIX_AUDIT_2026-10-13.md` | SEPARATE_PROJECT_MEMORY | Project-specific history/state; review for concise transferable lessons, but do not merge full project history into direct-scope PR. |
| 98 | `projects/RECIPE_MANAGER/PROJECT_STATE.md` | SEPARATE_PROJECT_MEMORY | Project-specific history/state; review for concise transferable lessons, but do not merge full project history into direct-scope PR. |
| 99 | `projects/RECIPE_MANAGER/RECIPE_SEARCH_REQUIREMENTS.md` | SEPARATE_PROJECT_MEMORY | Project-specific history/state; review for concise transferable lessons, but do not merge full project history into direct-scope PR. |
| 100 | `projects/RECIPE_MANAGER/SOURCE_COVERAGE.md` | SEPARATE_PROJECT_MEMORY | Project-specific history/state; review for concise transferable lessons, but do not merge full project history into direct-scope PR. |
| 101 | `projects/RECIPE_MANAGER/TASK_STATE.md` | SEPARATE_PROJECT_MEMORY | Project-specific history/state; review for concise transferable lessons, but do not merge full project history into direct-scope PR. |
| 102 | `projects/RECIPE_MANAGER/events.jsonl` | SEPARATE_PROJECT_MEMORY | Project-specific history/state; review for concise transferable lessons, but do not merge full project history into direct-scope PR. |
| 103 | `schemas/memory_intake_manifest.schema.json` | KEEP_CORE | Universal memory architecture, implementation, schema, fixture or test; confirm dependencies before scope removal. |
| 104 | `schemas/temporal_memory_snapshot.schema.json` | KEEP_CORE | Universal memory architecture, implementation, schema, fixture or test; confirm dependencies before scope removal. |
| 105 | `templates/archive_snapshot.json.example` | KEEP_CORE | Universal memory architecture, implementation, schema, fixture or test; confirm dependencies before scope removal. |
| 106 | `templates/event_record.jsonl.example` | KEEP_CORE | Universal memory architecture, implementation, schema, fixture or test; confirm dependencies before scope removal. |
| 107 | `templates/memory_intake_manifest.json.example` | KEEP_CORE | Universal memory architecture, implementation, schema, fixture or test; confirm dependencies before scope removal. |
| 108 | `templates/memory_record.json.example` | KEEP_CORE | Universal memory architecture, implementation, schema, fixture or test; confirm dependencies before scope removal. |
| 109 | `tests/fixtures/memory_intake_batch/manifest.json` | KEEP_CORE | Universal memory architecture, implementation, schema, fixture or test; confirm dependencies before scope removal. |
| 110 | `tests/fixtures/memory_intake_batch/records.jsonl` | KEEP_CORE | Universal memory architecture, implementation, schema, fixture or test; confirm dependencies before scope removal. |
| 111 | `tests/fixtures/temporal_snapshots_37_vs_74.json` | KEEP_CORE | Universal memory architecture, implementation, schema, fixture or test; confirm dependencies before scope removal. |
| 112 | `tests/test_archive_registry_staging.py` | KEEP_CORE | Universal memory architecture, implementation, schema, fixture or test; confirm dependencies before scope removal. |
| 113 | `tests/test_branch_result_registry.py` | KEEP_CORE | Universal memory architecture, implementation, schema, fixture or test; confirm dependencies before scope removal. |
| 114 | `tests/test_child_result_return_roundtrip.py` | KEEP_CORE | Universal memory architecture, implementation, schema, fixture or test; confirm dependencies before scope removal. |
| 115 | `tests/test_current_session_roundtrip.py` | KEEP_CORE | Universal memory architecture, implementation, schema, fixture or test; confirm dependencies before scope removal. |
| 116 | `tests/test_guarded_task_state_update.py` | KEEP_CORE | Universal memory architecture, implementation, schema, fixture or test; confirm dependencies before scope removal. |
| 117 | `tests/test_memory_intake_contract.py` | KEEP_CORE | Universal memory architecture, implementation, schema, fixture or test; confirm dependencies before scope removal. |
| 118 | `tests/test_memory_intake_planner.py` | KEEP_CORE | Universal memory architecture, implementation, schema, fixture or test; confirm dependencies before scope removal. |
| 119 | `tests/test_reconcile_branch_returns.py` | KEEP_CORE | Universal memory architecture, implementation, schema, fixture or test; confirm dependencies before scope removal. |
| 120 | `tests/test_restore_session_packet.py` | KEEP_CORE | Universal memory architecture, implementation, schema, fixture or test; confirm dependencies before scope removal. |
| 121 | `tests/test_resumable_chat_import.py` | KEEP_CORE | Universal memory architecture, implementation, schema, fixture or test; confirm dependencies before scope removal. |
| 122 | `tests/test_source_goal_preflight_contract.py` | KEEP_CORE | Universal memory architecture, implementation, schema, fixture or test; confirm dependencies before scope removal. |
| 123 | `tests/test_temporal_memory_model.py` | KEEP_CORE | Universal memory architecture, implementation, schema, fixture or test; confirm dependencies before scope removal. |
| 124 | `tests/test_unified_memory_control_loop.py` | KEEP_CORE | Universal memory architecture, implementation, schema, fixture or test; confirm dependencies before scope removal. |
| 125 | `tools/archive_registry_staging.py` | KEEP_CORE | Universal memory architecture, implementation, schema, fixture or test; confirm dependencies before scope removal. |
| 126 | `tools/archive_temporal_index.py` | KEEP_CORE | Universal memory architecture, implementation, schema, fixture or test; confirm dependencies before scope removal. |
| 127 | `tools/branch_result_registry.py` | KEEP_CORE | Universal memory architecture, implementation, schema, fixture or test; confirm dependencies before scope removal. |
| 128 | `tools/guarded_task_state_update.py` | KEEP_CORE | Universal memory architecture, implementation, schema, fixture or test; confirm dependencies before scope removal. |
| 129 | `tools/plan_memory_intake.py` | KEEP_CORE | Universal memory architecture, implementation, schema, fixture or test; confirm dependencies before scope removal. |
| 130 | `tools/reconcile_branch_returns.py` | KEEP_CORE | Universal memory architecture, implementation, schema, fixture or test; confirm dependencies before scope removal. |
| 131 | `tools/restore_session_packet.py` | KEEP_CORE | Universal memory architecture, implementation, schema, fixture or test; confirm dependencies before scope removal. |
| 132 | `tools/resumable_chat_import.py` | KEEP_CORE | Universal memory architecture, implementation, schema, fixture or test; confirm dependencies before scope removal. |
| 133 | `tools/temporal_memory_model.py` | KEEP_CORE | Universal memory architecture, implementation, schema, fixture or test; confirm dependencies before scope removal. |
| 134 | `tools/validate_memory.py` | KEEP_CORE | Universal memory architecture, implementation, schema, fixture or test; confirm dependencies before scope removal. |

Total: 134 paths. Updated status counts after bounded content review: REVIEW_MIXED=0, KEEP_AGMS=19, KEEP_CORE=52, KEEP_TRANSFERABLE_LESSON=4, SEPARATE_PROJECT_MEMORY=37, PRESERVE_RAW_OUT_OF_SCOPE=22.

## Safety

- This manifest does not authorize deleting files or merging PR #22.
- The older scope note's count of 39 is stale; current path-level decisions must use this live 134-path list.
- Project summaries and raw source history are different classes. Do not remove all project folders indiscriminately.
- `projects/B77_HTML_PWA/` describes B77's HTML/WMA contour and LK is the repository for the whole B77 project; Lite Cook is one simplified direction, while the APK direction was planned for later integration, not confirmed merged.
- After scope edits, fetch the exact branch HEAD, validate every preserved/excluded path, run repository checks, and confirm CI on the exact final SHA.