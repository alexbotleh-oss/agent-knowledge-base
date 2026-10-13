# EVENT_LOG — B77 HTML/PWA

This is a partial reconstruction from Git history, the B77 continuity report, and user statements. The date a record is added to memory is not treated as the date its event occurred. Times below are GitHub commit timestamps (UTC) when available; they describe commit order, not necessarily the full order of work or when a change was first attempted.

## 2026-09-22 — Earlier HTML/SQLite regression history recovered from source archive

### EVT-B77-20260922-001 — Ingredient normalization and database access
- **Source conversations:** `Нормализация ингредиентов` (`6ab2bc6a-1e38-83ed-9cd7-dec0af9324aa`) and `Исправление логики продуктов` (`6ab2c00e-82b8-83eb-afae-c73d36ece59c`).
- **Observed:** user specified ingredient equivalence/canonicalization rules and reported false product matches; later reported broken database access and asked to follow `index_db_path.html`.
- **Status:** user requirements and symptoms confirmed from raw source messages; implementation outcome and root cause unknown.
- **Confidence:** high that these are HTML-contour events; medium that the individual September 22 conversations specifically belong to B77 because those chat titles/messages do not all name B77. User's explicit later boundary identifies B77 as the separate HTML/WMA project.

### EVT-B77-20260922-002 — Recipe-list, nutrition and deletion regression
- **Source conversations:** `Продолжение разговора` (`6ab2cc8d-6770-83ed-b215-496904f80b77`) and `Восстановление файлов чата` (`6ab2ce9f-df74-83eb-9412-8bf2174dca04`).
- **Observed:** user reported recipe list no longer populating after database additions, then reported loss of recipe import, kcal/100 g and BJU display, and recipe deletion.
- **Status:** reported symptoms confirmed; root cause, exact candidate diff and final fix unknown.
- **Confidence:** high for HTML-contour attribution; medium for exact B77 attribution.

### EVT-B77-20260922-003 — Recipe deletion and Shopping-to-Products flow
- **Source conversation:** `Обновление рецептов и покупок` (`6ab2de4d-12f0-83ed-be6e-6212b0fdf4ad`).
- **Observed:** user requested delete-one/delete-all recipes, marking purchased entries in a shopping-list file and returning status to Products; added flour/butter/salt equivalence requirements.
- **Status:** requirement confirmed; implementation and persistence unverified.
- **Confidence:** high for HTML-contour attribution; medium for exact B77 attribution.

Full source-based details: `projects/B77_HTML_PWA/HTML_SQLITE_REGRESSION_2026-09-22.md`.


## 2026-10-05 — verified baseline and scanner iterations

