# EVENT_LOG — RECIPE_MANAGER

Хронология ниже — реконструкция по доступным сообщениям, сводкам и вложениям, а не полный экспорт чата. Даты указаны только там, где они видны в источниках. Время, не известное из источника, не выдумывается. Машиночитаемые записи связаны с событиями в `events.jsonl`.

## 2026-09-22 — Рецепты из БД и нормализация ингредиентов
- **Требование:** импорт/добавление рецептов из SQLite и HTML-интерфейса, корректное распознавание ингредиентов по регистру, перестановке слов и падежам.
- **Материалы, видимые в истории:** `index_db_path(4).html`, `recipes(2).db`, `Что приготовить 22_исправлена_логика_ингредиентов(1).htm`; в последующих сообщениях также были варианты HTML и БД.
- **Наблюдаемые регрессии:** список рецептов не пополнялся после добавления из БД; в другой итерации пропали удаление рецепта и КБЖУ/ккал на 100 г.
- **Статус:** исторические проблемы подтверждены пользовательскими сообщениями; точные версии исправленных файлов и последняя проверка не доступны в текущем архиве.

## 2026-09-22 — Импорт с сайтов и Android-сборка
- **Цель:** собрать Android-приложение на основе базы рецептов и интерфейса с помощью Flet и FastAPI; ранее назывался импорт с food.ru и 1000.menu.
- **Наблюдение:** пользователь сообщал о длительном ожидании процесса сборки и переходе на другой ПК без ожидания завершения.
- **Статус:** точные логи процесса и окончательный результат той попытки в доступной истории отсутствуют.

## 2026-09-27 — Несовместимость PopupMenuItem
- **Симптом:** `PopupMenuItem.__init__() got an unexpected keyword argument 'text'`.
- **Источник:** сообщение пользователя с трассировкой из `flet\app.py`, в котором ошибка возникает при создании сессии и вызывает `main.py`, строка около 4748.
- **Смысл:** реализация использовала параметр, которого установленная версия API Flet не принимала.
- **Ограничение:** факт конкретной ошибки установлен; окончательный патч/проверка версии Flet в текущей выдержке отсутствуют.

## 2026-10-07 — Проектная память и база знаний агента
- **Общий контекст:** пользователь уделяет особое внимание непрерывности состояния между чатами, происхождению сведений, сохранению причинно-следственных связей, разделению общей памяти и памяти проекта, обратимости удаления и защите памяти от потери.
- **Примечание:** это общие предпочтения проектного контекста, не свидетельство версии Android-кода.

## Последняя доступная рабочая итерация (точная дата в отдельных изменениях неизвестна; сведения из сводки)
- Локальная папка приложения: `C:\\RecipeManager_update`.
- `main.py` кандидат по пути `/mnt/data/main.py`, 193,705 байт, ранее прошёл `python -m py_compile`.
- `RecipeManager_final_before_apk.zip` описывался как архив примерно 47,837 байт, содержащий только `main.py`.
- Известны предыдущие материалы `main_new.py`, `main(2).py`, `main_BEFORE_REFRESH_SCROLL_FIX.py`, `seed_data.py`. Последний из них, согласно пользовательской истории, был возвращён в локальную папку вручную, после чего `flet run main.py` заработал.
- `pyproject.toml` по сводке: Flet dependency `flet>=1.0,<2`, version 1.0.1, module `main.py`, Android package `ru.recipe.manager`, build number 3; файл не сверялся в текущем сеансе.
- Изменения логики UI и данных, отмеченные в предыдущей сводке:
  - вода исключена из ряда расчётов/каталога/списка покупок;
  - удаление рецепта доступно в карточке списка рецептов, но не в карточке готовки;
  - верхняя строка оформлена с SafeArea и дополнительным отступом;
  - обновление вкладки переиспользует имеющийся ListView, чтобы сохранить прокрутку при локальных изменениях;
  - счётчик продуктов обновляется через маркер данных;
  - шаги изменения количества в покупках заданы по единицам и диапазонам;
  - буфер обмена переведён на async `ft.Clipboard().set/get` для Flet 1.x;
  - общий hover overlay переведён в ARGB-формат.
- Важно: это сведения сохранённой сводки. Текущий файл, наличие каждого патча и фактическая работа в текущем APK заново не проверены.

## 2026-10-12 — Зафиксирован правильный порядок работ
- **Требование пользователя:** «нет исправление интерфейса андроид, к этому мы вернемся после его отладки».
- **Результат:** ассистент подтвердил, что UI Android не трогается до завершения отладки текущего APK; первоочередно проверяются чёрный экран/запуск.
- **Статус:** решение подтверждено непосредственно в текущем чате.


## 2026-10-12 — Диагностика платформенной навигации после двух неудачных сборок
- **Источник:** переданные пользователем тексты ответа из чата Recipe Manager; они принесены для переноса опыта в `agent-knowledge-base`.
- **Сообщённый контекст:** две сборки не дали ожидаемого результата; точные логи и причины не приложены.
- **Предложенное направление проверки:** `apply_platform_nav()` должен применяться до первого `render_home()`, а `on_connect` может остаться дополнительным обновлением. Это гипотеза для проверки, не установленная первопричина.
- **Что проверить:** в Flet 1.0.1 момент доступности платформы; отражение изменений `nav.destinations` в уже созданном UI; Android должен показывать 5 кнопок, ПК — все 6 разделов.
- **Ограничения:** не трогать `recipes.db` и логику рецептов; не скрывать ошибки через `except Exception: pass`; перед новой сборкой проверить код/патч и запуск на ПК.
- **Текущий результат:** сам патч не был приложен в переданном материале; исправление, синтаксис, сборка и работа на телефоне не подтверждены. Первопричина остаётся unknown.

