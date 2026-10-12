# Сверка текущего чата с памятью RECIPE_MANAGER — 2026-10-12

## Цель и границы
Этот документ фиксирует сверку текущего доступного чата проекта «Что приготовить» с памятью репозитория `agent-knowledge-base`. Работа ограничена переносом опыта. Код приложения, БД и APK в рамках этой сверки не менялись, APK не собирался.

## Что уже было записано до этой сверки
На ветке `handoff/recipe-manager-chat-continuation-20261012` уже присутствуют проектные документы и машинные журналы:
- `PROJECT_STATE.md`, `TASK_STATE.md`, `EVENT_LOG.md`, `DECISIONS.md`, `LESSONS.md`, `HANDOFF.md`;
- `events.jsonl`, `lessons.jsonl`.

В них уже отражены:
- сообщения 2026-09-22 о HTML/SQLite: добавление рецептов из БД, нормализация ингредиентов, импорт food.ru и 1000.menu, удаление рецептов и КБЖУ;
- traceback от 2026-09-27: `PopupMenuItem.__init__() got an unexpected keyword argument 'text'`;
- различение пользовательских требований, сообщённых симптомов, неподтверждённых гипотез и фактически проверенных результатов;
- неудачные попытки/регрессии и запрет считать HTML-патч исправным без браузерной, DB-persistence и функциональной регрессии;
- явное ограничение полноты: доступная память основана на выбранных сообщениях/сводках и не является полным экспортом всех чатов и вложений.

Повторное добавление этих же симптомов как новых событий создало бы смысловые дубликаты, поэтому они не копируются заново.

## Что установлено в этой сверке
1. Целевой репозиторий доступен через подключённый GitHub-инструмент; default branch — `main`.
2. В `main` ранее не было каталога `projects/RECIPE_MANAGER/`, но он уже существует в отдельной рабочей ветке переноса.
3. До этой сверки уже существовали PR #6 для исторической памяти и PR #9 для дополнительной истории HTML/SQLite. Они открыты как draft и не слиты.
4. В видимых сообщениях текущей сессии нет новых проверенных фактов о поведении приложения сверх уже внесённых записей. Последние сообщения ассистента о неудаче инструмента записи HTML не являются доказательством исправления приложения; сам файл тогда не был создан.
5. По этой причине в данном документе записан именно результат дедупликационной сверки и границы доступной истории, без выдумывания новых результатов проверки приложения.

## Факты и гипотезы
### Подтверждённые факты по доступному источнику
- Пользователь явно переключил задачу на перенос опыта в `agent-knowledge-base` и запретил в рамках неё продолжать отладку Android, изменять код приложения или собирать APK.
- Пользователь просит создать отдельную ветку и PR, не сливая изменения в `main` без разрешения.
- Сообщения о HTML/SQLite-регрессиях и требованиях по ингредиентам уже представлены в существующих журналах памяти.
- В предыдущем контексте попытки записи HTML завершались внутренней ошибкой инструмента выполнения кода; готовый исправленный HTML не был подтверждён как созданный/проверенный.

### Не утверждать как факт
- Причины исторических HTML/SQLite регрессий.
- Что прежние патчи ингредиентов или доступа к базе окончательно исправили проблему.
- Что Android APK сейчас работает или что проблема чёрного экрана устранена.
- Что исторические вложения полностью извлечены из всех разговоров.
- Что новый вызов `apply_platform_nav()` был реально применён к установленному APK, если нет подтверждающего diff/лога.

## Оставшиеся пробелы
- Полный экспорт переписки за все сессии отсутствует в текущем контексте.
- Не все исторические файлы HTML, SQLite и Python, а также полные tracebacks, логи сборки и финальные diffs доступны для независимой повторной проверки.
- Точный финальный статус отдельных старых HTML-патчей остаётся unknown.
- Для полноты истории требуются доступные первоисточники, а не реконструкция по одному имени файла или краткому резюме.

## Проверки этой сверки
- Прочитаны README репозитория, основные инструкции памяти/передачи контекста, шаблоны проектного состояния и задачи, формат JSONL-записей и скрипты валидации.
- Прочитаны текущие проектные документы и машиночитаемые журналы на существующей ветке переноса.
- Смысловые повторы не добавлялись в события/уроки только ради объёма.
- Эта запись не подтверждает тесты приложения: в рамках текущей задачи такие тесты не выполнялись и не требовались.
- История остаётся `PARTIAL`, не `COMPLETE`.

