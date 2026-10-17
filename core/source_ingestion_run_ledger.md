# Resumable source-ingestion run ledger

Status: implementation contract for `tools/source_ingestion_runner.py`. The runner is intentionally bounded to archive staging → sanitized intake → metadata-only source registry. It does not claim semantic promotion, canonical index refresh, or next-session restore.

## Durable artifacts

- `run_events.jsonl`: authoritative append-only transition history, rewritten atomically as a whole file under an OS advisory lock. Each event has a monotonically increasing sequence, stable batch/source identity, previous-event hash and its own SHA-256. Invalid, truncated or tampered history fails closed.
- `run_state.json`: derived current-state projection. If missing, unreadable or behind the event ledger, it is reconstructed from the verified event history.
- Locking is process-scoped/OS-managed; process death releases the lock. A stale lock file is not used as the lock primitive.

## State contract

| State | Meaning |
|---|---|
| `RUNNING` | A run has begun or resumed; no completion claim. |
| `READY_FOR_SOURCE_REGISTRATION` | Staging was adapted, the read-only route plan validated, and registry dry-run succeeded. No canonical source-registry write was requested. |
| `SOURCE_REGISTERED_DOWNSTREAM_PENDING` | Source metadata was appended, or an exact replay proved it was already registered. Semantic promotion, canonical index refresh and next-session restore remain pending/not implemented by this runner. |
| `BLOCKED` | A validation, source-identity, ledger-integrity or stage operation failed. Do not treat it as successful persistence. |

## Resume protocol

1. Derive the batch/run ID from archive ID, immutable raw SHA-256 and parser version.
2. Acquire the run lock; verify the event hash chain and source identity before any stage mutation.
3. Rebuild the state projection from the ledger if needed.
4. Re-run the staging adapter and route planner; both must be idempotent/read-only at their respective boundaries.
5. If apply is requested, invoke the source registry's idempotent append. If the process died after registry commit but before recording the result, a resumed run receives `ALREADY_REGISTERED` and records the reconciled outcome without duplicating the registry row.
6. Persist the resulting stage event and projection atomically. A crash after event-ledger replacement but before projection replacement is recovered by rebuilding the projection.
7. Stop at `SOURCE_REGISTERED_DOWNSTREAM_PENDING`. Never infer promotion/index/restore completion from source registration.

## Failure injection acceptance

- Dry-run creates a verifiable run ledger/projection but does not write the source registry.
- Apply followed by replay leaves registry bytes unchanged and returns the explicit downstream-pending status.
- Crash immediately after the source registry commits but before the runner records that result; restart reconciles to `ALREADY_REGISTERED` with one registry revision.
- Tampered event ledger fails closed before registry mutation.
- Concurrent calls for the same run serialize under the OS lock and resume from the same event chain.

Limitations: this ledger tracks orchestration status; it does not make the separate source registry and run ledger one cross-file transaction. The crash/replay protocol resolves the known uncertain-acknowledgement window through idempotent registry identity. No semantic memory is accepted or promoted by this tool.
