# Bidirectional temporal-context retrieval — archive evidence and memory design — 2026-10-13

## Evidence inspected directly

The available Library artifact `conversations.zip` was materialized and inspected as data, not inferred from its filename.

- ZIP contains one `conversations.json` file.
- The JSON parses to 37 conversation objects.
- Every conversation object has `create_time` and `update_time` in the inspected sample/schema.
- Each conversation has a `mapping` of nodes. The examined export contains 10,034 message objects with numeric `create_time` values.
- Message-level `create_time` is Unix epoch seconds and can be converted to UTC. Message objects also retain conversation identity, node/message IDs, parent/child links in the mapping, author/role, content parts, and metadata.
- Observed message-time range in this ZIP: 2026-09-21T11:06:33.535Z through 2026-10-07T14:24:53.051577Z.
- Conversation `create_time` and `update_time` are also present. The archive is therefore not merely an untimed text dump: it contains data suitable for temporal indexing and reverse lookup.
- The ZIP's 37 conversation objects and 10,034 timed message objects describe this particular exported snapshot. They do not by themselves define the scope or cutoff of the separate historical “74 conversations” statement.

## Correction to the prior workflow

Do not stop at saying that snapshot timestamps are needed, and do not assume they are absent before inspecting the archive schema. The archive contains message-level timestamps and structural links that can be used to reconstruct event context and navigate in both directions.

The current task is to exploit those fields and test the extraction/retrieval approach, not to ask the user to re-explain the principle.

## Required bidirectional retrieval modes

### A. Context → time (forward temporal grounding)

Given an event, decision, error, user requirement, or distinctive phrase:
1. Search exact terms, variants, entity names, IDs, quoted code/error text, and semantic paraphrases in message content.
2. Return the matching original message(s), not only a summary.
3. Resolve conversation ID/title, message ID, author/role, message `create_time`, and nearest preceding/following messages through the conversation mapping.
4. Reconstruct the local exchange window and relevant branch/parent chain; distinguish the time the event was discussed from the time an artifact or decision actually took place.
5. Follow references to files, screenshots, commits, builds, or other event IDs to corroborate the claim.
6. Store the result as a provenance-bearing assertion with exact source anchors and confidence, preserving alternate matches when ambiguous.

### B. Time → context (reverse temporal retrieval)

Given an exact timestamp, approximate interval, or event date:
1. Convert input time to a normalized timezone-aware interval; retain the original timezone and precision.
2. Search message timestamps in the interval with configurable before/after margins.
3. Group hits by conversation, then order them using message timestamps and mapping parent/child links rather than import order.
4. Retrieve surrounding context and branch alternatives, not just the single message at the target second.
5. Search within that window for entities, files, IDs, decisions, errors, actions, and results; connect these to other conversations that refer to the same objects.
6. Report the observed timestamp, the inferred event-time interval (if different), and any uncertainty separately.

### C. Event/claim ↔ multiple temporal sources

For every significant event, preserve separately:
- `event_time`: when the underlying event happened (may be an interval or unknown).
- `source_time`: timestamp of the original message/document containing the evidence.
- `recorded_at`: when this assertion was added to the memory system.
- `snapshot_time` / `snapshot_interval`: when the source collection was exported/captured, where known.
- `received_at`: when the memory system obtained the source.
- `valid_time`: interval during which a claim is considered applicable, if different from when it was recorded.
- timezone, timestamp precision, and the basis for each time.
Never silently substitute one time for another.

## Reverse / inverse methods that must exist

- **Backward causal trace:** start from a current conclusion or failure and traverse to the decisions, hypotheses, actions, messages, artifacts, and earlier evidence that produced it.
- **Forward impact trace:** start from a corrected or newly corroborated source assertion and locate every downstream summary, lesson, project state, decision, and handoff that depends on it.
- **Nearest-context expansion:** start from a matching message and expand backward/forward by message sequence, timestamp, and reply graph until the relevant exchange is reconstructed.
- **Temporal diff:** compare “what memory believed at cutoff T1” with “what memory believed at cutoff T2”, including added, refined, contradicted, superseded, and newly linked claims.
- **Counterfactual/negative lookup:** for a claimed event, search for expected evidence around the claimed time and report what was/wasn't found in the inspected sources. Absence from one partial archive is not proof the event never occurred.
- **Cross-source triangulation:** connect message timestamps with Git commits, file modification/build timestamps, CI runs, screenshots, and user-reported times while preserving source-specific clocks and timezone uncertainty.
- **Ambiguity resolution:** when multiple events match, rank by content, entity/ID overlap, local context, and temporal proximity; do not collapse candidates until a primary anchor distinguishes them.

## Minimal test plan

1. **Context-to-time fixture:** choose a distinctive message in the archive, find it by content, and recover its exact `create_time`, conversation, role, message ID, and surrounding exchange.
2. **Time-to-context fixture:** use that exact timestamp as input and recover the same message plus its neighboring context.
3. **Round-trip invariant:** content → timestamp → temporal query must return the original message ID and conversation ID.
4. **Parent/branch fixture:** test a conversation with branching/edited nodes; demonstrate why chronological sorting alone is insufficient.
5. **Timezone fixture:** verify UTC epoch conversion and display in another timezone without altering the stored instant.
6. **Snapshot-scope fixture:** compare a known archive cutoff with later-added chat records; counts from different snapshots must not be called contradictory until their units and scopes are aligned.
7. **Impact fixture:** revise one source claim and verify that all dependent summaries/lessons are discoverable for review.
8. **Partial-source fixture:** ensure “not found in this archive” remains distinct from “did not happen”.

## Immediate implementation sequence

1. Build a small read-only parser/indexer for the current archive; preserve the original ZIP and record its hash.
2. Produce an index of conversation ID/title/create/update times and message ID/time/role/content reference/parent-child relationships.
3. Add reverse lookup by exact phrase/entity and by time interval.
4. Run the round-trip tests above and record exact outputs and known limits.
5. Only after those tests pass, use the index to reconcile specific event claims and snapshots. Do not bulk-rewrite canonical memory based on untested matching.

## Status and boundaries

- Archive timestamp fields: directly observed in the inspected export.
- Bidirectional retrieval/indexer: required capability; not yet implemented or tested in the repository.
- 37-vs-74: chronology and scope explanation is plausible given user-provided archive dates and ongoing development, but exact membership of the 74-count set is not established by this ZIP alone.
- Memory-system work only. No application source, database, or APK changes.
- Keep N99 / RECIPE_MANAGER, B77_HTML_PWA, CARD111, and ORGANISM as distinct project chains.
- PR #22 remains open/Draft/unmerged until the user explicitly authorizes merge.
