# ORGANISM — project state (source-grounded transfer)

**Record status:** PARTIAL — extracted from available project context, selected attachments, GitHub records and the current conversation; not a complete export of the entire chat.
**Memory entry created:** 2026-10-13
**Project repository:** https://github.com/alexbotleh-oss/organism
**Observed project branch:** `fix/oauth-diagnostic-trace-20261009`
**Last project commits directly verified in current work:** `03e19356ef19726b413b7374a5e58976b6bd887f` (handoff update), preceded by `ed7e9da8dfb25e7fc30764c6dbebbca730cc5932` (worklog update).
**Latest app-source SHA evidenced by the recovered APK:** `08cb9dafdbc2eae918808886adfa310b178d5a6e`; this is not asserted to be the current branch HEAD.

## Purpose and boundary
ORGANISM is an Android-first continuous-agent application with durable project memory, history/context restoration, experience recording and model/provider connectors. User-selected initial platform: Android phone; embed the provider's official web UI in the app; maximize autonomy within constraints. Its memory and project history should belong to the user/system rather than one model, provider session or chat.

This record covers ORGANISM only. It does not absorb CARD111, RECIPE_MANAGER, B77_HTML_PWA or the implementation history of the general agent-knowledge-base. Cross-project lessons are separately generalized in LESSONS.md and must not replace ORGANISM's event history.

## Confirmed architecture / product decisions
- Official provider web interfaces are a primary interaction path; API is optional/connector-dependent.
- Intended providers mentioned in project context: ChatGPT, Claude, DeepSeek, Qwen, Gemini and Yandex Alice.
- WebView prototype is manual and incomplete: user can open the official site and type/paste/send there; the app has a separate prompt composer that copies text to clipboard. No verified automatic DOM control, send/receive loop or response ingestion exists.
- Durable imported archive and user data must not be cleared or re-imported as a casual diagnostic shortcut.
- Android UI quality standard is mandatory across the app: safe areas/insets, keyboard reachability, 48dp touch targets, scrolling, adaptive layouts, accessibility and screen-by-screen release checklist. Source: project commit `43ce4ef35b697cb60d0fce690841a402c8ffd847`; project instructions updated at `c8530c0b4d3a76e79aaf78a99a9cc763f81fc916`.

## Known verified state (not a claim of release readiness)
- A successful CI debug APK exists for source SHA `08cb9dafdbc2eae918808886adfa310b178d5a6e`, Actions run `37987076157`, artifact ID `11642818226`. APK SHA-256: `ccadeea02297103d2f4f3c385a7f3b6d0910889e7fd09901f0e74d22376a3298`. Artifact was retrieved and inspected; it is a debug APK, not a production release.
- Project docs were updated to correct an earlier false-negative conclusion that no APK existed. Worklog commit: `ed7e9da8dfb25e7fc30764c6dbebbca730cc5932`; handoff commit: `03e19356ef19726b413b7374a5e58976b6bd887f`.
- A prior phone import test was reported in earlier project context: 74 conversations, 10,034 messages and a retained RAW ZIP. This is a historical reported result, not re-tested in this transfer.
- A prior ChatGPT API attempt hit `subscription_sharing_usage_limit_exceeded`; that was reported as account quota, not an app defect. Do not bypass provider quotas/authentication.
- Prior WebView login attempt reported a white page and `net::ERR_NAME_NOT_RESOLVED` (Android 16 / WebView 153.0.8010.36 in the supplied context). This was a network/name-resolution failure observed at that time, not proof of a general auth bug.

## Current visible defect report (2026-10-13 conversation)
User reports selecting a screenshot in the file picker and tapping add, but the image does not appear in the ChatGPT conversation. They provided five screenshots. They also said they would try restarting the app; no result of that retry is yet available.
Screenshots show:
1. ChatGPT cookie consent dialog overlays most of WebView while ORGANISM's own bottom helper/composer remains visible.
2. ChatGPT's native web composer and ORGANISM's separate composer coexist.
3. User text is visible in ChatGPT history while ORGANISM still shows a separate input/button.
4–5. ChatGPT composer state changes while the separate ORGANISM composer remains; no screenshot proves an image attachment was selected or delivered.
In source `app/src/main/java/com/organism/app/PlatformWebActivity.java` at project branch `fix/oauth-diagnostic-trace-20261009`, WebChromeClient implements `onShowFileChooser`, and `onActivityResult` passes parsed URI results back to WebView. However `WebSettings.setAllowContentAccess(false)` is set. This is a plausible attachment-path issue, not a confirmed root cause. A proposed change to enable content URI access was blocked before any GitHub write; therefore no fix/commit/new APK resulted from that attempt.

## Current status
- Functional architecture: PARTIAL / prototype.
- Automatic web-chat interaction: NOT IMPLEMENTED / NOT VERIFIED.
- Attachment upload: REPORTED FAIL; root cause NOT CONFIRMED; fix NOT APPLIED.
- UI: visible overlapping/duplicate composers and cookie-overlay layout issue reported from screenshots; device audit remains incomplete.
- APK: successful CI debug artifact retrieved; physical-device release gate remains incomplete.
- Data safety: previous investigation was read-only with respect to app data; no user archive/database/preferences were changed.

## Next step
Continue from attachment diagnosis on the exact branch/source. Read project instructions, handoff, continuity protocol, worklog and Android UI standard; inspect current branch/head before editing. Investigate WebView file chooser and content URI permission handling; make one minimal source change, build, inspect APK provenance, and record exact commit. Then verify on device: select image, ensure it appears as a ChatGPT attachment preview, cancel path, cookie dialog, keyboard/safe areas, and preservation of imported history. Do not claim device verification until evidence exists.


## OAuth return diagnostic state (2026-10-13 addendum)

The visible blocker is a repeated OAuth consent-page spinner and failure to return automatically to ORGANISM. The user says manually switching back makes the app show connected; that status is not proof the just-started OAuth exchange completed.

On branch fix/oauth-diagnostic-trace-20261009, source has an in-app copyable auth trace and a loopback listener. It launches auth.openai.com, waits up to 120 seconds, checks state/code, exchanges the code, validates ID token/scope, saves credentials and records outcomes. The inspected manifest has no custom-scheme callback filter; the source relies on an HTTP loopback callback page and an intent link. The installed APK identity remains unknown.

Next step: clear only the auth trace immediately before one controlled attempt, approve once, and copy the trace after the spinner stalls. CALLBACK_WAIT/TIMEOUT points to no callback reaching the listener; CALLBACK_RECEIVED followed by a later failure localizes the problem further; AUTH_COMPLETE/SUCCESS with spinner still visible suggests an issue after successful exchange, subject to confirming the installed APK matches inspected source. If previous trace events remain, separate them by timestamps and a fresh AUTH_START marker. Do not collect or share credentials, codes, tokens, cookies or full authorization URLs. The separate subscription_sharing_usage_limit_exceeded message remains a usage-limit issue.
