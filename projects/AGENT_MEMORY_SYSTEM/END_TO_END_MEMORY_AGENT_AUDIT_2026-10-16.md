# Сквозной аудит механизма памяти и непрерывного агента — 2026-10-16

## 1. Цель и границы аудита

Цель — восстановить полную цепочку проектирования и реализации: от исходной архитектуры непрерывного агента до импортёра, канонической памяти, индексов, восстановления сессии, выбора опыта и управления возвратом к активной цели. Отдельно зафиксировать, что реализовано, что проверено только на синтетических данных, что осталось спецификацией и какие противоречия возникли между кодом и документами после последовательных правок.

Аудит сверяет:

- интеграционную ветку `integration/memory-core-clean-20261015`, HEAD `d3f9c610b7865793960dc652c2ccccc88afef732`;
- отдельный draft PR #28, HEAD `b6d32a3c36aa5df8079f63aad20fd41a8f56c512`, который добавляет UMC-03 evaluator и decision frontier, но ещё не входит в ветку PR #27;
- архитектурные контракты `core/continuous_agent_architecture.md`, `core/agent_runtime_protocol.md`, `core/unified_memory_control_loop.md`, `core/source_ingestion_protocol.md`, `core/memory_model.md`, `core/memory_write_contracts.md`;
- исполняемые инструменты, тесты, PR-описания и доступные результаты GitHub Actions.

Это аудит отслеженных файлов и ревизий, а не утверждение, что каждый файл каждого старого ответвления был заново прочитан. Реальный пользовательский архив не импортировался в рамках этой проверки.

## 2. Краткий вывод

**В репозитории уже реализована значительная часть технического конвейера памяти. Основной риск теперь — разрыв между отдельными компонентами, runtime-управлением задачей и актуальным учётом статусов.** Часть документов осталась на состоянии до появления новых инструментов; часть функций всё ещё только описана; production-данные не прошли полный путь.

Три разных уровня нельзя смешивать:

1. **Компонент существует и покрыт тестами.**
2. **Компоненты прошли сквозной синтетический тест.**
3. **Система принята на реальном архиве и действительно автоматически работает в среде ChatGPT/Android.**

Подтверждены первые два уровня в ограниченном объёме. Третий не подтверждён.

## 3. Ревизии и проверяемое состояние

| Область | Проверенная ревизия / CI | Что это доказывает |
|---|---|---|
| Интеграционная ветка PR #27 | HEAD `d3f9c610b7865793960dc652c2ccccc88afef732`; run [38864512026](https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/38864512026) | 295 Python-тестов пройдены, 1 пропущен; 4 Node-теста пройдены; memory validation PASS. |
| Код и тесты PR #28 | Проверенный кодовый коммит `40d41701a9c58d498ccb5d2e092089a61e56dd12`; run [38897781306](https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/38897781306) | 344 Python-теста пройдены, 1 пропущен; 4 Node-теста пройдены. Последующие коммиты PR #28 — документационные обновления. |
| `main` | PR #27 базируется на `main` и остаётся Draft/open/unmerged | Перечисленные новые интеграционные компоненты не следует считать уже установленными в `main`. |
| PR #28 | [Draft PR #28](https://github.com/alexbotleh-oss/agent-knowledge-base/pull/28), база — интеграционная ветка PR #27 | UMC-03 evaluator и decision frontier — отдельная незавершённая ветка, не часть HEAD PR #27. |

CI подтверждает тесты и проверки конкретных ревизий. Он не доказывает полноту архива, доверенность реального подтверждающего субъекта, доступность ChatGPT API/браузера или автоматический запуск агента в новом чате.

## 4. Сквозная цепочка памяти: фактический статус

