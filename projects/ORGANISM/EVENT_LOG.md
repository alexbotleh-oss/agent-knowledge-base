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