## 2026-10-12 — APK build 5 собран, мобильная навигация всё ещё не соответствует критерию
- **Источник:** сообщения пользователя и команды, выполненные в текущем чате.
- **Команды/результаты, сообщённые непосредственно:** `python -m py_compile .\main.py` завершилась без вывода; пользователь запустил `python .\main.py` и сообщил «запустилось»; сохранена копия `pyproject.toml` как `pyproject_BEFORE_BUILD_5.toml`; команда изменения `build_number` сообщила «build_number установлен: 5»; `flet build apk` выдал `Successfully built your .apk for Android!` и сообщил копирование в `build\apk`.
- **Фактический результат устройства:** пользователь сообщил, что в APK 5 в нижней панели по-прежнему шесть пунктов, включая «О программе», а не ожидаемые пять.
- **Что это доказывает:** синтаксис локального `main.py` прошёл проверку, запуск на ПК состоялся, упаковка APK завершилась без ошибки согласно выводу. Критерий Android-панели не достигнут.
- **Что не доказывает:** не подтверждает первопричину; не подтверждает, что приложенный `main(7).py` был применён к рабочему `main.py`; не подтверждает исправление проблемы чёрного экрана.
- **Следующее действие памяти:** сопоставить текущий рабочий исходник с приложенным `main(7).py` и сохранить точный статус применённого патча. Не собирать APK повторно без новой проверяемой гипотезы.

## 2026-10-12 — Сверка доступной исторической памяти (реконструкция)
- **Цель:** сохранить недостающие детали сообщений за сентябрь, не дублируя события EVT-20260922-001 и EVT-20260927-001.
- **Добавлено:** симптомы импорта/добавления рецептов из БД, потери удаления/КБЖУ, требования к нормализации ингредиентов и импорту food.ru/1000.menu связаны с EVT-20261012-006.
- **Источники:** доступная сводка проекта и отдельные сообщения о вложениях/ошибке. Полный экспорт всех чатов и вложений отсутствует.
- **Статус:** PARTIAL; исправления, версии файлов и причины старых регрессий не подтверждены.

## 2026-10-12 — HTML prototype product scope/category regression (v16–v19)
- **Scope:** browser/HTML prototype review only. This is not evidence about active Flet Android code.
- **User-visible facts from screenshots and direct user reports:**
  - The user observed that expired butter was shown mid-list; after the v18 iteration the user reported expired items were now at the top and grouping appeared.
  - A household item, “Туалетная бумага 8 рулонов”, was initially in the household/other context, then the user reported it had moved to “прочее продукты”; it was absent from “Продукты питания” but present in the all-items view.
  - The user reported that the category menu did not allow category changes and that manual product entry did not provide a working way to assign/change food vs non-food classification.
  - After an assistant response claimed v19 had repaired selection and category editing, the user clarified that the response still missed the request: either manual add must allow choosing a non-food category at creation, or the existing product UI must have a working checkbox/toggle to reclassify it as non-food. They explicitly said the checkbox does not work.
- **Iteration history visible in this chat:**
  - v16: file was audited; observed gaps included category naming inconsistency, no real camera scanner/OFF integration, partial V3 data model, and substring-style alias matching. These were audit observations, not full interaction-test results.
  - v17: file name `Что_приготовить_v17_core_aligned.html`; static checks were reported as JavaScript syntax pass, 268 div pairs, 129 unique IDs, 138 inline handlers. Full Chromium runtime did not complete due environment/DBus; therefore no full browser interaction pass was established.
  - v18: file `Что_приготовить_v18_product_scope_fix.html`; assistant reported expired-first sort and a migration for known household goods. The user later verified the expired-first behavior but reported the category selection/reclassification flow still did not work correctly.
  - v19: file `Что_приготовить_v19_category_edit.html`; assistant claimed the category was written on create/add and editing had a message. No user confirmation of success exists. The user's immediate correction explicitly says the requirement was misunderstood and the checkbox still does not work.
- **Status of fixes:** expiry ordering is user-confirmed improved; category assignment/reclassification remains FAIL by latest user report. No claim of end-to-end HTML test success is supported.
- **Cause:** not established. Likely areas to inspect later are whether the manual-add form exposes/persists a classification control, whether the edit control is wired to the persisted `kind` field, and whether filter state hides an item after change. These are hypotheses, not confirmed code findings because the latest HTML wasn't re-opened and runtime-tested in this memory-only task.
- **Timeline correction:** the available summary dates v16 audit/v17 and follow-on category work to the period leading up to 2026-10-12; exact timestamps for individual HTML versions were not independently read from the files. Do not treat v17 as a fully approved interface; it was a static-checked prototype with browser runtime blocked.
- **Evidence/provenance:** current chat dated 2026-10-12; attached phone screenshots showing food list and “Туалетная бумага 8 рулонов” under “Прочее”; user reports about v18/v19 behavior; attachment names v16, v17, v18, v19 visible in conversation/summaries.
- **Important boundary:** the explicit current user task is to transfer memory to this repository; do not debug or change application files while performing this transfer.
