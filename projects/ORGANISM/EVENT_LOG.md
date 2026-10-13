# ORGANISM — event log

Append-only event history. Dates refer to event/artifact dates when known; the memory-write date is 2026-10-13. Where a timestamp is not independently available, it is explicitly omitted. These records cover selected evidence, not a full chat export.

## E-ORG-001 — Project write permission recovery
- **Event date:** 2026-10-08 (from saved context; exact time not carried here)
- **Observed:** Initial write to `alexbotleh-oss/organism` failed with HTTP 403; permissions were subsequently corrected and a test commit was created.
- **Evidence:** Commit `4bef5a18b7bfe3b7dd4279eef6dd67865e3320fc`.
- **Status:** Historical context record; original API trace not present in this transfer.
- **Lesson link:** `projects/ORGANISM/LESSONS.md#L-ORG-001`.

## E-ORG-002 — Android import/history capability reported tested
- **Event date:** 2026-10-09 (saved context)
- **Observed:** Prior project context reports a phone test with 74 conversations and 10,034 messages; RAW ZIP retained. It also records that completeness was not established.
- **Evidence:** Saved conversation summary; no corresponding raw device capture was available in this turn. A separate earlier CI APK is referenced at Actions runs `37934665987` and `37934665912`, source commit `258d0edd70d7fc5a30c78a3ddbafb633c85c61c5`.
- **Status:** Reported historical result, not re-run during this transfer.
- **Caveat:** Do not convert these counts into proof of complete archive ingestion.

## E-ORG-003 — API quota error distinguished from app defect
- **Event date:** 2026-10-09 (saved context)
- **Observed:** ChatGPT API connector returned `subscription_sharing_usage_limit_exceeded`; context said quota reset Nov 4 and auto top-up off.
- **Interpretation:** Evidence points to provider/account quota at that time, not an app-side implementation failure. Do not bypass provider limits.
- **Evidence:** Saved conversation summary; underlying provider response is not re-opened in this transfer.
- **Status:** Historical reported fact, not current quota status.

## E-ORG-004 — WebView file chooser implemented, device behavior unknown
- **Event date:** Source change is present by project source SHA `08cb9dafdbc2eae918808886adfa310b178d5a6e`; exact implementation commit not identified here.
- **Observed in source:** `PlatformWebActivity.java` installs a `WebChromeClient` with `onShowFileChooser`, starts the Android chooser, and forwards `WebChromeClient.FileChooserParams.parseResult` through `pendingFileChooser.onReceiveValue` in `onActivityResult`. It also sets `settings.setAllowContentAccess(false)`.
- **Status:** Source behavior verified by reading the file; end-to-end image upload not verified.
- **Causal hypothesis:** Disabling content URI access may prevent WebView from reading a user-selected `content://` URI. This is plausible but not proven.
- **Consequence:** A source edit was attempted in the current chat to set content access true while retaining file:// access false, but the tool blocked the write. No commit or APK resulted.

## E-ORG-005 — Successful debug APK artifact recovered after false negative
- **Event date:** Artifact created 2026-10-09T20:28:01Z
- **Observed:** Earlier check wrongly concluded there was no APK because a workflow-run helper filtered to PR-triggered runs and combined status returned no useful signal. Listing artifacts for the known push run found a successful build.
- **Evidence:** Actions run https://github.com/alexbotleh-oss/organism/actions/runs/37987076157 ; artifact ID `11642818226`; source SHA `08cb9dafdbc2eae918808886adfa310b178d5a6e`; extracted `app-debug.apk` size 11,460,069 bytes; SHA-256 `ccadeea02297103d2f4f3c385a7f3b6d0910889e7fd09901f0e74d22376a3298`.
- **Correction:** The earlier “no APK found” conclusion was false; a successful CI debug APK existed.
- **Limits:** CI build success does not prove device usability; no device test or production signing is implied.
- **Project records:** Worklog commit `ed7e9da8dfb25e7fc30764c6dbebbca730cc5932`; handoff commit `03e19356ef19726b413b7374a5e58976b6bd887f`.

## E-ORG-006 — Device WebView login showed DNS error in prior test
- **Event date:** 2026-10-10 (saved context; exact time was 08:33Z)
- **Observed:** After selecting a sign-in method, user reported a white screen; log was `WEBVIEW main-frame error code=-2`, `net::ERR_NAME_NOT_RESOLVED`. Device context: Android 16 / SDK 36, WebView 153.0.8010.36.
- **Interpretation:** Name resolution failed at that attempt. This alone does not prove the login code itself is defective.
- **Status:** Historical report; not reproduced in this transfer.