| Этап | Реализация | Проверено | Что остаётся |
|---|---|---|---|
| 1. Неизменяемый источник и возобновляемый импорт | `tools/resumable_chat_import.py`; snapshot identity/hash, checkpoint/cursor, повтор и возобновление | Тесты replay/resume и обработки неполного источника | Не доказана полнота пользовательского архива, всех чатов и бинарных вложений. Нельзя считать частичный экспорт полным. |
| 2. Структурный staging | `tools/archive_registry_staging.py` | Структурные записи и snapshot-манифест покрыты тестами | Staging — не семантическая память; извлечение не должно объединять похожие события. |
| 3. Адаптация и валидация intake | `tools/adapt_archive_staging_to_intake.py`, `tools/validate_memory.py`, intake schemas | Хеши, число записей, ссылки, состояния и структура intake проверяются | `IMPORT_READY` не означает одобрение и не разрешает promotion. |
| 4. Регистрация источников | `tools/source_ingestion_runner.py`, `tools/source_evidence_registry.py` | Реальный runner используется в синтетическом интеграционном тесте; повторы и восстановление после сбоя регистрации проверяются | Источник регистрируется как доказательная ссылка/метаданные. Это само по себе не создаёт принятую семантическую запись. |
| 5. Одобрение и promotion | `tools/semantic_memory_registry.py` | Проверка точного manifest/artifact hash, approval receipt, append-only revision, replay/conflict и provenance; есть тесты | Receipt привязан к данным, но репозиторий не доказывает криптографическую аутентификацию личности подтверждающего. Нет подтверждённого production approval workflow/UI. |
| 6. Исправления связей | `tools/edge_correction_registry.py`, `schemas/edge_correction*.json` | Проверяются привязка к записи/ревизии/хешу, approval receipt, add/retract/replace, replay/conflict | На проверенной ветке `registry/edge_corrections.jsonl` отсутствует. Механизм есть, реальный реестр исправлений не наполнен. |
| 7. Канонический индекс | `tools/canonical_memory_index.py` | Детерминированные поколения, многомерные представления, история ревизий, атомарный указатель CURRENT, проверка свежести и защита предыдущего указателя при неудаче | Покрытие остаётся PARTIAL без полного архива и реального correction registry. Индекс — производное представление, не источник истины. |
| 8. Восстановление задачи и памяти | `tools/restore_session_packet.py`, `tools/verified_session_restore.py`, `tools/memory_aware_session_restore.py` | Сбор TASK_STATE/HANDOFF/связанных событий; отдельная проверка live code/CI; чтение принятой памяти с источниками, противоречиями и статусами PARTIAL/STALE/UNAVAILABLE. Есть синтетический интеграционный тест | Нет автоматического запуска при старте каждого ChatGPT-чата. Восстановленный пакет сам по себе не доказывает полноту истории и не является автоматическим контроллером цели. |
| 9. Координация конвейера | `tools/memory_pipeline_coordinator.py` | Детерминированный run ID, hash-chained append-only ledger, восстанавливаемая проекция, отдельный учёт типов записей; синтетический end-to-end путь real ingestion → promotion/index → memory-aware restore подтверждён тестом `tests/test_memory_pipeline_real_ingestion.py` | Не было production-архива, обработанного целиком. Между отдельными реестрами нет одной атомарной транзакции; важны replay/reconciliation и испытания отказов на каждом границе этапов. |

### Подтверждённые отсутствующие production-данные

На проверенной интеграционной ветке не обнаружены:

- `registry/source_records.jsonl`;
- `registry/memory_records.jsonl`;
- `registry/edge_corrections.jsonl`.

Это означает, что в tracked-ветке есть инструменты и контракты, но не подтверждён наполненный production-набор канонических записей. Отсутствие файла не означает, что нет внешнего локального экземпляра; его состояние этим аудитом не проверялось.

## 5. Поиск опыта и выбор направления решения

### Уже реализовано в интеграционной ветке

