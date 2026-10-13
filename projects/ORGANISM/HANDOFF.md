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


## New highest-priority issue — OAuth browser never returns automatically (2026-10-13)

User screenshot shows auth.openai.com consent page with the primary action stuck on a spinner. User reports that the browser stays open and they must manually switch to ORGANISM; the app then displays connected as it has since the first use. This is separate from subscription_sharing_usage_limit_exceeded.

Branch fix/oauth-diagnostic-trace-20261009 had HEAD 2f67f6b817b065acaa8b9f4bd0e0a77e6b73d7ce when checked. Source has an OAuth trace UI and loopback callback listener with a 120-second timeout. Start with one fresh in-app auth trace; do not clear app data or credentials. Use the last trace stage to localize the next step. The installed APK/source SHA is not known, so do not assume it exactly matches inspected branch.

Suggested single-attempt procedure: open Settings → Журнал диагностики авторизации; clear only that trace; start Connect; approve once; when the spinner stalls, return to ORGANISM and copy the trace. Review it for sensitive values before sharing. This provides evidence to tell no callback from post-callback failure. Root cause remains unknown.


## Separate architecture-chat handoff — 2026-10-13

This section covers the architecture conversation only. It is not a replacement for the separate OAuth/attachment engineering handoff above.

- **User goal:** Android-first ORGANISM; embedded provider web UI; persistent chat history; context restoration across chat limits/transitions; experience-informed prompt construction; loop detection; maximum autonomy within defined safeguards.
- **Established design baseline:** continuity-first; preserve RAW/provenance; SQLite as the first local store; append-only events; Context/Resume Engine; CORE separate from MEMORY; replaceable model/provider adapters; loss/coverage and claim-vs-verification distinctions.
- **Correction to the assistant's previous architecture proposal:** Kotlin + Room was proposed before source inspection and is not an accepted decision. The existing source tree is a Java Android application with Db.java, ImportPipeline.java, ContextEngine.java, ExperienceEngine.java, ReflexEngine.java, and PlatformWebActivity.java. Continue from this implementation unless a migration is justified by evidence.
- **Current interaction limit:** inspected WebView composer copies prompt text to clipboard. Automatic provider send/receive and response ingestion remain NOT VERIFIED. A successful CI build for an older source SHA is not device verification.
- **Source branch ambiguity:** GitHub refs show fix/oauth-diagnostic-trace-20261009 at 2f67f6b817b065acaa8b9f4bd0e0a77e6b73d7ce; handoff text still names fix/zip-import-crash-and-archive-restore at c201c730604575bd799971accff486ff0e51bb22. The actual local checkout is unknown.
- **Next action for the memory transfer:** independently review the new architecture-chat transfer report, verify source links and event chronology, and check the exact transfer branch/commit. Do not infer that architecture plans have been implemented or tested.
