# PR #22 mixed-path review — 2026-10-14

Scope: bounded content review of the eight rows initially marked REVIEW_MIXED in `PR22_PATH_DISPOSITION_MANIFEST_2026-10-14.md`. This is a content-based disposition, not authorization to delete source records or merge PR #22.

## Decisions and evidence boundary

| Path | Decision | Basis |
|---|---|---|
| `ARCHIVE_TEMPORAL_ROUNDTRIP_AND_RECURRENCE_PROBE_2026-10-13.md` | KEEP_AGMS | Temporal round-trip fixture and recurrence probe; probe candidates are not independent incident counts. |
| `BIDIRECTIONAL_TEMPORAL_CONTEXT_RETRIEVAL_2026-10-13.md` | KEEP_AGMS | Memory-system design for temporal retrieval, lineage, causal/impact traces and tests; design is not proof of full implementation. |
| `MEMORY_ARCHITECTURE_GAP_EVOLVING_KNOWLEDGE_2026-10-13.md` | KEEP_AGMS | Direct analysis of evolving-memory gaps and missing end-to-end integration. |
| `SOURCE_RECONCILIATION_APK_BUILD_2026-10-13.md` | PRESERVE_RAW_OUT_OF_SCOPE | Primary subject is RECIPE_MANAGER/N99 APK history. Full copy now preserved at `projects/RECIPE_MANAGER/source_history/SOURCE_RECONCILIATION_APK_BUILD_2026-10-13.md`. Distinct reported build attempts remain separate; APK/hash/log/runtime were not verified for the 144 MB claim. |
| `SOURCE_RECONCILIATION_B77_HTML_REGRESSIONS_2026-10-13.md` | PRESERVE_RAW_OUT_OF_SCOPE | Primary subject is B77 HTML/SQLite regression history. Full copy now preserved at `projects/B77_HTML_PWA/source_history/SOURCE_RECONCILIATION_B77_HTML_REGRESSIONS_2026-10-13.md`. Event-level match exists, but primary messages and original HTML/SQLite artifacts were not reopened. |
| `SOURCE_REPORTS_AUDIT_2026-10-13.md` | KEEP_AGMS | Directly documents source-to-memory audit methodology: copied report text vs incidents, nonchronological report ordering, evidence grades, bounded source coverage and structural vs semantic completeness. Keep limitations explicit. |
| `UNIFIED_MEMORY_REGISTRY_AND_SAFE_ENRICHMENT_2026-10-13.md` | KEEP_AGMS | Direct memory architecture for snapshots, provenance, lineage, staging, idempotence, retrieval and integrity; no claim that runtime integration is complete. |
| `lessons/cross_project_review_20261012.md` | KEEP_TRANSFERABLE_LESSON | Keep only the explicitly scoped general prevention lesson; retain project-specific event details in the separate project memories. |

## Preservation and safety

- Two project-specific reconciliation reports were copied byte-for-byte from their root paths into the corresponding project `source_history/` folders on the preservation branch.
- The root copies remain intact. No deletion or exclusion from PR #22 has been performed by this review.
- This branch is a preservation/reconciliation branch, not a cleaned PR head. Before scope-cleaning PR #22, verify destination copies by readback and hash/length equality, inspect all references/dependencies, then create a separate reviewable candidate.
- CI is not verified for the latest preservation-branch HEAD. The previously reported passing run on PR head `52ff4df...` does not establish validation of this branch's later commits.
- Do not merge PR #22 without explicit user approval.
