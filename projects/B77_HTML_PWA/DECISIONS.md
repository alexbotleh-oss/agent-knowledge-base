# DECISIONS — B77 HTML/PWA

## D-B77-001 — Keep project histories separate
- **Decision/source:** user clarification, 2026-10-12.
- **Rule:** Б77 HTML/PWA in `alexbotleh-oss/LK` and the separate `RECIPE_MANAGER` ChatGPT project are two independent project chains, even though both concern «Что приготовить».
- **Reason:** they have different formats, implementation details, and accumulated histories. A shared product idea does not make their code state or chronology interchangeable.

## D-B77-002 — Learn from projects, not by endlessly polishing the protocol
- **Decision/source:** user clarification, 2026-10-12.
- **Rule:** prioritize extracting and applying lessons from real project errors and outcomes. Accept that some historical details may remain missing; do not let perfect reconstruction become a blocker to practical use.
- **Guardrail:** missing details must still be marked unknown, not filled in by guesswork.

## D-B77-003 — Preserve the existing business chain
- **Evidence:** B77 continuity report and scanner change history.
- **Rule:** scanner/camera work feeds the existing `Core.findQR()` and Products/Shopping/QR handlers. No parallel Core and no broad business-logic rewrite as part of an input-layer change.

## D-B77-004 — Keep verified checkpoints and frozen components
- **Evidence:** B77 continuity report.
- **Rule:** retain immutable pre-camera and WP backups; do not replace Stage14-WP with an unverified candidate; Fix6/Flet and Core/business logic remain frozen unless a separate, explicit task changes that boundary.

## D-B77-005 — A recorded change is not a validated outcome
- **Evidence:** Data Matrix attempt at [456b420](https://github.com/alexbotleh-oss/LK/commit/456b4208e94b9e2130ffa2a4a29d0041d9be7679) followed by rollback at [d5a77c1](https://github.com/alexbotleh-oss/LK/commit/d5a77c141e268bd2275af8748c2c4e5db2fec27a).
- **Rule:** preserve attempted changes, test evidence, and rollback relationships. Do not label a feature working merely because a commit exists.

## D-B77-006 — Use repository history as technical evidence, not as a substitute for user intent
- **Evidence:** `reports/PROJECT_CONTINUITY_20261005.md`.
- **Rule:** recover intent and decisions from the ChatGPT Project and its source chats/files; use LK for actual files, commits, diffs, and technical verification. Do not ask the user to repeat information that can already be retrieved.
