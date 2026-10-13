# ORGANISM handoff — 2026-10-13

## Working scope
Continue the Android ORGANISM project in `alexbotleh-oss/organism`, not another app/project. Current engineering focus: WebView image attachment failure and UI overlap observed in five screenshots.

## Known source and artifact references
- Project branch last directly verified: `fix/oauth-diagnostic-trace-20261009`.
- APK app-source SHA: `08cb9dafdbc2eae918808886adfa310b178d5a6e`.
- Successful CI run: https://github.com/alexbotleh-oss/organism/actions/runs/37987076157
- Artifact ID: `11642818226`; APK SHA-256 `ccadeea02297103d2f4f3c385a7f3b6d0910889e7fd09901f0e74d22376a3298`.
- Latest project documentation commits previously verified: `ed7e9da8dfb25e7fc30764c6dbebbca730cc5932` (worklog), `03e19356ef19726b413b7374a5e58976b6bd887f` (handoff).
- Source file: https://github.com/alexbotleh-oss/organism/blob/fix/oauth-diagnostic-trace-20261009/app/src/main/java/com/organism/app/PlatformWebActivity.java

## Immediate next engineering step
1. Re-read `PROJECT_INSTRUCTIONS.md`, `docs/CONTINUITY_HANDOFF_2026-10-09.md`, `docs/WORKLOG_AND_CONTINUITY_PROTOCOL_v1.0.md`, `docs/WORKLOG.md`, `docs/ANDROID_UI_STANDARD_v1.0.md` on the current project branch.
2. Fetch current branch HEAD and inspect source diffs before changing anything.
3. Trace Android file chooser callback, URI permissions and WebView upload behavior. `setAllowContentAccess(false)` is a plausible culprit but not a confirmed root cause.
4. Apply one minimal patch only after the diagnosis; run CI and record exact commit/artifact/hash.
5. On-device test image selection to attachment preview, send, cancellation, cookie overlay, keyboard/safe areas and history retention. Do not clear app data.
6. Separately plan UI cleanup: avoid simultaneous provider composer plus clipboard-only ORGANISM composer unless the app composer has a real supported connector.

## Limits
- The user said they would restart and retry attachment selection, but no retry result is yet available.
- No patch was applied in the prior attempt: the GitHub write tool was blocked by a security filter.
- No new APK was built; no device verification was performed during this transfer.
- This is a partial memory handoff, not proof that all historical chat messages/files were extracted.
