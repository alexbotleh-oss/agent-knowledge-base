# HANDOFF — ORGANISM

- **Проект:** ORGANISM — приложение непрерывного агента и собственной памяти.
- **Исходный репозиторий:** https://github.com/alexbotleh-oss/organism
- **Статус памяти:** PARTIAL; записи основаны на доступных сводках, не на полном экспорте всех чатов/вложений.
- **Главные требования:** полноценное приложение, не только ChatGPT bridge; первая платформа Android; встроенный WebView; автономность в заданных ограничениях; RAW/provenance; структурированная память; Context Engine; FTS5; импорт ChatGPT ZIP/TXT/MD/PDF/URL.
- **Критический функциональный пробел:** импортировано 74 беседы / 10 034 сообщения, но архив бесед, просмотр и поиск не были подключены к пользовательскому UI. Это требование не считать выполненным, пока пользователь может открыть/найти импортированные беседы и управлять ими.
- **Download flow:** на Android 16/WebView 153 скачивание в приложении давало application/octet-stream, bytes=0, content.bin; commit 380cb579ae8657e32b005bc01472f0cb71c67dc6 направлял chatgpt.com downloads во внешний браузер. Build commit 2f67f6b817b065acaa8b9f4bd0e0a77e6b73d7ce, Actions run 288 — success по сводке; device verification pending.
- **OAuth flow:** белый экран после входа, ERR_NAME_NOT_RESOLVED; attachment attempts 0, microphone permission granted. Причина неизвестна, не смешивать с download flow.
- **Другие ограничения:** subscription_sharing_usage_limit_exceeded при отправке в ChatGPT — отдельный внешний лимит, не доказательство дефекта локальной памяти.
- **Упоминания сборок:** commit 258d0edd70d7fc5a30c78a3ddbafb633c85c61c5, PR #10 и PWA prototype app.js/sw.js синтаксические проверки отмечены в сводках; актуальные статусы PR/branches нужно получать заново из GitHub.
- **Следующий шаг:** восстановить актуальное состояние репозитория/PR; подключить imported conversation archive к UI/search; затем отдельно тестировать download, attachment и OAuth на устройстве. Не объявлять runtime PASS только по CI.