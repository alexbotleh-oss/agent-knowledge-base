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
- adaptive_source_search.py: orders configured local roots by known compatibility, unknown metadata, and known conflict. It is not yet invoked by session restore or the pipeline coordinator.
- audit_memory_architecture.py: read-only static audit of Python tool imports, statically declared storage paths, and expected protocol locations. It reports evidence, not runtime call coverage.

## 4. Important gaps and status

1. No single executable source catalog is yet the authority for all locations. The adaptive search requires an explicitly supplied catalog; it currently covers local roots only.
2. The adaptive search is not yet composed into the normal restore path. Its existence and CI success do not mean it runs during every task or session start.
3. Remote branches, GitHub file history, connected apps, device storage, and external archives need separate adapters. Each adapter must report access, coverage, revision/freshness, stable identity and provenance.
4. Session-start execution is not automatic in ChatGPT. Repository instructions and Python tools require an actual caller/runtime.
5. Search ranking is currently limited. Approved-memory retrieval uses exact project/task/context filters and lexical substring; archive temporal search is a separate tool. A unified planner should route among them instead of assuming one index contains everything.
6. Ingestion has distinct stopping points. The source ingestion runner alone stops at metadata-only source registration. The broader pipeline coordinator can continue through semantic promotion/index/restore only with the required manifests, approval receipt and inputs.
7. The path core/agent_bootstrap.md is not present in the audited branch tree. This is a repository-local discrepancy, not proof that no bootstrap instructions exist in another branch or source. The active README instead points to core/universal_instructions.md and core/agent_runtime_protocol.md; search other known revisions before deciding whether to add, restore or update a pointer.

## 5. Next implementation sequence

1. Run python tools/audit_memory_architecture.py on the checked-out target revision; retain its JSON output as evidence when needed.
2. Define a versioned source catalog over existing stores and tools; do not duplicate the source registry or semantic-memory registry.
3. Add explicit adapters for local checkout and remote GitHub branch/revision retrieval, preserving branch SHA and file SHA.
4. Compose the planner into memory_aware_session_restore.py behind an explicit catalog argument/configuration, with current behavior unchanged when no catalog is supplied.
5. Add end-to-end tests for: expected path missing but same source found on another branch; a compatible source searched before a conflicting source; unknown metadata fallback; stale remote refs; incomplete permissions/coverage; conflicting revisions; and no silent move/promotion.
6. Only after those tests pass, evaluate whether the actual session/runtime can call the restore mechanism. Do not describe repository code as automatic ChatGPT behavior without an end-to-end runtime test.

## 6. Evidence discipline

- Static import edge = code dependency evidence, not proof the imported function is reached at runtime.
- A configured path = declared location, not proof that bytes exist in every runtime.
- CI success = repository checks passed at a specific SHA, not proof that the current ChatGPT session used the code.
- NOT_FOUND_WITHIN_SEARCH_SCOPE applies only to the scanned roots/revision and bounds.
- When a path is absent, inspect other known branches/revisions and aliases before concluding global absence.
