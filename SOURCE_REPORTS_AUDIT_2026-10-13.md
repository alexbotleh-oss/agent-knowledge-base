# Audit of extraction reports — 2026-10-13

## Status

Status: **PARTIAL**. This is a first-pass reconciliation of the user-provided report bundle `Отчеты о извлечении.txt` against the memory currently present in the PR #22 branch. It is not a claim that all source chats, final messages, or attachments have been recovered.

The report was received as a 169,371-byte / 1,425-line source according to Files metadata. Its text-materialized representation exposed only a subset in one local copy; Files read was used to inspect both reported ranges. Record this representation discrepancy rather than silently assuming every downstream copy is complete.

The user explicitly warned that some chats may lack their final messages and that reports may overlap because they were collected from multiple tabs. Repeated report text is treated as a copy-level duplicate, not a reason to discard distinct events described elsewhere.

## Findings

### 1. Repeated report blocks are present

The bundle contains duplicated large report blocks, including:
- the initial report describing PR #3 and the initial RECIPE_MANAGER transfer;
- the PR #14 artifact-verification report, repeated consecutively in the latter part of the bundle;
- repeated PR #16/related HTML regression reconciliation summaries.

This proves report-copy duplication exists. It does not prove that all repeated event summaries refer to the same underlying occurrence.

### 2. Report order is not event chronology

The bundle references PRs #3, #4, #6, #8, #14, #16, #17 and #21. These reports were collected out of sequence and contain backward references to earlier branches/PRs. Do not use their textual order as project event time. Use source-message timestamps, commit records, event times and recorded/import times separately where available.

### 3. Structural deduplication is not semantic completeness

Some reports use unique JSONL IDs, parse checks and successful CI as evidence that there are no duplicates. Those checks only prove structural properties of the records and the validations actually executed. They do not prove every independent recurrence, failed attempt, new hypothesis, changed outcome, contradiction or later correction was retained.

A later observation should be handled as follows:
- same occurrence, same evidence: link the repeated source to the canonical event rather than creating another event;
- distinct recurrence: create a new linked event even when the symptom is similar;
- new diagnostic fact or changed result: append it to the occurrence/evidence chain and update state without erasing prior failures;
- conflicting accounts: preserve both with provenance until resolved;
- report-level repeated copy: deduplicate the copied block but retain any unique claims contained in its non-repeated portions.

### 4. Git/PR branch state is part of completeness

The reports describe memory prepared in multiple open Draft PRs, sometimes based on earlier transfer branches instead of `main`. Presence in one branch or in a report is not proof that it reached `main`. PR #22 is a consolidation candidate and remains open Draft; no source PR is merged, closed, or rewritten by this audit.

### 5. Confirmed source and repository distinctions

The report content includes useful experience around HTML/SQLite recipe-list and database access regressions, nutrition/deletion controls, ingredient normalization, packaging errors, Flet API compatibility, Android/WebView diagnostics, CARD111 UI/scanner behavior, and ORGANISM memory/archive requirements.

Respect the explicit identity boundary:
- N99 / RECIPE_MANAGER: Android APK / Flet-Python contour.
- B77_HTML_PWA: separate HTML/WMA web prototype intended for iPhone, repository `alexbotleh-oss/LK`.
- CARD111: separate loyalty-card Web/PWA.
- ORGANISM: separate continuous-agent application.

Shared product names, ingredient rules or UI techniques do not establish shared implementation history. Mixed conversations must be split by message-level provenance. HTML/SQLite regressions are not evidence of Android APK defects.

### 6. Specific open completeness issues

- Reports are secondary summaries and cannot substitute for missing primary messages and attachment bytes.
- The export audit still reports 37 conversation objects versus an older note of 74 chats, both associated with 10,034 distinct message IDs. This discrepancy remains unresolved.
- Binary attachments, full intermediate HTML/SQLite diffs, several original diagnostic logs, and missing chat tails are not established as available. Do not infer an artifact's content from its filename or marker.
- The RECIPE_MANAGER event sequence intentionally has the unexplained gap `EVT-20261012-007`. Do not invent a record to fill it.
- Reported events and outcomes vary in evidence level: some are user-reported, some directly visible in files/logs, and some only present in prior summaries. Preserve those distinctions.

