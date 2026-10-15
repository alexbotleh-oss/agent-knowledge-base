/**
 * Client SDK for the local turn lifecycle adapter.
 *
 * Import this from a trusted chat wrapper / extension background worker. This
 * module does not scrape a ChatGPT page and does not infer delivery. The host
 * must call registerIncoming before starting work and call responseSubmitted /
 * deliveryAcknowledged only when those states are actually observed.
 */
export class TurnLifecycleClient {
  constructor({ baseUrl = "http://127.0.0.1:8765", token, fetchImpl = globalThis.fetch, timeoutMs = 3000 } = {}) {
    if (typeof token !== "string" || token.length < 32) {
      throw new TypeError("A bearer token of at least 32 characters is required");
    }
    if (typeof fetchImpl !== "function") throw new TypeError("fetch implementation is required");
    const parsed = new URL(baseUrl);
    if (parsed.protocol !== "http:" || !["127.0.0.1", "localhost", "[::1]"].includes(parsed.hostname)) {
      throw new TypeError("The default client only permits a local HTTP adapter");
    }
    if (!Number.isInteger(timeoutMs) || timeoutMs < 100 || timeoutMs > 30000) {
      throw new TypeError("timeoutMs must be an integer between 100 and 30000");
    }
    this.baseUrl = parsed.origin;
    this.token = token;
    this.fetchImpl = fetchImpl;
    this.timeoutMs = timeoutMs;
  }

  async request(path, { method = "GET", body } = {}) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), this.timeoutMs);
    try {
      const response = await this.fetchImpl(this.baseUrl + path, {
        method,
        headers: {
          "Authorization": "Bearer " + this.token,
          ...(body === undefined ? {} : { "Content-Type": "application/json" }),
        },
        ...(body === undefined ? {} : { body: JSON.stringify(body) }),
        cache: "no-store",
        signal: controller.signal,
      });
      let data;
      try { data = await response.json(); }
      catch { throw new Error("Turn adapter returned invalid JSON (HTTP " + response.status + ")"); }
      if (!response.ok) {
        const error = new Error("Turn adapter rejected request (HTTP " + response.status + "): " + (data.error || "unknown_error"));
        error.status = response.status;
        error.code = data.error || "adapter_error";
        throw error;
      }
      return data;
    } catch (error) {
      if (error && error.name === "AbortError") {
        const timeoutError = new Error("Turn adapter request timed out; work must not assume the event was recorded");
        timeoutError.code = "adapter_timeout";
        throw timeoutError;
      }
      throw error;
    } finally {
      clearTimeout(timeout);
    }
  }

  registerIncoming({ turnId, taskId, userText, previousCheckpoint = null }) {
    return this.request("/v1/turns", {
      method: "POST",
      body: {
        turn_id: turnId,
        task_id: taskId,
        user_text: userText,
        previous_checkpoint: previousCheckpoint,
      },
    });
  }

  recordEvent(turnId, eventType, fields = {}) {
    return this.request("/v1/turns/" + encodeURIComponent(turnId) + "/events", {
      method: "POST",
      body: { event_type: eventType, ...fields },
    });
  }

  progress(turnId, detail, eventId) {
    return this.recordEvent(turnId, "PROGRESS", { detail, ...(eventId ? { event_id: eventId } : {}) });
  }

  artifactCreated(turnId, artifact, eventId) {
    return this.recordEvent(turnId, "ARTIFACT_CREATED", { artifact, ...(eventId ? { event_id: eventId } : {}) });
  }

  reportPrepared(turnId, report, eventId) {
    return this.recordEvent(turnId, "REPORT_PREPARED", { report, ...(eventId ? { event_id: eventId } : {}) });
  }

  responseSubmitted(turnId, submission, eventId) {
    return this.recordEvent(turnId, "RESPONSE_SUBMITTED", { submission, ...(eventId ? { event_id: eventId } : {}) });
  }

  deliveryAcknowledged(turnId, delivery, eventId) {
    return this.recordEvent(turnId, "DELIVERY_ACKNOWLEDGED", { delivery, ...(eventId ? { event_id: eventId } : {}) });
  }

  async runTrackedTurn({ turnId, taskId, userText, previousCheckpoint = null, work }) {
    if (typeof work !== "function") throw new TypeError("work must be a function");
    // This await is the safety gate: never start the callback if durable receipt
    // was not acknowledged by the local adapter.
    await this.registerIncoming({ turnId, taskId, userText, previousCheckpoint });
    await this.recordEvent(turnId, "WORK_STARTED");
    const context = {
      progress: (detail, eventId) => this.progress(turnId, detail, eventId),
      artifactCreated: (artifact, eventId) => this.artifactCreated(turnId, artifact, eventId),
      reportPrepared: (report, eventId) => this.reportPrepared(turnId, report, eventId),
    };
    try {
      return await work(context);
    } catch (error) {
      const safeMessage = String(error && error.message ? error.message : "work callback failed").slice(0, 4000);
      try {
        await this.recordEvent(turnId, "TURN_FAILED", { detail: safeMessage });
      } catch (journalError) {
        // Keep the original work error, but expose the uncertain journal outcome.
        error.lifecycleJournalError = journalError;
      }
      throw error;
    }
  }

  listIncomplete() {
    return this.request("/v1/turns?incomplete=true");
  }

  getTurn(turnId) {
    return this.request("/v1/turns/" + encodeURIComponent(turnId));
  }
}
