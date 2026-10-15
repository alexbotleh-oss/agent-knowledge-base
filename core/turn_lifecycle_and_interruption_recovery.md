# Turn lifecycle ledger and interruption recovery

Status: **implemented as a callable repository tool; platform integration is not implemented**.

## Why this exists

A missing assistant report is not proof that no work happened. The process may have stopped after receiving the instruction, after starting work, while writing an artifact, after preparing a report, or after submitting a response whose delivery signal is unavailable. Keep these states separate.

## Lifecycle

The append-only JSONL journal records:

1. `TURN_RECEIVED`: exact user text, SHA-256, task ID and previous checkpoint. A trusted client must persist this before starting work.
2. `WORK_STARTED` and `PROGRESS`: work started and durable milestones.
3. `ARTIFACT_CREATED`: artifact path/status references, including temporary or partial output when known.
4. `REPORT_PREPARED`: report artifact exists; this is **not** proof it was submitted.
5. `RESPONSE_SUBMITTED`: submission attempted/confirmed by the host; this is **not** proof of delivery.
6. `DELIVERY_ACKNOWLEDGED`: only a real host/client acknowledgement may close the turn as delivered.
7. `TURN_FAILED` / `TURN_ABANDONED`: explicit terminal states, with cause kept separate from the state.

On restart, `inspect` identifies all turns without a terminal event and preserves the exact instruction, prior checkpoint, progress, artifact references and last event. A missing terminal event means **incomplete/unknown**, not “the model did nothing” and not proof of a network failure.

## Artifact forensics

`scan-artifacts` can inspect explicitly supplied workspace roots for zero-byte files and common partial/temp names (`.tmp`, `.part`, `.partial`, `.pending`, `.inprogress`, temporary-name patterns and lock files). It reports paths, size, modification time and signals. Findings are leads only: file names/timestamps cannot prove that a specific turn created an artifact. Correlate with lifecycle events, Git diff/status, CI, file hashes and checkpoint timestamps. Do not delete suspected leftovers automatically.

## Runtime budget

For environments where long sessions have been observed to fail around 15 minutes, plan **10–12 minute work slices**, with a durable checkpoint at each meaningful boundary and before a risky/long action. Each slice should have one concrete outcome, a bounded validation, and a recorded next action. Stop at the boundary rather than beginning another large phase. The 15-minute figure is an observed user-side limit, not a guaranteed platform timeout; interruptions can occur sooner.

## Use

The CLI defaults to a user-local state path outside the repository:
```sh
python tools/turn_lifecycle_ledger.py receive --turn-id T-20261015-001 --task-id AGMS-2026-10-15-MEMORY-PIPELINE-CONTINUITY --previous-checkpoint CKPT-AGMS-20261015-INTERRUPTION-RECOVERY-03 --text 'продолжай дальше'
python tools/turn_lifecycle_ledger.py event --turn-id T-20261015-001 --type WORK_STARTED
python tools/turn_lifecycle_ledger.py event --turn-id T-20261015-001 --type PROGRESS --detail 'added and tested lifecycle ledger'
python tools/turn_lifecycle_ledger.py inspect
python tools/turn_lifecycle_ledger.py scan-artifacts --root /path/to/workspace
```

Exact user text can be sensitive. Do not override `--ledger` to a public repository path. Avoid shell history in a production client: pass the text through a trusted API/integration rather than a shell command. The ledger tool serializes local writers, fsyncs appends, fails closed on malformed journal records, and makes identical `TURN_RECEIVED` replay idempotent.

## Critical integration boundary

This Python tool **does not automatically see ChatGPT messages, detect browser disconnects, or receive the host's response-delivery receipt**. The calling client/wrapper must invoke `receive` before work, emit lifecycle events, and provide a genuine acknowledgement if the platform exposes one. If no acknowledgement exists, retain `RESPONSE_SUBMITTED_UNCONFIRMED`; never upgrade it to delivered based on assumption. Repository CI cannot by itself capture this conversation's future messages.

## Validation scope

Unit tests exercise exact-text retention, restart inspection, interrupted work, prepared-but-unconfirmed reports, delivery acknowledgement, idempotent registration, conflicting input, unknown turns, terminal-state protection, corrupt-journal fail-closed behavior, and empty/partial artifact discovery. These tests validate the local ledger logic, not an end-to-end ChatGPT/mobile-browser integration or real network-failure recovery.
