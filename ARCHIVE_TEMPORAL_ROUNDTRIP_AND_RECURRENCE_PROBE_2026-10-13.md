# Archive temporal index: first round-trip and recurrence probe — 2026-10-13

## Scope and privacy

A read-only index utility was run against the supplied local `conversations.zip`. The archive itself and its full conversation text were **not** uploaded to this repository. The utility preserves conversation IDs, message IDs, node IDs, UTC timestamps, roles, parent/child links, text parts, and an attachment-presence flag. It does not pretend image or attachment payloads are textual messages.

Utility: [`tools/archive_temporal_index.py`](./tools/archive_temporal_index.py)

## Observed archive coverage

- Conversation records: **37**
- Message nodes containing a message object: **10,034**
- Nodes with a numeric message timestamp: **10,034**
- Nodes with missing timestamps: **0**
- Nodes with textual parts: **4,597**
- Earliest message: **2026-09-21T11:06:33.535Z**
- Latest message: **2026-10-07T14:24:53.051Z**

These counts describe this particular archive snapshot only. They do not prove that the archive represents every conversation or all work performed after its export.

## Bidirectional round-trip test

Fixture was found by searching the distinctive phrase `нету строчки изготовлено в россии` in conversation **«Создание шаблона бирок Tkinter»**.

- Search result count: **1**
- Exact UTC timestamp returned: `2026-09-21T11:52:45.263Z`
- Message ID: `0515f703-9127-4afa-809b-d76a17addece`
- Conversation ID: `6ab10f7d-345c-83eb-b2d0-a72ba5777c51`
- Reverse lookup at that exact timestamp with a zero-minute window returned the **same message ID and conversation ID**.
- Context expansion followed actual parent/child node relationships and returned the nearby branch context.

Result: **PASS** for text → timestamp/IDs/context → exact timestamp → same message. This verifies the retrieval path on one real fixture, not the completeness of the whole memory.

## Initial recurrence probe (exploratory, not a verdict)

Simple case-insensitive substring probes returned:
- `чёрный экран`: **24 message hits across 9 conversations**
- `не работает`: **95 message hits across 20 conversations**
- `пропала`: **16 message hits across 11 conversations**

These are search candidates, **not counts of independent failures**. Results include assistant explanations, quoted text, follow-up discussions, and possibly duplicate descriptions. A second-stage review must group by underlying event, distinguish user-reported symptoms from assistant hypotheses and verified outcomes, then compare each event against existing memory entries.

## Next implementation step

Build a recurrence-audit layer that accepts a known memory-entry reason or failure signature and returns:
1. all matching source messages with timestamps and branch-aware context;
2. clustered candidate incidents (not raw keyword counts);
3. a coverage comparison against the memory journal;
4. proposed missing entries with source evidence and confidence;
5. a human-review status, with no automatic promotion of candidates into established memory.

Important: temporal proximity alone must not merge separate events, and repeated wording alone must not be treated as proof of repeated agent error.
