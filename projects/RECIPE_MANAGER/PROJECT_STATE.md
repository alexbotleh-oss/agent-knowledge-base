# PROJECT_STATE — RECIPE_MANAGER

- **Название:** «Что приготовить» — Recipe Manager Android
- **Обновлено:** 2026-10-12 (Europe/Riga; текущая локальная дата указана системным контекстом)
- **Достоверность состояния:** partial
- **Репозиторий / основной источник приложения:** точный репозиторий приложения в доступных сведениях не установлен; известна локальная папка пользователя `C:\\RecipeManager_update`
- **Ветка и HEAD-коммит приложения:** unknown; не сообщать SHA без проверки исходного репозитория
- **Рабочее дерево:** unknown; локальная папка пользователя недоступна для проверки в этой сессии
- **Цель проекта:** приложение для ведения рецептов, продуктов и списка покупок на Android и ПК, с базой рецептов SQLite и интерфейсом на Flet
- **Текущая цель:** продолжить диагностику Android-приложения; по последнему переданному материалу — проверить платформенную навигацию (Android: 5 кнопок, ПК: 6 разделов) после двух неудачных сборок. Отдельно ранее отмеченная проблема чёрного экрана остаётся неподтверждённой как решённая
- **Критерии завершения текущей цели:** приложение запускается на целевом Android-устройстве, вместо чёрного экрана отображается ожидаемый интерфейс, доступны основные вкладки и данные; результат подтверждён фактическим запуском/скриншотом и проверкой основных сценариев
- **Активные ограничения и обязательства:**
  - Не переделывать интерфейс Android на текущем этапе; пользователь явно отложил эту работу до завершения отладки.
  - Не добавлять сейчас сканирование DataMatrix/штрихкодов и интеграции с каталогами.
  - Не считать APK успешно собранным или исправленным, пока это не подтверждено реальным запуском на устройстве.
  - Не перезаписывать пользовательские данные, базу, иконку и локальные правки; сначала проверить исходное состояние и сделать обратимую контрольную точку.
  - Изменения должны быть небольшими, проверяться последовательно, с регрессией связанных функций.
  - Не утверждать, что отдельное ядро контроля определённой версии активно в данном проекте: имеющиеся упоминания версий относятся в том числе к другим проектам и не подтверждают текущую установку.
- **Текущий этап и почему:** Android-отладка до улучшения UI; последний прямой ответ пользователю закрепил этот порядок работ.
- **Подтверждённо завершено (по доступной истории, не является состоянием текущей сборки):**
  - В проекте имеется Python/Flet-основа с SQLite; упоминались Flet 1.0.1 и зависимость `flet>=1.0,<2`.
  - В одном из последних локальных кандидатов `/mnt/data/main.py` успешно проходил `python -m py_compile`; это не доказывает сборку APK или корректный Android-запуск.
  - Пользователь ранее подтвердил работоспособность общего исправления hover-кнопок.
  - Пользователь сообщил, что `seed_data.py` был вручную возвращён в локальную папку и после этого `flet run main.py` заработал.
- **Изменено, но не подтверждено на текущей точке:**
  - ZIP `/mnt/data/RecipeManager_final_before_apk.zip` описывался как пакет с `main.py`; актуальность и состав файла сейчас не перепроверены.
  - Упоминались `pyproject.toml`, иконка `assets/icon.png`, `build_number=3` и Android package `ru.recipe.manager`; их текущее состояние следует сверить с локальными исходниками.
  - Существуют ранее подготовленные изменения Flet-кода (обновление ListView, буфер обмена, шаги количества покупок и др.), но нельзя считать, что все они входят в установленный пользователю APK.
- **Известные ошибки/риски:**
  - Текущая проблема Android: чёрный экран / ожидаемая отладка запуска; точная причина по доступной истории не установлена.
  - Ранее возникала ошибка Flet: `PopupMenuItem.__init__() got an unexpected keyword argument 'text'` (сообщение/трассировка от 2026-09-27 в сохранённых выдержках).
  - Ранее после изменений в HTML-проекте терялись добавление рецептов из БД, удаление рецепта и отображение КБЖУ; это отдельный исторический веб-контур, не доказательство текущего APK-дефекта.
  - Риск потерять `seed_data.py` или другие пользовательские файлы при копировании/сборке.
- **Решения, которые остаются в силе:**
  - Отладка Android предшествует любым визуальным улучшениям.
  - Новую возможность сканирования товаров обсуждать позже; пока только сохранить проектное намерение в истории.
  - Текущие рабочие функции сохранять и проверять регрессией.
