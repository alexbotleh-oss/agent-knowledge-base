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


## 2026-10-02 — IndexedDB and scanner-mode failures

### EVT-B77-20261002-001 — IndexedDB backing-store open error
- **Источник:** «Часть 2» (conversation_id 6abf7d53-15c8-83ed-b5f4-dd819664ce6f), 2026-10-02 11:01–11:12 UTC.
- **Наблюдение:** пользователь сообщил о неработающем сканере и предоставил журнал с повторяющимися сообщениями `[pwa-storage] IndexedDB: Internal error opening backing store for indexedDB.open`, возникавшими при выборе сканера и нажатии Scan.
- **Статус:** ошибка IndexedDB подтверждена вставленным логом; связь с декодированием камеры и причина не установлены.
- **Сообщения:** `bbb2116e-efc8-459d-b3b9-b45e880b1ea7`, `bbb2129f-4b6a-405f-8dca-c1860b0bf2a1`.

### EVT-B77-20261002-002 — смешение режимов Products/Shopping и отказ camera/decode
- **Источник:** «Часть 2», 2026-10-02 11:27–12:46 UTC.
- **Наблюдение:** пользователь потребовал сохранить раздельные режимы сканирования Products и Shopping, как в Flet-референсе; сообщил, что системная камера, остановка и распознавание штрихкода не работают как ожидалось. Позже уточнил, что скриншот относится к настройкам сканера, а не к экрану продукта.
- **Граница:** вопрос о запуске локального content:// HTML не является доказательством, что secure context — единственная причина. Ошибка IndexedDB из EVT-B77-20261002-001 остаётся отдельной диагностической цепочкой.
- **Статус:** требования и симптомы подтверждены сообщениями; успешный decode/save и окончательное исправление не подтверждены.
- **Сообщения:** `bbb21b92-4ebb-4145-a9aa-ef92630bdccc`, `bbb2187b-1f57-489b-86d1-031548e770dc`, `bbb21994-bda8-45a7-ad38-1b4c93eb842f`, `bbb21392-41c4-4bb5-b7c5-c4d72e4075ca`.

## 2026-10-03–05 — HTML prototype interaction regressions and failed recovery

### EVT-B77-20261003-001 — repeated long-press, swipe and Light Cook regressions
- **Source conversation:** `Часть 2` (`6abf7d53-15c8-83ed-b5f4-dd819664ce6f`), user messages 2026-10-03 09:10–10:24 UTC and 19:33–19:50 UTC.
- **Observed:** the user reported long-press recipe editing not working, missing swipes in Products/Shopping compared with V20, Light Cook not selecting a dish, product editing unavailable, and a critical UI regression after a bounded toolbar change. Later, a confirmation dialog appeared, but swipe captions and other UI details remained incomplete.
- **Status:** multiple symptoms and a partial recovery are user-reported; root cause and complete restoration are unknown.
- **Evidence:** messages `bbb21a40-dd55-460e-84cb-8251705a2e1f`, `bbb2156a-c0be-4129-a526-7c275a5d41bd`, `bbb21b50-e3d6-4981-9549-e50fe50ca3e5`, `bbb21365-ba6b-4079-be22-4f6293300faa`, `bbb217ed-d92c-4204-a6d3-c8c9997c48c0`, `bbb21ccf-c381-4f2a-9656-ed89f40c04fe`, `bbb2141c-5ba5-4497-b70c-937ffae67120`, `bbb21a64-cc02-4cd9-8071-0e351415b3ac`.

### EVT-B77-20261003-002 — Products/Shopping flow failures and partial recovery
- **Source conversation:** `Часть 2` (`6abf7d53-15c8-83ed-b5f4-dd819664ce6f`), user messages 2026-10-03 19:54–21:28 UTC.
- **Observed:** swiping an existing product into Shopping did not add it; Shopping filters, share, copy and Add were reported broken. The user directed the assistant to reuse the working V20/B77 flow. Later, Shopping was reported working while Products remained broken.
- **Status:** partial recovery reported; Products remained in a bad state at the last message in this chain. No all-functions PASS.
- **Evidence:** messages `bbb21734-460c-4cf2-8bc5-c79892ff8d18`, `bbb21498-a0cf-463f-a5e6-04de89a1fe64`, `bbb21b0e-859a-4a66-bc30-734a6660dac6`, `bbb21416-74c5-4113-b8f9-ca594f7a7819`, `bbb21d3e-8b30-4dd9-a889-5b0604752c6d`, `bbb21eee-ba0b-4fd4-97af-32cc0de41d9c`, `bbb2140a-1a7d-4493-9e26-ac91af564bb3`, `bbb218fa-38df-4f68-94c3-509a396f77fc`.