- `tools/minimal_agent_loop.py` восстанавливает пакет контекста и ищет кандидатов в явно переданных JSONL-журналах событий.
- Поиск ограничен заданными источниками; сохраняет ID, source path/hash/line, статусы, временные поля, ссылки на доказательства и конфликты.
- Проверка локального источника ограничивается безопасностью пути, существованием, типом, чтением и простым форматом файла. Она **не** доказывает, что источник поддерживает утверждение.
- `tools/context_extractor.py` и `tools/context_trust_gate.py` выделяют рабочий контекст и применяют ограничения доверия.
- `tools/decision_frontier.py` в PR #28 собирает кандидатов в `KEEP_FOR_RATIONALE_REVIEW`, `EXCLUDE`, `HOLD`, `CONFLICT`, `OUT_OF_SCOPE`, сохраняет доступную provenance и предлагает следующую информационную проверку.
- PR #28 добавляет отдельный тип lesson-record, S1 по явным маркерам текущего проекта и S2 lexical fallback. Положительная применимость не выводится из совпадения текста и не должна автоматически разрешать действие.

### Ключевые ограничения

1. **Поиск пока не равен полноценной навигации по памяти.** Он не строит доказанную причинную цепочку «цель → решение → попытка → результат → проверка → урок» для всех записей и не делает полный семантический/графовый поиск по всему каноническому реестру.
2. **Индекс многомерный, но реальный runtime retrieval остаётся ограниченным.** Наличие измерений в индексе не означает, что каждый запрос использует все нужные измерения, связи, исправления, отрицательные результаты и повторяемость случаев.
3. **PR #28 не закрывает доверенную применимость.** Положительный путь evaluator проверяется через injected test verifier. Производственный verifier/trust root не настроен; реальное покрытие уроков явными маркерами не доказано.
4. **Decision frontier — не планировщик.** Она помогает выбрать следующую проверку, но не выполняет план, не подтверждает истинность judgement и не разрешает действия.
5. **S3 cross-project retrieval отложен.** Общие уроки нельзя считать применимыми лишь из-за сходства текста; межпроектное использование требует отдельной проверки условий переноса и ограничений.
6. **Дубликаты/противоречия должны оставаться видимыми.** Любая дедупликация по одному ID без сохранения всех provenance должна считаться риском потери источника; это требует отдельного регрессионного теста для frontier и retrieval.

## 6. Контроллер задачи, внимание и стек возврата

Это один из главных разрывов между целевой архитектурой и текущей реализацией.

### Что есть

- Протоколы восстановления и handoff.
- Реестр child/branch result, acknowledgement API, guarded TASK_STATE updater и reconciliation утилиты.
- Парный checkpoint bundle и тесты целостности, блокировок, replay и части crash-boundaries.
- Локальный turn lifecycle ledger, который фиксирует получение/состояние работы/подготовленный отчёт и может различать подтверждённую доставку от неподтверждённой.

### Чего нет или не доказано

- UMC-02 — общего runtime-контроллера, который для каждого нового сообщения автоматически различает продолжение, побочный вопрос, отложенную идею, новую задачу, смену приоритета и возврат к родительской задаче — остаётся BLOCKED.
- Нет подтверждённой автоматической интеграции, которая сама получает каждое сообщение ChatGPT, сохраняет его до потери соединения и получает реальный receipt доставки ответа. Документы прямо говорят, что локальный lifecycle ledger сам по себе этого не делает.
- Acknowledgement child-result доступен как Python API, но не соединён с полноценным автоматическим chat workflow.
- `HANDOFF.md` остаётся вне полного протокола парных блокировок; внешняя/ручная мутация и некоторые обходные write paths не исключены. Проверка реальных GitHub permissions, branch protection и credentials агентов не выполнена.
- Контроль возврата к цели описан подробно, но не доказано, что он вызывается автоматически на каждом turn и сохраняет причинный стек между чатами.

**Вывод:** локальные механизмы непрерывности есть, но они пока не складываются в постоянно работающий диалоговый контроллер.

## 7. Остальные запланированные функции агента

