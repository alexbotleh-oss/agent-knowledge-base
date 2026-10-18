# Практическая проверка verified task executor

## 1. Сквозной smoke-тест без данных рабочего проекта

Из корня репозитория:

```bash
python3 -m unittest discover -s tests -p 'test_verified_task_executor.py' -v
```

Тест использует временный каталог и синтетический проект. Он проверяет поиск исходного опыта, dry-run, явное выполнение тестового действия, независимую проверку артефакта, сохранение события с происхождением и повторное извлечение сохранённого успешного кандидата в следующем цикле задачи. Также проверяются блокировки для не найденного опыта, несвязанного обоснования, критического риска и изменения контрольной точки.

Это тест механизма на синтетическом сценарии, а не подтверждение работы на настоящем проекте или автоматического запуска из ChatGPT.

Дополнительно CI запускает изолированный сценарий `test_real_agent_memory_event_drives_isolated_controlled_action`: он читает реальное событие `EVT-AGMS-20261017-004` из `projects/AGENT_MEMORY_SYSTEM/events.jsonl`, копирует журнал в отдельный временный workspace и вызывает `tools/verified_task_executor.py` через настоящий CLI с явным `--execute`. Низкорисковое действие создаёт JSON-артефакт; исполнитель независимо проверяет результат, сохраняет evidence и provenance-bound candidate. Тест подтверждает связь с исходным событием и побайтную неизменность исходного журнала. Канонические файлы проекта не меняются. Это проверка реального CLI и реального источника памяти в изолированной среде, но не live workspace пользователя и не автоматический хост ChatGPT.

## 2. Подготовка реальной низкорисковой задачи

Используйте только контролируемую рабочую копию и команду, которую вы предварительно проверили. Исполнитель **не является OS/container sandbox**: `shell=False`, ограничение cwd и проверка путей артефактов не запрещают запущенной программе обращаться к другим доступным учётной записи файлам.

В workspace должны находиться:
- актуальные `TASK_STATE.md` и `HANDOFF.md`;
- проектный `events.jsonl`;
- журнал опыта, содержащий найденное событие с тем же `project_id`;
- JSON-файл спецификации действия.

Пример `action-spec.json` для безопасной проверки создания артефакта в выбранном workspace:

```json
{
  "argv": [
    "python3",
    "-c",
    "from pathlib import Path; Path('artifacts').mkdir(exist_ok=True); Path('artifacts/check.txt').write_text('PASS', encoding='utf-8')"
  ],
  "cwd": ".",
  "acceptance_criterion": "artifacts/check.txt contains PASS",
  "acceptance_checks": [
    {"type": "command_exit_code", "expected": 0},
    {"type": "file_contains", "path": "artifacts/check.txt", "expected": "PASS"}
  ],
  "evidence_report": "artifacts/task-run-evidence.json",
  "observed_outcome": "The reviewed artifact check passed"
}
```

Путь к исполняемому Python в `argv` при необходимости замените на путь, используемый вашей средой. Не используйте этот пример поверх важной рабочей директории без проверки путей.

## 3. Сначала только план

Из корня репозитория вызовите `tools/verified_task_executor.py`, передав абсолютный `--workspace-root`, пути к трём проектным файлам, `--experience-log`, текст задачи, точный ID найденного события, обоснование выбора действия и путь к `action-spec.json`. Например:

```bash
python3 tools/verified_task_executor.py \
  --workspace-root /absolute/path/to/workspace \
  --task-state projects/TEST/TASK_STATE.md \
  --handoff projects/TEST/HANDOFF.md \
  --event-log projects/TEST/events.jsonl \
  --experience-log projects/TEST/events.jsonl \
  --request "verify the generated artifact" \
  --project-id TEST \
  --task-id TASK-SMOKE-001 \
  --reviewed-experience-event-id EVT-EXAMPLE-001 \
  --action-rationale "Prior experience identified the artifact verification path; repeat the focused check" \
  --action-spec /absolute/path/to/action-spec.json
```

Все пути к файлам, кроме `--workspace-root` и самого файла спецификации, разрешаются относительно workspace, если не являются абсолютными. Замените примерные ID и пути реальными значениями. Указанное событие должно быть реально извлечено и принадлежать этому же проекту; обоснование должно явно отражать найденный опыт. Команда без `--execute` не запускает действие и должна вернуть `PLAN_READY_REQUIRES_EXPLICIT_EXECUTE`.

## 4. Явное выполнение и проверка результата

Только после проверки плана и команды добавьте `--execute`. При успехе ожидается `VERIFIED_ACTION_AND_CAPTURED`; проверьте отчёт `artifacts/task-run-evidence.json`, каждый критерий приёмки и новое событие в журнале. Затем запустите следующий task-start/retrieval cycle с тем же журналом и убедитесь, что ID сохранённого кандидата появился в результатах.

Если проверка не проходит, исполнитель не должен сохранять успешный кандидат; при безопасном состоянии журнала он записывает наблюдаемое событие `failed_attempt`. Оно остаётся наблюдением, а не автоматически принятым уроком.

## Ограничения

- CLI запускается явно и не интегрирован автоматически в каждый ход ChatGPT.
- Лексическое совпадение обоснования с опытом — только проверка трассируемости, не доказательство смысловой применимости.
- Критерии должны содержательно проверять результат; сам исполнитель не придумывает правильные критерии.
- Сохранённые успехи остаются кандидатами со статусом наблюдения. Promotion в семантическую память требует отдельного утверждённого процесса.