## Происхождение
- Источник: текущий доступный чат от 2026-10-12, существующие записи `projects/RECIPE_MANAGER/*` и `projects/RECIPE_MANAGER/events.jsonl` / `lessons.jsonl` на ветке `handoff/recipe-manager-chat-continuation-20261012`.
- Время: 2026-10-12, Europe/Riga.

## Additional unique evidence from scanner/theme/water and recipe-search discussion

The available chat fragment contains new material not recorded by the earlier packaging reconciliation:

- Build39's native barcode path was reported working by the user: ask prompt, add/edit form, repeated scan finding existing product, and automatic quantity accumulation. This is only verified for the reported Build39 scenarios.
- The old WebView scanner showed a white screen after a scanner-engine change. Build40 was described as reverting the old HTML to a known baseline, but no later successful device validation is present in the available history.
- After an assistant stated that water was allowed again, the user reported that a subsequent scan failed to find it and created three separate «Вода» entries. The cause is unknown and the claimed water fix did not satisfy the repeated-scan requirement.
- Build39 screenshots show a light/dark theme mismatch: in dark mode the work surface/top bar are dark while the app's bottom NavigationBar is white. The user explicitly said this is not only a bottom-bar issue and must be audited throughout all menus and UI/system layers. The subsequent bottom-only focus (Build42 proposal) was criticized as too narrow; Build42 is not confirmed fixed or device-tested in this material.
- The user requires a persistent dependency/achievement tree, done/not-done markers, preservation of earlier known-good implementations, analysis of component layers/intersections, related regression checks, and a final comparison against the original request before claiming completion.
- The recipe-search UX specification, including automatic/semi-automatic/professional modes and mandatory PDF import, is now preserved in `RECIPE_SEARCH_REQUIREMENTS.md`. It describes requested behavior, not implementation proof. The requested interactive HTML prototype remains unverified as created.

These are recorded as EVT-20261012-010/011 and L-RM-013..016. Earlier HTML/SQLite, recipe import and Flet packaging facts were not duplicated. Exact intermediate-build diffs and the complete project chat export are still unavailable; the transfer remains PARTIAL.



## Additional current-chat event — archive verification failure and user-approved canon (2026-10-12)

A separate later archive failure is recorded as `EVT-20261012-012`, with preventative lesson `L-RM-017`. The assistant claimed the delivered Build43 archive had the local extension dependency fixed. Inspection of the delivered ZIP subsequently found `flet-barcode-scanner @ ./flet_barcode_scanner_ext` remained in its `pyproject.toml`. User then ran `flet build apk --verbose` from the copied project, and pip rejected that exact argument with `Invalid URL './flet_barcode_scanner_ext': No scheme supplied`.

The user explicitly confirmed the mandatory prevention canon: verify the exact saved artifact after editing; inspect contents, dependencies, and the actual consumer chain before claiming success; when a user followed the instructions and gets the same issue, check the assistant's artifact/instructions first; each error must change the process so the same class of failure is caught earlier. This is confirmed process policy, not proof of an app fix.

Scope unchanged: memory transfer only; app code/DB untouched, no APK build performed. Transfer stays PARTIAL because complete chat exports and all historic attachment bytes are unavailable.


## Additional reconciliation — 2026-10-12, continuation from PR #14

### Already transferred; intentionally not duplicated
- `EVT-20261012-010`: user-reported native scanner flows on Build39, unresolved old WebView white screen, theme mismatch, and duplicate-water report.
- `EVT-20261012-011` / `L-RM-016`: explicit user requirement for dependency/achievement tracking, status markers, baseline preservation, cross-component regression, and final comparison to the original request.
- `EVT-20261012-012` / `L-RM-017`: Build43 archive still had a relative extension dependency and pip failed; user-approved end-artifact verification rule.
- `RECIPE_SEARCH_REQUIREMENTS.md`: local-first search, three modes, shared normalizer and PDF import as a requirement, not implementation evidence.