| Функция из `core/continuous_agent_architecture.md` | Статус аудита |
|---|---|
| Контроллер задачи/цели и goal-drift detection | Спецификация есть; извлечение контекста есть; автономное поддержание активной цели и автоматический возврат после ветки не доказаны. |
| Многослойная память: эпизодическая, семантическая, решения, процедурная, рабочая, RAW | Части схем, реестров и инструментов есть; сквозное извлечение всех слоёв при выборе задачи не реализовано как единый подтверждённый runtime-путь. |
| Реестр и исполнитель навыков | `core/skill_catalog.md` и шаблон спецификации существуют. Каталог описывает навыки, но это не означает наличие версионируемых исполняемых модулей и runtime-dispatcher. |
| Обнаружение окружения и внешних изменений | Есть протокол, реестр/шаблон внешних компонентов и stack validators в CI. Постоянный runtime discovery и автоматический мониторинг обновлений не подтверждены. |
| Планировщик и исполнитель | Координатор исполняет конкретный memory pipeline; общий планировщик задач, который выбирает и исполняет навыки на основании опыта, не подтверждён. |
| Самоконтроль, возврат к цели, обработка отклонений | Есть локальные инструменты и спецификация; общий автоматический контроллер остаётся незавершённым. |
| Проверка результата и обучение на опыте | Тесты, журналы событий, реестр уроков и guarded promotion есть. Автоматическое доказательное извлечение уроков из всей истории и обязательный runtime retrieval перед повтором известных ошибок не доказаны. |
| VLM/визуальная диагностика/Android | Протокол визуальной проверки есть; браузерное расширение — прототип. Приёмка на реально установленном Yandex Browser Android и рабочая интеграция VLM не подтверждены. |
| Защита памяти, карантин, обратимое удаление | Guarded write contracts, append-only записи и аудит мутаций есть. Полный проверенный lifecycle критичной памяти — quarantine → review → reversible restore/delete — в рассмотренном исполняемом контуре не подтверждён. |
| Управление зависимостями и границами проектов | Проектная изоляция и тесты границ есть. Полная проверка всех внешних/динамических write paths и автоматическое предотвращение любого смешения контекста ещё не доказаны. |

## 8. Расхождения и устаревшие утверждения в документах

Это отдельная причина потери нити: один документ описывает старое состояние, а другой — уже реализованную следующую ступень.

1. **Матрица приёмки в `core/unified_memory_control_loop.md`.** Базовая таблица содержит прежние статусы UMC-01…UMC-12 и местами не учитывает позднейшие инструменты. Ветка PR #28 обновляет UMC-03, но этот статус относится только к отдельной ветке PR #28.
2. **`core/source_ingestion_protocol.md`.** Старый раздел «Граница реализации» говорит, что promotion, индекс и восстановление ещё не соединены. Это было верно для более ранней ревизии, но теперь есть `memory_pipeline_coordinator.py` и synthetic end-to-end test. Историческое описание следует сохранить как историю, но явно пометить последующим статусом.
3. **`core/memory_write_contracts.md`.** В конце документа говорится, что тесты координатора используют synthetic records и mocked stage/API results. Это верно для отдельных unit/integration tests, но неполно как итоговое описание: появился отдельный тест, который проходит реальный ingestion runner, promotion/index и memory-aware restore на синтетическом архиве.
4. **`projects/AGENT_MEMORY_SYSTEM/MEMORY_PIPELINE_INTEGRATION_AUDIT_2026-10-16.md`.** Его вывод «promotion/index/restore не реализованы» привязан к более раннему audited HEAD `95524a90...`. Это исторически корректный снимок, но без явной ссылки на более позднюю проверку читатель может принять его за актуальный статус.
5. **Архитектурные документы не имеют единого автоматически проверяемого реестра capability → code → test → exact SHA/CI → residual gap.** Поэтому статусы обновляются вручную и начинают расходиться. Само наличие спецификации или успешного CI не должно автоматически переводить функцию в VERIFIED.

