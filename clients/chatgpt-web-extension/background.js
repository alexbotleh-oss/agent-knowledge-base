const DB_NAME = "chat-turn-continuity";
const DB_VERSION = 1;
const STORE = "turns";
const MAX_TEXT_CHARS = 1_000_000;
const TERMINAL = new Set(["CLOSED_DELIVERED", "CLOSED_FAILED", "CLOSED_ABANDONED"]);
const EVENT_TYPES = new Set([
  "WORK_STARTED", "PROGRESS", "ARTIFACT_CREATED", "REPORT_PREPARED",
  "RESPONSE_SUBMITTED", "DELIVERY_ACKNOWLEDGED", "TURN_FAILED", "TURN_ABANDONED"
]);

let dbPromise;
function openDb() {
  if (dbPromise) return dbPromise;
  dbPromise = new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains(STORE)) db.createObjectStore(STORE, { keyPath: "turn_id" });
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error || new Error("indexeddb_open_failed"));
  });
  return dbPromise;
}
function stableJson(value) {
  if (Array.isArray(value)) return "[" + value.map(stableJson).join(",") + "]";
  if (value && typeof value === "object") {
    return "{" + Object.keys(value).sort().map(k => JSON.stringify(k) + ":" + stableJson(value[k])).join(",") + "}";
  }
  return JSON.stringify(value);
}
function now() { return new Date().toISOString(); }
function makeEvent(turnId, eventType, fields = {}, eventId) {
  return { event_id: eventId || (turnId + ":" + eventType + ":" + crypto.randomUUID()),
    turn_id: turnId, event_type: eventType, timestamp: now(), ...fields };
}
function transition(turn, event) {
  switch (event.event_type) {
    case "WORK_STARTED": turn.state = "IN_PROGRESS"; break;
    case "PROGRESS": break;
    case "ARTIFACT_CREATED": turn.artifacts.push(event.artifact || {}); break;
    case "REPORT_PREPARED": turn.state = "REPORT_PREPARED_UNCONFIRMED"; turn.report = event.report || {}; break;
    case "RESPONSE_SUBMITTED": turn.state = "RESPONSE_SUBMITTED_UNCONFIRMED"; turn.response_submission = event.submission || {}; break;
    case "DELIVERY_ACKNOWLEDGED": turn.state = "CLOSED_DELIVERED"; turn.delivery = event.delivery || {}; break;
    case "TURN_FAILED": turn.state = "CLOSED_FAILED"; turn.failure = event.detail || ""; break;
    case "TURN_ABANDONED": turn.state = "CLOSED_ABANDONED"; turn.abandonment = event.detail || ""; break;
  }
  if (event.delivery?.conversation_id) {
    turn.conversation_id = event.delivery.conversation_id;
    turn.task_id = "chatgpt:" + event.delivery.conversation_id;
  }
  turn.events.push(event);
  turn.last_event = event;
  turn.updated_at = event.timestamp;
}

function withTurn(turnId, mutate) {
  return openDb().then(db => new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, "readwrite");
    const store = tx.objectStore(STORE);
    let outcome;
    let failure;
    const request = store.get(turnId);
    request.onsuccess = () => {
      try {
        const turn = request.result;
        if (!turn) throw new Error("unknown_turn_id:" + turnId);
        outcome = mutate(turn, store);
      } catch (error) {
        failure = error;
        try { tx.abort(); } catch {}
      }
    };
    request.onerror = () => { failure = request.error; };
    tx.oncomplete = () => resolve(outcome);
    tx.onabort = () => reject(failure || tx.error || new Error("journal_transaction_aborted"));
    tx.onerror = () => { failure = failure || tx.error; };
  }));
}

async function registerTurn(payload, sender) {
  const { turn_id, task_id, user_text, previous_checkpoint = null,
    previous_assistant_message = "", assistant_count_before = 0, url = "", conversation_id = null } = payload || {};
  if (typeof turn_id !== "string" || !turn_id || typeof task_id !== "string" || !task_id ||
      typeof user_text !== "string" || !user_text.trim() || user_text.length > MAX_TEXT_CHARS ||
      typeof previous_assistant_message !== "string" || previous_assistant_message.length > MAX_TEXT_CHARS) {
    throw new Error("invalid_turn_payload");
  }
  const db = await openDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, "readwrite");
    const store = tx.objectStore(STORE);
    let outcome;
    let failure;
    const get = store.get(turn_id);
    get.onsuccess = () => {
      const old = get.result;
      if (old) {
        if (old.task_id === task_id && old.user_text === user_text && old.previous_checkpoint === previous_checkpoint) {
          outcome = { status: "ALREADY_REGISTERED", turn: old };
          return;
        }
        failure = new Error("turn_id_collision_with_different_input");
        tx.abort();
        return;
      }
      const received = makeEvent(turn_id, "TURN_RECEIVED", {
        task_id, user_text, previous_checkpoint, user_text_sha256: null,
        previous_assistant_message
      }, turn_id + ":TURN_RECEIVED");
      // WebCrypto is asynchronous; exact text is retained locally. The hash is a
      // convenience integrity field, not a substitute for the stored exact text.
      const turn = {
        turn_id, task_id, user_text, previous_checkpoint, previous_assistant_message,
        assistant_count_before: Number.isInteger(assistant_count_before) ? assistant_count_before : 0,
        tab_id: sender?.tab?.id ?? null, url, conversation_id,
        state: "AWAITING_START", received_at: received.timestamp, updated_at: received.timestamp,
        events: [received], artifacts: [], last_event: received
      };
      store.add(turn);
      outcome = { status: "APPENDED", turn };
    };
    get.onerror = () => { failure = get.error; };
    tx.oncomplete = () => resolve(outcome);
    tx.onabort = () => reject(failure || tx.error || new Error("journal_transaction_aborted"));
    tx.onerror = () => { failure = failure || tx.error; };
  });
}