### New structure finding
The actual tree at HEAD `2f056046946bf1e5a16f54e858f71e7ee8ebd49a` contains `LESSONS.md` with L-RM-001..017 but no `lessons.jsonl`. Older handoff/validation text references the JSONL file. Without the historical commit/file this conflict cannot be resolved by assertion. The discrepancy is recorded, not silently repaired with a guessed schema.

### Still unknown or unavailable
- Source-level cause of old WebView white screen.
- Implementation-level cause of duplicate water records and final behavior of Build41+ artifacts.
- Device-confirmed results for Build40/41/42/43 across WebView/theme/water paths.
- Exact diffs for every intermediate build, full project chat export and original binary attachment bytes.
- Why `lessons.jsonl` was mentioned in earlier handoff records but is absent in current tree.

### Scope and completion
Memory transfer only; no application/database changes and no APK build. Status remains PARTIAL. No merge into `main` is authorized.


## Additional unique evidence — HTML/SQLite regressions and ingredient normalization (2026-10-12)

The available current-chat segment includes later user-reported regressions not to be confused with the earlier September baseline event:
- The latest HTML candidate no longer added recipes from DB and no longer displayed per-100g nutrition.
- The user separately asked to restore recipe deletion and kcal/protein/fat/carbs display from the reference `index_db_path(5).html`.
- Multiple HTML variants and `recipes(3).db` were attached/named in the source. Full inter-version diffs and an independently verified runtime result for the latest supplied file are not available here.
- The reference HTML contains nutrition rendering and recipe deletion paths, but that fact does not prove these features worked in the later candidate.

The user's explicit ingredient lookup contract:
- `лук`, `белый лук`, `репчатый лук` → `репчатый лук`; `красный лук` and `зелёный лук` remain separate.
- generic `рис` → long-grain rice; `рис для плова` and explicit parboiled rice → parboiled rice.
- account for case, `ё/е`, word order, and grammatical endings; test `яйцо/яйца/яйцом` and forms of olive oil.
- avoid false matches such as `рис` → `рисовая мука` or `рисовое масло`; show original recipe ingredient wording while using a normalized lookup key.

The reports are captured as EVT-20261012-014 and prevention lesson L-RM-019. Root causes remain unknown and HTML behavior NOT VERIFIED. This update does not diagnose or modify the app.

## Additional verification — this chat's final memory-transfer request (2026-10-12)

The latest user request explicitly redirects work back to memory transfer and prohibits HTML/Android debugging or APK building in this task. The already-open Draft PR #16 is the canonical place for the current chat's HTML/SQLite regression evidence, so no duplicate event or second PR is needed unless new primary evidence appears.

### What was verified during this continuation
- The repository root and `core/guardrails.md`, `core/universal_instructions.md`, and `README.md` were read from `main`; the project-specific transfer files were read back from PR #16's head branch.
- The actual `projects/RECIPE_MANAGER` tree on PR #16 contains `PROJECT_STATE.md`, `TASK_STATE.md`, `EVENT_LOG.md`, `DECISIONS.md`, `LESSONS.md`, `HANDOFF.md`, `events.jsonl`, `RECIPE_SEARCH_REQUIREMENTS.md`, `BUILD_PACKAGING_ATTEMPT_2026-09-22.md`, `CHAT_TRANSFER_RECONCILIATION_2026-10-12.md`, and `HTML_SQLITE_REGRESSION_2026-10-12.md`. It does **not** contain `lessons.jsonl`; do not generate it using an assumed schema.
- `events.jsonl` has 15 records with unique IDs through `EVT-20261012-014`. `LESSONS.md` has L-RM-019. This chat's requirements and the user's reports are already represented; duplicating them would reduce chronology quality.
- GitHub Actions validation run #61 for head `587eff3816652a661210bf9393c655103ff0d5d3` completed successfully: https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/38278032266.
- PR #16 is currently open as Draft and unmerged. No changes were made to the app, HTML candidates, SQLite product database, or APK in this continuation.