Эти исторические записи не следует удалять или переписывать задним числом. Нужно добавлять superseding status с точной ревизией и доказательствами.

## 9. Происхождение данных и незавершённый перенос истории

PR #22 с cross-chat memory export остаётся отдельным draft и не заменяет runtime-конвейер. Его описание фиксирует существенные ограничения источников:

- в архивном ZIP отсутствует точный чат с названием «Настройка Агента»;
- проверенный ZIP заканчивается 2026-10-07 и не включает последующие изменения;
- отдельный manifest перечисляет 1,374 entries и карта имён ассетов — 876 mappings, но не все payload bytes были независимо сопоставлены;
- полная история чатов и вложений остаётся PARTIAL; отчёт «Последние действия…» — сводка, не первичный полный transcript;
- исторические project-specific PR #23/#24 и другие memory branches также отмечают частичность первичных источников.

Поэтому нельзя утверждать, что текущая каноническая память уже содержит всю историю разработки. Сначала нужно подтвердить доступность и полноту исходных payloads, сохранить их без потерь, затем провести отдельный acceptance/coverage audit. Кодовая готовность pipeline и полнота архивного содержимого — независимые критерии.

## 10. Что упущено в последовательности разработки

1. **Не был сохранён единый живой реестр реализации.** Компоненты добавлялись отдельными PR и документами; некоторые старые статусы не обновлялись после появления новых этапов.
2. **Проверки отдельных этапов опережали сквозную проверку.** Это привело к тому, что ранее честный вывод «не соединено» продолжал жить рядом с более поздним интеграционным кодом.
3. **Runtime-поиск не был доведён от индекса до поведения при старте задачи.** Индекс и restore существуют, но не доказан обязательный путь «новая задача → восстановить цель → извлечь релевантные эпизоды/решения/уроки → показать варианты решения с доказательствами → выбрать следующий различающий тест».
4. **Механизм управления вниманием остался спецификацией.** Ветка side-task может иметь локальные result/checkpoint primitives, но это не равнозначно автоматическому причинному стеку возврата, описанному в архитектуре.
5. **Не разделены на уровне единой приёмки три критерия:** корректность механизма, полнота исходных данных и реальная интеграция в клиентскую среду.
6. **Положительная применимость опыта ещё не имеет production trust root.** PR #28 создаёт безопасный review frontier, но не доказывает применимость записей и не подключает планировщик.
7. **Часть planned capabilities (skill executor, runtime environment discovery, VLM/Android, quarantine lifecycle) не имеет подтверждённой исполняемой реализации.** Их нельзя считать готовыми только по описанию в документах.

## 11. Рекомендуемый порядок продолжения

### P0 — сделать состояние проекта однозначным

- Создать единую матрицу трассировки функций: ID требования → владеющий документ → код → тест → проверенная ревизия/CI → статус → остаточный пробел.
- Сохранить старые аудиты как исторические, но добавить superseding status с новой ревизией.
- Исправить несогласованные статусы в `unified_memory_control_loop.md`, `source_ingestion_protocol.md`, `memory_write_contracts.md` и TASK_STATE/HANDOFF. Не переписывать историю без указания причины и revision.

### P1 — довести «выбор задачи → опыт на ладони»

- Подключить retrieval к реальному старту задачи: сначала восстановление активного проекта/цели и её доказательств; затем релевантные события текущего проекта; затем решения, уроки, неудачные попытки и связи; после этого — ограниченный поиск общих уроков с отдельной проверкой переносимости.
- Для каждого найденного направления показывать путь: исходная ситуация → условия/ограничения → решение → попытки → результат → независимая проверка → урок/исправление → источник и ревизия.
- Разделять «похожий кандидат», «неприменим», «не хватает данных», «конфликт» и «подтверждённо применим». Не выдавать отсутствие совпадений в частичном индексе за отсутствие опыта.
- Использовать decision frontier как слой обзора/следующей проверки, но не как разрешение на действие.

