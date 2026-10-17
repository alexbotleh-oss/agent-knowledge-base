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
2. Stable unique source/record ID with consistent provenance.
3. Exact composite identity (for example archive + conversation + message ID).
4. Exact textual match with corroborating metadata.
5. Lexical or semantic similarity alone.

Similarity may suggest where to look; it cannot establish that two records are the same. Conflicting versions remain visible until reconciled.

## Current implementation boundary

\`tools/relocation_aware_discovery.py\` is a read-only, bounded local filesystem discovery primitive. It accepts explicit search roots, checks the expected path first, searches for a stable identity/hash before using normalized text, reports incomplete coverage, and performs no writes or relocation.

It does **not** yet query GitHub branches, external connectors, device storage, or arbitrary archives automatically. It is not automatically invoked by ChatGPT merely because the file exists in this repository. Runtime integration must explicitly call it or compose equivalent retrieval across those sources. The existing semantic-memory restore also returns \`PARTIAL_NO_MATCH\` for a zero-result partial index; that must trigger this discovery sequence before a broader absence claim is made.

## Acceptance tests

- An expected path is missing but a stable identity is found in another known location.
- An exact hash identifies a moved byte-identical source.
- Text-only candidates are labelled unverified.
- A complete bounded no-match is scoped, never described as global absence.
- File/size/access limits produce \`SEARCH_INCOMPLETE\`.
- Discovery is read-only and never changes source records or canonical pointers.
