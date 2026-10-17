# Bounded source reconciliation — historical APK build claim

Date: 2026-10-13  
Project: RECIPE_MANAGER / N99  
Scope: one historical claim from `Отчеты о извлечении.txt`. This is not a claim that the entire report has been reconciled.

## Claim under review

The extraction report says an APK was reportedly built on 2026-09-24, was 144 MB, and the application worked on PC. The report itself says the APK, SHA-256, build log, and installation result were not inspected in that audit.

## Canonical memory cross-check

- `EVT-RM-20260930-002`: a later build summary reports `app-release.apk` at 151.9 MB after a JNI override change. Its notes say the original log was not reopened in the rollup.
- `EVT-20261012-005`: a separate sequence records a user-reported APK build 5 and PC launch; the expected Android navigation criterion was not met.
- `EVT-20261012-002`: explicitly records that the current working tree, commit, and installed APK were not confirmed.

## Result

**Status: reported historically; not independently corroborated in this pass.**

The 144 MB / 2026-09-24 statement must not be merged with the later 151.9 MB build or build 5. These are distinct reported attempts unless an artifact identity, hash, or primary log proves otherwise. A PC launch does not establish Android runtime success.

## Evidence limitations

No raw APK, SHA-256, original build log, installation record, or primary chat message for the 144 MB claim was inspected in this pass. The claim remains a secondary-source historical report, not a verified build result.

## Changes and next step

No application source, database, APK, or build configuration was modified. Next, reconcile one separate claim against its exact canonical record and evidence level. After several bounded passes, update the durable handoff with remaining source gaps and validation state. Keep PR #22 open, Draft, and unmerged unless the user explicitly authorizes merging.
