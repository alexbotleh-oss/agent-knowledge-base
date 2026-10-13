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
