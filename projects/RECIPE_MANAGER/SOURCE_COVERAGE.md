# RECIPE_MANAGER — охват источников и пробелы экспорта

## Что включено в консолидированную память
- Линия N99/RECIPE_MANAGER: Flet/Android, ингредиенты и покупки в Android-контуре, scanner/theme/water, package/build incidents и scope correction перенесена из доступной ветки PR #20. Ранние HTML/SQLite события вынесены из цепочки N99 в B77 HTML/PWA; общие требования сопоставления ингредиентов сохраняются только как явно переносимые требования.
- Параллельная ветка PR #19 сверена: camera decode failure сохранён отдельным EVT-20261012-019; lesson collision разрешена как L-RM-022 (camera) и L-RM-023 (task boundary).
- Отдельная ранняя память PR #17 добавила Core Lite/JNI FIX1/legacy WebView PROBE1–PROBE3 как исторические события EVT-RM-20260930-001/002 и EVT-RM-20261001-001..004; это материал сводки, не повторно прочитанные оригинальные ZIP/JSON.
- Пересекающаяся ветка PR #21 не копировалась целиком из-за конфликтующих EVT-20261012-005/006. Её уникальные ingredient-equivalence requirements/web regression уже представлены в DEC-RM-006, EVT-20261012-014 и L-RM-008/009; точные исходные артефакты остаются недоступны.

## Классы источников
- **A — прочитано при этой консолидации:** инструкции и файлы agent-knowledge-base из main/PR branches; project memory files PR #17, #19, #20; summaries/metadata GitHub PRs.
- **B — сохранённая сводка/предыдущий transfer:** Core Lite baseline hashes, JNI build log, scanner diagnostics PROBE1–PROBE3, часть build logs и результатов пользователя.
- **C — упомянуты, но оригинальные байты здесь недоступны:** полный экспорт исходных чатов, Android/Python/ZIP attachments, полный diff Android-версий, полный Android/PWA diagnostic JSON, некоторые полные tracebacks. HTML/SQLite артефакты B77 описаны в `projects/B77_HTML_PWA/HTML_SQLITE_REGRESSION_2026-09-22.md` и не считаются исходниками N99.

## Прямая проверка сырого архива — 2026-10-13

- **Доступный сырой архив:** `conversations.zip` содержит ровно одну запись `conversations.json`; это не ZIP всех файлов из отдельного манифеста экспорта.
- **Объекты диалогов:** 37; уникальных ID диалогов — 37.
- **Объекты сообщений / уникальные ID сообщений:** 10 034 / 10 034. В структуре JSON 10 071 узел mapping, часть узлов не является объектами сообщений.
- **Временной диапазон источника:** первый диалог создан 2026-09-21T11:05:34Z; последний диалог обновлён 2026-10-07T14:25:03Z; последнее сообщение датировано 2026-10-07T14:24:53Z.
- **Ограничение охвата:** сырой архив не содержит текущий переносной диалог от 12–13 октября. Для более поздней работы доступны отчётный пакет и заметка о предыдущем сеансе; это вторичные источники, поэтому нельзя выдумывать для них ID исходных сообщений.
- **Ограничение манифеста:** `export_manifest.json` перечисляет 1 374 файла экспорта, а индекс ресурсов связывает имена вложений с файлами, но сами файлы/байты вложений не присутствуют внутри `conversations.zip`. Одно имя файла не подтверждает его содержимое.
- **Расхождение количества:** 37 подтверждено для этого архива. Более ранняя заметка о «74 чатах» не подтверждается проверенным ZIP или текстом отчётов; её происхождение остаётся неизвестным, поэтому число сохраняется как неподтверждённое историческое утверждение.

## Важные ограничения
1. Полная выгрузка всех чатов и всех бинарных вложений не доступна; статус PARTIAL, не COMPLETE.
2. Причины Android/WebView white screen, отсутствия PROBE3 markers, scanner decode failure и package path errors остаются UNKNOWN там, где нет прямого доказательства. HTML/SQLite регрессии принадлежат отдельному HTML-контуру и не должны описываться как дефекты APK.
3. Успешный syntax/targeted check/CI/build не приравнивается к end-to-end runtime на ПК/телефоне.
4. EVT-20261012-007 отсутствует в доступной последовательности событий; это пробел нумерации, не доказательство потери записи.
5. Исходные PR #17/#19/#20/#21 остаются открытыми и не переписаны; этот rollup — отдельная консолидированная ветка.
- **Structured lessons gap:** the consolidated RECIPE_MANAGER chain keeps LESSONS.md as the canonical human-readable lesson index. No lessons.jsonl was synthesized: older branches disagree about its presence/content, and generating 24 structured records from summaries without a source-aligned mapping would create unsupported precision. This is an explicit gap for a later schema-backed conversion.