### Remaining gaps
- The full exported source conversation and original binary attachments for all previous HTML candidates are unavailable; source history stays PARTIAL.
- Candidate-to-candidate diffs and independent browser/runtime/persistence evidence for the last HTML artifact are missing. The import, delete, edit, nutrition, and normalization behavior remains NOT VERIFIED.
- The PR head/base relationships should remain explicit: #16 is a stacked PR based on #15's branch, not a direct-to-main PR. Keep it unmerged pending user review/permission.

This is a source-coverage and verification note, not evidence that the application itself was repaired.


## Additional evidence — Flet local-extension dependency gate (2026-10-12)

### Confirmed by the latest user log
- At about 19:49:53 the user ran `flet build apk --verbose` from `C:\RecipeManager_FIX_PLUS`.
- Flet found the entrypoint, created the app shell, identified Flutter 3.44.8, JDK 17 and Android SDK, and started the `serious_python package` path.
- Installation invoked `flet-barcode-scanner @ ./flet_barcode_scanner_ext` and pip aborted with `Invalid URL './flet_barcode_scanner_ext': No scheme supplied`.
- No successful APK compilation or artifact verification appears in this log. Assistant admitted that actual extension installation was not tested before calling the package ready.

### Facts versus hypotheses
- The log does not prove the extension directory is missing or establish whether the cause is its structure, project manifest, path resolution or pip/packaging behavior. Root cause = UNKNOWN.
- This is a dependency-packaging failure before confirmed APK; do not classify it as a device scanner runtime test.

### User-required prevention
1. Inventory all inputs and select the canonical source/baseline.
2. Resolve direct and transitive local dependency/resource closure.
3. Manifest added/changed/excluded files; any excluded required file blocks release.
4. Read back the exact saved artifact; compare SHA-256, complete file tree and required hashes; check duplicate entrypoints/config files.
5. Test actual downstream dependency installation/build consumer path. If not run, mark NOT VERIFIED and do not call the package build-ready.
6. Any mandatory FAIL/BLOCKED means STOP; do an evidence-based minimal correction or ask the user for the exact missing input. Do not bypass controls by deleting dependencies or altering architecture.
7. For every change log file path, line range/stable context, before/after, reason, related event/lesson, dependencies, and validation results.

New records `EVT-20261012-015` and `L-RM-020` are a distinct follow-on to `EVT-20261012-012` / `L-RM-017`, not a replacement.

### Scope and completeness
Memory transfer only. No app code, extension or product database was changed and no APK was built in this task. Full chat export and exact persisted archive/directory are unavailable to this memory pass; status remains **PARTIAL**.

## Additional continuation — PWA Products/Shopping interaction regression (2026-10-12)

### What this chat segment adds
- The user requested visual consistency of the Add Product/Add Shopping windows, a gray input border with an inset text position, a top-level Add action and moving the Shopping source filter into a sheet.
- The user rejected adding sorting by name/quantity/status in Shopping; the required control to move under a sheet was the source filter «Все / Из рецептов / Ручные / Куплено».
- The user's core31 screenshot shows the intended Shopping header «Откуда» alongside «＋ Добавить».
- After filtering Shopping, the user reported Latin unit labels; they explicitly confirmed that core32 fixed labels in the demonstrated scenario. This is not a blanket assertion that all unit scenarios are correct.
- Products category and sort sheets displayed options in the user screenshots, but selecting failed. After core33 the user said a tap only highlights and does not change the list; after core34 the user said selection still produces no result.

### Confirmed vs unknown
- Confirmed: the user's report of the Shopping unit-label fix for the shown scenario.
- Confirmed failure: Products category/sort selection does not apply according to the latest user message.
- Unknown: exact code-level cause. No runtime trace or console evidence establishing a handler/state/render defect was captured in this memory-only task.
- The assistant's statements that core33/core34 were fixed are not evidence; subsequent user feedback contradicts the claimed outcome.

### Deduplication and provenance
- This is follow-on evidence after earlier package and HTML/SQLite transfers; it does not duplicate the recipe DB/nutrition incident EVT-20261012-014 or package incident EVT-20261012-015.
- Linked lesson: L-RM-021; event: EVT-20261012-016.
- Candidate references core30–core34 appear in the conversation, but availability of each exact file and complete inter-version diffs was not verified here.

### Scope and completeness
Memory-only; no PWA/HTML/JS/application database modification and no APK build. Source completeness remains PARTIAL.