## E-ORG-007 — UI evidence: duplicate composer and cookie overlay
- **Event date:** 2026-10-13 (current conversation; screenshot message time not available)
- **Observed:** Five screenshots show ChatGPT's own web composer plus ORGANISM's separate bottom composer/helper, cookie consent overlay obscuring the WebView, and message text present in ChatGPT while ORGANISM's own composer remains.
- **User report:** Selecting a screenshot in Android files and tapping Add does not make it appear in the ChatGPT conversation. User said they would restart the app; no result of that retry is present yet.
- **Source evidence:** User-uploaded screenshots in the current chat (five images; available paths were /mnt/data/19920.jpg, /mnt/data/19946.jpg, /mnt/data/19947.jpg, /mnt/data/19948.jpg, /mnt/data/19949.jpg in this runtime).
- **Status:** UI overlap directly observed; image-upload failure is user-reported; exact failure point and root cause unknown.
- **Next test:** Verify whether chooser returns a URI, whether ChatGPT shows the selected-image preview, and whether cancellation/error is surfaced. Do not clear app data.

## E-ORG-008 — UI standard made mandatory project-wide
- **Event date:** 2026-10-09 (commit sequence from saved project context)
- **Observed:** `docs/ANDROID_UI_STANDARD_v1.0.md` added at commit `43ce4ef35b697cb60d0fce690841a402c8ffd847`; `PROJECT_INSTRUCTIONS.md` updated at `c8530c0b4d3a76e79aaf78a99a9cc763f81fc916`.
- **Requirements:** Safe-area/window insets, keyboard reachability, touch target >=48x48dp, spacing, adaptive layouts, accessibility, and screen-by-screen release checklist.
- **Status:** Policy documented; full audit is not complete.

## E-ORG-009 — Proposed WebView upload patch blocked
- **Event date:** 2026-10-13
- **Precondition:** Source inspection showed `setAllowContentAccess(false)` alongside a WebChromeClient file chooser.
- **Action:** Attempted GitHub contents update to set content URI access true with file:// access still disabled.
- **Result:** Tool returned “blocked by OpenAI security systems”; no commit SHA was returned and no write was verified.
- **Conclusion:** No code fix, new build, or test resulted. The proposed causal explanation remains a hypothesis.


## E-ORG-010 — OAuth consent page spinner and manual return (2026-10-13)

- Event date: 2026-10-13; phone status bar in screenshot shows 18:20, but timezone and message timestamp are unavailable.
- User report: after approving permissions on auth.openai.com, the browser remains on the consent page with the primary control spinning and does not automatically return to ORGANISM. Manually switching back to the app causes it to display connected. User says this has happened since the first use.
- Direct evidence: screenshot shows the consent page, spinner, and browser chrome. It does not show a callback URL or diagnostic trace.
- Source branch inspected: fix/oauth-diagnostic-trace-20261009; branch HEAD separately fetched as 2f67f6b817b065acaa8b9f4bd0e0a77e6b73d7ce. This does not prove the installed APK was built from this HEAD.
- MainActivity.signIn() starts a loopback listener on 127.0.0.1 using an OS-assigned port (fallback hint 1455), opens the auth URL, and waits up to 120 seconds for ServerSocket.accept(). Trace stages include CALLBACK_LISTENER/READY, BROWSER_LAUNCH/REQUESTED, CALLBACK_WAIT/WAITING, CALLBACK_RECEIVED, OAUTH_STATE, OAUTH_CODE, TOKEN_EXCHANGE, ID_TOKEN_VALIDATION, OAUTH_SCOPE, AUTH_PERSISTENCE and AUTH_COMPLETE; timeout records CALLBACK_WAIT/TIMEOUT.
- AndroidManifest.xml on this branch has only the MainActivity launcher filter, with no custom organism-scheme callback filter. The callback implementation instead serves an HTTP page with a JavaScript/intent link intended to return to the app.
- AuthTrace.java stores a bounded timestamped trace (up to 120 lines); Settings exposes “Журнал диагностики авторизации” with copy/clear actions. No credential values should be logged.
- Hypotheses, not facts: browser/provider might not redirect to the listener; callback may arrive while automatic foreground handoff fails; installed APK may not match inspected source; current “connected” UI may reflect already-persisted credentials rather than this attempt.
- Separate issue: subscription_sharing_usage_limit_exceeded is a provider/account usage-limit response and is not evidence of OAuth callback failure.
- Status: symptom user-reported and screenshot-observed; root cause UNCONFIRMED. No patch, build or fresh device trace was made in this event.
- Next test: clear only the auth diagnostic trace, not app data; run one controlled connect attempt; after spinner stalls, copy trace. Determine whether it ends at BROWSER_LAUNCH/CALLBACK_WAIT, records CALLBACK_RECEIVED, or advances to token validation/persistence. Do not share full URLs, codes, tokens, cookies or account details.


## E-ORG-011 — Master architecture v0.3 consolidates the continuity-first design
- **Event/artifact date:** 2026-10-07 (date printed in the artifact).
- **Source:** S-ORG-019 (master architecture v0.3), supported by S-ORG-020 (ORGANISM_SOLUTION_v0.2) and S-ORG-021 (memory/history pipeline).
- **Prior state:** several competing proposals described different implementation orders and storage complexity.
- **Documented outcome:** prioritize a demonstrable continuity test; preserve RAW and provenance; establish a sound logical memory model without overbuilding the physical schema; use SQLite as the first local store; append event history; implement Context/Resume Engine; keep CORE separate from MEMORY; treat the model as a replaceable executor.
- **Status:** architecture decision documented in a project artifact; not evidence that these components were implemented or tested in the app.
- **Causal confidence:** direct evidence of what the document decided; not evidence that the design has already succeeded in runtime.

