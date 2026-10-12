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

## Важные ограничения
1. Полная выгрузка всех чатов и всех бинарных вложений не доступна; статус PARTIAL, не COMPLETE.
2. Причины Android/WebView white screen, отсутствия PROBE3 markers, scanner decode failure и package path errors остаются UNKNOWN там, где нет прямого доказательства. HTML/SQLite регрессии принадлежат отдельному HTML-контуру и не должны описываться как дефекты APK.
3. Успешный syntax/targeted check/CI/build не приравнивается к end-to-end runtime на ПК/телефоне.
4. EVT-20261012-007 отсутствует в доступной последовательности событий; это пробел нумерации, не доказательство потери записи.
5. Исходные PR #17/#19/#20/#21 остаются открытыми и не переписаны; этот rollup — отдельная консолидированная ветка.
- **Structured lessons gap:** the consolidated RECIPE_MANAGER chain keeps LESSONS.md as the canonical human-readable lesson index. No lessons.jsonl was synthesized: older branches disagree about its presence/content, and generating 24 structured records from summaries without a source-aligned mapping would create unsupported precision. This is an explicit gap for a later schema-backed conversion.