## Additional raw-source requirement — 2026-10-02
- EVT-RM-20261002-001 records the user's report that an already saved product expiry date could not be edited and the proposal to move Add Product above the list.
- The later same-day control-matrix workbook corroborates the intended requirements: Add Product at top is `CHANGE / USER`, expiry editing is `CHANGE / USER + AUDIT`, and separate batch editing remains `TODO`. The current data model and runtime implementation are still unverified.

## Additional raw-source recovery — N99 HTML-prototype phase gate (2026-10-13)
- Added `EVT-RM-20261001-005` and `DEC-RM-009` from direct message-level evidence in the raw export conversation `Часть 1` (conversation_id `6abe10f8-03d8-83eb-8219-eac3bdd308b0`).
- The user explicitly specified an HTML-first validation phase for N99 before porting logic into Flet; V20 is the visual/layout reference, the existing Flet project is a functional reference, and FIX6/V21/audit/master-map materials are inputs for checking lost/missing functions and dependencies. The old scanner was excluded; native scanner retained.
- This is distinct from B77's iPhone-oriented HTML/WMA/PWA project. The exact state of HTML mockup implementation and whether every function was validated remain unknown.
- The later 2026-10-12 DEC-RM-001 changes the immediate priority to Android debugging before UI redesign; preserve both decisions with their event times instead of flattening them into one timeless instruction.

## Master control matrix artifacts recovered from Library — 2026-10-13

The following dated XLSX artifacts were found and their extracted sheet text inspected; their location under `/Б77/` is not evidence that all rows belong exclusively to B77:
- `RecipeManager_MASTER_CONTROL_MATRIX_v1_2_20261002.xlsx` (9 tabs; latest inspected matrix snapshot).
- `RecipeManager_MASTER_CONTROL_MATRIX_v1_1_20261002.xlsx` (7 tabs) and `RecipeManager_MASTER_CONTROL_MATRIX_v1_20261002.xlsx` (earlier revisions).
- `RecipeManager_V20_FIX6_HTML_контрольная_матрица_20261002.xlsx` (V20/FIX6/HTML comparison).
- `RecipeManager_сводка_изменений_FIX6_V20_V21_N99.xlsx` (5-tab change summary, removed features and N99 regressions).

A source-grounded synthesis is preserved in `MASTER_CONTROL_MATRIX_AUDIT_2026-10-13.md`. Key points: V20 is the visual/layout reference; FIX6 is an existing Flet behavior source but not a completeness oracle; the HTML prototype was a planned validation surface before Flet porting; the Flet target uses the native scanner only; the matrix describes a shared Core contract, batch expiry, safe normalization, explicit availability states, staged imports, separate Shopping/Products/QR contexts, reversible backup/family operations and Lite Cook. Matrix statuses are dated snapshot claims, not fresh runtime tests. The v1.2 workbook lists KTP-01…KTP-20 and explicitly says KTP-21…KTP-28 require their original source; do not invent them.

The matrix is mixed-scope and must be reconciled by message-level provenance. The N99 HTML-first prototype in `Часть 1` is not the same project as B77's separate iPhone-oriented HTML/WMA/PWA camera path in `Часть 2`. The matrix itself lists open questions around diet scope, Roulette, web adapters, PC DB schema, family server sync and PWA camera; none is silently promoted to a settled implementation fact here.

## Control-matrix cross-check for saved expiry editing — 2026-10-13
- The direct 2026-10-02 user message is now corroborated by the Library workbook `RecipeManager_сводка_изменений_FIX6_V20_V21_N99.xlsx` (modified 2026-10-02T13:30:48Z): UI-05 records Add Product at the top as `CHANGE / USER`; P-07 records expiry editing as `CHANGE / USER + AUDIT`; P-10 marks separate batch editing as `TODO`.
- This resolves the requirement-status uncertainty in DEC-RM-008, but not the implementation question. The matrix records the target; no app source/runtime test was performed here.
