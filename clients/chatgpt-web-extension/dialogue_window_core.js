/* Pure rolling-window logic shared by the browser extension and Node tests. */
(function attachRimaDialogueWindowCore(root) {
  "use strict";
  const TERMINAL = new Set(["CLOSED_DELIVERED", "CLOSED_FAILED", "CLOSED_ABANDONED"]);

  function text(value) { return typeof value === "string" ? value : ""; }
  function time(value) { return typeof value === "string" ? value : ""; }

  function buildDialogueWindows(turns, currentConversationId = null, pairLimit = 5) {
    if (!Array.isArray(turns)) throw new TypeError("turns must be an array");
    if (!Number.isInteger(pairLimit) || pairLimit < 1) throw new TypeError("pairLimit must be a positive integer");
    if (currentConversationId !== null && (typeof currentConversationId !== "string" || !currentConversationId.trim())) {
      throw new TypeError("currentConversationId must be null or a non-empty string");
    }

    const seen = new Map();
    for (const turn of turns) {
      if (!turn || typeof turn !== "object" || typeof turn.turn_id !== "string" || !turn.turn_id) {
        throw new TypeError("every turn must have a stable turn_id");
      }
      const prior = seen.get(turn.turn_id);
      if (prior && JSON.stringify(prior) !== JSON.stringify(turn)) {
        throw new Error("turn_id collision: " + turn.turn_id);
      }
      seen.set(turn.turn_id, turn);
    }

    const ordered = [...seen.values()].sort((a, b) => {
      if (Number.isInteger(a.received_sequence) && Number.isInteger(b.received_sequence) &&
          a.received_sequence !== b.received_sequence) {
        return a.received_sequence - b.received_sequence;
      }
      const byTime = time(a.received_at).localeCompare(time(b.received_at));
      return byTime || a.turn_id.localeCompare(b.turn_id);
    });
    const complete = [];
    const pending = [];
    for (const turn of ordered) {
      const assistantText = text(turn.report?.text);
      if (turn.state === "CLOSED_DELIVERED" && text(turn.user_text) && assistantText && text(turn.conversation_id)) {
        complete.push({
          conversation_id: turn.conversation_id,
          turn_id: turn.turn_id,
          task_id: text(turn.task_id) || null,
          project_id: null,
          received_sequence: Number.isInteger(turn.received_sequence) ? turn.received_sequence : null,
          received_at: time(turn.received_at) || null,
          completed_at: time(turn.delivery?.observed_at || turn.updated_at) || null,
          user: { text: turn.user_text, message_id: turn.turn_id + ":user", attachments: turn.attachments || [] },
          assistant: { text: assistantText, message_id: turn.turn_id + ":assistant", attachments: [] },
          source: "LOCAL_EXTENSION_LEDGER",
        });
      } else if (text(turn.user_text) && (!assistantText || turn.state !== "CLOSED_DELIVERED")) {
        pending.push({
          conversation_id: text(turn.conversation_id) || null,
          turn_id: turn.turn_id,
          task_id: text(turn.task_id) || null,
          project_id: null,
          state: text(turn.state) || "UNKNOWN",
          user_text: turn.user_text,
          assistant_text: assistantText || null,
          previous_assistant_message: text(turn.previous_assistant_message) || null,
          received_at: time(turn.received_at) || null,
          attachments: Array.isArray(turn.attachments) ? turn.attachments : [],
        });
      }
    }

    const globalRecent = complete.slice(-pairLimit);
    const currentRecent = currentConversationId
      ? complete.filter(pair => pair.conversation_id === currentConversationId).slice(-pairLimit)
      : [];
    const currentPending = currentConversationId
      ? pending.filter(turn => turn.conversation_id === currentConversationId)
      : [];
    return {
      schema: "rima-browser-dialogue-windows-v1",
      status: pending.length || !currentConversationId ? "PARTIAL" : "COMPLETE_FOR_CAPTURED_LEDGER",
      pair_limit: pairLimit,
      source_turn_count: ordered.length,
      global_recent_pairs: globalRecent,
      current_chat_recent_pairs: currentRecent,
      global_pending_turns: pending.slice(-1),
      current_chat_pending_turns: currentPending,
      source_scope: "CAPTURED_EXTENSION_LEDGER_ONLY",
      project_assignment: "UNKNOWN_NOT_INFERRED_FROM_CONVERSATION_ID",
      attachment_capture: "MANUAL_LIBRARY_IMPORT_ONLY_AUTOMATIC_CHATGPT_UPLOAD_CAPTURE_NOT_IMPLEMENTED",
    };
  }

  function formatRecoveryContext(packet) {
    if (!packet || packet.schema !== "rima-browser-dialogue-windows-v1") {
      throw new TypeError("unsupported dialogue window packet");
    }
    const membership = new Map();
    for (const pair of packet.global_recent_pairs || []) {
      membership.set(pair.turn_id, { pair, scopes: ["GLOBAL_LAST_FIVE"] });
    }
    for (const pair of packet.current_chat_recent_pairs || []) {
      const found = membership.get(pair.turn_id);
      if (found) found.scopes.push("CURRENT_CHAT_LAST_FIVE");
      else membership.set(pair.turn_id, { pair, scopes: ["CURRENT_CHAT_LAST_FIVE"] });
    }
    const entries = [...membership.values()].sort((a, b) =>
      time(a.pair.received_at).localeCompare(time(b.pair.received_at)) ||
      a.pair.turn_id.localeCompare(b.pair.turn_id)
    );
    const lines = [
      "ВОССТАНОВЛЕНИЕ КОНТЕКСТА ИЗ ЛОКАЛЬНОГО ЖУРНАЛА РИМЫ",
      "Статус покрытия: " + packet.status,
      "Источник: " + packet.source_scope,
      "Назначение проекта: " + packet.project_assignment,
      "Вложения: " + packet.attachment_capture + "; использовать только явно указанные библиотечные ссылки, не предполагать доступность байтов.",
      "Используй историю как ближайший контекст, но не считай её заменой актуального состояния проекта или первичных доказательств.",
      "",
      "ПОСЛЕДНИЕ ПАРЫ (каждая пара приводится один раз; scopes показывают принадлежность окон):"
    ];
    for (const { pair, scopes } of entries) {
      lines.push(
        "",
        "[" + scopes.join(" + ") + "] conversation=" + pair.conversation_id +
          " turn=" + pair.turn_id + " project=UNKNOWN",
        "Пользователь: " + pair.user.text
      );
      const attachments = Array.isArray(pair.user.attachments) ? pair.user.attachments : [];
      for (const attachment of attachments) {
        if (!attachment || typeof attachment !== "object") continue;
        const safeRef = {
          attachment_id: attachment.attachment_id || "UNKNOWN",
          library_ref: attachment.library_ref || "UNKNOWN",
          access_status: attachment.access_status || "UNKNOWN",
          sha256: attachment.sha256 || "UNKNOWN",
          original_name: attachment.original_name || "UNKNOWN",
          size_bytes: Number.isSafeInteger(attachment.size_bytes) ? attachment.size_bytes : null
        };
        lines.push("Вложение (только ссылка и метаданные): " + JSON.stringify(safeRef));
      }
      lines.push("Рима: " + pair.assistant.text);
    }
    const pendingById = new Map();
    for (const turn of packet.global_pending_turns || []) {
      pendingById.set(turn.turn_id, { turn, scopes: ["GLOBAL_PENDING"] });
    }
    for (const turn of packet.current_chat_pending_turns || []) {
      const found = pendingById.get(turn.turn_id);
      if (found) found.scopes.push("CURRENT_CHAT_PENDING");
      else pendingById.set(turn.turn_id, { turn, scopes: ["CURRENT_CHAT_PENDING"] });
    }
    for (const { turn, scopes } of pendingById.values()) {
      lines.push("", "НЕЗАВЕРШЁННЫЙ ХОД [" + scopes.join(" + ") + "]: turn=" + turn.turn_id +
        " state=" + turn.state + " conversation=" + (turn.conversation_id || "UNKNOWN"),
        "Пользователь: " + turn.user_text,
        "Ответ ассистента: " + (turn.assistant_text || "НЕ ЗАФИКСИРОВАН"));
    }
    lines.push("", "Перед действием сверь цель, проектное состояние, ограничения и релевантные источники. После действия зафиксируй результат и доказательство. Не повторяй проверенную попытку без новой причины.");
    return lines.join("\n");
  }

  root.RimaDialogueWindowCore = { buildDialogueWindows, formatRecoveryContext };
})(globalThis);
