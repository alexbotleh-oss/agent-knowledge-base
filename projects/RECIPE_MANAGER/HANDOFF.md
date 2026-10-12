# HANDOFF — RECIPE_MANAGER

- **Проект:** RECIPE_MANAGER / «Что приготовить» — Recipe Manager Android
- **Обновлено:** 2026-10-12
- **Достоверность:** partial — история восстановлена по видимому контексту и сохранённой сводке, не по полному экспорту чата
- **Главная цель проекта:** поддерживать Android/PC-приложение рецептов, продуктов и покупок с SQLite и Flet, сохраняя работу с данными и существующие функции.
- **Текущая цель:** завершить отладку Android-сборки, прежде всего проблему чёрного экрана/неправильного старта.
- **Критический порядок:** сначала отладка Android → подтверждение запуска → регрессия основных функций → только после этого возвращаться к улучшению интерфейса Android.

## Подтверждённо сделано
- В прошлой локальной итерации кандидат `/mnt/data/main.py` проходил `python -m py_compile` (сведения из сохранённой сводки, повторной проверки в этом сеансе не было).
- По сохранённой истории пользователь восстановил `seed_data.py` в `C:\\RecipeManager_update`; после этого команда `flet run main.py` работала.
- Пользователь ранее подтвердил, что общий hover-фикс кнопок с ARGB overlay работает.
- Текущий чат напрямую подтверждает решение не менять Android UI до окончания отладки.

## Не завершено
- Точная причина чёрного экрана не установлена в доступной истории.
- Не подтверждён факт успешной сборки/установки/запуска текущего APK.
- Не подтверждены текущий SHA/ветка приложения, чистота рабочей копии, содержимое актуального `main.py`, `pyproject.toml`, БД и артефакта.
- Не выполнена свежая проверка основного пользовательского сценария на устройстве.
- Поддержка сканирования DataMatrix/EAN обсуждалась только как будущая идея; сейчас не внедрять.
- Полный архив всех чатов/вложений в этом сеансе не был доступен; некоторые прошлые файлы сохранились только по именам и кратким описаниям.

## Активные ограничения
1. Не переделывать интерфейс Android до исправления запуска.
2. Не добавлять сканирование товара/API в текущую отладку.
3. Не удалять и не заменять пользовательские данные, БД и вспомогательные ресурсы; прежде проверить состав, копию и возможность отката.
4. Не повторять длительную сборку вслепую: сначала установить точную команду, последнюю стадию, логи и признак прогресса.
5. Один минимальный диагностический патч за итерацию, с фактической проверкой.
6. Не заявлять PASS без доказательства. Статический Python compile, сборка, установка и runtime — разные статусы.

## Источники, прочитать в первую очередь
- Этот каталог `projects/RECIPE_MANAGER/`: `PROJECT_STATE.md`, `TASK_STATE.md`, последние записи `events.jsonl`, `DECISIONS.md`, `LESSONS.md`.
- Предыдущий локальный baseline, если доступен: `C:\\RecipeManager_update`.
- Именованные артефакты из доступной сводки: `main.py`, `main_new.py`, `main(2).py`, `main_BEFORE_REFRESH_SCROLL_FIX.py`, `seed_data.py`, `pyproject.toml`, `RecipeManager_final_before_apk.zip`.
- Реальные логи Flet/Android build/runtime и любые актуальные скриншоты чёрного экрана.
- Универсальный протокол базы знаний: `core/guardrails.md`, `core/agent_runtime_protocol.md`, `core/session_handoff.md`, `core/visual_diagnostics.md`.

## Первый логичный шаг следующего чата
Не начинать с нового UI и не пересобирать APK вслепую. Сначала восстановить точный актуальный набор исходников и конфигурацию, определить последнюю воспроизводимую команду сборки/запуска и получить конкретный лог ошибки/события, связанного с чёрным экраном. Установить, возникает ли он до старта Python/Flet, при инициализации приложения или при загрузке данных. После этого выбрать один минимальный проверяемый патч, выполнить статические проверки, сборку и фактический запуск; если доступ к Android отсутствует, честно оставить runtime BLOCKED и запросить только необходимый лог/результат.

