# Чистая интеграция ядра памяти — 2026-10-15

**Статус:** draft integration; no merge.  
**Base:** `main` at `a0c12ba849a3416f50e1289d8f0dd20844e1e51f`.  
**Reviewed source revisions:** PR #25 `efd5de131be5c037373c8a61a6a5dbc02d2d8c1c`; PR #26 `a7860d6562ba2078b636a69db6e3fb934e658c89`.

## Why this branch exists

PR #25 and PR #26 are stacked on a preservation branch rather than directly on `main`. The preservation branch is 567 commits ahead of `main`; PR #25's base branch is 684 commits ahead of `main`. A direct merge would therefore carry a broad history and project-specific paths from PR #22, not just the memory mechanisms reviewed in PR #25/#26.

This branch is created from the verified `main` HEAD and selectively ports core protocols, tools, schemas, tests, AGENT_MEMORY_SYSTEM state and transferable lessons. It does not modify `main` or merge any PR.

## Included

- Existing core protocols updated with source-ingestion, scope, provenance and unified memory-loop rules.
- Memory tools from PR #25/#26, including resumable raw import, message-level staging, temporal indexing, intake planning, restore/context/trust gates, guarded checkpoint updates, branch-result registry and candidate retrieval.
- Schemas, examples, synthetic intake fixtures, regression tests and the AGMS-specific task/handoff/audit context.
- General lessons whose source and cross-project applicability are explicitly represented.

## Intentionally excluded

- Full project-specific histories for B77_HTML_PWA, CARD111, ORGANISM and RECIPE_MANAGER.
- Raw conversation JSON payloads and supplementary source-history artifacts.
- These are not deleted: they remain on the preserved reconciliation branch for separate review and project-scoped integration. The historical path manifest is retained as a disposition record, not as a deletion instruction.

## Corrections made in this integration candidate

1. Branch-result publication now rejects a caller-supplied `project_id` other than `AGENT_MEMORY_SYSTEM` and writes the canonical project ID rather than trusting the payload.
2. Intake validation for `event_records` now requires the same core fields as the existing event template: `event_id`, `project_id`, `type`, `summary`, `status`, `evidence`, `confidence`.
3. Project-boundary tests use synthetic fixtures when full project histories are intentionally absent; if all project logs are later integrated, the same checks run against those real files. Legacy timestamp/evidence compatibility remains tested with synthetic records.

## Confirmed remaining integration gaps

- `tools/plan_memory_intake.py` routes `source_records` to the logical operation `source_evidence_registry.append_source_records`, but `tools/source_evidence_registry.py` does not exist.
- `archive_registry_staging.py` writes `archive_snapshot.json` and message-level source records; this is not the `manifest.json` contract consumed by the intake validator. No adapter connects them.
- The raw SQLite importer, message-level staging, temporal index, intake planner, canonical promotion, derived index refresh, branch-result publication and next-session restore are not yet connected as one tested end-to-end path.
- The write-contract audit is a partial static inventory and CI currently runs it without `--strict`.
- Six raw conversation JSON payloads (about 4.7 MB total) are accessible from the public PR #22 branch. This integration branch excludes them. No deletion or history rewrite has been attempted; a commit deleting files would not by itself remove older reachable blobs from public history. Repository visibility/history cleanup needs a separate deliberate decision if those payloads were not intended to be public.

## Verification status

CI has not yet run on this new clean integration HEAD. Do not treat the source PRs' green CI as proof that this curated tree passes. The next step is exact-HEAD CI, followed by focused end-to-end intake integration and regression tests.