## Reconciliation against PR #22 branch

Read-back of current machine-readable event logs established:
- `projects/RECIPE_MANAGER/events.jsonl`: 22 parseable records with unique event IDs. The chain contains Android build/navigation, packaging, Flet/WebView diagnostics, and task-scope transfer lessons; source status is still partial.
- `projects/B77_HTML_PWA/events.jsonl`: 6 parseable records with unique IDs, including September HTML/SQLite incidents and October UI/camera recurrences. The September issues are attributed to the HTML contour with medium confidence for exact B77 ownership where source chats do not name B77.
- `projects/CARD111/events.jsonl`: 6 records; `projects/ORGANISM/events.jsonl`: 7 records; global lessons: 5 records. The rollup coverage file records the latest earlier uniqueness/parse checks for these sets. This report audit does not re-validate every JSONL schema for every project beyond those noted counts.
- Event identifiers that occur later than the September baseline are preserved as later events instead of overwritten by earlier summaries. For example, B77's October reports retain the failed Products category/sort selection, the packaging artifact failure, and camera video-without-code-recognition as distinct evidence chains. A user-confirmed narrow UI improvement does not convert unrelated scenarios to PASS.

## Process correction

**Deduplicate copied reports and canonical summaries; do not deduplicate evidence events by topic alone.**

For every future reconciliation, record:
- source report identity and exact location;
- underlying conversation ID, message ID and source timestamp when available;
- event ID / lesson ID and project attribution;
- repository path, branch, commit and whether present in `main`;
- relationship: duplicate copy, same occurrence, recurrence, new detail, conflict, or unknown;
- evidence status, confidence and unresolved questions.

Do not increase confidence by repeating the same second-hand report. Keep independent corroboration and failed attempts linked to the event chain.

## Verification update from supplied prior-session note — 2026-10-13

The user supplied an additional text extract, `Последние дествия в предидущем чате.txt`, describing the prior session's latest actions. It confirms that the report-bundle audit had been added to PR #22 and read back, and that the PR remained Draft/open and unmerged. These statements were checked against live GitHub state rather than accepted from the extract alone.

- The supplied note described the earlier PR #22 checkpoint at head `879fb70c8f24175dbe7404902bae9a76c73b9475`; GitHub Actions `Validate knowledge base` passed on that exact head, run #123: https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/38355846764.
- During this continuation, the audit and coverage documents were updated and read back. PR #22 then advanced to head `504c993ea5092517a1509b7b67c4b7b51a6e086d`; `Validate knowledge base` also passed on that exact head, run #124: https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/38356845711.
- PR #22 remains Draft, open, and unmerged; base is `main`.
- GitHub reports 59 changed files. The comparison against `main` shows all 59 are memory, protocol, audit, template, or project-memory files; no app source, HTML/JS app code, database, or APK files are included. Full file-by-file read-back and semantic reconciliation of every source claim are not yet complete.

## Next reconciliation steps

1. Continue message-by-message matching of report claims against source chat messages and current event/lesson records.
2. Complete file-by-file read-back of all 59 changed paths and verify that each change remains within memory/core-documentation scope.
3. Inspect whether every report claim is present in the PR branch and distinguish it from claims present only in older PRs or reports.
4. Resolve or explicitly preserve the 37-versus-74 conversation count discrepancy using actual export evidence.
5. Keep source completeness `PARTIAL` until primary-source coverage and missing artifacts are accounted for.

## Non-claims

This first-pass audit does not claim a specific memory fact has definitely been lost. It demonstrates that report copies repeat and that unique IDs/CI are insufficient to establish semantic completeness. It does not prove that all source chat messages or binary attachments are present.
