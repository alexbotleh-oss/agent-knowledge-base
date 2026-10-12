# RECIPE_MANAGER — журнал событий (append-only)

Этот перенос построен из доступного контекста/сводки и двух диагностических JSON, а не полной необработанной выгрузки сообщений. Временные метки приводятся только там, где доступны.

## EVT-RM-20260922-001 — Требования базы, импорта и ингредиентов
- **Статус:** требования пользователя подтверждены; реализация unknown.
- **Событие:** пользователь задал правила нормализации, импорт Food.ru/1000.menu, функциональность базы, КБЖУ и покупок.
- **Источник:** сводка истории от 2026-09-22. Упомянуты `index_db_path(3).html`, `Что приготовить 22_исправлена_логика_ингредиентов.htm`, `recipes(1).db`; исходные байты здесь не перечитаны.

## EVT-RM-20260927-001 — Flet PopupMenuItem API exception
- **Статус:** observed; fix not confirmed.
- **Событие:** `PopupMenuItem.__init__() got an unexpected keyword argument 'text'`; traceback указывал на main.py line 4748.
- **Источник:** сообщение пользователя около 2026-09-27; исправление и проверка неизвестны.

## EVT-RM-20260930-001 — Core Lite baseline и diagnostic path
- **Статус:** из доступной проектной сводки.
- **Событие:** Core Lite lane D; reference → read → one patch → build → device test → evidence; проверки C1–C9 плюс C6b.
- **Baseline:** `RecipeManager_CAMERA_DIAGNOSTIC_v3_1_12_3_COMPLETE_20260930(1).zip`; ZIP SHA-256 `85850905c12f367d53fc311f34db4efef8db56804d7c18d68e49acea0bdb886b`; main.py SHA-256 `20987d735c60b21ab08d7fc915990e088ce1e5bf41b901f40eaf4dc039e6e191`; build_number 45.
- **Путь диагностики:** `diagnostics.py` `_data_dir()` настроен на root `diagnostics.json`, текст в `main.py` обновлён. Архив `RecipeManager_CAMERA_DIAGNOSTIC_v3_1_12_3_CORE_LITE_20260930.zip`, SHA-256 `d6e11128fd94c224b12d0eefd0fc0ff661da9d0da4beade42494e7fc8dc7ece7`. По сводке ZIP test и Core Lite C1–C9+C6b PASS; targeted py_compile main.py и diagnostics.py PASS. Полный py_compile прерван после 60 секунд, не считать PASS.
- **Источник:** сохранённая проектная сводка; baseline ZIP здесь заново не скачивался.

## EVT-RM-20260930-002 — JNI FIX1 APK build
- **Статус:** APK_BUILD_CONFIRMED.
- **Событие:** сборка падала из-за JNI mismatch: generated bindings требовали jni ^1.1.0, но override фиксировал 1.0.0.
- **Исправление:** override jni 1.1.0; build number 47 → 48.
- **Результат:** предоставленный build log показывал `jni 1.1.0 (overridden)`, `mobile_scanner 7.4.2` и `Built build\\app\\outputs\\flutter-apk\\app-release.apk (151.9MB)`.
- **Источник:** ранее в истории назван `Вставленный текст(10).txt`; здесь не перечитан заново.

## EVT-RM-20261001-001 — ORIGIN probe оставил белый экран
- **Статус:** white-screen observed; cause unknown.
- **Событие:** после APK JNI FIX1 экран старого сканера был белым. Диагностика сообщала CAMERA permission GRANTED, WebView created, local HTML load с base_url `https://unpkg.com/` и URL event `about:blank`; camera-denied, scan и native fallback не наблюдались.
- **Гипотеза:** HTTPS-like base origin может изменить доступ getUserMedia по сравнению с file://, опираясь на исторический main_11_UI_final.py. Не подтверждена; визуальный рендер не доказан.
- **Источник:** сохранённая сводка; прежняя диагностика заново не перечитана.

## EVT-RM-20261001-002 — PROBE1 тест рендера невалиден
- **Статус:** invalid test confirmed.
- **Событие:** `diagnostics_probe1.json` содержал `SCANNER_HTML_LOAD_FAILED` с сообщением об отсутствующем локальном html5-qrcode bundle и просьбой запустить `PREPARE_LEGACY_SCANNER.ps1`.
- **Результат:** probe HTML не был загружен; этот белый экран не диагностировал render engine.
- **Источник:** сводка, ранее связанная с turn76file0; файл заново не прочитан.

## EVT-RM-20261001-003 — PROBE2 цепочка дошла до load_html
- **Статус:** наблюдения напрямую подтверждаются доступным JSON; реальный рендер не подтверждён.
- **Событие:** session `cfddc99adaa8`, export 2026-10-01T06:22:49Z, Android 16 arm64, Flet 1.0.3. Permission returned `PermissionStatus.GRANTED`; есть `SCANNER_VIEW_OBJECT_CREATED`, `SCANNER_PAGE_UPDATE_DONE`, `SCANNER_LOAD_TASK_STARTED`, `SCANNER_WEBVIEW_RENDER_PROBE`; URL events включают `https://unpkg.com/` и `about:blank`.
- **Результат:** permission request не зависает в этой сессии; view создаётся, load_html учтён без зарегистрированного исключения; отображение HTML не доказано.
- **Источник:** пользовательский файл `diagnostics_probe2 (1).json`.

## EVT-RM-20261001-004 — PROBE3 marker events отсутствуют
- **Статус:** отсутствие событий подтверждено JSON; объяснение unknown.
- **Событие:** session `6afcf0d623e8`, export 2026-10-01T07:57:09Z. Есть GRANTED, создание view, page.update, начало load и `SCANNER_WEBVIEW_RENDER_PROBE`; пользователь сообщил белый экран.
- **Наблюдение:** `diagnostics_probe3.json` не содержит `SCANNER_HOST_MARKER_START/ADDED/UPDATED`, хотя предыдущий отчёт о ZIP PROBE3 сообщал, что код маркера есть.
- **Результат:** неизвестно, исполнялся ли ожидаемый код. Wrong source/build/APK остаётся гипотезой.
- **Источник:** пользовательский `diagnostics_probe3.json`.

## EVT-RM-20261012-001 — Перенос опыта в память
- **Статус:** in progress until PR checks.
- **Событие:** в main был `projects/CARD`, но отсутствовал `projects/RECIPE_MANAGER`.
- **Действие:** создана ветка `memory/recipe-manager-experience-20261012`; проектная память пишется туда. main не меняется.
- **Пробел:** полная история и не все исторические вложения доступны.
