# Source archive audit — 2026-10-12

## Input actually inspected
- User-provided file: `conversations.zip`, containing only `conversations.json` (uncompressed size about 43.0 MB).
- Parsed conversation objects: **37**.
- Distinct message IDs: **10,034** (7,446 assistant-role records and 2,588 user-role records in the mappings).
- User messages whose serialized text includes an attachment marker: **485**. These markers do **not** mean the binary attachment contents were included in this ZIP.
- Conversation creation timestamps span **2026-09-21 through 2026-10-07 UTC**; latest conversation update timestamp is 2026-10-07 UTC.
- The supplied ZIP does not include `chat.html`, `export_manifest.json`, `conversation_asset_file_names.json`, or the separate attachment assets shown in the user's Yandex Disk folder screenshot.

## What this changes
This is direct inspection of raw conversation JSON, not merely a prior summary. It improves provenance for the period covered by these 37 conversation objects. It does **not** establish that the entire ChatGPT export is represented: the user's folder showed many more export items, and the JSON alone does not include the separately stored attachment files. A previous note described an archive/search gap of 74 chats / 10,034 messages; this supplied artifact contains 37 conversation objects but the same 10,034 distinct message IDs. Treat the mismatch (37 vs 74 conversations) as **unresolved**, not as proof that either count is wrong or that the archive is complete.

## Project-boundary correction — authoritative user clarification
The user explicitly clarified in the active transfer task:
- **N99 / «Что приготовить» = the Android APK application.**
- **B77 / «Что приготовить» = a separate HTML/WMA prototype, UI/logic and web version intended for iPhone; its repository is `alexbotleh-oss/LK`.**

These are separate project identities despite the shared product name and overlapping recipe domain. Do not merge their code histories, release states, event IDs, or acceptance claims. The user’s explicit clarification is authoritative for project identity.

### Source-derived classification signals
- `Импорт рецептов Foodru` and `Сборка APK продолжается` contain explicit Android/Flet/APK build and runtime history (including the September 22–25 build sequence); classify that Android-specific material under **N99 / Android APK**.
- `Нормализация ингредиентов`, `Исправление логики продуктов`, `Восстановление файлов чата`, and `Обновление рецептов и покупок` contain HTML-file, HTML/SQLite database-path, recipe-list, nutrition, delete and shopping-list regression reports. These are **HTML-contour evidence** and must not be described as defects in the Android APK. The supplied text supports an HTML association; assigning every individual historical incident to B77 rather than an earlier HTML predecessor should retain provenance and uncertainty where the project label is absent.
- `Часть 2` and `Часть 3` explicitly discuss both N99 and B77 in the same conversation. These are mixed-scope source conversations and must be split by individual message/evidence, not assigned wholesale to one project.
- `Фиксация Stage14 WP` contains B77 / Stage14 continuity, baseline and scanner work linked to `alexbotleh-oss/LK`; keep it in B77.
- `для скидкарт`, `Продолжение работы CARD111`, and `Зафиксирован контекст CARD111` include separate CARD111 work. Do not fold it into either «Что приготовить» project merely because Android, HTML, QR or scanner techniques overlap.

## Chronology and evidence rules
1. Keep the original conversation title and message timestamp as provenance when creating or correcting events.
2. Do not use a conversation's latest update time as the event time for every message inside it.
3. Keep user-reported symptoms, assistant hypotheses, code changes, and verified runtime outcomes distinct.
4. A mention of HTML in a mixed conversation does not by itself prove that the item belongs to B77; use surrounding user messages, file names, repository links and Stage14 references.
5. Attachment placeholders in `conversations.json` are not a substitute for the original HTML, Python, SQLite, ZIP, screenshots or logs. Do not claim those artifacts were audited unless their bytes are supplied and inspected.
6. Do not alter `main` or merge PR #22 as part of this audit. Corrections belong on the existing draft consolidation branch pending review.

## Required reconciliation against the current rollup
- The current rollup labels RECIPE_MANAGER as “Flet/Android + historical HTML/SQLite” and includes an HTML regression event under `RECIPE_MANAGER`. That wording is now known to risk conflating N99 with B77. Review each HTML-specific event and move or cross-reference it only when source evidence establishes its project; otherwise mark it **HTML contour, exact project attribution unresolved**.
- B77's current event log starts with Stage14/scanner records around October 5, while the source JSON contains earlier HTML-specific recipe/SQLite incidents from September 22 onward. Evaluate these as possible earlier B77 history, but do not invent exact B77 attribution for entries lacking a project identifier.
- The archive supports a much stronger audit than the previous summary-only basis for the covered dates, but overall export completeness remains **PARTIAL**.

## Next audit steps
1. Reconcile each event in `projects/RECIPE_MANAGER/events.jsonl` against the actual user-message evidence, especially HTML/SQLite entries.
2. Review mixed N99/B77 conversations message-by-message and attach the original conversation ID/title/timestamp to each imported event.
3. Add earlier B77 HTML events only with explicit confidence and attribution notes.
4. Reconcile the 37-conversation count against the 74-chat note and inspect the export manifest / asset index and original attachments if supplied.
5. Re-run validation after any changes and confirm the exact PR head/CI result. Keep PR #22 draft and unmerged until the user explicitly authorizes merging.
