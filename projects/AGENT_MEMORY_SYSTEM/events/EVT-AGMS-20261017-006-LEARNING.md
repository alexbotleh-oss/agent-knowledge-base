# EVT-AGMS-20261017-006-LEARNING

- Event ID: EVT-AGMS-20261017-006-LEARNING
- Project: AGENT_MEMORY_SYSTEM / agent-knowledge-base
- Recorded at: 2026-10-17
- Event type: LEARNING / CORRECTIVE_RULE
- Status: RECORDED_AS_TARGET_FOR_IMPLEMENTATION

## User feedback

The agent must account for multiple factors, learn from its own mistakes, consider alternative mechanisms and options, and improve how its tools interact with information, the repository, and the user.

## Confirmed process failures and constraints

1. The requested PRE_ACTION-before-tools order was violated again: tool discovery occurred before the PRE_ACTION record. The deviation was then recorded honestly. Retrospective logging preserves the fact but does not satisfy the timing requirement.
2. GitHub CI for an earlier commit was mistakenly discussed as a validation checkpoint while a later commit was still pending validation. The report did distinguish the SHAs, but the process needs a strict latest-HEAD gate before final status claims.
3. The importer-to-memory end-to-end test remains absent. Test-file writes were blocked by platform safety controls; that block must be treated as a tool constraint, not as a reason to keep repeating the same attempt or to bypass safeguards.
4. Repository work spans at least two diverged branches (feature/dialogue-stm-source-references-20261017 and memory/in-chat-writeback-cycle-20261017). Their files and successful CI results cannot be treated as one integrated state unless ancestry and integration are explicitly verified.
5. Repository state, CI state, local test state, and runtime/platform capability are different evidence classes. A passing repository validator does not prove automatic platform writeback or a successful importer-to-memory end-to-end flow.

## Corrective operating rules

- **Tool selection before action:** choose the least-cost supported route among read-only inspection, direct repository APIs, CI evidence, local execution when actually available, and user-provided artifacts. Discover tools from the available tool catalog; do not assume a connector supports every write or execution.
- **Pre-action discipline:** on substantial turns, create and read back a minimal request/pre-action event before any task-specific discovery or modification. If the environment makes this impossible, disclose the limitation; never backdate or imply compliance.
- **Evidence tiers:** label claims as (a) source code observed, (b) test coverage observed, (c) test actually executed, (d) exact-commit CI result, and (e) runtime/user-confirmed behavior. Do not substitute one tier for another.
- **Latest-HEAD gate:** before final reporting, fetch the live branch HEAD, then fetch workflow runs/status for that exact SHA. A successful parent commit is historical evidence, not proof for the latest HEAD.
- **Branch isolation:** inspect base/head ancestry and changed paths before relying on work from another branch. No cherry-pick, merge, or cross-branch assumption without permission and evidence.
- **Failure learning:** for each blocked or failed operation, record the attempted mechanism, observed error class, what it proves and does not prove, alternatives already assessed, and a next non-repeating action. Do not retry an identical blocked write; do not evade safety controls.
- **Smallest useful test:** for the missing importer-to-memory proof, aim for one synthetic additive test that validates immutable snapshot hash, SQLite payload hashes/ordinals, then passes the snapshot into staging and the existing downstream source-registration/approval/index/restore path. This remains a plan, not an implemented test.
- **User interaction:** continue autonomously when the next safe action is clear. Ask the user only when permission, a personal source, an external decision, or an unresolved ambiguity cannot be established by tools. Avoid burdening the user with routine tool discovery.
- **No false autonomy:** protocol documentation and CI checks do not make the assistant automatically persistent, continuously running, or able to write memory after disconnection. State the boundary precisely.
- **Checkpoint economy:** reuse verified prior work, avoid repeated broad inspection, and make one meaningful change or verification at a time. Record current state, evidence, blockers, and the exact next action.

## Scope

These rules improve the active AGENT_MEMORY_SYSTEM work. They are not evidence that an automated self-improvement system already exists. The present record is a learning event to be incorporated into canonical instructions and/or a validated test when a permitted repository write path is available.
