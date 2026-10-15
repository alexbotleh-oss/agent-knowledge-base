(() => {
  const MAX_TEXT_CHARS = 1_000_000;
  const ACTIVE_KEY = "chat-turn-continuity-active-turn";
  let pending = false;
  let allowNextSend = false;
  let allowNextSubmit = false;
  let activeTurnId = sessionStorage.getItem(ACTIVE_KEY);
  let responseTimer = null;
  let responseRecording = false;
  let lastObservedCount = 0;

  function conversationId() {
    const match = location.pathname.match(/\/c\/([^/?#]+)/);
    return match ? match[1] : null;
  }
  function taskId() {
    const id = conversationId();
    if (id) return "chatgpt:" + id;
    let session = sessionStorage.getItem("chat-turn-continuity-new-chat");
    if (!session) {
      session = crypto.randomUUID();
      sessionStorage.setItem("chat-turn-continuity-new-chat", session);
    }
    return "chatgpt-new:" + session;
  }
  function assistantNodes() {
    return [...document.querySelectorAll('[data-message-author-role="assistant"]')];
  }
  function assistantText(node) {
    return (node?.innerText || node?.textContent || "").trim();
  }
  function composer() {
    return document.querySelector("#prompt-textarea") ||
      document.querySelector('[data-testid="prompt-textarea"]') ||
      document.querySelector('textarea[placeholder]') ||
      document.querySelector('[contenteditable="true"][role="textbox"]');
  }
  function composerText(node = composer()) {
    if (!node) return "";
    return (typeof node.value === "string" ? node.value : (node.innerText || node.textContent || "")).trim();
  }
  function sendButton() {
    const known = document.querySelector('button[data-testid="send-button"]') ||
      document.querySelector('button[aria-label="Send prompt"]') ||
      document.querySelector('button[aria-label="Send message"]');
    if (known) return known;
    const input = composer();
    return input?.closest("form")?.querySelector('button[type="submit"]') || null;
  }
  function generating() {
    return Boolean(document.querySelector('button[data-testid="stop-button"], button[aria-label*="Stop generating"], button[aria-label*="Stop streaming"]'));
  }
  function toast(message) {
    let node = document.getElementById("chat-turn-continuity-toast");
    if (!node) {
      node = document.createElement("div");
      node.id = "chat-turn-continuity-toast";
      Object.assign(node.style, {
        position: "fixed", zIndex: "2147483647", left: "12px", right: "12px", bottom: "16px",
        padding: "12px 14px", borderRadius: "10px", background: "#222", color: "#fff",
        font: "14px/1.4 sans-serif", boxShadow: "0 2px 12px #0006"
      });
      document.documentElement.appendChild(node);
    }
    node.textContent = message;
    node.style.display = "block";
    clearTimeout(node._hideTimer);
    node._hideTimer = setTimeout(() => { node.style.display = "none"; }, 6000);
  }
  function sendWorker(message) {
    return new Promise((resolve, reject) => {
      chrome.runtime.sendMessage(message, response => {
        const err = chrome.runtime.lastError;
        if (err) return reject(new Error(err.message));
        if (!response || response.status === "ERROR") return reject(new Error(response?.error || "extension_journal_failed"));
        resolve(response);
      });
    });
  }
  function cancelEvent(event) {
    event.preventDefault();
    event.stopPropagation();
    if (typeof event.stopImmediatePropagation === "function") event.stopImmediatePropagation();
  }

  async function gatedSend(button) {
    if (pending) return;
    const input = composer();
    const text = composerText(input);
    if (!text) return; // Empty/attachment-only submissions are outside this prototype's capture contract.
    if (text.length > MAX_TEXT_CHARS) {
      toast("Сообщение слишком большое для журнала восстановления. Оно не отправлено.");
      return;
    }
    pending = true;
    const before = assistantNodes();
    const previousAssistant = assistantText(before[before.length - 1]);
    const turnId = crypto.randomUUID();
    const payload = {
      turn_id: turnId,
      task_id: taskId(),
      user_text: text,
      previous_checkpoint: null,
      previous_assistant_message: previousAssistant,
      assistant_count_before: before.length,
      url: location.href,
      conversation_id: conversationId()
    };
    try {
      await sendWorker({ action: "REGISTER_TURN", payload });
      await sendWorker({
        action: "RECORD_EVENT", turn_id: turnId, event_type: "WORK_STARTED",
        event_id: turnId + ":WORK_STARTED",
        fields: { detail: "Durable input receipt acknowledged; dispatching ChatGPT composer" }
      });
      if (composerText(input) !== text) {
        await sendWorker({
          action: "RECORD_EVENT", turn_id: turnId, event_type: "TURN_ABANDONED",
          event_id: turnId + ":TURN_ABANDONED",
          fields: { detail: "Composer text changed while receipt was being persisted; send cancelled to avoid mismatch" }
        });
        toast("Текст изменился во время сохранения. Отправка отменена; проверь поле ввода.");
        return;
      }
      activeTurnId = turnId;
      sessionStorage.setItem(ACTIVE_KEY, turnId);
      lastObservedCount = before.length;
      const freshButton = sendButton() || button;
      if (freshButton && freshButton.isConnected && !freshButton.disabled) {
        allowNextSend = true;
        freshButton.click();
      } else {
        allowNextSend = false;
        const form = input?.closest("form");
        if (!form || typeof form.requestSubmit !== "function") {
          toast("Сообщение сохранено, но отправку нельзя безопасно продолжить. Ход остался незавершённым.");
          return;
        }
        allowNextSubmit = true;
        form.requestSubmit();
      }
      scheduleResponseCheck();
    } catch (error) {
      toast("Сообщение НЕ отправлено: не удалось надёжно записать его в журнал. " + String(error.message || error));
    } finally {
      pending = false;
    }
  }

  document.addEventListener("click", event => {
    const target = event.target instanceof Element ? event.target : null;
    const button = target?.closest("button");
    const input = composer();
    const form = input?.closest("form");
    const knownSend = button && button.matches('button[data-testid="send-button"], button[aria-label="Send prompt"], button[aria-label="Send message"]');
    const genericSubmit = button && form && form.contains(button) && button.type === "submit";
    if (!button || (!knownSend && !genericSubmit)) return;
    if (allowNextSend) {
      allowNextSend = false;
      return;
    }
    const text = composerText(input);
    if (!text) return;
    cancelEvent(event);
    void gatedSend(button);
  }, true);

  document.addEventListener("submit", event => {
    const form = event.target instanceof HTMLFormElement ? event.target : null;
    const input = composer();
    if (!form || !input || !form.contains(input)) return;
    if (allowNextSubmit) {
      allowNextSubmit = false;
      return;
    }
    if (!composerText(input)) return;
    cancelEvent(event);
    void gatedSend(sendButton());
  }, true);

  document.addEventListener("keydown", event => {
    if (event.key !== "Enter" || event.shiftKey || event.isComposing) return;
    const input = composer();
    if (!input || !(event.target === input || input.contains(event.target))) return;
    if (!composerText(input)) return;
    cancelEvent(event);
    void gatedSend(sendButton());
  }, true);

  function scheduleResponseCheck() {
    clearTimeout(responseTimer);
    responseTimer = setTimeout(() => { void checkForResponse(); }, 1300);
  }
  async function recoverActiveTurn() {
    if (activeTurnId) {
      try {
        const response = await sendWorker({ action: "INSPECT_TURN", turn_id: activeTurnId });
        if (response.turn && !["CLOSED_DELIVERED", "CLOSED_FAILED", "CLOSED_ABANDONED"].includes(response.turn.state)) return response.turn;
      } catch {}
      activeTurnId = null;
      sessionStorage.removeItem(ACTIVE_KEY);
    }
    try {
      const response = await sendWorker({ action: "LIST_INCOMPLETE" });
      const turns = response.turns || [];
      const cid = conversationId();
      const matching = cid ? turns.filter(t => t.conversation_id === cid || t.task_id === "chatgpt:" + cid) : [];
      const candidates = matching.length ? matching : (turns.length === 1 ? turns : []);
      if (candidates.length === 1) {
        activeTurnId = candidates[0].turn_id;
        sessionStorage.setItem(ACTIVE_KEY, activeTurnId);
        return candidates[0];
      }
    } catch {}
    return null;
  }
  async function checkForResponse() {
    if (responseRecording) return;
    const turn = await recoverActiveTurn();
    if (!turn || ["CLOSED_DELIVERED", "CLOSED_FAILED", "CLOSED_ABANDONED"].includes(turn.state)) return;
    const nodes = assistantNodes();
    const beforeCount = Number.isInteger(turn.assistant_count_before) ? turn.assistant_count_before : 0;
    if (nodes.length <= beforeCount || generating()) return;
    const latest = nodes[nodes.length - 1];
    const text = assistantText(latest);
    if (!text || text.length > MAX_TEXT_CHARS) return;
    responseRecording = true;
    try {
      await sendWorker({
        action: "ASSISTANT_RENDERED",
        payload: { turn_id: turn.turn_id, text, message_count: nodes.length, conversation_id: conversationId() }
      });
      activeTurnId = null;
      sessionStorage.removeItem(ACTIVE_KEY);
      toast("Ответ обнаружен в интерфейсе и сохранён в журнале восстановления.");
    } catch (error) {
      toast("Ответ виден, но его фиксация не подтверждена. Ход останется для восстановления.");
    } finally {
      responseRecording = false;
    }
  }

  const observer = new MutationObserver(() => scheduleResponseCheck());
  observer.observe(document.documentElement, { childList: true, subtree: true, characterData: true });
  void recoverActiveTurn().then(turn => { if (turn) scheduleResponseCheck(); });
})();