- **Применимые уроки:** см. `LESSONS.md` и `../../lessons/global/LESSONS.md`; IDs в журнале.
- **Следующий логичный шаг и обоснование:** получить/проверить точный текущий набор исходников и конфигурацию сборки, сверить последние логи Android-запуска/сборки, определить где появляется чёрный экран (стартовый экран Flutter/Flet, загрузка Python-приложения, ошибка инициализации/БД), затем сделать один минимальный диагностический патч и проверить на реальном устройстве.
- **Связанные файлы:** TASK_STATE.md, EVENT_LOG.md, DECISIONS.md, LESSONS.md, HANDOFF.md, events.jsonl, lessons.jsonl
- **Ограничение истории:** полная история всех сообщений и вложений чата недоступна как единый архив. Этот снимок основан на доступном контексте, сводках недавних разговоров и записях о файлах; пробелы явно сохранены как unknown/partial.


## Новое наблюдение — платформенная навигация (2026-10-12)
- Из переданного ответа другого чата: после двух неудачных сборок предложено проверить вызов `apply_platform_nav()` до первого `render_home()` и оставить `on_connect` дополнительным обновлением.
- Это не подтверждённая причина. Требуется проверить поведение Flet 1.0.1, момент доступности платформы и обновление `nav.destinations`.
- Критерии: Android — ровно 5 кнопок; ПК — все 6 разделов. `recipes.db` и логику рецептов не изменять.
- Не скрывать исключения платформенного определения через `except Exception: pass`.
- Патч и логи двух сборок в полученном материале отсутствуют; успешное исправление не подтверждено.

## Дополнение по результату текущего чата (2026-10-12)
- **Подтверждено по локальным выводам/сообщению пользователя:** `python -m py_compile .\main.py` вернулся без вывода; `python .\main.py` запустился на ПК; `flet build apk` для заявленного build 5 завершился сообщением `Successfully built your .apk for Android!`.
- **Подтверждённое отрицательное наблюдение:** пользователь сообщил, что установленный APK 5 всё ещё показывает шесть кнопок внизу. Требование Android=5 не выполнено.
- **Важное различие:** предложенный пользователем вариант `apply_platform_nav()` до первого `render_home()` виден в прикреплённом `main(7).py`, но из текущего чата нельзя подтвердить, что он был применён к локальному `main.py`. В выполненной последовательности на ПК/в APK использовалась версия с `page.on_connect = handle_page_connect`.
- **Статусы:** Python syntax — PASS для локального файла в момент проверки; desktop run — PASS по сообщению пользователя; APK packaging — PASS по выведенному логу; mobile nav acceptance — FAIL; первопричина — UNKNOWN. Содержимое `pyproject.toml` независимо не перечитано, поэтому точный build_number файла остаётся частично подтверждённым.

## Память исторических инцидентов (2026-10-12)
- Доступная реконструкция сентябрьских проблем HTML/SQLite дополнена событием EVT-20261012-006, ссылающимся на EVT-20260922-001 и EVT-20260927-001.
- Требования к ингредиентам, импорту food.ru/1000.menu, удалению и КБЖУ являются пользовательскими требованиями/сообщёнными симптомами; реализация и окончательные проверки старых фиксов не подтверждены.
- Полная история остаётся PARTIAL: доступны сводка и отдельные сообщения/имена файлов, но не все первичные исторические материалы.
- **Memory follow-up (2026-10-12):** the separate Flet packaging attempt is documented in `BUILD_PACKAGING_ATTEMPT_2026-09-22.md` and `EVT-20261012-008`. The attempt reached `Packaging python app...` after an earlier `git`/engine-version failure, but no terminal build success or APK artifact was confirmed. Do not treat this as the earlier `build_number 5`/Android-navigation attempt.


## Memory-transfer continuation — current chat reconciliation (2026-10-12)
- **Current task:** transfer all available project experience from the present chat to `agent-knowledge-base`; this is a memory-only task, not Android troubleshooting.
- **Source status:** PARTIAL. The currently attached `Сборка APK продолжается.txt` only provides a limited continuity excerpt; the complete conversation export and all prior binary/source attachments are not available in this session.
- **Screenshot evidence:** one PowerShell window showed `Packaging python app...`; a second window held an unfinished `Get-Process ... |` pipeline. The command did not produce process measurements, so CPU/activity and whether the build was hung remain unknown.
- **Deduplication:** do not create a second packaging incident for the same apparent screenshot chain unless primary chronology establishes it is distinct. Existing `EVT-20261012-008` and `L-RM-011` remain the canonical record; current transfer boundaries are recorded in `EVT-20261012-009`.
- **User boundary:** do not modify application code/data or build an APK during memory transfer. Do not merge these memory PRs without explicit approval.

