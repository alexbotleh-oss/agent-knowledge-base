# RECIPE_MANAGER — проверка переноса памяти

**Дата:** 2026-10-12, Europe/Riga  
**Статус:** PARTIAL; проектная память перенесена, полная история не предоставлена.

## Проверки, реально выполненные

- **GitHub repository metadata:** PASS. Репозиторий доступен, default branch `main`, права push доступны.
- **Протоколы:** PASS. Прочитаны README.md, core/universal_instructions.md, core/agent_runtime_protocol.md, core/memory_model.md, core/session_handoff.md, core/guardrails.md, core/context_interpretation.md, core/autonomy_policy.md, core/stack_registry.json, шаблоны project/task/event/lesson, tools/validate_memory.py, tests/test_memory_validation.py и workflow .github/workflows/validate.yml.
- **Сверка наличия старой памяти:** PASS. В дереве `main` до переноса не было `projects/RECIPE_MANAGER/`; API-запросы существующих предполагаемых файлов вернули 404. Дубликаты с проектными файлами отсутствовали.
- **Проверка новой директории на ветке:** PASS. В дереве ветки находятся README.md, context.md, PROJECT_STATE.md, TASK_STATE.md, EVENT_LOG.md, DECISIONS.md, LESSONS.md, HANDOFF.md и этот файл.
- **Статический аудит содержимого:** PASS на уровне ручной сверки доступного источника. Документы не пустые; SOURCE/provenance и partial/unverified статусы присутствуют; в добавляемых файлах не обнаружены очевидные токены API по простым шаблонам.
- **Количество записей:** EVENT_LOG.md — 7 событий; DECISIONS.md — 6 решений/требований; LESSONS.md — 5 уроков.
- **Проверка приложения:** OUT OF SCOPE по явному требованию пользователя; никакой код приложения не менялся, APK не собирался.
- **Автоматический валидатор knowledge base:** PASS in GitHub Actions (run 38256363073), including `tools/validate_memory.py`.
- **Юнит-тесты/CI:** PASS. Workflow step `Validate memory protocol and records` and `Validate knowledge base and detected stacks` both succeeded.
- **Функциональные тесты Recipe Manager:** NOT RUN и не являются частью этого переноса.

## Пробелы исходных материалов

1. Не доступен полный машинно-читаемый экспорт всех сообщений текущего и предыдущих чатов.
2. Часть прежних HTML/DB/Python-вложений и логов запуска/сборки упоминаются в истории, но нет всех их исходных байтов/точных SHA в этом переносе.
3. Более ранние разговоры известны частично через контекстные сводки. Поэтому даты отдельных этапов указаны только там, где они выводятся из доступной проектной истории.
4. Предыдущие утверждения ассистента об успешных исправлениях синтаксиса/сборки не считаются независимым доказательством успешной функциональной проверки.
5. Точная первопричина последнего сбоя списка рецептов и работоспособность предложенного HTML не подтверждены запуском/регрессией.

## Условия закрытия переноса

- Открыть PR на эту ветку без merge.
- Проверить изменённые файлы и результат CI.
- Если CI не запустился или отсутствуют автоматические проверки для Markdown, обозначить это, а не подменять PASS.
