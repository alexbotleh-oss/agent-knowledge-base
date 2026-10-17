const statusNode = document.getElementById("status");
const turnsNode = document.getElementById("turns");
function message(text, className) {
  const node = document.createElement("div");
  node.textContent = text;
  if (className) node.className = className;
  return node;
}
function ask(payload) {
  return new Promise((resolve, reject) => chrome.runtime.sendMessage(payload, response => {
    const error = chrome.runtime.lastError;
    if (error) return reject(new Error(error.message));
    if (!response || response.status === "ERROR") return reject(new Error(response?.error || "journal_error"));
    resolve(response);
  }));
}
const memoryStatusNode = document.getElementById("memory-status");
function activeConversationId() {
  return new Promise((resolve, reject) => {
    chrome.tabs.query({ active: true, currentWindow: true }, tabs => {
      const error = chrome.runtime.lastError;
      if (error) return resolve(null);
      const url = tabs?.[0]?.url || "";
      try {
        const parsed = new URL(url);
        const segments = parsed.pathname.split("/");
        const cIndex = segments.indexOf("c");
        resolve(cIndex >= 0 && segments[cIndex + 1] ? segments[cIndex + 1] : null);
      } catch {
        resolve(null);
      }
    });
  });
}
async function copyDialogueMemory() {
  memoryStatusNode.textContent = "Читаю локальные пары диалога…";
  try {
    const currentConversationId = await activeConversationId();
    const result = await ask({ action: "LIST_DIALOGUE_WINDOWS", current_conversation_id: currentConversationId });
    const packet = result.packet;
    const context = globalThis.RimaDialogueWindowCore?.formatRecoveryContext(packet);
    if (typeof context !== "string" || !context) throw new Error("dialogue_context_unavailable");
    try {
      await navigator.clipboard.writeText(context);
    } catch {
      const area = document.createElement("textarea");
      area.value = context;
      document.body.append(area);
      area.focus();
      area.select();
      throw new Error("clipboard_blocked; context selected for manual copy");
    }
    memoryStatusNode.textContent = "Скопировано: " + packet.global_recent_pairs.length +
      " глобальных пар, " + packet.current_chat_recent_pairs.length + " пар текущего чата. Покрытие: " + packet.status + ".";
  } catch (error) {
    memoryStatusNode.textContent = "Контекст не скопирован: " + String(error.message || error);
  }
}

function resumeText(turn) {
  return [
    "Восстанови незавершённый ход по сохранённым данным.",
    "Точный текст моей инструкции:",
    turn.user_text,
    "",
    "Предыдущее сообщение ассистента (сохранено локально):",
    turn.previous_assistant_message || "[не сохранено]",
    "",
    "Последнее подтверждённое состояние: " + turn.state,
    "Последнее событие: " + JSON.stringify(turn.last_event || {}),
    "Последний контрольный пункт: " + (turn.previous_checkpoint || "UNKNOWN"),
    "Продолжи с первого неподтверждённого шага. Не повторяй завершённые проверки без причины. Отдели подтверждённые факты от неизвестного и не утверждай, что отчёт был доставлен, если это не подтверждено."
  ].join("\n");
}
async function refresh() {
  statusNode.textContent = "Читаю локальный журнал…";
  turnsNode.replaceChildren();
  try {
    const result = await ask({ action: "LIST_INCOMPLETE" });
    const turns = result.turns || [];
    statusNode.textContent = turns.length ? "Незавершённых ходов: " + turns.length : "Незавершённых ходов нет.";
    for (const turn of turns) {
      const card = document.createElement("section");
      card.className = "card";
      card.append(message(turn.state, "state"));
      card.append(message("Обновлён: " + (turn.updated_at || turn.received_at || "UNKNOWN"), "muted"));
      card.append(message("Инструкция"));
      card.append(message(turn.user_text || "[пусто]", "message"));
      card.append(message("Предыдущее сообщение ассистента"));
      card.append(message(turn.previous_assistant_message || "[не сохранено]", "message"));
      card.append(message("Контрольная точка: " + (turn.previous_checkpoint || "UNKNOWN"), "muted"));
      const copy = document.createElement("button");
      copy.textContent = "Скопировать запрос восстановления";
      copy.addEventListener("click", async () => {
        try {
          await navigator.clipboard.writeText(resumeText(turn));
          copy.textContent = "Скопировано";
        } catch {
          const area = document.createElement("textarea");
          area.value = resumeText(turn);
          card.append(area);
          area.focus();
          area.select();
          copy.textContent = "Выделен текст для копирования";
        }
      });
      card.append(copy);
      turnsNode.append(card);
    }
  } catch (error) {
    statusNode.textContent = "Не удалось прочитать журнал: " + String(error.message || error);
  }
}
document.getElementById("refresh").addEventListener("click", () => void refresh());
document.getElementById("copy-memory").addEventListener("click", () => void copyDialogueMemory());
document.getElementById("export").addEventListener("click", async () => {
  try {
    const result = await ask({ action: "EXPORT_LEDGER" });
    const blob = new Blob([result.jsonl || ""], { type: "application/x-ndjson;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "chat-turn-continuity-events.jsonl";
    anchor.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  } catch (error) {
    statusNode.textContent = "Не удалось экспортировать журнал: " + String(error.message || error);
  }
});
void refresh();