## Memory follow-up: scanner, theme, water and recipe-search scope (2026-10-12)
- **Source completeness:** PARTIAL. The current available chat includes the user's direct narrative and Build39 screenshots, plus a summary of preceding Build29–Build42 interactions. Exact source diffs for all intermediate builds are not all present here.
- **User-verified native scanner paths:** Build39 feedback confirms scan → ask/add prompt → add/edit form, repeat scan finds existing product for editing, and automatic-add mode increments quantity. These are scenario reports from that version, not proof about a later APK.
- **Unresolved scanner issue:** legacy WebView opened a white screen after changing scanner engine; Build40's return to prior SCANNER_HTML was asserted, but no confirmed device test is available. Do not mark the old scanner fixed until tested.
- **Water regression:** user reported three separate «Вода» entries after repeat scans. Keep the distinct rules: water can be stored in Products; water should not automatically generate a shopping item; repeat scan should find the existing product. Root cause and fix remain UNKNOWN/NOT VERIFIED.
- **UI theme regression:** Build39 screenshots showed a dark work area/top application bar but a white bottom app NavigationBar. The user explicitly corrected the bottom-only analysis: audit every menu, app bar, content/cards/forms/dialogs, Android status bar, app navigation bar and Android system navigation area. Exact low-level cause remains unverified.
- **User process rule:** use a dependency/achievement tree and persistent status markers; preserve verified baselines; test old working paths before replacing them; inspect component layers and intersections; test all related UI/menu states and regressions; compare final results against every initial requirement before reporting done.
- **Recipe search/PDF import:** detailed in `RECIPE_SEARCH_REQUIREMENTS.md`. These are requirements, not implemented features. The requested interactive HTML workflow prototype was not created/verified in the available history.
- **Scope:** memory transfer only. No app source/database was edited and no APK was built for this transfer.

## Unique experience from the Build39–Build42 discussion (2026-10-12 transfer)
- User-verified for Build39 only: native scanner scan/ask/add/edit/repeat-scan/automatic-increment flow worked according to user feedback.
- Still unverified: legacy WebView white screen after engine switch; Build40 intended rollback to canonical old scanner HTML but lacks a successful device test; app-wide theme behavior across all menus and Android system chrome; repeat scan deduplication for water.
- Observed failure: user reported three separate `Вода` entries after repeated scanning. Keep catalog inclusion, shopping exclusion, and repeat-scan identity resolution as separate requirements.
- Process lesson from user: do not solve only the most visible widget; keep dependency/achievement markers and previous known-good baselines, inspect component/layer intersections, run full related regressions and re-check against the original request.
- Search workflow requirements, including mandatory PDF import, are in `RECIPE_SEARCH_REQUIREMENTS.md`; this records desired behavior only, not implementation status.

## Verification status map for current memory transfer
| Item | Status | Evidence / open condition |
|---|---|---|
| Build39 native scanner paths (ask/add/edit/repeat/add-quantity) | USER-REPORTED PASS for that build only | EVT-20261012-010; not extrapolated to later builds |
| Old WebView scanner | NOT VERIFIED / prior failure reported | White screen after engine change; Build40 rollback was not device-confirmed |
| Theme across all UI/system layers | FAIL / NOT VERIFIED | Dark screenshot showed white app NavigationBar; full layer matrix not tested |
| Water product persistence | Prior desired fix claimed, incomplete outcome | Repeat scans produced three separate entries |
| Water excluded from Shopping | Existing requirement; current APK behavior not re-tested | Must test independently of Products presence |
| Repeat-scan product identity/deduplication | FAIL by user report | Same water code/name was added as multiple entries |
| Recipe search modes and PDF import | SPECIFIED, IMPLEMENTATION NOT VERIFIED | `RECIPE_SEARCH_REQUIREMENTS.md` |
| Complete chat/binary source export | NOT AVAILABLE | Transfer remains PARTIAL |

Events `EVT-20261012-010/011` and lessons `L-RM-013..016` preserve the newly reconciled details and process rule. No app test/build was run for this documentation-only continuation.



## Memory transfer update — confirmed packaging/archive regression (2026-10-12)
- New incident/canon is recorded as `EVT-20261012-012`; prevention lesson `L-RM-017`.
- Confirmed from archived `pyproject.toml` inspection and user's build output: the artifact still supplied the relative extension path to pip, causing packaging failure before APK compilation.
- Required future behavior: inspect exact persisted artifact, SHA/content/dependencies and the actual consumer command before claiming it fixed; state unverified runtime separately.
- App code/build remains out of scope for this memory transfer.
- Transfer completeness remains PARTIAL; full archive of all chats and all historic binary attachments unavailable.


