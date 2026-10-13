# Archive staging audit — Recipe Manager / «Что приготовить»

Date: 2026-10-13  
Status: **STAGED / PARTIAL** — source records generated locally; semantic migration is not complete.

## Source identity

- Original filename: `conversations.zip`
- Source archive ID: `RECIPE-MANAGER-CHAT-EXPORT-20261013`
- SHA-256: `df7ffbe9a2ffcad27b5367af90d69c5cb38f17d61bb9f7a5207484e0343db956`
- Size: 6,560,282 bytes
- Format: ZIP containing one `conversations.json`
- Parser: `source-registry-staging-v1`
- Original archive was read only; no content was changed.

## Observed coverage

- Conversation objects: **37**
- Message-bearing source nodes: **10,034**
- Nodes with non-empty extracted text: **5,131**
- Nodes with attachment markers: **466**
- Nodes missing source message IDs: **0**
- Source time range: **2026-09-21T11:06:33.535Z** to **2026-10-07T14:24:53.051Z**
- Source records SHA-256: `ac09f4e1ce37578c1a9309d2804b6f5666bb849f4aa907bfaf450530aba2307d`

## Generated local staging outputs

- `archive_snapshot.json` — source manifest and coverage limitations.
- `source_records.jsonl` — one stable source record per message-bearing node, including source IDs, node graph, timestamps, role, extracted text, text hash, attachment marker, and stable locator.

These outputs were generated locally under `/mnt/data/recipe_manager_memory_staging`. The source text and JSONL were **not committed to the public repository**.

## Known limitations

1. The source snapshot contains 37 conversations. The separate historical claim of 74 conversations is still unresolved; do not silently reconcile it to 37 or treat 74 as confirmed.
2. 466 nodes have attachment markers, but binary attachment payloads were not extracted or individually inspected in this staging run.
3. Structural extraction is not semantic extraction. Decisions, events, positive/negative experience, failures, fixes, and recurrence chains still require review and mapping to existing project records.
4. The source archive's completeness relative to all historical chats is **PARTIAL/UNKNOWN**, not complete.
5. The source records are derived, reproducible staging data. Stable locators use archive ID + conversation ID + node ID, not line numbers or array positions.

## Next required stage

1. Compare staged source records against the existing `RECIPE_MANAGER` events, lessons, decisions, state, and handoffs.
2. Extract candidates with source locators and independent evidence statuses.
3. Reconcile candidate duplicates and separate recurring incidents from repeated wording.
4. Produce a coverage matrix: covered / partly covered / missing / disputed.
5. Add only reviewed semantic records and safe provenance to the repository; preserve RAW locally.
6. Run local unit tests and verify the GitHub Actions result on the final commit before claiming PASS.
