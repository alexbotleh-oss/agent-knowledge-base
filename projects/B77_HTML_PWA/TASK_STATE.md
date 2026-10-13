# TASK_STATE — B77-LEARN-FROM-REAL-INCIDENTS-20261012

- **Current task:** turn the available B77 HTML/PWA history into actionable lessons that reduce repeated errors across project work.
- **User's priority:** stop debating the memory system in the abstract; use real project experience. Some history may be missing, but addition/recording time must never be mistaken for the actual order of events.
- **Desired outcome:** capture the verified chronology, failed approaches, rollbacks, preserved baselines, and reusable prevention rules; later compare with the separate RECIPE_MANAGER project to promote only supported cross-project lessons.
- **Not the current task:** resume feature development, rewrite Core/business logic, redesign the UI, or declare the HTML/PWA or APK fully working.
- **Acceptance criteria:**
  1. Keep B77 history separate from RECIPE_MANAGER history.
  2. Distinguish event time, source time, and recording time where known; mark unknown dates rather than inventing them.
  3. Preserve failed attempts and rollbacks as learning evidence.
  4. Label each lesson as candidate or validated; a commit alone proves a change was recorded, not that the change worked at runtime.
  5. Derive prevention rules from concrete events and link to the supporting commit/report.
  6. Do not change application files as part of this learning pass.
- **Evidence currently available:** LK commit history; `reports/PROJECT_CONTINUITY_20261005.md`; raw `conversations.json` from the 37-object archive; user clarification dated 2026-10-12; and the separately supplied report bundle. The ZIP does not include the manifest's separate attachment files.
- **Known gap:** not all source chats, local versions, screenshots, and device logs are present in this record. Therefore this is a useful partial reconstruction, not a claim of complete history.
- **Progress:** 22 B77 event records now match 22 narrative event headings. Nine older narrative-only records were added to JSONL; five additional B77 incidents were recovered directly from October 3–5 raw user messages. Canonical B77 lessons B77-L-008/009/010 now hold the HTML regression, ineffective filter, and camera-decode rules. RECIPE_MANAGER retains short pointers for historical ID continuity.
- **Additional source finding:** October 2 raw messages added EVT-B77-20261002-001/002 for IndexedDB and scanner-mode/camera/decode failures; the N99 expiry-edit request from the same mixed conversation is kept separate as EVT-RM-20261002-001.
- **Next step:** continue source-message reconciliation for remaining mixed-scope conversations and check whether other B77 incidents in the 37-object archive remain absent. Do not invent root causes or change application files.
