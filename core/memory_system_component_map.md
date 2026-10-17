# Memory system component map

Status: repository-derived architecture map. This document distinguishes implemented code paths from proposed or not-yet-connected behavior. It must be refreshed after material changes; the audit tool can regenerate the evidence inventory.

## 1. Current canonical flow

~~~text
Immutable export / archive
  -> tools/archive_registry_staging.py
  -> staging inventory + source snapshot metadata
  -> tools/adapt_archive_staging_to_intake.py
  -> validated intake manifest + candidate artifacts
  -> tools/plan_memory_intake.py
  -> route proposal (dry run; not every route has a writer)
  -> tools/source_ingestion_runner.py
  -> registry/source_records.jsonl (metadata-only source registry)
  -> separately prepared, reviewed semantic-memory manifest + approval receipt
  -> tools/semantic_memory_registry.py
  -> registry/memory_records.jsonl (accepted semantic memory)
  -> tools/canonical_memory_index.py
  -> registry/memory_index/ (derived generations + CURRENT pointer)
  -> tools/memory_aware_session_restore.py
  -> verified task/session packet + approved memory retrieval
~~~

The coordinator tools/memory_pipeline_coordinator.py composes source ingestion, provenance-link validation, approved semantic promotion, optional correction registration, index refresh and a fresh memory-aware restore. Its CLI is a controlled workflow, not an automatic ChatGPT session-start hook.

## 2. Stores and their distinct jobs

| Store / artifact | Role | Do not confuse it with |
|---|---|---|
| Immutable RAW archive/snapshot | Original evidence and snapshot identity | Extracted records or approved memory |
| Staging inventory and intake manifest | Coverage, hashes, parser/version metadata, proposed artifact routing | Proof that all payloads/attachments were inspected |
| registry/source_records.jsonl | Source locators, source/parser hashes, timestamps, message/node edges, attachment-presence metadata | Semantic memory; it deliberately has no message text or project assignment |
| registry/memory_records.jsonl | Accepted, revisioned semantic memory with provenance and approval evidence | Raw source registry or derived index |
| registry/edge_corrections.jsonl | Explicit correction/retraction overlay for relationships | Silent rewrite of append-only event history |
| registry/memory_index/ | Rebuildable multidimensional retrieval projection | Authority independent of the canonical registry |
| Archive temporal index output | Read-only search/timeline view of a ChatGPT export | Canonical semantic memory |
| projects/AGENT_MEMORY_SYSTEM/{TASK_STATE,HANDOFF,EVENT_LOG}.md and related event files | Current task checkpoint, handoff, and project chronology | Universal memory index or automatic runtime state |

## 3. Main code responsibilities

- archive_registry_staging.py: reads export bytes locally and builds metadata staging; does not upload source text.
- adapt_archive_staging_to_intake.py + validate_memory.py: map staging into a validated intake batch and validate contracts.
- plan_memory_intake.py: maps artifact kinds to logical destinations; the plan is read-only and some routes remain unimplemented.
- source_evidence_registry.py + source_registry_contract.py: validate and append metadata-only source records with stable source identity and replay handling.
- semantic_memory_registry.py: guarded promotion of hash-bound, explicitly approved semantic records; this is a distinct authorization step.
- edge_correction_registry.py: records authorized relationship corrections/retractions without erasing original history.
- canonical_memory_index.py: validates the canonical semantic registry and creates versioned multidimensional index generations.
- archive_temporal_index.py: searches a source export by chronology and text; useful for evidence retrieval, but not a replacement for canonical memory.
- verified_session_restore.py: checks live GitHub revision/CI evidence and assembles a source-backed task restore packet.
- memory_aware_session_restore.py: combines verified task recovery with freshness-checked approved-memory retrieval; its retrieval is exact multidimensional filtering plus lexical substring matching, not embedding-based semantic ranking.
- memory_pipeline_coordinator.py: composes the guarded import/promotion/correction/index/restore stages when explicitly run.
- relocation_aware_discovery.py: bounded, read-only discovery in explicitly supplied local roots when the expected location misses.
- adaptive_source_search.py: orders configured local roots by known compatibility, unknown metadata, and known conflict. It is called by memory_aware_session_restore.py after PARTIAL_NO_MATCH when the local source catalog is available. The GitHub adapter github_source_discovery.py separately searches the bounded remote catalog; the restore fallback routes only semantic_memory and event_history source profiles, not protocol/bootstrap sources. Neither path runs automatically at ChatGPT session start.
- audit_memory_architecture.py: read-only static audit of Python tool imports, statically declared storage paths, and expected protocol locations. It reports evidence, not runtime call coverage.

