# ORGANISM lessons and cross-project candidates

Project-specific observations stay linked to ORGANISM events. Only the generalized rule is portable to other projects; do not use this file to rewrite another project's history.

## L-ORG-001 — A negative status query is not proof an artifact does not exist
- **Origin event:** `E-ORG-005`
- **Observed failure:** A helper only returned PR-triggered workflow runs and combined status did not expose the successful push build, producing a false conclusion that no APK existed.
- **Corrective evidence:** Directly querying artifacts for run `37987076157` returned artifact `11642818226` tied to source SHA `08cb9dafdbc2eae918808886adfa310b178d5a6e`.
- **Rule:** Before declaring an artifact absent, inspect the relevant workflow run/artifact endpoint and trigger type; treat “no result from a filtered helper” as “not found by this query,” not “does not exist.”
- **Confidence:** High for this observed incident.
- **Portable candidate:** Yes — build/artifact diagnostics across projects.

## L-ORG-002 — Build success is not device verification
- **Origin events:** `E-ORG-005`, `E-ORG-008`
- **Evidence:** CI confirms compilation for a commit, while the app still has unverified WebView safe areas, keyboard behavior, file chooser and visual layout. The project UI standard explicitly separates CI build from device verification.
- **Rule:** Report exact commit and CI evidence separately from emulator/physical-device evidence; never call a screen usable based on compilation alone.
- **Confidence:** High.
- **Portable candidate:** Yes — all UI/app projects.

## L-ORG-003 — Do not infer upload success from a file-picker callback existing
- **Origin event:** `E-ORG-004`, `E-ORG-007`, `E-ORG-009`
- **Observed:** Source has a WebChromeClient chooser callback and forwards parsed URIs, but user reports image not appearing in ChatGPT.
- **Hypothesis:** `setAllowContentAccess(false)` may interfere with reading the selected content URI.
- **Rule:** Test the full chain: picker opens → URI returned → WebView can read URI → website displays attachment preview → message sends with attachment. Track each step; don't claim a root cause until evidence localizes the failure.
- **Confidence:** High for the testing rule; medium/low for the proposed specific root cause.
- **Portable candidate:** Yes — Android WebView upload integrations.

## L-ORG-004 — Duplicate control surfaces create ambiguous ownership
- **Origin event:** `E-ORG-007`
- **Observed:** Provider page has its own message composer, while ORGANISM renders a separate composer and helper below the WebView. Screenshots show the two surfaces coexisting and consuming viewport space.
- **Rule:** Choose one explicit interaction model: (a) provider-owned web composer with no redundant app composer, or (b) an integrated app composer backed by a real supported send/receive connector. Avoid presenting a clipboard-only composer as if it were integrated chat.
- **Confidence:** High for observed duplication and UX ambiguity; exact best final implementation remains an architecture decision.
- **Portable candidate:** Yes — embedded third-party web experiences.

## L-ORG-005 — Diagnose before making an access-control change
- **Origin event:** `E-ORG-004`, `E-ORG-009`
- **Observed:** Enabling WebView content access was proposed based on source inspection but was not applied or tested.
- **Rule:** Keep file:// access disabled where possible; inspect Android URI grants, file chooser params, WebView/provider behavior and logs before changing broad access. Make the narrowest change and test both upload and cancellation.
- **Confidence:** High for cautious diagnostic process; root cause unresolved.
- **Portable candidate:** Yes — Android permission/security fixes.

## L-ORG-006 — Preserve user data while diagnosing
- **Origin:** Project safety requirements and current issue.
- **Rule:** Do not advise clearing app data, uninstalling, deleting the RAW archive or re-importing as a first-line test. Establish recovery and permission before destructive steps.
- **Confidence:** High.
- **Portable candidate:** Yes — any app with user-owned persistent data.


## L-ORG-007 — Diagnose OAuth handoff at the redirect boundary

- Origin event: E-ORG-010.
- Observed: consent screen can remain on a spinner while the app later appears connected after manual switching. Screenshot alone does not prove callback receipt or token persistence.
- Rule: trace launch, callback-listener readiness, browser handoff, callback receipt/timeout, state/code checks, token exchange, token validation, persistence and foreground return. Let the last confirmed stage determine the next investigation; do not patch OAuth/browser code before locating the boundary.
- Privacy: record sanitized stage/outcome and presence/absence only; never log credential values, codes, tokens, cookies or full URLs.
- Portable candidate: mobile OAuth/browser handoff flows.


## L-ORG-008 — Inspect the existing implementation before recommending a new stack
- **Origin event:** E-ORG-014; counter-evidence in E-ORG-015.
- **Observed mistake:** the architecture response proposed Kotlin + Room before inspecting the live repository. The source already contains a Java Android application and SQLite-related modules (Db.java, ImportPipeline.java, ContextEngine.java, ExperienceEngine.java, ReflexEngine.java, PlatformWebActivity.java).
- **Prevention rule:** before recommending a language, framework, database migration or project restart, inspect the current repository tree, build files, branch, HEAD and existing implementation. Mark a stack suggestion as PROPOSED until reconciled with source and user decisions. Prefer incremental continuation over migration without a demonstrated need.
- **Confidence:** High for the observed premature recommendation and the current source inventory.
- **Portable candidate:** Yes — existing software projects.

## L-ORG-009 — An embedded web page is not proof of an automated connector
- **Origin events:** E-ORG-013, E-ORG-014, E-ORG-015; source S-ORG-029.
- **Observed boundary:** the current Android screen has a separate prompt composer that copies text to the clipboard. This does not establish automatic send, response extraction, or response persistence.
- **Prevention rule:** test and report each boundary separately: provider page opens → user/session is valid → input is submitted through a supported mechanism → response completion is detected → response is read → response is persisted → history/context is reconciled. Do not describe a manual clipboard flow as integrated automation.
- **Confidence:** High for the distinction; automatic provider interaction remains unverified.
- **Portable candidate:** Yes — embedded third-party web experiences and browser automation.

## L-ORG-010 — Pin source observations to immutable commits or blob SHAs
- **Origin event:** E-ORG-015; prior mutable-path observation S-ORG-002 and current blob S-ORG-029.
- **Observed risk:** a file URL on a branch can show different contents after that branch advances. An earlier note described setAllowContentAccess(false), while the current branch file blob 64719a041ac899884bb6abb462b2e536a8088528 has it enabled.
- **Prevention rule:** store branch HEAD and file blob SHA/commit with every important source observation. When a later read disagrees, append a correction event and keep the old observation as historical evidence; do not overwrite history or assume the branch path is immutable.
- **Confidence:** High for this repository-state discrepancy.
- **Portable candidate:** Yes — repository investigations and memory provenance.
