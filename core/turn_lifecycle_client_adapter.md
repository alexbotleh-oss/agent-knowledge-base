# Turn lifecycle client adapter

Status: **local HTTP adapter and client SDK implemented; integration into a real ChatGPT UI is not implemented**.

## Purpose

The existing ledger is only useful if a trusted client calls it before work starts. This contract provides a small authenticated local HTTP service and a JavaScript SDK for a chat wrapper, extension background worker, or native app bridge.

## Required order

1. The host receives a user message and assigns a stable `turn_id` and `task_id`.
2. It calls `registerIncoming` and waits for a successful durable receipt.
3. Only after receipt acknowledgement may it start the model/task work and emit `WORK_STARTED`.
4. It emits `PROGRESS` and `ARTIFACT_CREATED` after material milestones, referencing durable artifacts where possible.
5. If an output is durably saved, emit `REPORT_PREPARED` with its path/hash. Do not put private report contents in a public repository.
6. Emit `RESPONSE_SUBMITTED` only when the host can establish that submission occurred. Emit `DELIVERY_ACKNOWLEDGED` only if a genuine platform/client receipt exists. Otherwise the turn remains unconfirmed.
7. On restart, query incomplete turns and correlate their last event with checkpoints, repository state, CI, and suspicious artifacts. Resume from the first unverified milestone.

A failed registration is a hard gate: the SDK does not invoke the work callback. A timeout means the caller cannot know whether the server committed the request; retry with the same `turn_id` and identical payload. The server is designed to treat an exact replay idempotently and reject conflicting reuse.

## HTTP API

Default base URL: `http://127.0.0.1:8765`. All endpoints require `Authorization: Bearer <token>`, except preflight handling for an exact allowlisted CORS origin. Configure `AGENT_TURN_ADAPTER_TOKEN` with a random secret of at least 32 characters.

- `POST /v1/turns` — register exact input before work. JSON: `turn_id`, `task_id`, `user_text`, optional `previous_checkpoint`.
- `POST /v1/turns/{turn_id}/events` — append one lifecycle event. JSON: `event_type`, optional stable `event_id`, and relevant `detail`, `artifact`, `report`, `submission`, or `delivery`.
- `GET /v1/turns?incomplete=true` — retrieve unresolved turns.
- `GET /v1/turns/{turn_id}` — inspect one turn.
- `GET /health` — authenticated liveness check.

The request body limit is 1 MiB and user text is limited to 250,000 characters. Unknown fields are rejected. The server binds to loopback by default; a non-loopback bind requires an explicit flag. CORS is denied unless the exact origin was configured. Request logs do not include message bodies or bearer tokens.

## Running locally

```sh
export AGENT_TURN_ADAPTER_TOKEN="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
python3 tools/turn_lifecycle_adapter.py --ledger "$HOME/.local/state/agent-turn-ledger/events.jsonl" --bind 127.0.0.1 --port 8765
```

Do not commit the token or exact-message ledger. Do not expose the server to a network without a deliberate security review. For a browser extension, allow only its exact origin and keep the bearer token in the trusted background/native component, not page-injected code.

## SDK

`clients/turn_lifecycle_client.js` exposes `registerIncoming`, `recordEvent`, lifecycle helpers, `listIncomplete`, and `runTrackedTurn`. The latter guarantees that incoming registration and `WORK_STARTED` are acknowledged before invoking the supplied work callback. It does not automatically submit a response or claim delivery; the host must call those methods when actual lifecycle signals exist.

The client restricts its base URL to loopback HTTP by default. Request timeout is a bounded acknowledgement wait, not proof the write failed: after a timeout, inspect/retry with the same stable IDs and reconcile the server state before starting work.

## Platform integration boundary

This is a real callable adapter and SDK, **not a ChatGPT page hook**. It does not read messages from the current ChatGPT web UI, intercept its Send button, observe its connection indicator, or receive ChatGPT delivery receipts. Those require a separately implemented and tested integration specific to the actual host (for example, a trusted app wrapper or a browser extension with supported permissions). Do not scrape private page internals or claim end-to-end capture until that host integration is built and tested. A local HTTP endpoint cannot by itself observe messages that were never sent to it.

## Interruption budget

Use work slices of 10–12 minutes as a target in environments with observed interruptions near 15 minutes. Persist progress at meaningful boundaries, keep each slice's next action explicit, and do not start a large phase close to the boundary. This is an operational risk target, not a guaranteed session timeout.

## Acceptance scenarios

1. Normal turn: exact message receipt → start → progress/artifact → prepared report → submission and delivery only when independently observed.
2. Disconnect immediately after user send: a durable receipt exists and is listed as incomplete.
3. Adapter unavailable before receipt: the work callback does not run.
4. Timeout after uncertain receipt: retry with same turn ID/payload; no duplicate logical turn.
5. Same turn ID with different text/task/checkpoint: conflict; no silent reuse.
6. Crash during work: latest durable progress/artifact reference is available; turn remains incomplete unless a terminal event exists.
7. Empty/partial artifact found: flag as an investigative lead, correlate with events/mtime/hash/Git/CI, never auto-delete.
8. Report prepared but not submitted: remains `REPORT_PREPARED_UNCONFIRMED`.
9. Submission without delivery receipt: remains `RESPONSE_SUBMITTED_UNCONFIRMED`.
10. Actual delivery acknowledgement: closes the turn as delivered.
11. Duplicate lifecycle event with same ID/content: idempotent replay; same ID with changed content: conflict.
12. Restart server/client: journal remains readable; malformed journal fails closed.

## Validation scope

The HTTP adapter tests exercise the real local server in-process, auth, origin checks, exact-text registration, incomplete-turn inspection, event ordering, and delivery acknowledgement. SDK tests verify the work gate and event ordering. These do not prove integration with ChatGPT's current UI or Android browser capabilities.

## Browser extension prototype for the current ChatGPT UI

A separate local-only prototype now lives in `clients/chatgpt-web-extension/`. It uses IndexedDB in the browser profile rather than requiring a Python server to be running on the phone. It intercepts known text-send controls/form submissions, persists the exact message and previous assistant message before dispatch, records a visible final assistant response when DOM observation is confident, shows incomplete turns in a popup, and supports user-initiated JSONL export. It makes no external network requests.

**Status: implementation prototype; live-device acceptance is still pending.** Static CI verifies manifest scope, the local-only/send-gate contract and JavaScript syntax. It cannot verify that the current ChatGPT mobile DOM, Yandex Browser Android's extension runtime, click timing or response selectors behave as expected on the user's device. See `clients/chatgpt-web-extension/README.md` for install and limitations. The extension does not have a canonical checkpoint bridge yet, so the prior checkpoint field is explicitly UNKNOWN/null. If selectors stop matching, automatic capture may fail; do not rely on the extension until the real-browser acceptance tests pass.