### EVT-B77-20261004-001 — Products filters/sorting and Shopping unit integrity
- **Source conversation:** `Часть 2` (`6abf7d53-15c8-83ed-b5f4-dd819664ce6f`), user messages 2026-10-04 08:09–08:41 UTC.
- **Observed:** Products category/sort controls did not work after being moved into drawers. An incorrect Shopping sort was proposed and rejected by the user; the intended sort was by source/category. The user reported that changing Shopping sorting changed measurement units, then said one narrow behavior worked while Products sorting still did not.
- **Status:** partial user-reported recovery; Products filtering/sorting remained broken in the last report. Root cause unknown.
- **Evidence:** messages `bbb21e0f-c244-481f-ab32-9b8a0c013622`, `bbb2127b-a96f-4e79-805d-95a8c109ab75`, `bbb216be-f9c1-4017-8715-3e81abbf58ed`, `bbb21fcc-1c0b-4827-9d50-7739fab9385a`, `bbb21d7c-96ad-4007-a360-d8bb3901cf02`.

### EVT-B77-20261004-002 — recipe identity and context-menu regression
- **Source conversation:** `Часть 3` (`6ac27bda-dfa4-83eb-a3b0-6f984b026f9a`), user messages 2026-10-04 16:18–19:52 UTC.
- **Observed:** opening “куриный суп” showed “блины на молоке”; recipe-card titles/content were reported duplicated or mismatched; the Products ellipsis menu and long-press recipe-edit menu regressed. The user pointed to Core 26 as a working reference and requested bounded repairs without disturbing working mechanics. Swipe/delete and long-press failures were reported again before a later user-reported recovery.
- **Status:** recurring symptoms confirmed as user reports; some recovery was reported, but final state of all affected controls is not verified.
- **Evidence:** messages `bbb21e25-7073-4d0c-b892-85a2268d186b`, `bbb21d93-a3ff-40c7-b967-d92f997b78ed`, `bbb2124f-e24e-45bc-9cb6-8a41053a7590`, `bbb21714-fb2d-4a6b-80d4-5d7a2ef60bdb`, `bbb21fcd-69b6-4419-8d7d-08a84012d071`, `bbb219e6-1304-4c16-aac9-622b78ec19b0`, `bbb21c60-0895-4cad-b759-9c7ee4321312`, `bbb21ecd-cb9c-44de-9b8f-cd4ac091c0b8`, `bbb21d15-be1c-42cb-b98e-b35a1e1b9544`, `bbb21340-bdf6-45d0-a146-27e8b7280a8d`.

### EVT-B77-20261005-008 — rollback impossible after source-file loss
- **Source conversation:** `Часть 3` (`6ac27bda-dfa4-83eb-a3b0-6f984b026f9a`), user messages 2026-10-05 03:17:39 and 03:24:00 UTC.
- **Observed:** the user said the interface had been broken and could not be restored because the original source file was lost. The user explicitly required retaining a copy of the source file after work, comparing changes against the last working version, and recording the incident.
- **Status:** recovery failure and prevention requirement confirmed from the raw source; exact lost file/version and complete cause are unknown.
- **Evidence:** messages `bbb2116b-7212-47ad-857f-0a4844d08776` and `bbb21aa0-01a8-4068-98a1-747dcc030758`.
- **Boundary:** this is a distinct recovery incident; later Stage14/camera backups do not prove that the earlier lost source was recovered.

## 2026-10-05 — verified baseline and scanner iterations

### EVT-B77-20261005-002 — HTTPS / secure-context diagnosis
- **Event time:** reported around 2026-10-05 09:30 UTC in prior project context; exact primary chat excerpt is not currently attached here.
- **Observation:** camera/QR behavior was associated with opening the page through a `content://` address instead of an HTTPS secure context.
- **Status:** recorded prior finding; verify against the relevant source report/device conditions before generalizing beyond browser camera APIs.
- **Prevention candidate:** test camera access through the real intended HTTPS deployment, not only by opening a local content URI.

### EVT-B77-20261005-001 — Stage14 baseline
- **Event time:** 2026-10-05; exact time not established in this record.
- **Evidence:** [baseline commit e1eaf7c](https://github.com/alexbotleh-oss/LK/commit/e1eaf7cd20b1265f35a023c8c87db8b1994044f0).
- **Status:** recorded as the verified Stage14 HTML baseline in the continuity report.
- **Meaning:** known checkpoint to compare against; not proof of every feature on every device.

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