## Контрольное ядро и его статус
- В базе agent-knowledge-base есть текущие универсальные протоколы/guardrails; на момент проверки репозиторий `alexbotleh-oss/agent-knowledge-base`, ветка `main`, HEAD `a0c12ba849a3416f50e1289d8f0dd20844e1e51f` (это коммит базы знаний, не приложения).
- В других доступных проектных заметках упоминались CORE v1.7.9.3, v1.7.9.7 и v1.7.9.8; они относились в том числе к CARD111 / B77. Не подтверждено, что одна из этих версий была установлена или активна для Recipe Manager Android.
- Поэтому не отключать и не удалять контрольные инструкции. Для эксперимента можно временно приостановить лишь внешний протокол выполнения задач после отдельной фиксации версии/копии инструкций и явного решения пользователя; сохранить diff, commit SHA и процедуру возврата. Текущее задание не требует паузы, поэтому ничего не отключать.

## Состояние репозитория памяти
- Целевой репозиторий: `https://github.com/alexbotleh-oss/agent-knowledge-base`.
- Подготовленная ветка: `handoff/recipe-manager-20261012`.
- Дальнейшая запись должна оставаться в этой ветке до проверки и открытия PR; не менять `main` напрямую.


## Дополнение к передаче — навигация Android/ПК (2026-10-12)

В переданных из другого чата ответах описана новая/уточнённая подзадача: после двух неудачных сборок добиться правильного набора пунктов навигации. Предлагаемая гипотеза — вызвать `apply_platform_nav()` до первого `render_home()`, сохранив `on_connect` как дополнительное обновление. Это пока только гипотеза: требуется проверить момент доступности платформы в Flet 1.0.1 и то, как `nav.destinations` обновляет уже созданный UI.

**Критерии:** Android показывает ровно пять кнопок; ПК сохраняет все шесть разделов. Не менять `recipes.db` и бизнес-логику рецептов. Не скрывать ошибки платформенного определения через `except Exception: pass`. Сначала проверить исходник/патч и запуск на ПК, затем только собирать APK и проверять на устройстве. В предоставленном материале патча нет, причины двух неудачных сборок и runtime-результаты не подтверждены. Ранее отмеченная проблема чёрного экрана также не считается решённой без отдельного доказательства.

## Позднее дополнение — продолжение навигационной попытки в чате (2026-10-12)
В текущем чате был применён подготовленный патчер, который переносил настройку мобильного списка в обработчик `page.on_connect`. После этого:
- `python -m py_compile .\main.py` — без вывода/ошибки;
- `python .\main.py` — пользователь подтвердил запуск на ПК;
- `flet build apk` — успешно завершён, APK скопирован в `build\apk`;
- пользователь подтвердил, что на телефоне по-прежнему шесть пунктов навигации.
Следовательно, этот путь **не удовлетворил критерий Android=5**. Загруженный позднее `main(7).py` предлагает альтернативную гипотезу: синхронно вызвать `apply_platform_nav()` до первого `render_home()`. Факт применения именно этого альтернативного файла к рабочему `main.py` не подтверждён. Не приписывать ему результат предыдущей сборки. Первопричина остаётся неизвестной.

## Проверки последнего дополнения (2026-10-12)
- После записи изменения ветки были повторно прочитаны через GitHub Contents API.
- `projects/RECIPE_MANAGER/events.jsonl`: 6 JSON-записей событий плюс пустая последняя строка; все непустые строки разбираются как JSON.
- `projects/RECIPE_MANAGER/lessons.jsonl`: 4 JSON-записи уроков плюс пустая последняя строка; все непустые строки разбираются как JSON.
- GitHub Actions для commit `2bf99b1c32933860458a84fe7bd31445d7127ec1` завершился `success`; job `validate` завершился успешно. Проверка репозитория в CI прошла.
- PR #6 остаётся открытым draft и не объединён. Android runtime/визуальный критерий не является проверкой этого PR и остаётся FAIL по сообщению пользователя.

## Продолжение переноса исторического опыта — 2026-10-12

