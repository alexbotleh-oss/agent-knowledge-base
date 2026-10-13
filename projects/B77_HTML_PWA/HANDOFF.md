# HANDOFF — B77_HTML_PWA

## Current purpose
Use the real history of Б77 HTML/PWA to learn from recurring failures and improve subsequent work. Do not treat this handoff task as permission to edit application code.

## Baseline and protected areas
- Repository: [alexbotleh-oss/LK](https://github.com/alexbotleh-oss/LK)
- Main application file: `stage14.html`
- Historical baseline: [e1eaf7c](https://github.com/alexbotleh-oss/LK/commit/e1eaf7cd20b1265f35a023c8c87db8b1994044f0)
- Pre-camera backup: [7e911a9](https://github.com/alexbotleh-oss/LK/commit/7e911a97dd95df6d08efb24b2eb39846efa0ce1c)
- WP backup: [6d9038e](https://github.com/alexbotleh-oss/LK/commit/6d9038eb0b37f53698074be7ea1a0dc3b1eb77eb)
- Historical scanner layer commit: [e29c156](https://github.com/alexbotleh-oss/LK/commit/e29c156544357ae998041d5f46c8571ffffba00f)
- Protected: Fix6/Flet, Stage14-WP working reference, Core/business logic.

## Work completed in this memory pass
- Added a partial project state.
- Reconstructed selected events from dated Git commits, the continuity report, and raw messages from the available 37-conversation archive.
- Restored nine B77 events that already existed in the narrative log but were missing from structured JSONL.
- Added five distinct B77 regression/recovery events from raw October 3–5 user messages: long-press/swipe/Light Cook regressions; Products/Shopping flow failures; category/sort/unit integrity; wrong recipe identity/context-menu regressions; and rollback blocked by a lost source file.
- Added source message IDs/timestamps where available and corrected the October 5 scanner baseline time from Git history.
- Added canonical B77 lessons B77-L-008/009/010; moved HTML-specific rules in RECIPE_MANAGER to explicit cross-project pointers instead of duplicate N99 lessons.
- The raw archive itself still contains only conversations.json; binary attachments and later October 12–13 primary messages are not included.
- No application files were changed by this learning pass.

## Next practical steps
1. Read the available RECIPE_MANAGER handoff and incident/lesson records from its own project chain.
2. Compare candidate lessons against actual evidence from both projects; retain separate event timelines.
3. For each candidate, label it as supported in B77 only, supported in both projects, disputed, or unknown.
4. Test the rules in the next real project iteration; record whether they prevent the previous failure.
5. Only after evidence supports generalization, promote lessons to shared/global memory with source links and applicability limits.

## Important unknowns
- The available raw archive includes 37 conversation objects through 2026-10-07, but not the full export or separate binary attachments; October 12–13 transfer notes are secondary sources.
- The precise technical reason for the Data Matrix rollback is not established by the commit titles alone.
- This handoff does not establish that every scanner feature is currently working on iPhone.
- The user's current report that the project is stopped due to recurring errors is authoritative as a project-status statement, but it does not identify a single technical root cause.