async function appendEvent(turnId, eventType, fields = {}, eventId) {
  if (!EVENT_TYPES.has(eventType)) throw new Error("unsupported_event_type");
  return withTurn(turnId, (turn, store) => {
    const event = makeEvent(turnId, eventType, fields, eventId);
    const old = turn.events.find(e => e.event_id === event.event_id);
    if (old) {
      if (old.event_type === event.event_type &&
          stableJson(Object.fromEntries(Object.entries(old).filter(([k]) => k !== "timestamp"))) ===
          stableJson(Object.fromEntries(Object.entries(event).filter(([k]) => k !== "timestamp")))) {
        return { status: "ALREADY_RECORDED", turn };
      }
      throw new Error("event_id_collision_with_different_content");
    }
    if (TERMINAL.has(turn.state)) throw new Error("turn_already_terminal");
    transition(turn, event);
    store.put(turn);
    return { status: "APPENDED", turn };
  });
}

async function listTurns() {
  const db = await openDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, "readonly");
    const request = tx.objectStore(STORE).getAll();
    request.onsuccess = () => resolve(request.result.sort((a,b) => b.updated_at.localeCompare(a.updated_at)));
    request.onerror = () => reject(request.error || new Error("journal_read_failed"));
  });
}
function incomplete(turn) { return !TERMINAL.has(turn.state); }
async function assistantRendered(payload) {
  const { turn_id, text, message_count, conversation_id } = payload || {};
  if (typeof text !== "string" || !text.trim() || text.length > MAX_TEXT_CHARS) throw new Error("invalid_assistant_text");
  await appendEvent(turn_id, "REPORT_PREPARED", {
    report: { text, source: "chatgpt-dom", message_count }
  }, turn_id + ":REPORT_PREPARED");
  await appendEvent(turn_id, "RESPONSE_SUBMITTED", {
    submission: { source: "chatgpt-dom", message_count }
  }, turn_id + ":RESPONSE_SUBMITTED");
  return appendEvent(turn_id, "DELIVERY_ACKNOWLEDGED", {
    delivery: {
      source: "chatgpt-dom",
      evidence: "final assistant message observed in page DOM after generation stopped",
      observed_at: now(),
      conversation_id: conversation_id || null,
      message_count
    }
  }, turn_id + ":DELIVERY_ACKNOWLEDGED");
}

function isChatPage(url) {
  try { const u = new URL(url); return u.protocol === "https:" && ["chatgpt.com", "chat.openai.com"].includes(u.hostname); }
  catch { return false; }
}
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  const fromChat = isChatPage(sender?.url || "");
  const fromExtension = (sender?.url || "").startsWith(chrome.runtime.getURL(""));
  const action = message?.action;
  if (["REGISTER_TURN", "RECORD_EVENT", "ASSISTANT_RENDERED", "LIST_INCOMPLETE", "INSPECT_TURN"].includes(action) && !fromChat && !fromExtension) {
    sendResponse({ status: "ERROR", error: "untrusted_sender" });
    return false;
  }
  (async () => {
    switch (action) {
      case "REGISTER_TURN":
        if (!fromChat) throw new Error("register_requires_chat_page");
        return registerTurn(message.payload, sender);
      case "RECORD_EVENT":
        if (!fromChat) throw new Error("event_requires_chat_page");
        return appendEvent(message.turn_id, message.event_type, message.fields || {}, message.event_id);
      case "ASSISTANT_RENDERED":
        if (!fromChat) throw new Error("render_requires_chat_page");
        return assistantRendered(message.payload);
      case "LIST_INCOMPLETE": {
        const all = await listTurns();
        const tabId = sender?.tab?.id;
        const rows = all.filter(t => incomplete(t) && (tabId == null || t.tab_id === tabId));
        return { status: "OK", turns: rows };
      }
      case "INSPECT_TURN": {
        const all = await listTurns();
        const turn = all.find(t => t.turn_id === message.turn_id);
        if (!turn) throw new Error("turn_not_found");
        return { status: "OK", turn };
      }
      case "EXPORT_LEDGER": {
        if (!fromExtension) throw new Error("export_requires_extension_popup");
        const all = await listTurns();
        const events = all.flatMap(t => t.events).sort((a,b) => a.timestamp.localeCompare(b.timestamp));
        return { status: "OK", jsonl: events.map(e => JSON.stringify(e)).join("\n") + (events.length ? "\n" : "") };
      }
      default: throw new Error("unknown_action");
    }
  })().then(result => sendResponse(result)).catch(error => sendResponse({ status: "ERROR", error: String(error?.message || error) }));
  return true;
});