### Что дополнено
- EVT-20261012-006 связывает доступные сообщения о рецептах из БД, нормализации ингредиентов, импорте food.ru/1000.menu, удалении/КБЖУ и ошибке Flet от 2026-09-27 с первичными event IDs без дублирования исходных записей.
- LESSON-RM-009 фиксирует регрессионные сценарии импорта/сопоставления ингредиентов. Причины старых HTML-регрессий оставлены UNKNOWN.

### Источники и пробелы
- Доступны текущие сообщения, сохранённая сводка, имена нескольких вложений и текст ошибки; полного экспорта всех чатов и бинарных вложений нет.
- Недоступны для независимой проверки: полные исторические версии index_db_path*.html, Что приготовить 22*.htm, все recipes*.db, полные логи импорта и окончательный diff, показывающий какие исправления вошли в финальный файл.
- Перенос имеет статус PARTIAL, не COMPLETE. Не реконструировать причины и итог старых фиксов по косвенным упоминаниям.

### Граница текущей задачи
Задача текущего чата — перенос опыта в agent-knowledge-base; изменения приложения и сборка APK не выполнялись. PR #6 остаётся без слияния. Не подменять задачу памяти новой отладкой Android.


## Memory-transfer continuation — Windows Flet packaging attempt (2026-10-12)

An additional build-attempt chain was saved as `BUILD_PACKAGING_ATTEMPT_2026-09-22.md`, `EVT-20261012-008`, and `L-RM-011`. In the user's screenshots, an initial call had an entry-point/root error, a later call reported that `git` was not recognized and could not determine the Flutter engine version, and a later attempt after `flet clean` stayed on `Packaging python app...` for approximately ten minutes by user report. The attempted process-monitoring command was incomplete, so no CPU/working-set or build-directory trend was established.

**Do not infer:** the APK was built, the build was definitely hung, Git was definitely installed, or the application launched. This sequence is distinct from the earlier APK build 5/navigation issue. History remains PARTIAL because complete build logs, final artifact listing, full chat export, and all historical attachment bytes are not available.


## Handoff — продолжение переноса опыта по текущему чату (2026-10-12)
- **Текущая задача:** memory-only перенос истории «Что приготовить» в `agent-knowledge-base`.
- **Подтверждено:** доступный скриншот показывает незавершённый этап `Packaging python app...`; процессная команда не завершена из-за trailing pipe, поэтому нагрузка/активность процесса неизвестна.
- **Уже сохранено ранее:** отдельный эпизод упаковки — `BUILD_PACKAGING_ATTEMPT_2026-09-22.md`, `EVT-20261012-008`, `L-RM-011`. Не плодить дубликаты; текущая сверка записана в `EVT-20261012-009`.
- **Ограничения:** не запускать сборку, не редактировать приложение/БД; не сливать открытые PR без явного разрешения.
- **Пробелы:** полный экспорт чата и все исходные вложения не доступны; идентичность текущего скриншота и ранее записанной попытки не доказана окончательно. Статус памяти PARTIAL.
- **Следующий шаг:** проверить диффы PR #10/#11 и повторный CI после последних изменений; сообщить пользователю, какие файлы/записи реально включены и какие источники нужно добавить для полноты.

## Handoff continuation — scanner/theme/water and search requirements (2026-10-12)
- Current task remains **memory transfer only**. Do not debug the Android app or build an APK in this task.
- Read `PROJECT_STATE.md`, `TASK_STATE.md`, latest `EVENT_LOG.md` additions and `events.jsonl` events `EVT-20261012-010/011`, `LESSONS.md` IDs `L-RM-013..016`, and `RECIPE_SEARCH_REQUIREMENTS.md`.
- **Confirmed from user feedback for Build39:** native barcode scanning → ask prompt → add/edit form works; repeat scan finds an existing product; auto mode increments quantity. This does not establish later builds still work.
- **Open/NOT VERIFIED:** old WebView scanner white screen; the proposed Build40 rollback to baseline HTML has no confirmed device result; full app-wide WHITE/DARK consistency across status bar, app bar, pages, dialogs, menus, app navigation and Android navigation; repeated scanning should not create duplicate “Вода” entries. User reported three separate Water entries, so this must not be called fixed.
- **Critical distinctions:** water is allowed in the Products catalog; water should not be automatically inserted into Shopping; repeat scan should resolve the existing product. Track these as three separate invariants.
- **Process requirement from user:** carry a dependency/achievement map and done/not-done markers; compare against the known-good baseline before swapping technology; inspect layering/intersections; run the exact acceptance test plus regression tests for previous successes; re-read the original request before reporting completion.
- Recipe search modes and the local-first/search/normalize/validate/add/ingredients/shopping/search-again pipeline, including PDF import, are specified in `RECIPE_SEARCH_REQUIREMENTS.md` but are **not verified as implemented**. The requested interactive HTML prototype is still uncreated/unverified.
- **Source gaps:** full export of all project chats and all historic binaries/diffs/build logs is not available here. Keep memory status PARTIAL. Preserve hypotheses as hypotheses.