### P2 — реализовать контроллер внимания и возврата

- Реализовать runtime-классификацию сообщения (продолжение / боковой вопрос / отложенная идея / новая задача / смена приоритета / возврат).
- Сохранять active goal, stopping point, parent checkpoint, reason for branch, branch findings, unknowns и return condition.
- Возвращать управление исходной задаче автоматически после завершения боковой ветки, если пользователь не сменил приоритет.
- Подкрепить это сценарными тестами на нескольких последовательных переключениях и новом процессе, а не только unit tests классификатора.

### P3 — закрыть доверие и production acceptance

- Настроить проверяемый production verifier/approval trust root; тестовый callback не считать production.
- Прогнать реальный доступный архив через импорт, promotion, corrections, index и fresh restore, сохранив отчёт о пропущенных чатах/вложениях.
- Проверить crash/replay на каждой границе pipeline и writer coverage, включая HANDOFF и внешние пути.
- Отдельно принять или заблокировать клиентскую интеграцию ChatGPT/Android; не считать локальный ledger автоматическим захватом сообщений.

### P4 — затем расширять автономность

- Исполняемый versioned skill registry и безопасный dispatcher.
- Runtime environment/tool discovery и контролируемый внешний change monitor.
- Автоматизированный повторный regression retrieval по известным инцидентам.
- Проверенный lifecycle защиты памяти, quarantine и обратимого удаления.
- VLM/визуальная диагностика и Android/browser acceptance.

## 12. Критерий успеха для следующего этапа

При выборе новой задачи агент должен без повторного опроса, если источники доступны:

1. восстановить цель, ограничения, подтверждённые решения и точку продолжения;
2. показать найденные релевантные случаи с первоисточниками, включая неудачные попытки и отрицательные результаты;
3. объяснить, почему одни способы решения подходят для рассмотрения, другие исключены, а по третьим не хватает данных;
4. показать оставшиеся неизвестные и конфликтующие свидетельства;
5. выбрать следующий шаг, который даёт максимум полезной информации при минимальном риске;
6. после результата связать наблюдение с исходной гипотезой/решением и сохранить событие, не перезаписывая историю;
7. при переключении на другую задачу сохранить причинный путь возврата.

До успешного end-to-end теста этого поведения механизм считается **частично интегрированным**, даже если отдельные тесты памяти, индекса и evaluator проходят.

## 13. Контрольная точка аудита

- Цель: сквозная проверка механизма памяти и всех запланированных функций непрерывного агента.
- Подтверждено: кодовая цепочка импорт → source registry → approval-bound promotion → corrections → canonical index → memory-aware restore → coordinator существует; синтетический end-to-end тест пройден; PR #27 и #28 остаются draft/unmerged.
- Не подтверждено: полнота реального архива; заполненность production canonical registries; automatic ChatGPT startup/message capture; runtime attention/return controller; production applicability verifier; полноценный retrieval по всему графу памяти; runtime skill executor/environment discovery/VLM acceptance.
- Обнаружено: статусы в нескольких документах отстают от реализации; нужен единый traceability ledger и явные superseding updates.
- Единая матрица трассировки создана: `projects/AGENT_MEMORY_SYSTEM/CAPABILITY_TRACEABILITY_MATRIX_2026-10-16.md`. Следующий шаг — реализовать CAP-02/UMC-02: runtime-контроллер внимания и причинный стек возврата; затем подключить task-time experience map.


## 12. Implementation update after the audited revision — 2026-10-16

The earlier sections above remain a snapshot of the exact revisions named in section 3. The following changes occurred later on separate draft branch `umc02/attention-return-controller-20261016`, PR #30 (base `audit/agent-memory-e2e-20261016` / PR #29); they must not be read as already merged into PR #27 or `main`.

