# Audit of text-focused ChatGPT transfer archive — 2026-10-17

## Status

**Raw-source audit: PASS for the received transfer ZIP's internal structure and included-member integrity. Overall historical coverage: PARTIAL.** This record documents a derived transfer archive, not a claim that the user's entire ChatGPT history is present or that semantic memory promotion is complete.

## Provenance chain

- Original filename reported by the user's local inventory: `archive_gpt.zip`.
- Original archive size: `147411310` bytes.
- Original archive SHA-256, recorded by the local inventory and repeated in the transfer manifest: `2facd72232a4d7c4a04e24e4db7faef3624822c44dae5a5d75f39ddf219f7ec5`.
- Original ZIP CRC: PASS according to the user's locally generated inventory report; the original 147 MB ZIP itself was not uploaded to this review.
- Derived file received here: `AGENT_HISTORY_TRANSFER.zip`, size `12439840` bytes, SHA-256 `63fd0ffd62dc547fd032d16ce52fbdb6a6ba028a2c8188028e2fc5726ede8685`.
- Derived ZIP CRC: PASS on independent read-back.
- The derived ZIP contains 10 source members plus `TRANSFER_MANIFEST.json`. SHA-256 and uncompressed byte counts for all 10 included source members match their manifest entries.
- The transfer manifest records that the original source was not modified. This claim is consistent with the user's local run output, but cannot be independently proven without the original ZIP.

## Included source members

The transfer archive preserves these source members without semantic rewriting:

- `conversations.json` — raw conversation objects and message mappings.
- `chat.html` — HTML export representation.
- `conversation_asset_file_names.json` — attachment filename map.
- `library_files.json` — ChatGPT Library file metadata.
- `export_manifest.json` and `sites/export_manifest.json` — export inventories/manifests.
- `ads.json`, `message_feedback.json`, `sectioned_conversations.json`, `user_settings.json`.

The derived archive additionally contains `TRANSFER_MANIFEST.json`, with source provenance, included-member hashes, excluded-member paths/sizes/reasons, and structural estimates.

## Conversation-structure findings

Direct parsing of `conversations.json` from the received transfer archive established:

- 37 conversation objects.
- 10,071 mapping nodes.
- 10,034 nodes containing message objects with distinct message IDs; no duplicate message IDs were observed.
- 7,446 assistant-role messages and 2,588 user-role messages.
- 37 mapping nodes have no message object. This explains why a structural node count (10,071) differs from the actual message-object count (10,034); do not label both as message counts.
- Conversation creation timestamps span 2026-09-21 through 2026-10-07 UTC; latest conversation update is 2026-10-07 UTC.

These are counts within this export, not proof that the export contains every conversation the user intended to preserve. A previously recorded “74 chats” claim remains unresolved and must not be substituted for the 37 conversations verified here.

## Excluded attachment payloads

- 1,364 `.dat` members were excluded.
- `user.json` was excluded because it contains account-identifying fields.
- Total excluded source members: 1,365.
- `conversation_asset_file_names.json` has 876 filename mappings. All 876 mapped keys refer to excluded `.dat` members; 488 additional `.dat` members have no friendly-name entry in this map.
- The filename map shows that `.dat` payloads are not necessarily images: mapped examples include JPG/PNG images, DOCX documents, and an HTML file. The user's stated policy was to omit attachments, so the payloads remain excluded; however, they were not content-sniffed or individually classified before exclusion.
- Conversation-level attachment pointers and the filename map remain in the text archive, but pointers to excluded bytes are references only and do not restore the attachment contents.

## Library-reference limitation

- `library_files.json` contains 1,583 metadata records.
- No direct HTTP(S) URLs were present in the inspected Library metadata records.
- Therefore the archive preserves available file IDs, names, metadata, and conversation/message provenance, but it does **not** provide a verified clickable web URL for every Library item. Do not invent URLs from IDs. Where an actual link exists in conversation text, preserve that source text verbatim.

## What is and is not verified

Verified:
- The received derived ZIP opens and passes CRC.
- All 10 included source-member byte lengths and SHA-256 hashes match `TRANSFER_MANIFEST.json`.
- The raw conversation JSON parses and the structural counts above are reproducible.
- The original-source SHA-256 recorded by the local inventory matches the source SHA-256 embedded in the transfer manifest.

Not verified:
- Byte-for-byte comparison of included members against the original ZIP, because the original ZIP was not uploaded.
- Integrity or content type of the excluded `.dat` bytes, because they are not in the derived archive and the original was not available here.
- Whether the export contains all conversations, missing final messages, or all Library content the user intended to preserve.
- Whether every attachment pointer resolves to an accessible Library item.
- Semantic promotion of the 37 conversations into canonical project memory, or full chronology reconciliation against later chats and Git history.

## Next step

Use this derived archive as a **partial raw source**. Preserve its source SHA, transfer SHA, source conversation IDs, per-message IDs/timestamps, and attachment omissions as provenance. Process mixed-scope conversations message by message; do not assign a whole conversation to one project merely from its title. Keep the 2026-10-07 export cutoff distinct from later messages and repository events. Do not merge any PR or change `main` as part of this audit.