## Handoff update — artifact-verification canon (2026-10-12)
- **Current task:** memory transfer only into `agent-knowledge-base`; do not debug app or build APK.
- **New event:** `EVT-20261012-012`; new process lesson: `L-RM-017`.
- **Confirmed new failure:** the issued Build43 ZIP still held `flet-barcode-scanner @ ./flet_barcode_scanner_ext`; user’s actual Flet build log surfaced the same argument and pip rejected it with `Invalid URL ... No scheme supplied`.
- **User-approved mandatory canon:** inspect the exact saved artifact after modification; validate dependencies and consumer path; do not ask user to repeat completed steps before checking own artifact/instructions; each failure must strengthen the preventive verification process.
- **Not done in this memory-only task:** no app edit, no APK build, no new APK claim.
- **Completeness:** PARTIAL because full historical chat export and all original attachment bytes/intermediate diffs are unavailable.


## Handoff — memory continuation / cross-cutting regressions (2026-10-12)
- Continue only the transfer to `agent-knowledge-base`; do not debug the app, edit application/database code, or build an APK.
- User's process requirement: maintain a dependency/achievement map with done/not-done markers; preserve known-good baselines; inspect the full related component/layer graph; test both the reported issue and adjacent previously working flows; compare the final result to the original request.
- Existing canonical records (do not duplicate): EVT-20261012-010 (scanner/theme/water reports), EVT-20261012-011 (process rule), EVT-20261012-012 (bad archive dependency); lessons L-RM-013..017 in `LESSONS.md`.
- `RECIPE_SEARCH_REQUIREMENTS.md` documents three modes, local-first search, shared normalizer, add/skip/search-again and mandatory PDF import. It is a specification, not proof of implementation; requested interactive HTML prototype remains uncreated/unverified in available evidence.
- New EVT-20261012-013/L-RM-018 records a structural mismatch: actual tree contains `LESSONS.md`, no `lessons.jsonl`, despite older handoff references.
- Source completeness remains PARTIAL: full chat export, all original binary attachments and exact diffs for every intermediate build are not available.
- Next: validate this memory-only PR (read-back, JSONL schema/IDs, diff, CI); do not merge without explicit user approval.


## Handoff continuation — HTML/SQLite regression reports (2026-10-12)
- Continue the memory-transfer task only; do not switch into HTML/Android debugging unless the user starts that as a separate task.
- New records: `EVT-20261012-014`, `L-RM-019`, and `HTML_SQLITE_REGRESSION_2026-10-12.md`.
- Confirmed user reports: database recipe addition and KБЖУ disappeared in the latest HTML candidate; delete-recipe and per-100g kcal/protein/fat/carbs also had to be restored relative to `index_db_path(5).html`.
- User normalization contract: generic/white/bulb onion → bulb onion; red/green onion remain distinct; generic rice → long-grain; pilaf/parboiled rice → parboiled; normalize case, ё/е, grammatical cases and word order without false matches against rice flour/oil. Preserve display text separate from pantry lookup key.
- Do not state that a candidate is fixed based only on syntax or static source inspection. Report artifact read-back, runtime, and persistence separately.
- Source completeness remains **PARTIAL**: no complete project chat export, exact diffs between every HTML variant, or independent runtime/persistence evidence for the last link is available.