## E-ORG-012 — Memory/History pipeline and adversarial review requirements documented
- **Event/artifact date:** 2026-10-08 (dates printed in the specifications).
- **Sources:** S-ORG-021, S-ORG-022, S-ORG-025, S-ORG-026.
- **Documented pipeline:** RAW → PROVENANCE → EXTRACTION → AUDIT → MEMORY MAP / LOSS-COVERAGE MAP → MEMORY → CONTEXT / ACTIVE FIELD → MEMORY HANDOFF → MODEL → NEW EXPERIENCE, with feedback into the event log and memory.
- **Key constraints:** preserve the original source; retain chronology and changes in understanding; distinguish claims from verification status; keep project-specific experience separate from transferable lessons; retain negative experience and rejected paths; show extraction coverage and uncertainty.
- **Important limit:** S-ORG-025 and S-ORG-026 are task/specification documents for independent analysis, not proof that every requested stress test was executed or passed.
- **Status:** design requirements documented; runtime implementation and end-to-end tests are not established by these artifacts alone.

## E-ORG-013 — User clarifies browser-mediated Android agent requirements
- **Event date:** 2026-10-13; exact message timestamp/ID unavailable in the retained chat excerpt.
- **Source:** S-ORG-017.
- **User-stated goal:** Android application stores chat history, restores context when a chat reaches its limit or work moves to another chat, uses prior experience to build better prompts, and detects repetitive no-progress loops.
- **Interaction preference:** embed the AI provider's web interface; the application should mediate input and read the response from the browser rather than defaulting to a model API.
- **Autonomy preference:** maximize autonomy within explicit safety and permission limits.
- **Status:** user requirement / product direction. This event does not establish that browser send/receive automation is implemented or that a provider permits every proposed interaction.

## E-ORG-014 — Assistant proposed a Kotlin/Room implementation before inspecting the live source repository
- **Event date:** 2026-10-13, in the assistant architecture response immediately preceding this transfer request.
- **Source:** S-ORG-017 (current conversation); counter-evidence: S-ORG-029 and S-ORG-030.
- **Action:** the response proposed Kotlin and Room as the Android implementation stack and depicted WebView input/output as an interaction loop.
- **New evidence:** the live ORGANISM repository already contains Java application classes including MainActivity.java, Db.java, ImportPipeline.java, ContextEngine.java, ExperienceEngine.java, ReflexEngine.java and PlatformWebActivity.java. The inspected PlatformWebActivity source implements a separate composer that copies text to the clipboard; it does not by itself demonstrate automatic provider-message submission and response ingestion.
- **Assessment:** the Kotlin/Room recommendation was premature and was not grounded in the existing implementation. Treat it as an unaccepted proposal, not a project decision. Continue from the existing Java/SQLite application unless an explicit migration case is established.
- **Status:** corrected design recommendation; no project source was changed by this transfer.

## E-ORG-015 — Current source readback corrects a stale WebView content-access observation
- **Observation date:** 2026-10-13.
- **Sources:** S-ORG-029 and S-ORG-030; earlier transfer observation S-ORG-002.
- **Observed current branch state:** fix/oauth-diagnostic-trace-20261009 points to 2f67f6b817b065acaa8b9f4bd0e0a77e6b73d7ce. The current PlatformWebActivity.java blob is 64719a041ac899884bb6abb462b2e536a8088528 and sets WebSettings.setAllowContentAccess(true) while retaining the separate clipboard-based composer.
- **Correction boundary:** the earlier note that the source contained setAllowContentAccess(false) may accurately describe the older blob inspected at that time, but it is not accurate for the current branch file. The old observation must remain in history, not be silently rewritten. It is not a current explanation of the upload issue.
- **Status:** source-level readback verified; end-to-end attachment behavior is not established by this readback.

## E-ORG-016 — Source repository branch pointers are inconsistent across current refs and handoff text
- **Observation date:** 2026-10-13.
- **Sources:** S-ORG-027 and S-ORG-028.
- **Observed refs:** main → 6835e00ba03a3bef3206eb49c924f80604c1da17; fix/oauth-diagnostic-trace-20261009 → 2f67f6b817b065acaa8b9f4bd0e0a77e6b73d7ce; fix/zip-import-crash-and-archive-restore → c201c730604575bd799971accff486ff0e51bb22.
- **Conflict:** PROJECT_INSTRUCTIONS / handoff text still points to fix/zip-import-crash-and-archive-restore, while the inspected fix/oauth-diagnostic-trace-20261009 branch has a later commit timestamp. GitHub branch refs establish these branch heads, but cannot establish which branch is checked out in a user's local working tree.
- **Status:** conflicting project metadata preserved; no local-worktree branch is asserted.
