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
function activeChatTab() {
  return new Promise((resolve, reject) => {
    chrome.tabs.query({ active: true, currentWindow: true }, tabs => {
      const error = chrome.runtime.lastError;
      if (error) return reject(new Error(error.message));
      const tab = tabs?.[0];
      if (!tab?.id || !/^https:\/\/(chatgpt\.com|chat\.openai\.com)\//.test(tab.url || "")) {
        return resolve(null);
      }
      resolve(tab);
    });
  });
}
function sendToTab(tabId, payload) {
  return new Promise((resolve, reject) => chrome.tabs.sendMessage(tabId, payload, response => {
    const error = chrome.runtime.lastError;
    if (error) return reject(new Error(error.message));
    if (!response || response.status === "ERROR") return reject(new Error(response?.error || "content_script_error"));
    resolve(response);
  }));
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

const bridgeStatusNode = document.getElementById("attachment-status");
const bridgeProjectNode = document.getElementById("project-id");
const bridgeTokenNode = document.getElementById("bridge-token");
const attachmentTurnNode = document.getElementById("attachment-turn");
const attachmentFileNode = document.getElementById("attachment-file");
const extensionOrigin = chrome.runtime.getURL("").replace(/\/$/, "");

function storageGet(keys) {
  return new Promise((resolve, reject) => chrome.storage.local.get(keys, value => {
    const error = chrome.runtime.lastError;
    if (error) reject(new Error(error.message));
    else resolve(value || {});
  }));
}
function storageSet(value) {
  return new Promise((resolve, reject) => chrome.storage.local.set(value, () => {
    const error = chrome.runtime.lastError;
    if (error) reject(new Error(error.message));
    else resolve();
  }));
}
async function loadBridgeSettings() {
  try {
    const settings = await storageGet(["rima_project_id", "rima_attachment_bridge_token"]);
    bridgeProjectNode.value = settings.rima_project_id || "";
    bridgeTokenNode.value = settings.rima_attachment_bridge_token || "";
    bridgeStatusNode.textContent = "Origin расширения для allowlist локального bridge: " + extensionOrigin;
  } catch (error) {
    bridgeStatusNode.textContent = "Не удалось прочитать локальные настройки: " + String(error.message || error);
  }
}
async function insertDialogueMemory() {
  memoryStatusNode.textContent = "Собираю контекст для текущего чата…";
  try {
    const tab = await activeChatTab();
    if (!tab) throw new Error("Открой ChatGPT в активной вкладке");
    let currentConversationId = null;
    try {
      const parsed = new URL(tab.url);
      const segments = parsed.pathname.split("/");
      const cIndex = segments.indexOf("c");
      currentConversationId = cIndex >= 0 && segments[cIndex + 1] ? segments[cIndex + 1] : null;
    } catch {}
    const result = await ask({ action: "LIST_DIALOGUE_WINDOWS", current_conversation_id: currentConversationId });
    const context = globalThis.RimaDialogueWindowCore?.formatRecoveryContext(result.packet);
    if (typeof context !== "string" || !context) throw new Error("dialogue_context_unavailable");
    const inserted = await sendToTab(tab.id, { action: "INSERT_DIALOGUE_CONTEXT", text: context });
    memoryStatusNode.textContent = "Контекст вставлен (" + inserted.characters +
      " символов). Он НЕ отправлен: проверь поле и нажми отправку сам. Покрытие: " + result.packet.status + ".";
  } catch (error) {
    memoryStatusNode.textContent = "Контекст не вставлен: " + String(error.message || error) +
      ". Существующий черновик не изменён.";
  }
}
async function saveBridgeSettings() {
  const projectId = bridgeProjectNode.value.trim();
  const token = bridgeTokenNode.value.trim();
  if (!/^[A-Za-z0-9][A-Za-z0-9._-]{1,127}$/.test(projectId)) {
    bridgeStatusNode.textContent = "Укажи явный ID проекта (2–128 символов: буквы, цифры, точка, подчёркивание, дефис).";
    return;
  }
  if (token.length < 32) {
    bridgeStatusNode.textContent = "Токен должен содержать не менее 32 символов.";
    return;
  }
  try {
    await storageSet({ rima_project_id: projectId, rima_attachment_bridge_token: token });
    bridgeStatusNode.textContent = "Настройки сохранены локально. Хранилище профиля браузера не является зашифрованным хранилищем секретов.";
    await refreshAttachmentTurns();
  } catch (error) {
    bridgeStatusNode.textContent = "Не удалось сохранить настройки: " + String(error.message || error);
  }
}
async function refreshAttachmentTurns() {
  const currentConversationId = await activeConversationId();
  attachmentTurnNode.replaceChildren();
  if (!currentConversationId) {
    attachmentTurnNode.add(new Option("Сначала открой конкретный чат ChatGPT", ""));
    bridgeStatusNode.textContent = "ID текущего чата не распознан; источник вложения не назначен.";
    return;
  }
  const result = await ask({ action: "LIST_DIALOGUE_WINDOWS", current_conversation_id: currentConversationId });
  const packet = result.packet;
  const byId = new Map();
  for (const pair of packet.current_chat_recent_pairs || []) {
    byId.set(pair.turn_id, { turn_id: pair.turn_id, text: pair.user?.text || "", state: "CLOSED_DELIVERED" });
  }
  for (const turn of packet.current_chat_pending_turns || []) {
    byId.set(turn.turn_id, { turn_id: turn.turn_id, text: turn.user_text || "", state: turn.state || "PENDING" });
  }
  const turns = [...byId.values()].reverse();
  if (!turns.length) {
    attachmentTurnNode.add(new Option("В этом чате пока нет записанных ходов", ""));
    bridgeStatusNode.textContent = "Нет подходящего хода. Сначала отправь сообщение через установленное расширение.";
    return;
  }
  for (const turn of turns) {
    const snippet = turn.text.replace(/\s+/g, " ").slice(0, 55);
    attachmentTurnNode.add(new Option(turn.state + " · " + turn.turn_id + " · " + snippet, turn.turn_id));
  }
  bridgeStatusNode.textContent = "Выбери точный ход, к которому относится файл. Origin расширения: " + extensionOrigin;
}
async function uploadAttachmentToLibrary() {
  bridgeStatusNode.textContent = "Проверяю проект, ход и доступность локального bridge…";
  try {
    const settings = await storageGet(["rima_project_id", "rima_attachment_bridge_token"]);
    const projectId = settings.rima_project_id;
    const token = settings.rima_attachment_bridge_token;
    if (!projectId || !token) throw new Error("сначала сохрани ID проекта и bearer token");
    const file = attachmentFileNode.files?.[0];
    if (!file) throw new Error("выбери файл");
    if (file.size > 25 * 1024 * 1024) throw new Error("файл больше лимита bridge (25 MiB)");
    const turnId = attachmentTurnNode.value;
    if (!turnId) throw new Error("выбери ход-источник");
    const conversationId = await activeConversationId();
    if (!conversationId) throw new Error("ID текущего чата не распознан");
    const response = await fetch("http://127.0.0.1:8766/v1/attachments", {
      method: "POST",
      headers: {
        "Authorization": "Bearer " + token,
        "Content-Type": file.type || "application/octet-stream",
        "X-Rima-Project-ID": projectId,
        "X-Rima-Conversation-ID": conversationId,
        "X-Rima-Source-Message-ID": turnId,
        "X-Rima-Filename": encodeURIComponent(file.name)
      },
      body: file,
      cache: "no-store"
    });
    let payload;
    try { payload = await response.json(); } catch { throw new Error("bridge вернул некорректный ответ"); }
    if (!response.ok || !payload.attachment) throw new Error(payload.error || "bridge_http_" + response.status);
    const received = payload.attachment;
    if (received.access_status !== "AVAILABLE" || received.project_id !== projectId ||
        received.conversation_id !== conversationId || received.source_message_id !== turnId) {
      throw new Error("bridge returned mismatched project/conversation/turn provenance");
    }
    const attachment = {
      attachment_id: received.attachment_id,
      project_id: received.project_id,
      conversation_id: received.conversation_id,
      source_message_id: received.source_message_id,
      library_ref: received.library_ref,
      sha256: received.sha256,
      size_bytes: received.size_bytes,
      access_status: received.access_status,
      original_name: received.original_name,
      media_type: received.media_type
    };
    const linked = await ask({ action: "LINK_ATTACHMENT", turn_id: turnId, attachment });
    attachmentFileNode.value = "";
    bridgeStatusNode.textContent = "Готово: " + linked.status + ". Файл сохранён в локальной библиотеке и связан с ходом " +
      turnId + ". В окне диалога хранится ссылка, не содержимое файла.";
    await refreshAttachmentTurns();
  } catch (error) {
    bridgeStatusNode.textContent = "Вложение не связано: " + String(error.message || error) +
      ". Сообщение ChatGPT не изменялось.";
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
document.getElementById("insert-memory").addEventListener("click", () => void insertDialogueMemory());
document.getElementById("save-bridge").addEventListener("click", () => void saveBridgeSettings());
document.getElementById("upload-attachment").addEventListener("click", () => void uploadAttachmentToLibrary());
void loadBridgeSettings();
void refreshAttachmentTurns().catch(error => {
  bridgeStatusNode.textContent = "Не удалось обновить список ходов: " + String(error.message || error);
});
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
