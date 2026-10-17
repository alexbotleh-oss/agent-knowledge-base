import assert from "node:assert/strict";
import test from "node:test";
import "../clients/chatgpt-web-extension/dialogue_window_core.js";

const core = globalThis.RimaDialogueWindowCore;
function turn(i, conversation = "chat-A", overrides = {}) {
  return {
    turn_id: "T-" + i,
    task_id: "chatgpt:" + conversation,
    conversation_id: conversation,
    user_text: "user message " + i,
    previous_assistant_message: "previous assistant " + (i - 1),
    state: "CLOSED_DELIVERED",
    received_at: new Date(Date.UTC(2026, 9, 17, 0, i)).toISOString(),
    updated_at: new Date(Date.UTC(2026, 9, 17, 0, i, 30)).toISOString(),
    delivery: { observed_at: new Date(Date.UTC(2026, 9, 17, 0, i, 30)).toISOString() },
    report: { text: "assistant response " + i },
    events: [],
    ...overrides,
  };
}

test("global and current-chat windows are independent and capped at five pairs", () => {
  const turns = [
    turn(1, "chat-A"), turn(2, "chat-B"), turn(3, "chat-A"),
    turn(4, "chat-C"), turn(5, "chat-A"), turn(6, "chat-A"),
    turn(7, "chat-B"), turn(8, "chat-A"),
  ];
  const packet = core.buildDialogueWindows(turns, "chat-A", 5);
  assert.deepEqual(packet.global_recent_pairs.map(p => p.turn_id), ["T-4", "T-5", "T-6", "T-7", "T-8"]);
  assert.deepEqual(packet.current_chat_recent_pairs.map(p => p.turn_id), ["T-1", "T-3", "T-5", "T-6", "T-8"]);
  assert.equal(packet.status, "COMPLETE_FOR_CAPTURED_LEDGER");
  assert.equal(packet.project_assignment, "UNKNOWN_NOT_INFERRED_FROM_CONVERSATION_ID");
});

test("pending and unconfirmed turns remain visible and make coverage partial", () => {
  const turns = [
    turn(1, "chat-A"),
    turn(2, "chat-A", { state: "IN_PROGRESS", report: undefined }),
  ];
  const packet = core.buildDialogueWindows(turns, "chat-A");
  assert.deepEqual(packet.global_recent_pairs.map(p => p.turn_id), ["T-1"]);
  assert.equal(packet.global_pending_turns[0].turn_id, "T-2");
  assert.equal(packet.current_chat_pending_turns[0].turn_id, "T-2");
  assert.equal(packet.status, "PARTIAL");
});

test("recovery prompt deduplicates pairs shared by both windows", () => {
  const packet = core.buildDialogueWindows([turn(1, "chat-A"), turn(2, "chat-B")], "chat-A");
  const prompt = core.formatRecoveryContext(packet);
  assert.equal((prompt.match(/turn=T-1/g) || []).length, 1);
  assert.match(prompt, /GLOBAL_LAST_FIVE \+ CURRENT_CHAT_LAST_FIVE/);
  assert.match(prompt, /Вложения: NOT_IMPLEMENTED_BY_CURRENT_EXTENSION/);
});

test("conflicting reuse of a turn ID blocks window construction", () => {
  assert.throws(
    () => core.buildDialogueWindows([turn(1), turn(1, "chat-B")], "chat-A"),
    /turn_id collision/
  );
});

test("unknown current chat is explicit partial rather than guessed", () => {
  const packet = core.buildDialogueWindows([turn(1)], null);
  assert.equal(packet.status, "PARTIAL");
  assert.deepEqual(packet.current_chat_recent_pairs, []);
});