## 4. Important gaps and status

1. The versioned local catalog registry/source_catalog.json covers the current checkout's registry, AGENT_MEMORY_SYSTEM project files, core protocols, tools, and tests. It is not a global authority for all locations; it omits remote branches, external archives, connected apps and device storage.
2. The local adaptive search and bounded remote GitHub adapter are both composed into the partial-index fallback in memory_aware_session_restore.py. They run only when approved-memory retrieval returns PARTIAL_NO_MATCH and the restore function is actually invoked. They are not automatically executed by ChatGPT at the start of every task.
3. The GitHub adapter covers explicit refs/paths in `registry/remote_source_catalog.json`; it does not enumerate every branch or scan arbitrary remote paths. It preserves commit/blob/content identity, rechecks branch heads on a verified match, and marks denied/incomplete/stale-ref results as SEARCH_INCOMPLETE. Source routing is capability-aware: semantic memory and event history are eligible for the memory fallback; protocol/bootstrap is not. Git history beyond configured refs, connected apps, device storage, and external archives still need separate adapters.
4. Search ranking is currently limited. Approved-memory retrieval uses exact project/task/context filters and lexical substring; archive temporal search is a separate tool. A unified planner should route among them instead of assuming one index contains everything.
5. Ingestion has distinct stopping points. The source ingestion runner alone stops at metadata-only source registration. The broader pipeline coordinator can continue through semantic promotion/index/restore only with the required manifests, approval receipt and inputs.
6. The path core/agent_bootstrap.md is absent from main (HEAD a0c12ba849a3416f50e1289d8f0dd20844e1e51f), integration/memory-core-clean-20261015, and the current feature branch, but it is present on the separate open Draft PR #33 branch fix/identity-continuity-contract-20261017 (HEAD 82ce508c6b77f6060e4674ecfe24830b61eb27c6; exact-head CI run 39012907765 SUCCESS). This is a branch-location discrepancy, not global absence. PR #33 is based on main and is not part of the current #27/#34/#35 stack. Its global instruction points to a feature-branch URL; after deliberate integration, replace that with a stable canonical ref. Do not create a duplicate bootstrap file on #35.

## 5. Next implementation sequence

1. Run python tools/audit_memory_architecture.py on the checked-out target revision; retain its JSON output as evidence when needed.
2. Extend the versioned source catalog with verified branch-head snapshots and explicit stale-ref/conflicting-revision reporting; keep the registry distinct from semantic-memory/source registries.
3. Add cross-path tests for multiple conflicting revisions, catalog-head drift, and partial access across all configured source types.
4. Extend the bounded catalog only through a maintained source registry with aliases and per-source capabilities; do not enumerate arbitrary refs without limits.
5. Add adapters for external archives, connected apps and device storage, each with explicit access/coverage/provenance contracts.
6. Only after those adapters are tested, evaluate whether the actual session/runtime can call the restore mechanism. Do not describe repository code as automatic ChatGPT behavior without an end-to-end runtime test.

## 6. Evidence discipline

- Static import edge = code dependency evidence, not proof the imported function is reached at runtime.
- A configured path = declared location, not proof that bytes exist in every runtime.
- CI success = repository checks passed at a specific SHA, not proof that the current ChatGPT session used the code.
- NOT_FOUND_WITHIN_SEARCH_SCOPE applies only to the scanned roots/revision and bounds.
- When a path is absent, inspect other known branches/revisions and aliases before concluding global absence.