## Статус memory transfer — 2026-10-12
- Текущая активность в этом чате — перенос памяти, не отладка приложения. Пользователь явно вернул задачу в `agent-knowledge-base`.
- Источник PARTIAL: доступный фрагмент чата/сводка, два скриншота Build39, отдельные имена/архивы и документы памяти; не полный экспорт всех разговоров и бинарных приложений.
- Открытые статусы для будущей отдельной работы: old WebView white screen не решён/не проверен; полная тема не считается исправленной правкой только нижней панели; вода в каталоге, исключение из покупок и идентичность при повторном сканировании — разные инварианты, при повторном скане пользователь сообщил о дублях. См. EVT-20261012-010 и L-RM-013..016.
- Структурное наблюдение: фактическое дерево содержит `LESSONS.md`, но не `lessons.jsonl`; записано в EVT-20261012-013/L-RM-018.
- Ни одну заявленную правку старого сканера/темы/воды не считать подтверждённой без прямого результата.
- Код приложения, продуктовая БД и APK не изменялись/не собирались.


## Memory-transfer update — HTML/SQLite regressions (2026-10-12)
- Event `EVT-20261012-014` records the latest user-reported loss of database recipe addition and nutrition display, plus the request to restore delete recipe and per-100g nutrition from `index_db_path(5).html`.
- Lesson `L-RM-019` requires the exact saved HTML candidate to be checked against the reference and the real import/add, delete/persistence, edit and nutrition paths; syntax/static inspection alone is not sufficient.
- Ingredient matching requirements are listed in the new event and `HTML_SQLITE_REGRESSION_2026-10-12.md`; do not infer the code now implements them.
- Source history remains PARTIAL: full chat export and all intermediate candidate diffs/runtime evidence are unavailable.
- This memory-transfer task made no HTML/database/application changes and did not build an APK.


## Memory-only status — package validation incident (2026-10-12)
- Added `EVT-20261012-015` and `L-RM-020`.
- User's Flet log fails during pip installation of local extension; no APK success. Assistant admits it called the archive ready without testing actual extension install through the Flet consumer path.
- Related to but distinct from `EVT-20261012-012`; preserve both chronology entries.
- Newly reinforced required controls: source/input inventory; dependency closure; exact artifact read-back; SHA/file-manifest comparison; include/exclude accounting; real consumer-path test; STOP on mandatory FAIL/BLOCKED; request missing source when unresolved; per-change file/line/context provenance.
- Root cause UNKNOWN. No application source, extension, database or APK changed in this memory transfer.
- Completeness remains PARTIAL because full chat export and complete binary/archive history are not available.

## Memory-transfer continuation — Stage14 recipe-manager HTML/PWA and scanner boundary (2026-10-12)
- **Current task for this branch:** memory-only transfer. Do not continue app debugging, edit HTML/JS/DB, or build APK in this task.
- **Source distinction:** Stage14 is a UI/mechanics reference; its six recipe-card names/data are generated placeholders. User clarified that actual recipe content should come from v21 (web-derived data). Do not use the generated Stage14 card labels as canonical recipe semantics.
- **Confirmed Stage14 interaction tests from prior user responses:** product-context-menu actions work after the event-handler fix; Shopping interactions, recipe long-press/context menu, and swipe navigation were reported working on the verified Stage14 candidate. The exact immutable local snapshot was documented with SHA-256 `a535f15973fc5d8672654296824d89c7aa3958901882af6ff45cd63ae26cd387`; the later remote main camera patch is a separate artifact and must not be treated as covered by that earlier E3 confirmation.
- **Camera attempt status:** user reported on the live HTTPS/PWA page that it requested camera permission and showed an image, but presenting a code did not result in recognition and the camera kept running. Camera permission and video display are confirmed; decoding and stop-on-detection are FAIL/UNVERIFIED. Exact failure point is unknown because no camera diagnostic export or decode trace was captured. No fix is established.
- **Known diagnostic exploration:** local Android `content://` variants V5–V9 loaded quickly and reported no JS exceptions; diagnostic logs showed one active home screen. Tailwind toggling and Service Worker off/on did not establish a cause. This was not proof of camera decode correctness. Next step in any separate authorized debugging task: capture the actual HTTPS page's camera diagnostics and inspect `BarcodeDetector` support/formats, detected-result count/rawValue and error events before changing code.
- **History completeness:** PARTIAL. All original intermediate HTML candidates/diffs and full chat export are not available in this transfer. Preserve this as an additional chronological fact; don't replace earlier core30–34 events.

## Memory-transfer update — PWA Products/Shopping interaction regression (2026-10-12)

- **Confirmed user report:** after filtering Shopping, unit labels appeared in Latin; the user confirmed core32 corrected the labels in the demonstrated scenario. No claim is made for all unit cases.
- **Current failure from the latest direct user report:** Products category/sort sheets display options, but tapping an option does not produce the expected filtered/sorted list. The user reported this after core33 and again after core34; prior assistant claims that it was fixed are unverified.
- **Root cause:** UNKNOWN. No runtime event trace or code diagnosis was performed in this memory-only task.
- **State:** Shopping display fix = USER-CONFIRMED for shown scenario; Products selection = FAIL; cause = UNKNOWN.
- **Scope:** memory transfer only; no PWA/HTML/JS/database change and no APK build.