- UMC-02 now has an executable local attention/return controller and task-start composition. The controller reconstructs a persistent nested return stack from the canonical AGENT_MEMORY_SYSTEM event log, and return replay is idempotent.
- UMC-03 S1/S2 retrieval, applicability evaluator and decision frontier from PR #28 were copied into PR #30 with exact blob provenance recorded in TASK_STATE/HANDOFF. PR #28 remains separately open/draft/unmerged, so duplicate branch history must be consolidated before merging either PR.
- The task-start path now composes restore, attention, event/lesson retrieval, applicability/frontier review, source hash/event-ID revalidation and source-bound no-repeat check reuse. Duplicate candidate IDs remain HOLD with all source locators; source mutation blocks candidate expansion; cross-project/global lessons remain OUT_OF_SCOPE; conflicting judgments surface as CONFLICT.
- A completed check is reused only when check identity, relevant source hashes and candidate fingerprints match exactly and evidence refs are present. Changed inputs require recheck; missing/malformed inputs and invalid journals fail closed. A recorded PASS is not independently authenticated and does not grant planning/execution permission.
- Exact code/test HEAD `842088a1c3210e716318f830c687f76e9af58878` passed CI [38902588618](https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/38902588618): 373 Python tests (1 skipped), 4 Node tests, write audit 140 mutation sites / 0 unclassified, memory/project validation PASS.

These are synthetic repository tests. They do not prove complete real-archive ingestion, automatic ChatGPT capture/new-chat startup, production trusted applicability verification, a production planning consumer, or automatic TASK_STATE/HANDOFF reconciliation on return.


## 13. No-repeat and source-fingerprint update — 2026-10-16

After the UMC-02/UMC-03 integration above, PR #30 added a source-bound check-reuse ledger and refined the fingerprint so unrelated checkpoint metadata does not cause unnecessary repeated work. The current task-start map records and evaluates verification_check_completed events in the existing AGENT_MEMORY_SYSTEM event log; it does not create a second authoritative database.

- A prior PASS is reusable only when the stable check key, next-check specification, relevant semantic task context, candidate identities and source-line hashes match and evidence references are present. Changed candidate/context inputs force a rerun. If retrieval is truncated, whole-source hashes are included to guard against unseen candidates.
- Event/lesson source lines are revalidated after retrieval. Source mutation blocks review and check reuse; duplicate IDs remain HOLD with all source locators.
- Exact code/test HEAD `2e0135175421cb99ab2b7325018b0bb648f5a1e0` passed CI [38902931125](https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/38902931125): 373 Python tests (1 skipped), 4 Node tests, write audit 140/0, memory/project validation PASS.
- The result remains PARTIAL: recorded check results are not independently authenticated; production applicability verifier/trust root, full child-result/parent-state/return reconciliation, automatic ChatGPT capture/startup, full semantic graph retrieval and real archive acceptance remain open. PR #30 is still draft/unmerged; no changes to main.

## 13. Unified memory-cycle entry point — 2026-10-16

The separate task-start, attention controller, child-result registry and return reconciliation now have a single local orchestration entry point: `tools/agent_memory_cycle.py`.

It composes task-start experience retrieval, attention-stack inspection, read-only branch-result reconciliation, exact current-branch result/accepted-acknowledgement checks and (when explicitly requested) parent return. It refuses the return if reconciliation is inconsistent, the parent ID does not match the top frame, the matching child result is missing, or the latest acknowledgement for that result is not accepted. After a successful return it rebuilds the task-start experience map so the returned state and no-repeat decision are visible in the same output. Replaying the same return turn is idempotent.

Exact code/test HEAD `2e47f8e596de7c3329dea73dea6845d7a0276d2d` passed CI [38903772855](https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/38903772855): 377 Python tests (1 skipped), 4 Node tests, strict write audit 140/0, memory/project validation PASS.

This establishes a tested synthetic repository path, not an automatically running production agent. The caller must still provide paths and explicit task context; the guarded parent checkpoint is represented as already projected; production applicability trust, real archive acceptance and automatic ChatGPT capture/startup remain open. No planning permission is granted by a successful cycle.