# HANDOFF — RECIPE_MANAGER

- **ID/название:** RECIPE_MANAGER / «Что приготовить» — Recipe Manager (web + Android/Flet).
- **Цель проекта:** база рецептов/продуктов, импорт, нормализация ингредиентов, КБЖУ и Android UI.
- **Текущая цель:** перенести доступный опыт из чата в `agent-knowledge-base`, не отлаживая приложение.
- **Ветка/коммит приложения:** unknown. **Ветка памяти:** `memory/recipe-manager-experience-20261012`, база `main`.
- **Завершено и подтверждено:** прочитаны README, протоколы, memory model, templates, validator и CI. В исходном main был `projects/CARD`, `projects/RECIPE_MANAGER` отсутствовал.
- **Проверено:** семь новых файлов перечитаны после записи; EVENT_LOG содержит девять уникальных событий; GitHub Actions workflow `Validate knowledge base` завершился success (run 38285407579). PR #17 открыт и не слит. Требуется пользовательское review.
- **События:** требования базы/ингредиентов/КБЖУ; Flet `PopupMenuItem` exception; Core Lite lane D; успешный build после JNI override 1.1.0; белый экран legacy WebView; PROBE2 подтвердил permission/view/page-update/load path; PROBE3 JSON не содержит ожидаемых marker events.
- **Уроки:** не приравнивать регрессию к установленной причине; после HTML/DB патчей проверять baseline функций; WinError 32 не позволяет считать clean успешным; возврат из load_html не доказывает рендер; отсутствие marker events требует проверки идентичности исходника и APK.
- **Открытые вопросы:** root cause белого экрана неизвестен; доставка PROBE3 в APK не подтверждена; текущие import/КБЖУ не ретестированы; app repo/HEAD неизвестны; полная история/вложения недоступны.
- **Следующий шаг:** проверить файлы, открыть PR, проверить changed files и CI. Не мержить без разрешения.
- **Журналы:** EVENT_LOG.md, DECISIONS.md, LESSONS.md, SOURCE_COVERAGE.md, TASK_STATE.md.
- **Дата/достоверность:** 2026-10-12 / partial.