### EVT-B77-20261005-001 — Stage14 baseline
- **Event time:** 2026-10-05; exact time not established in this record.
- **Evidence:** [baseline commit e1eaf7c](https://github.com/alexbotleh-oss/LK/commit/e1eaf7cd20b1265f35a023c8c87db8b1994044f0).
- **Status:** recorded as the verified Stage14 HTML baseline in the continuity report.
- **Meaning:** known checkpoint to compare against; not proof of every feature on every device.

### EVT-B77-20261005-002 — HTTPS / secure-context diagnosis
- **Event time:** reported around 2026-10-05 09:30 UTC in prior project context; exact primary chat excerpt is not currently attached here.
- **Observation:** camera/QR behavior was associated with opening the page through a `content://` address instead of an HTTPS secure context.
- **Status:** recorded prior finding; verify against the relevant source report/device conditions before generalizing beyond browser camera APIs.
- **Prevention candidate:** test camera access through the real intended HTTPS deployment, not only by opening a local content URI.

### EVT-B77-20261005-003 — immutable pre-camera checkpoints
- **Event time:** 2026-10-05 10:43:01 UTC and 10:53:15 UTC.
- **Evidence:** [WP backup](https://github.com/alexbotleh-oss/LK/commit/6d9038eb0b37f53698074be7ea1a0dc3b1eb77eb); [main backup](https://github.com/alexbotleh-oss/LK/commit/7e911a97dd95df6d08efb24b2eb39846efa0ce1c).
- **Status:** confirmed by Git commit records.
- **Meaning:** separate recovery points were created before camera changes.

### EVT-B77-20261005-004 — camera layer added
- **Event time:** 2026-10-05 10:53:19 UTC.
- **Evidence:** [commit e29c156](https://github.com/alexbotleh-oss/LK/commit/e29c156544357ae998041d5f46c8571ffffba00f).
- **Recorded result:** continuity report says the change was isolated to `stage14.html`, with 74 additions and 7 deletions relative to the pre-camera backup.
- **Integration constraint:** camera is an input layer; it must feed the existing chain `openScanner(context) → scanSubmit() → Core.findQR() → existing Products/Shopping/QR handler`. Do not create a parallel Core or business-result path.

### EVT-B77-20261005-007 — cross-chat context failure recorded
- **Event time:** 2026-10-05 11:34:08 UTC.
- **Evidence:** [continuity incident commit](https://github.com/alexbotleh-oss/LK/commit/ded22885e28773b12ccd0fb8c494af5d2991af55); [report](https://github.com/alexbotleh-oss/LK/blob/main/reports/PROJECT_CONTINUITY_20261005.md).
- **Observation:** during chat transition, the assistant rediscovered the repository generically and asked the user for a repository identifier already available in the project context.
- **Classification:** assistant context-continuity failure, not an application-code defect.

### EVT-B77-20261005-005 — scanner diagnostics and button binding
- **Event times:** 2026-10-05 12:18:05 UTC (diagnostics), 13:03:33 UTC (pre-change snapshot), and 13:03:45 UTC (delegated click binding).
- **Evidence:** [diagnostics commit](https://github.com/alexbotleh-oss/LK/commit/8926667ecbfd95fcb83b3e50dcd17177224c5370); [snapshot](https://github.com/alexbotleh-oss/LK/commit/162442d1fbccf6e41e536ffed3fc5882eef7e2be); [binding fix](https://github.com/alexbotleh-oss/LK/commit/52fb9851bb5f6cde5fad73463b6dd4051221c7a7).
- **Status:** commits confirm these changes were recorded. Full device-level acceptance evidence is not reproduced in this memory entry.

### EVT-B77-20261005-006 — Data Matrix attempt and rollback
- **Event times:** 2026-10-05 13:05:28 UTC (pre-change snapshot), 13:05:50 UTC (add supported Data Matrix format), 13:07:56 UTC (rollback).
- **Evidence:** [pre-change snapshot](https://github.com/alexbotleh-oss/LK/commit/2af27cd62e87376d3409ba30a298fe7a3512a22c); [attempt](https://github.com/alexbotleh-oss/LK/commit/456b4208e94b9e2130ffa2a4a29d0041d9be7679); [rollback](https://github.com/alexbotleh-oss/LK/commit/d5a77c141e268bd2275af8748c2c4e5db2fec27a).
- **Status:** confirmed that the change was attempted and rolled back. The commit messages alone do not establish the exact technical cause or the complete test outcome.
- **Learning signal:** a scanner-format change was not retained as a verified improvement; preserve the rollback and do not reintroduce it without a specific test case and observed result.

### EVT-B77-20261006-001 — project state snapshot added
- **Event time:** 2026-10-06 03:15:09 UTC.
- **Evidence:** [commit 8b6ef2e](https://github.com/alexbotleh-oss/LK/commit/8b6ef2e5e6a876b3e3e5503dcbef6b76d02efe13).
- **Status:** current project state for cross-chat recovery was recorded.

### EVT-B77-20261012-001 — practical learning becomes the priority
- **Event time:** 2026-10-12; exact time not stored in this event record.
- **Source time:** user statement in the current conversation.
- **Observation:** user reports that the project is stopped after repeated circular errors and successive changes, with loss of context and change history between chats. The immediate priority is learning from both real «Что приготовить» projects, not further abstract debate.
- **Status:** user-confirmed project-level status; this is not a new code diagnosis.
- **Next action:** extract and compare lessons while preserving separate event chains and chronology.

## Chronology cautions
- Commit timestamps are evidence of when commits were created, not absolute proof of when a symptom first occurred or when a fix was first attempted.
- A later-discovered historical source must be inserted by its event time and linked to its source; it must not be appended as though it were the newest project event merely because it was imported later.
- Unknown dates and uncertain causal links stay explicitly unknown.

## 2026-10-12 — HTML/SQLite, PWA Shopping/Products and mobile camera decode issues

### EVT-20261012-014 — later HTML/SQLite regression reconciliation
- **Source:** follow-up report in the October 12 memory-transfer conversation; the supplied raw `conversations.zip` ends with conversations updated on October 7, so the exact original October 12 message ID is not present in that archive.
- **Observed:** the user again reported recipe database additions failing and the loss of recipe deletion and kcal/100 g / BJU display in later HTML candidates. The working reference `index_db_path(5).html` contains relevant deletion and nutrition paths, but the latest candidate's runtime behavior was not independently verified.
- **Relationship to September events:** this is a later report about subsequent candidate files, not a duplicate copy of the September source messages. Preserve both the original September occurrence chain (EVT-B77-20260922-001/002/003) and this later report, linked rather than merged.
- **Status:** user report confirmed; root cause and final candidate outcome unknown.
- **Source details:** `HTML_SQLITE_REGRESSION_2026-09-22.md` and structured record `events.jsonl:EVT-20261012-014`.

## 2026-10-12 — PWA Shopping/Products and mobile camera decode issues

### EVT-20261012-016 — Shopping units and Products filters
- **Source:** user reports and screenshots in the HTML/PWA project continuation; exact source chat ID not retained in the earlier summary.
- **Reported result:** unit labels in Shopping appeared fixed after filtering in core32, but category/sort selections in Products still did not change the result after subsequent attempts.
- **Status:** partial regression report; root cause unknown and final behavior not verified.
- **Confidence:** high that the event concerns the HTML/PWA contour; exact timestamp and complete source-message chain remain incomplete.

### EVT-20261012-019 — HTTPS/PWA camera video did not decode the code
- **Source:** user reports/screenshots in the mobile HTTPS/PWA page context; exact source chat ID not retained in the earlier summary.
- **Observed:** browser camera permission was granted and video appeared, but the code was not recognized while the camera continued running.
- **Status:** decode failure reported; exact code format, camera/browser details and final fix are not verified.
- **Boundary:** this is the browser/PWA camera pipeline, not the native Android scanner implementation in N99.

Both events were moved out of the N99 event chain after the user's explicit clarification that B77 is the separate HTML/WMA/iPhone web project. Preserve uncertainty where original message-level provenance is missing.
