# ORGANISM — decisions

## D-ORG-001 — Android phone as first platform
- **Decision date:** 2026-10-09 or earlier; exact timestamp unavailable in this extract.
- **Decision owner:** User.
- **Decision:** First platform is Android phone; provider web UI is embedded in the app; autonomy should be maximized within constraints.
- **Evidence:** Project conversation memory; current task continuity instructions.
- **Status:** Active.

## D-ORG-002 — Provider-neutral memory and connectors
- **Decision:** User/project memory must remain separate from any single model, provider, API or browser session; use one shared memory with different connectors.
- **Evidence:** Project conversation memory and architecture discussions; see `ORGANISM_CURRENT_STATE_v0.1_2026-10-08.md` (uploaded Library file, not a live repo path).
- **Status:** Active architectural goal, not fully implemented.

## D-ORG-003 — Official web interfaces primary; API optional
- **Decision:** Keep official provider web interfaces as a primary path and use API when suitable/available. No authentication bypass, hidden session extraction, or quota circumvention.
- **Evidence:** Current project context and the reported API quota incident E-ORG-003.
- **Status:** Active.

## D-ORG-004 — Preserve user data and reversibility
- **Decision:** Do not clear imported archives, databases, chats, preferences or credentials for convenience. Any destructive operation requires explicit user approval and a recovery plan.
- **Evidence:** Project continuity instructions and current task constraints.
- **Status:** Active, mandatory.

## D-ORG-005 — UI standard applies to every screen
- **Decision:** `docs/ANDROID_UI_STANDARD_v1.0.md` is mandatory across the project, not only the WebView screen.
- **Evidence:** Project commit `43ce4ef35b697cb60d0fce690841a402c8ffd847` and instruction update `c8530c0b4d3a76e79aaf78a99a9cc763f81fc916`.
- **Status:** Active; compliance audit incomplete.

## D-ORG-006 — Manual WebView prototype is not the intended final UX
- **Decision/requirement:** Avoid a workflow that forces the user to copy/paste prompts and responses between ORGANISM and provider websites. The current prototype is explicitly acknowledged as an interim/manual state; desired direction is a unified interaction with shared history/context, using an appropriate mix of official web UI and APIs where feasible.
- **Evidence:** Current conversation (2026-10-13) and source text in `PlatformWebActivity.java` that says the prompt is copied and must be manually pasted/sent.
- **Status:** Requirement active; automatic send/receive is not implemented or verified.


## D-ORG-007 — Instrument the OAuth boundary before patching

- Decision date: 2026-10-13.
- Owner: user explicitly proposed diagnostics on the phone showing sent/received commands/events so the failing side and exact stage are visible.
- Decision: use the existing copyable OAuth trace first; add markers only for unobserved boundaries. Record listener readiness, browser handoff, callback receipt/timeout, state/code presence (never values), token exchange outcome, validation, persistence and foreground return.
- Privacy: do not log authorization URLs, codes, tokens, cookies, email or secret parameters.
- Status: accepted diagnostic strategy; no fresh trace for this failure has been collected yet.
