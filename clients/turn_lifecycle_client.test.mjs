import test from "node:test";
import assert from "node:assert/strict";
import { TurnLifecycleClient } from "./turn_lifecycle_client.js";

const token = "unit-test-secret-token-which-is-longer-than-32-chars";

function response(status, data) {
  return { ok: status >= 200 && status < 300, status, json: async () => data };
}

test("client rejects non-loopback adapter URLs", () => {
  assert.throws(() => new TurnLifecycleClient({ baseUrl: "http://192.168.1.5:8765", token }), /local HTTP adapter/);
  assert.throws(() => new TurnLifecycleClient({ baseUrl: "https://127.0.0.1:8765", token }), /local HTTP adapter/);
});

test("work callback cannot start until durable incoming receipt is acknowledged", async () => {
  const calls = [];
  const client = new TurnLifecycleClient({
    token,
    fetchImpl: async (url, init) => {
      calls.push({ url, init });
      return response(400, { error: "journal_unavailable" });
    },
  });
  let workStarted = false;
  await assert.rejects(client.runTrackedTurn({
    turnId: "T1", taskId: "TASK1", userText: "продолжай дальше",
    work: async () => { workStarted = true; },
  }), /HTTP 400/);
  assert.equal(workStarted, false);
  assert.equal(calls.length, 1);
  assert.match(calls[0].url, /\/v1\/turns$/);
  assert.equal(JSON.parse(calls[0].init.body).user_text, "продолжай дальше");
});

test("tracked turn records receive before start, progress and prepared report", async () => {
  const calls = [];
  const client = new TurnLifecycleClient({
    token,
    fetchImpl: async (url, init) => {
      calls.push({ url, init, body: init.body ? JSON.parse(init.body) : undefined });
      return response(201, { status: "APPENDED" });
    },
  });
  const result = await client.runTrackedTurn({
    turnId: "T2", taskId: "TASK2", userText: "continue",
    previousCheckpoint: "CKPT-2",
    work: async (ctx) => {
      await ctx.progress("step 1 verified", "T2-progress-1");
      await ctx.reportPrepared({ path: "reports/T2.md", sha256: "abc123" }, "T2-report-1");
      return "done";
    },
  });
  assert.equal(result, "done");
  assert.deepEqual(calls.map(x => x.body?.event_type || "TURN_RECEIVED"),
    ["TURN_RECEIVED", "WORK_STARTED", "PROGRESS", "REPORT_PREPARED"]);
  assert.equal(calls[0].body.user_text, "continue");
  assert.equal(calls[0].body.previous_checkpoint, "CKPT-2");
  assert.equal(calls[2].body.event_id, "T2-progress-1");
});

test("work exception is recorded as failed while preserving original error", async () => {
  const calls = [];
  const client = new TurnLifecycleClient({
    token,
    fetchImpl: async (url, init) => {
      calls.push({ url, body: init.body ? JSON.parse(init.body) : undefined });
      return response(201, { status: "APPENDED" });
    },
  });
  await assert.rejects(client.runTrackedTurn({
    turnId: "T3", taskId: "TASK3", userText: "test",
    work: async () => { throw new Error("known work failure"); },
  }), /known work failure/);
  assert.equal(calls.at(-1).body.event_type, "TURN_FAILED");
  assert.equal(calls.at(-1).body.detail, "known work failure");
});
