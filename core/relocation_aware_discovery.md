# Relocation-aware source discovery

## Purpose

A failed lookup at an expected address is a location discrepancy, not proof that the information is absent. This protocol requires a bounded search across explicitly known locations before concluding that a source is missing.

## Retrieval sequence

1. **Resolve the expected address.** Check the canonical path or index entry and record whether it exists and whether its identity matches.
2. **Search by identity before wording.** Prefer exact source SHA-256, stable memory/source/event ID, archive/conversation/message identity, or another stable locator. Text search is a fallback for candidate discovery, not identity proof.
3. **Search alternate known locations.** Use explicit roots and known registries, project state/handoff files, source manifests, archive inventories, and versioned branches/revisions where the caller has access. Never silently broaden scope to unrelated or private locations.
4. **Classify the result.**
   - \`FOUND_AT_EXPECTED_PATH\`: identity evidence is present at the expected path.
   - \`FOUND_ELSEWHERE_IDENTITY_MATCH\`: matching identity evidence exists elsewhere; verify provenance and intended canonical location.
   - \`CANDIDATES_UNVERIFIED\`: text candidates exist, but identity is not established.
   - \`NOT_FOUND_WITHIN_SEARCH_SCOPE\`: no match in the completely scanned configured scope; this is not proof of global absence.
   - \`SEARCH_INCOMPLETE\`: limits, unreadable files, unavailable roots, stale indexes, or skipped payloads prevent a reliable negative conclusion.
5. **Reconcile, do not silently relocate.** If the item is found elsewhere, preserve its source, version, hash, provenance, and links. Determine whether the correct repair is to restore the item, update a stale pointer, or record an intentional move. Never move, overwrite, delete, promote, or rewrite canonical memory automatically as a side effect of discovery.
6. **Close the loop.** After an authorized repair, read back the changed location/pointer, verify the identity and provenance, rebuild/check affected indexes, and record the outcome and any unresolved conflict.

## Identity and confidence

Evidence strength, from strongest to weakest:
1. Exact byte hash bound to the expected source snapshot.
2. Stable unique source/record ID present in its declared identity field, with consistent provenance; a textual mention alone is only a candidate.
3. Exact composite identity (for example archive + conversation + message ID).
4. Exact textual match with corroborating metadata.
5. Lexical or semantic similarity alone.

Similarity may suggest where to look; it cannot establish that two records are the same. Conflicting versions remain visible until reconciled.

## Current implementation boundary

\`tools/relocation_aware_discovery.py\` is a read-only, bounded local filesystem discovery primitive. It accepts explicit search roots, checks the expected path first, searches for a stable identity/hash before using normalized text, reports incomplete coverage, and performs no writes or relocation.

It is called by \`tools/memory_aware_session_restore.py\` when approved semantic retrieval returns \`PARTIAL_NO_MATCH\`, using available task/context IDs and/or a text query. Its results remain separate from approved memory and never promote a candidate automatically.

For source ordering across multiple known local locations, \`tools/adaptive_source_search.py\` adds capability-aware tiers: known-compatible sources first, sources with unknown metadata second, and known-conflicting sources only as an emergency fallback. It keeps expanding after text-only candidates and stops early only on verified identity/hash evidence.

Neither tool is automatically invoked by ChatGPT merely because the files exist in the repository. The memory-aware restore command must actually run. Remote GitHub branches, connected apps, device storage, and arbitrary external archives still require dedicated source adapters and runtime integration.

## Acceptance tests

- An expected path is missing but a stable identity is found in another known location.
- An exact hash identifies a moved byte-identical source.
- Text-only candidates are labelled unverified.
- A complete bounded no-match is scoped, never described as global absence.
- File/size/access limits produce \`SEARCH_INCOMPLETE\`.
- Discovery is read-only and never changes source records or canonical pointers.
