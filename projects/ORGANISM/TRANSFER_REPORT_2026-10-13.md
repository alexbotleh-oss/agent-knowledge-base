# ORGANISM experience transfer report — 2026-10-13

## Purpose
Transfer verifiable ORGANISM-specific experience from the currently available project conversation/context into this repository, keeping source provenance, chronology, decisions, failures and generalizable lessons separate.

## Coverage boundary
Available: current user request; current conversation context including five uploaded screenshots; saved project memory excerpts; selected uploaded/library artifact search results; live GitHub reads of `PlatformWebActivity.java`, `docs/ANDROID_UI_STANDARD_v1.0.md`, project `WORKLOG.md` and handoff; known CI artifact metadata and previous verified project commits.
Not available: a complete raw export of every message in this project chat with stable message IDs/timestamps; full contents of every uploaded DOCX/ZIP; direct device access; a new Android build/test in this turn. Therefore coverage is PARTIAL and must not be described as complete chat mining.

## Chronology and causality
- Earlier architecture decisions (Android first, embedded official provider UI, provider-neutral memory) are retained as user decisions but some exact timestamps are unavailable.
- 2026-10-09: CI debug APK artifact later found to exist despite a prior negative lookup. The earlier lookup was insufficient because the helper filtered to PR-triggered runs; the successful push run artifact query provided the counter-evidence.
- 2026-10-10: a prior sign-in attempt was reported to end on a white page with `net::ERR_NAME_NOT_RESOLVED`. This is recorded as a network/name-resolution error at that attempt, not as a proven app authentication defect.
- 2026-10-13: user reports image selection does not result in an attachment visible in ChatGPT. Screenshots establish overlapping UI and duplicate composers, but do not show the chooser return path. Source inspection found chooser callbacks and disabled content access; causality is not proven.
- A patch was proposed but the GitHub write was blocked. It did not change source and did not generate a new artifact.

## Duplication and scope controls
No attempt was made to copy ORGANISM source code or the whole app into the memory repository. This is a project-memory record. No records for CARD111, RECIPE_MANAGER or B77_HTML_PWA are being changed. Cross-project candidates are expressed as generalized rules only in `LESSONS.md`.

## Verification plan / results
- Re-read every file created by this transfer after commits.
- Check JSONL syntax in SOURCES.jsonl.
- Run the repository's documented memory validator and unit tests if accessible via connector or local source; if unavailable, record BLOCKED, not PASS.
- Verify branch and exact commit URLs.
- Do not merge this branch to main.


## Addendum: OAuth return-flow symptom from later message (2026-10-13)

The user supplied a new screenshot and clarified that auth.openai.com stays on a spinner after consent and does not return automatically to ORGANISM; manually switching back makes the app show connected. This is a distinct event from the earlier 2026-10-10 DNS failure and the separate usage-limit error.

Verified source on fix/oauth-diagnostic-trace-20261009 has AuthTrace and a Settings trace viewer. MainActivity.signIn() binds a loopback HTTP server, launches the provider authorization page, waits up to 120 seconds, checks state/code, exchanges the code, validates ID token/scope and persists credentials with trace markers. Branch HEAD at inspection: 2f67f6b817b065acaa8b9f4bd0e0a77e6b73d7ce; file blob IDs recorded in SOURCES.jsonl. The manifest has no custom callback-scheme filter in this branch; callback handoff uses a local HTTP page plus intent link.

Causality is unknown until a fresh device trace is collected. Use the final stage to localize the issue; do not infer callback success from the app status alone. The usage-limit message is independent and must not be bypassed.

Coverage remains PARTIAL: this is extracted from available chat context, one screenshot, selected project records and live source reads, not a complete raw-chat export. No code changes, build, device trace capture or OAuth fix were performed in this memory transfer. No user data was changed. Do not merge this branch to main.
