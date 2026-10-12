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
