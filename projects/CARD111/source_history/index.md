# CARD111 source history index

- Original archive: `/conversations.zip`; SHA-256 `df7ffbe9a2ffcad27b5367af90d69c5cb38f17d61bb9f7a5207484e0343db956`; member `conversations.json` (37 conversation objects in this archive snapshot).
- Export manifest: `/export_manifest.json`; SHA-256 `2a945f37a3330bafd0f7aad2c6e9bbfbfa0d139107adfcd62811332a98b55e06`; 1374 export entries and 1374 logical entries.
- Asset name map: `/conversation_asset_file_names.json`; SHA-256 `056a3ffab3de1a96d74c0a8f4acdd9247cc026b011a820e9c78aa12d86a38059`; 876 mappings.

## Coverage

- Selected conversations: 6
- Messages with message objects: 2060
- Unique message IDs: 2060
- Message time span: 2026-10-05T10:42:43.484000Z — 2026-10-07T14:24:53.051577Z
- Attachment occurrences: 152; unique attachment IDs: 150; distinct mapped names: 128.

## Conversations

- **для скидкарт** — `6ac37f12-5b7c-83eb-bcee-b7cc20d48046`; 303 messages; 2026-10-05T10:42:43.484000Z — 2026-10-05T19:30:47.573007Z; `raw/conversations/6ac37f12-5b7c-83eb-bcee-b7cc20d48046.json`; scope: CARD111-focused.
- **Дубль два продолжение** — `6ac3c8f4-c55c-83ed-8f87-61017faf4c9d`; 863 messages; 2026-10-05T15:57:45.896000Z — 2026-10-06T11:45:38.341425Z; `raw/conversations/6ac3c8f4-c55c-83ed-8f87-61017faf4c9d.json`; scope: CARD111-focused.
- **Продолжение работы CARD111** — `6ac4e22f-1174-83ed-921f-467bf4a31b7d`; 419 messages; 2026-10-06T11:57:37.038382Z — 2026-10-07T09:52:02.063371Z; `raw/conversations/6ac4e22f-1174-83ed-921f-467bf4a31b7d.json`; scope: CARD111-focused.
- **Оценка T8 и STOP** — `6ac51760-2c30-83eb-9311-3f229c67f3ee`; 6 messages; 2026-10-06T15:44:54.066000Z — 2026-10-06T15:55:36.161518Z; `raw/conversations/6ac51760-2c30-83eb-9311-3f229c67f3ee.json`; scope: mixed-context; preserve as source but do not import unrelated project facts into CARD111 memory.
- **Приветствие unerquicklich** — `6ac51c82-4b70-83eb-a16b-b7085d95daeb`; 457 messages; 2026-10-06T16:06:30.610645Z — 2026-10-07T14:24:53.051577Z; `raw/conversations/6ac51c82-4b70-83eb-a16b-b7085d95daeb.json`; scope: mixed-context; preserve as source but do not import unrelated project facts into CARD111 memory.
- **Зафиксирован контекст CARD111** — `6ac613a6-d118-83ed-a2ea-b85f766a18ee`; 12 messages; 2026-10-07T09:40:59.886185Z — 2026-10-07T10:03:57.730795Z; `raw/conversations/6ac613a6-d118-83ed-a2ea-b85f766a18ee.json`; scope: CARD111-focused.

## Lookup

- Exact message ID: search `message_index.jsonl`, then open the conversation file and locate the matching `mapping` entry by `node_id` or `message.id`.
- Attachment: search `attachment_index.jsonl` by attachment ID/name. The export ZIP itself does not contain attachment bytes.
- Do not treat mixed-context source conversations as CARD111-only memory; keep unrelated project facts in their own project chain.

## Coverage boundary

This is the CARD111-related subset of the accessible archive snapshot, not proof that all CARD111 chats ever created are present. Other available Library files (screenshots, PDFs, HTML builds, and reports) are indexed separately by their actual Library paths; only files whose bytes can be safely retrieved and verified should be marked as copied to this repository.
