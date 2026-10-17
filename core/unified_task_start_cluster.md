# Unified task-start memory cluster

Status: implemented as an explicitly invoked local composition; exact-head CI is the verification boundary. This is not automatic ChatGPT startup or a live host bridge.

## Single entry point

Use \`tools/agent_memory_cycle.py\` for the task-start path. It composes:

1. **Verified task restore** — \`memory_aware_session_restore.build_memory_aware_packet\` verifies the configured GitHub branch/code/CI evidence and restores the project checkpoint packet.
2. **Approved semantic memory** — retrieves only accepted records from the canonical registry and freshness-checked index; when partial index retrieval returns no match, invokes bounded adaptive local discovery.
3. **Experience candidates** — \`minimal_agent_loop.py\` searches explicitly configured event logs and lesson files, preserving source hashes and record IDs.
4. **Applicability and conflicts** — \`applicability_evaluator.py\` assesses structured lesson candidates; \`decision_frontier.py\` reduces outcomes to review directions. Unknown applicability remains HOLD/INSUFFICIENT_DATA.
5. **Attention and reuse** — \`dialogue_attention_controller.py\` restores attention/return state; \`check_reuse_policy.py\` reuses a prior check only when its input/source/candidate fingerprint matches and any required trust receipt verifies.
6. **Optional parent return** — a separate explicit return request checks branch reconciliation, newest child result, signed owner acknowledgement, and a precommit recheck. Task-start itself does not return to parent automatically.

The orchestrator passes the already-built memory-aware packet into the candidate-retrieval loop. It does not independently restore the same checkpoint a second time.

## Invocation

From a checked-out repository with the required local files:

~~~bash
python tools/agent_memory_cycle.py \
  --task-state projects/AGENT_MEMORY_SYSTEM/TASK_STATE.md \
  --handoff projects/AGENT_MEMORY_SYSTEM/HANDOFF.md \
  --project-event-log projects/AGENT_MEMORY_SYSTEM/events.jsonl \
  --attention-log projects/AGENT_MEMORY_SYSTEM/events.jsonl \
  --request "Continue the current task" \
  --project-id AGENT_MEMORY_SYSTEM \
  --repository alexbotleh-oss/agent-knowledge-base \
  --experience-log projects/AGENT_MEMORY_SYSTEM/events.jsonl
~~~

Lesson retrieval is optional; only pass `--lesson-log` when a real, schema-compatible JSONL lesson source is available. The repository argument enables live GitHub revision/CI checks and approved-memory retrieval. Without it, the tool runs the legacy local task-start path and explicitly reports semantic-memory integration as NOT_CONFIGURED. If the checkpoint's branch is not the intended ref, supply `--repository-ref` explicitly after verifying that ref.

Relevant options:
- \`--memory-query\`: override the request used for approved-memory retrieval.
- \`--memory-registry\`, \`--memory-index-root\`, \`--source-catalog\`: select the canonical local registry, derived index and source catalog.
- \`--return-turn-id\` plus \`--parent-task-id\`: request a guarded return. Both are required together; never set these for ordinary task-start.

## Trust and status semantics

- \`semantic_memory_integration.status=CONFIGURED\` means the verified restore/retrieval path was invoked, not that records were found.
- \`cluster_readiness.status=READY_FOR_REVIEW\` means a configured read-only packet is reviewable. It does not grant planning or execution permission.
- \`cluster_readiness.status=PARTIAL\` identifies missing configuration, unavailable memory, stale/unknown attention, incomplete retrieval, or inconsistent branch reconciliation.
- \`cluster_readiness.status=BLOCKED\` means a hard task-start or requested-return gate failed.
- \`applicability_evaluator\` has no trusted positive path unless the verifier callback can validate receipts against the configured externally pinned keyring. A repository file or label alone does not establish trust.
- \`writes_performed\` and \`execution_performed\` remain false for ordinary task-start. The optional parent-return path is a separately requested write operation.

## Known boundaries

- The entry point is local CLI code and must be invoked by a host; GitHub Actions runs repository validation but does not invoke it for each ChatGPT turn.
- The turn-lifecycle HTTP adapter still needs a trusted client/host that can call it. This ChatGPT conversation does not directly call the user's local loopback service.
- Adaptive source discovery covers configured local roots and the explicit known GitHub refs/paths in registry/remote_source_catalog.json. It does not enumerate every branch, inspect arbitrary remote paths, or search Git history beyond configured refs. External archives, connected apps and device storage still need adapters.
- Approved-memory retrieval remains exact multidimensional filtering plus lexical substring matching; experience retrieval is bounded lexical search, not a unified embedding/graph search.
- Raw archive import and completeness reconciliation remain deferred until the recovery and task-start cluster is proven.
