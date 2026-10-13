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
- Direct inspection of the supplied `conversations.zip` confirms 37 conversation objects and 10,034 distinct message IDs. The older note of 74 chats is not supported by the supplied archive or report text; its origin remains unresolved. Treat 37 as the verified count for this archive and 74 as an unverified historical claim, not as equivalent measurements.
- Binary attachments, full intermediate HTML/SQLite diffs, several original diagnostic logs, and missing chat tails are not established as available. Do not infer an artifact's content from its filename or marker.
- Earlier audit wording described `EVT-20261012-007` as an unexplained gap. That statement is superseded by the later direct read-back documented below: the event was recovered from open Draft PR #8 and the extraction report, and candidate lesson `L-RM-010` was restored with provenance and partial/medium-confidence status. The original message is absent from the inspected raw ZIP, so this recovery does not prove the underlying app behavior or full source completeness.
- Reported events and outcomes vary in evidence level: some are user-reported, some directly visible in files/logs, and some only present in prior summaries. Preserve those distinctions.

## Reconciliation against PR #22 branch

Read-back of current machine-readable event logs established:
- `projects/RECIPE_MANAGER/events.jsonl`: 23 parseable records with unique event IDs. The chain contains Android build/navigation, packaging, Flet/WebView diagnostics, and task-scope transfer lessons; source status is still partial.
- `projects/B77_HTML_PWA/events.jsonl`: 22 parseable records with unique IDs after source-to-memory reconciliation. Nine previously narrative-only events (Stage14 baseline, secure-context diagnosis, pre-change checkpoints, camera layer, diagnostics/click binding, Data Matrix attempt/rollback, cross-chat context failure, project-state snapshot, and October 12 learning priority) are now structured; five additional events were recovered directly from raw October 3–5 user messages for repeated UI/Products/Shopping regressions, sorting/unit integrity, recipe identity/context-menu regression, and the failed rollback caused by a missing source file. The September issues are attributed to the HTML contour with medium confidence for exact B77 ownership where source chats do not name B77.
- `projects/CARD111/events.jsonl`: 15 records after nine source-backed October 5–6 events were recovered from raw messages; `projects/ORGANISM/events.jsonl`: 7 records; global lessons: 5 records. All four project event JSONL files now total 67 records; 16 lesson records are present across CARD111 (6), ORGANISM (5) and global lessons (5). All records were re-parsed; IDs are unique and structured event references resolve. This report audit does not claim every source chat has been semantically reconciled.
- Event identifiers that occur later than the September baseline are preserved as later events instead of overwritten by earlier summaries. For example, B77's October records retain the failed Products category/sort selection and camera video-without-code-recognition as distinct evidence chains. The Flet packaging-artifact failure is a separate RECIPE_MANAGER/N99 event and must not be attributed to B77. A user-confirmed narrow UI improvement does not convert unrelated scenarios to PASS.

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
- Historical checkpoint: all 59 paths then in PR #22 had been retrieved and scope-reviewed; source records were reconciled and CI passed on head `2e7183c71dec3906ecb3df22f6ad318050e6ee19`, run #182: https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/38362213710. This is not the latest checkpoint.
- PR #22 remains Draft, open, and unmerged; base is `main`.
- GitHub reports 60 changed files. The comparison against `main` shows all 60 are memory, protocol, audit, template, or project-memory files; no app source, HTML/JS app code, database, or APK files are included. Line-by-line semantic reconciliation of every source claim remains incomplete.

## Structured cross-reference and event-coverage audit — 2026-10-13

The comparison of B77 narrative event headings with structured records exposed a concrete coverage gap: nine events already documented in `projects/B77_HTML_PWA/EVENT_LOG.md` were absent from `events.jsonl`. These were not inferred new incidents; each already had a distinct event ID and evidence in the narrative log. The missing structured records were added without creating duplicate IDs. The B77 event log and JSONL now each contain 22 distinct event IDs; after the initial nine narrative-only records and five October 3–5 source events, a targeted October 2 review added two earlier B77/PWA events for IndexedDB and scanner-mode/camera/decode failures. The event-log ordering of the October 5 context-continuity incident was also corrected to follow its recorded source time.

A direct read-back of all seven structured JSONL event/lesson files found a referential-integrity defect after the N99 / B77 project-boundary correction: three structured records still referenced the retired identifier `EVT-20260922-001`, which is not present in the consolidation branch. The canonical event for the HTML/SQLite incident is `EVT-B77-20260922-001` under `projects/B77_HTML_PWA/events.jsonl`.

The stale references were repaired in:
- `projects/RECIPE_MANAGER/events.jsonl` (the N99 cross-project link now points to the canonical B77 event);
- `projects/B77_HTML_PWA/events.jsonl` (the later HTML regression points to the canonical September event);
- `lessons/global/records.jsonl` (the global CRUD/import lesson now cites the canonical source event).

This is an identifier/link repair, not a claim that the HTML defect was fixed. Historical prose that documents prior branch state remains historical evidence and must not be rewritten as if the old identifier never existed.

Initial read-back validation at the time of the stale-reference repair (before later October source additions):
- 41 event records parsed across RECIPE_MANAGER (22), B77_HTML_PWA (6), CARD111 (6), and ORGANISM (7);
- 14 lesson records parsed across CARD111 (4), ORGANISM (5), and global lessons (5);
- no JSONL parse errors or duplicate IDs in those sets;
- no unresolved `related_event_ids`, `created_from_event_ids`, or event-formatted `evidence_refs` in those structured records.

This structural check does not establish semantic completeness of every source chat or confirm application runtime behavior.

A second source-to-memory comparison against raw `conversations.json` identified five additional B77 incident chains that were absent from both the previous B77 narrative log and structured JSONL. They are now recorded with original conversation IDs and message IDs/timestamps: `EVT-B77-20261003-001` (long-press/swipe/Light Cook regressions), `EVT-B77-20261003-002` (Products/Shopping flow failures and partial recovery), `EVT-B77-20261004-001` (filters/sorting and unit integrity), `EVT-B77-20261004-002` (wrong recipe content and context-menu regression), and `EVT-B77-20261005-008` (rollback impossible after source-file loss). Root causes remain unknown unless supported by code/diff evidence. The event log and JSONL now both contain 22 distinct B77 event IDs in historical order.

A third source reconciliation pass found that CARD111's raw October 5–6 conversations contained incidents absent from the structured memory. Nine distinct event records were added with conversation/message IDs: project kickoff/scope, Flet toolchain/API error, APK storage permission error, Web/PWA decode/save failure, loss of QR symbology, empty-wallet/syntax failure, editor visual regression, Pages branch/cache plus backup-restore failure, and mobile scanner freeze with a format-list patch attempt. Two project lessons were added: fail closed on storage errors rather than displaying an empty wallet, and preserve the detected code format together with its value. The records explicitly distinguish source-reported diagnoses from independently verified code/runtime results.

The RECIPE_MANAGER narrative log also contained two near-identical headings for `EVT-20261012-013`. The blocks described the same occurrence and source chain with minor wording differences; the wording was merged into one canonical narrative block and the duplicate copy removed. The JSONL event record was not deleted or rewritten. Three remaining headings in the RECIPE_MANAGER log (`EVT-20261012-014/016/019`) are explicit cross-project pointers to canonical B77 records, not N99 events. Ten other RECIPE_MANAGER events remain present in structured JSONL without standalone headings in `EVENT_LOG.md`; they are not being recreated as new events. Their narrative-index coverage is a presentation gap to review, not evidence that the structured records are absent.

A provenance check across lesson records found that global lesson `G-LESSON-004` still pointed to the retired RECIPE_MANAGER path while its canonical event had been moved to B77. The path and Markdown attribution were corrected to `projects/B77_HTML_PWA/events.jsonl:EVT-B77-20260922-001`. The full HTML-specific lessons `L-RM-019/021/022` and the HTML-source portion of `L-RM-004` were also found inside RECIPE_MANAGER lessons; they are now concise historical cross-project pointers to canonical global/B77 lessons, and canonical B77 lessons `B77-L-008/009/010` hold the HTML regression, ineffective filter and camera-decode rules. This preserves historical IDs while removing the false implication that those HTML incidents were N99 Android defects.

A targeted pass over the October 2 mixed-scope source conversation recovered two earlier B77/PWA incidents absent from the current event chain: repeated IndexedDB backing-store open errors during the scan action, and the separate scanner-mode/camera/stop/decode failure. These are now EVT-B77-20261002-001/002, linked to later B77 scanner events but retained as a distinct earlier occurrence. The same conversation also contains a separate N99 product-list requirement, EVT-RM-20261002-001, recording that a saved expiry date could not be edited and that the user proposed moving Add Product above the list; the proposed UI change remains pending source/decision reconciliation.

At earlier audit checkpoints, GitHub's compare API reported 206 and later 230 commits ahead of `main`, 0 behind, with 59 and later 60 changed files respectively. At the 206-commit checkpoint, the PR commit endpoint returned 208 paginated entries with 152 unique commit subjects; those subjects were reviewed as export/docs/memory-oriented. These are historical checkpoints, not the current count. Current live comparison is recorded in the latest coverage checkpoint below. The subject review is not a full diff review of every historical commit. Keep the PR Draft/open and do not merge without explicit user permission.

## Master control matrix artifacts recovered from Library — 2026-10-13

A Library inventory found five dated control-matrix workbooks under `/Б77/`: `RecipeManager_MASTER_CONTROL_MATRIX_v1_2_20261002.xlsx` (9 tabs), v1.1 (7 tabs), v1, `RecipeManager_V20_FIX6_HTML_контрольная_матрица_20261002.xlsx`, and `RecipeManager_сводка_изменений_FIX6_V20_V21_N99.xlsx`. Extracted sheet text was read for v1.2, the V20/FIX6/HTML comparison and the change summary. Their contents are now summarized in `projects/RECIPE_MANAGER/MASTER_CONTROL_MATRIX_AUDIT_2026-10-13.md`; project source coverage records the artifact names and boundaries.

These matrices are mixed-scope. The folder name `/Б77/` does not establish that every row belongs to B77; the source explicitly names N99 regressions, Flet behavior and a temporary HTML prototype as well as PWA camera behavior. The matrices are dated planning/control artifacts, not proof of current implementation. They identify open decisions for diet scope, Roulette, web adapters, PC DB schema, family server sync and PWA camera; they also state that KTP-21…KTP-28 must not be invented without the original source. No app source was changed.

## Requirement-state correction — expiry editing (2026-10-13)

The earlier audit left the acceptance status of expiry editing and Add Product placement unresolved. Inspection of the Library change-summary workbook now provides secondary corroboration: `RecipeManager_сводка_изменений_FIX6_V20_V21_N99.xlsx` records Add Product at the top as `CHANGE / USER`, expiry editing as `CHANGE / USER + AUDIT`, and separate batch editing as `TODO`. DEC-RM-008 and `EVT-RM-20261002-001` were updated accordingly. The requirement is now supported; whether it was implemented or passed runtime tests remains unknown. The workbook's `/Б77/` location does not make the explicitly N99-scoped user report a B77 incident.

## Next reconciliation steps

1. Continue message-by-message matching of report claims against source chat messages and current event/lesson records.
2. Continue line-by-line semantic reconciliation of the 60 retrieved/scope-reviewed files against primary messages and attachments; the file retrieval/scope review is complete, but semantic source coverage is not.
3. Inspect whether every report claim is present in the PR branch and distinguish it from claims present only in older PRs or reports.
4. Keep the archive count grounded at 37 conversation objects / 10,034 distinct message IDs; the older 74-chat note is explicitly marked unsupported by current source evidence until its originating manifest or report is found.
5. Keep source completeness `PARTIAL` until primary-source coverage and missing artifacts are accounted for.

## Non-claims

This first-pass audit does not claim a specific memory fact has definitely been lost. It demonstrates that report copies repeat and that unique IDs/CI are insufficient to establish semantic completeness. It does not prove that all source chat messages or binary attachments are present.

## Additional source-to-memory reconciliation — N99 HTML-first phase (2026-10-13)

A message-level pass over the raw archive found a significant historical N99 task-scope decision that was not represented in the RECIPE_MANAGER structured event log or decisions file. In conversation `Часть 1` (`6abe10f8-03d8-83eb-8219-eac3bdd308b0`), the user explicitly asked to pause the T-003 path, inventory existing/missing functions, validate windows/logic/dependencies in an HTML mockup, and port verified behavior into Flet only after that phase. Follow-up messages name V20 as the visual/layout reference, the existing Flet project as a functional reference, FIX6/V21/audit/master-map as reconciliation inputs, and exclude the old scanner while retaining the native scanner.

This is **N99/RECIPE_MANAGER** evidence, not automatically B77 evidence. The source archive contains both project identities and mixed-scope conversations; a generic HTML mention alone is insufficient for B77 attribution. Added `EVT-RM-20261001-005` to the structured and narrative event logs and `DEC-RM-009` to decisions. No app files were changed. Whether the HTML mockup was fully completed remains unverified. The later 2026-10-12 `DEC-RM-001` establishes Android debugging as the immediate priority before UI redesign; both historical and later task priorities are preserved with dates.


## Event-count and narrative-index checkpoint before PR #8 recovery — 2026-10-13

The earlier first-pass count of 23 RECIPE_MANAGER structured events was superseded when `EVT-RM-20261001-005` was recovered from the raw export as the N99 HTML-first phase decision. At this checkpoint, before the later PR #8 recovery below, canonical `projects/RECIPE_MANAGER/events.jsonl` contained **24 parseable records with 24 unique IDs**. The current B77 JSONL had 22 parseable records with unique IDs; CARD111 had 15 and ORGANISM had 7. Total at this checkpoint: **68 structured events**. This count is historical and is superseded by the recovery section below. Structured lessons then numbered 16; RECIPE_MANAGER had no `lessons.jsonl` by deliberate choice because a source-aligned schema mapping was not available.

A structured-to-narrative comparison found that 10 of the 24 RECIPE_MANAGER records did not have standalone event headings in `EVENT_LOG.md`. A concise index was added to point to those existing records without duplicating their payloads. This improves traceability; it does not establish that every source message or final outcome is recovered.

The count correction is structural, not a change to the source-completeness verdict. The archive remains **PARTIAL**: the supplied raw ZIP covers 37 conversation objects and 10,034 distinct message IDs through 2026-10-07; it does not contain the later transfer chat or the separate binary attachment bytes. The source-report text itself has a metadata/materialized-text size discrepancy and contains repeated report blocks, so report claims still require event-by-event provenance checks.


## Recovery of report-identified EVT-20261012-007 — 2026-10-13

The report bundle explicitly identifies `EVT-20261012-007` as a PR #8 event about the shift toward a shared Flet UI Design System and the risk of platform regressions. A direct read of PR #8's branch confirms the record and its candidate lesson `LESSON-RM-010`; neither was present in the current consolidated `RECIPE_MANAGER/events.jsonl` or `LESSONS.md`. This is a concrete transfer omission, unlike the previously unexplained number gap.

The event was recovered into the canonical JSONL after `EVT-20261012-006`, with the original facts, hypotheses, evidence classes, related IDs, confidence and next action preserved. A corresponding human-readable candidate lesson was added as `L-RM-010`; the old source ID `LESSON-RM-010` is retained in provenance. The event and lesson remain **partial/candidate, confidence medium**: the original October 12 message is not in the inspected raw ZIP, and historical `main(9).py`/project summaries do not prove the current app state. No application files were changed.

Current structured counts after recovery: RECIPE_MANAGER 25, B77 22, CARD111 15, ORGANISM 7 = 69 events; 16 structured lessons remain in CARD111, ORGANISM and global lesson records. The RECIPE_MANAGER lesson index remains Markdown-only by design. CI and final file read-back must be checked against the resulting branch head. The overall source completeness remains **PARTIAL**.


## Cross-check of PR #8 event chain — 2026-10-13

Compared all nine structured event records on PR #8's branch `handoff/recipe-manager-ui-platform-memory-20261012` against the current canonical RECIPE_MANAGER and B77 event logs:

- Eight event IDs from PR #8 now exist exactly in the consolidated RECIPE_MANAGER event chain, including the recovered `EVT-20261012-007`.
- The remaining legacy `EVT-20260922-001` was not copied under its old project attribution; its HTML/SQLite recipe-list, deletion and nutrition evidence is represented by canonical B77 event `EVT-B77-20260922-001`. This is an intentional project-boundary correction, not an omission.
- The event `EVT-20261012-007` and candidate lesson `LESSON-RM-010` were absent from the consolidation branch but present in PR #8. The event and lesson are now restored with partial/medium-confidence provenance. The Markdown canonical lesson ID is `L-RM-010`; the legacy structured ID is preserved as provenance only, and no `lessons.jsonl` was synthesized.
- PR #8 remains open Draft and unmerged. The source event was imported for memory continuity, not as proof that the current desktop/mobile code has any particular state.

This cross-check did not identify another PR #8 event payload that was missing from the consolidated project memories. It does not close the separate mixed-chat primary-source review or establish completeness of the report bundle.


## Cross-branch event-ID and summary reconciliation — 2026-10-13, continuation checkpoint

A direct comparison of structured RECIPE_MANAGER event IDs and summaries on the canonical consolidation branch against PR #3, #6, #8, #14, #16, #19, #20 and #21 found the following mappings. This is an ID/summary-level comparison; it is not yet a line-by-line equivalence proof for every fact, hypothesis and evidence reference in every old branch.

- Legacy `EVT-20260922-001` appears in earlier RECIPE_MANAGER branches but is intentionally not retained under the N99 project ID after scope correction. Its HTML-contour evidence is represented by B77 canonical events `EVT-B77-20260922-001/002/003`, including ingredient matching/database access, recipe list/nutrition/deletion regressions, and delete-all/Shopping-to-Products requirements. The exact B77 attribution for the earliest conversations remains medium confidence where the source does not name B77.
- Source PR #16/#19/#20 contain HTML/PWA event `EVT-20261012-014` and Products/Shopping event `EVT-20261012-016`. Both IDs are present under `projects/B77_HTML_PWA/events.jsonl` and have matching narrative headings in the B77 event log; they are intentionally absent from the N99 structured event chain.
- PR #19 used `EVT-20261012-017` for camera/video-without-decode evidence, while PR #20 used the same ID for a different task-boundary occurrence. The canonical resolution is to keep the N99 task-boundary/transfer occurrences as `EVT-20261012-017/018` and the B77/PWA camera-decode occurrence as `EVT-20261012-019`. These distinct chains are present in the corresponding project JSONL files; the source branches were not rewritten.
- PR #8's nine-record chain was separately compared in the prior section: eight events are in the current RECIPE_MANAGER chain, while the one HTML-contour legacy event maps to canonical B77 evidence. The reported `EVT-20261012-007` omission and candidate lesson `LESSON-RM-010` were recovered into the canonical memory with provenance and medium-confidence/partial status.
- PR #21's conflicting `EVT-20261012-005/006` summaries are not imported under the colliding IDs. The user requirements are preserved through `DEC-RM-006` and B77 canonical events. Its legacy ingredient lesson (`L-RM-008` / `LESSON-RM-008`) and HTML data-path lesson (`LESSON-RM-009`) had ID/content conflicts with canonical N99 lessons; they are now represented as `B77-L-011` (ingredient normalization) and `B77-L-012` (HTML/SQLite end-to-end regression), with cross-project pointers from `projects/RECIPE_MANAGER/LESSONS.md`. The older branch's event/lesson meanings remain historical evidence; do not treat a matching ID as proof of matching event identity.

Structural read-back remains clean for the current canonical JSONL sets: 25 RECIPE_MANAGER events, 22 B77 events, 15 CARD111 events, 7 ORGANISM events, and 5 global + 6 CARD111 + 5 ORGANISM lessons; all parsed and had unique IDs in the checks performed. This establishes structural integrity only. Remaining work is to compare detailed claims/evidence refs for source branches and the repeated report bundle, and to verify CI against the final current branch head.


## Quantified duplicate-block check in supplied report bundle — 2026-10-13

The Library file `Отчеты о извлечении.txt` was materialized for local text analysis. The accessible raw file contains 1,425 lines and 110,155 Unicode characters; Files metadata reports 169,371 bytes. These are different measurement units/representations and should not be silently equated. The metadata/materialized-text discrepancy remains documented; it does not by itself prove truncation because byte length and character count differ.

A direct line comparison found a near-verbatim repeated audit block: source lines 206–503 and 765–1062 each contain 298 lines; 296 aligned lines match exactly, with the differences confined to closing/blank lines. This confirms a copied report block, not a second independent project event. The block should be deduplicated at the report-copy layer while any unique details elsewhere in the file remain eligible for extraction. Other report sections also repeat or overlap, so the entire file must not be treated as a single chronological log.


## Cross-project ingredient-rule parity check — 2026-10-13

A comparison of PR #21's ingredient-equivalence decision with the canonical B77 HTML source record found a documentation-parity gap: the B77 source record explicitly preserves three further user-requested cases from 2026-09-22 20:47 — wheat flour vs. flour, butter naming order/units, and a pinch of salt vs. salt — while the consolidated RECIPE_MANAGER `DEC-RM-006` did not list them. The rules were already preserved in the B77 regression record, so this is not a missing source event; it is a gap in the transferable requirement index.

The cases are now added to `DEC-RM-006` and `RECIPE_SEARCH_REQUIREMENTS.md`, with explicit source provenance and a boundary note: they are user requirements from the HTML contour, not evidence of current implementation in N99 or B77. The original conversation ID is `6ab2de4d-12f0-83ed-be6e-6212b0fdf4ad`. Exact early B77 ownership remains medium confidence because the source chat discusses the HTML contour without consistently naming B77.


## Lesson-ID collision resolved for ingredient normalization — 2026-10-13

A detailed comparison of PR #21's RECIPE_MANAGER `LESSONS.md` found a real lesson-ID collision that needed a semantic, not numeric, resolution: source PR #21 used `L-RM-008` for domain-specific ingredient equivalence, while the consolidated RECIPE_MANAGER `L-RM-008` is already assigned to the separate Android navigation/packaging lesson. The domain requirement itself was already preserved in `DEC-RM-006` and the B77 event/narrative records, but the specific transferable lesson—explicit product-type rules, positive and negative test pairs, and preserving original display text separately from normalized lookup keys—was not yet represented under a non-colliding canonical lesson ID.

To avoid silently dropping the lesson or overwriting the Android lesson, added `B77-L-011` to `projects/B77_HTML_PWA/LESSONS.md` and added a cross-project pointer to `projects/RECIPE_MANAGER/LESSONS.md`. The provenance explicitly preserves the legacy source ID and the medium-confidence B77 attribution boundary. No application code or database was changed. The new lesson records user requirements and acceptance tests; it does not claim the matcher is implemented or fixed.


The lesson reconciliation was verified by reading PR #21's `projects/RECIPE_MANAGER/lessons.jsonl` and `LESSONS.md` directly. Its ingredient lesson and HTML regression lesson contained distinct practical guidance not safe to preserve by reusing colliding `L-RM-008` / `LESSON-RM-009` identifiers. Canonical B77 lessons `B77-L-011` and `B77-L-012` now preserve the guidance, acceptance checks and source limitations; RECIPE_MANAGER `L-RM-009` links to both. The legacy IDs are retained as provenance in the new B77 records, not as active IDs. The B77 lesson index now has 12 distinct canonical lesson headings; structured JSONL lesson count remains 16 because the B77 lesson index is Markdown-only.


The same PR #21 lesson comparison found its other four structured lessons (`LESSON-RM-001/002/003/007`) are already represented by canonical RECIPE_MANAGER Markdown lessons `L-RM-001/002/003/007` with matching practical rules. Their older structured JSONL IDs are not recreated in a new `lessons.jsonl`, consistent with the canonical branch's documented choice to keep RECIPE_MANAGER lessons Markdown-only until source-aligned schema mappings are available. Their source-specific evidence references remain summarized in the current Markdown/event history; no additional missing lesson was identified in this six-record PR #21 JSONL comparison.


## Cross-check of PR #8 lesson chain — 2026-10-13

The seven structured lesson records in PR #8 were compared with the current project Markdown indexes:

- `LESSON-RM-001/002/003` are represented by canonical `L-RM-001/002/003`.
- The legacy PR #8 `LESSON-RM-007/008` are represented by canonical `L-RM-007/008` with the Android navigation/build evidence retained.
- The legacy `LESSON-RM-009` mixed HTML/ingredient lesson is represented by the existing N99 pointer `L-RM-009` and the detailed canonical B77 lessons `B77-L-011` (ingredient normalization) and `B77-L-012` (end-to-end HTML/SQLite regression gate). This preserves the source project's HTML boundary rather than importing the old lesson under a colliding N99 ID.
- `LESSON-RM-010` was the one lesson absent from the consolidated Markdown memory; it has now been restored as candidate `L-RM-010`, with its legacy ID and source branch preserved in provenance.

No other PR #8 lesson payload was found to be absent after these mappings. The PR #8 branch remains open Draft and is not merged; the audit did not modify or close it.


## Current branch and CI checkpoint — 2026-10-13 07:42 UTC

Live GitHub recheck: PR #22 is still Draft/open/unmerged against `main`; its exact HEAD is `e3557497f757b8377a4c01a5e7d1f7ab4fbbafba`, with 60 changed paths. The compare API reports 263 commits ahead and 0 behind. GitHub Actions `Validate knowledge base` passed on this exact HEAD, run #38364347001: https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/38364347001.

The 60 paths were fetched and scope-reviewed in bounded batches. This does not mean every sentence has been semantically matched against every primary message or binary attachment. The remaining source-to-memory comparison is still PARTIAL. The latest PR #21 lesson reconciliation added B77-L-011 and B77-L-012, and corrected the B77 EVT-20261012-014 lesson references; these changes are included in the successful HEAD above.

## Recheck after lesson reconciliation — 2026-10-13 07:43 UTC

Live branch ref currently resolves to eca56274378f54dfecedb52d301cce7e0b5c65f7. GitHub compare reports 266 commits ahead of main, 0 behind, and 60 changed paths. PR #22 remains Draft/open/unmerged.

CI status is recorded precisely: run #38364347001 passed on exact branch head e3557497f757b8377a4c01a5e7d1f7ab4fbbafba. A later completed run #38364455942 reports success for SHA 82b96bc5ee29ca6d65ebd7322cb4f9ca0bcc450f, which did not match the branch ref when rechecked. Therefore the current branch head eca56274378f54dfecedb52d301cce7e0b5c65f7 does not yet have an independently confirmed matching CI result in this read-back. Do not represent a different SHA's successful run as proof for this head.

The latest source-memory additions (B77-L-011/012, RECIPE_MANAGER cross-pointers, corrected B77 EVT-20261012-014 lesson references, report duplicate line ranges and PR #21 event/lesson collision mappings) were read back from their canonical branch files. Overall semantic source coverage remains PARTIAL.

## Subsequent exact-head verification — 2026-10-13 07:44 UTC

The next branch checkpoint superseded the prior eca562... snapshot. Current PR #22 HEAD was re-read as a5b41f3f0028671f29a6f094010e0a2b460199ec; GitHub Actions Validate knowledge base passed on that exact SHA, run #38364549105: https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/38364549105. The live compare at that checkpoint was 268 commits ahead of main, 0 behind, with 60 changed paths. PR #22 remained Draft/open/unmerged.

This checkpoint was subsequently verified: GitHub Actions Validate knowledge base passed on resulting HEAD 6fd1c9b01bbc143a032d02b79f4124cfba7804f8, run #38364657618: https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/38364657618. That is a pass for the cited SHA only; any later commit requires its own exact-head check. Semantic source completeness remains PARTIAL.


## Bounded continuation checkpoint — 2026-10-13

This continuation resumed after the user requested shorter sessions due to unreliable connectivity. The current PR branch was re-read before any write.

- PR #22 remains Draft/open/unmerged against `main`; branch head at the start of this checkpoint was `d178ef40fe3684b474d1664e8719704bfe0e8f24`, with 60 changed files.
- GitHub Actions run #38364890030 passed on that exact SHA: https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/38364890030.
- Bounded JSONL read-back: RECIPE_MANAGER events 25/25 parseable, unique IDs; B77_HTML_PWA events 22/22; CARD111 events 15/15 and lessons 6/6; ORGANISM events 7/7 and lessons 5/5; global lessons 5/5. No parse errors, missing IDs, or duplicate IDs were found in these inspected files.
- The existing coverage report states all 60 changed paths were fetched and scope-reviewed in bounded batches. This continuation additionally re-read the control-matrix audit, RECIPE_MANAGER task state/handoff, both coverage/audit reports, and the structured JSONL files listed above.
- Next substantive work is semantic matching of source-report claims to canonical events/decisions/lessons, and resolution or explicit preservation of the 37-versus-74 conversation-count discrepancy. Do not infer source completeness from CI or unique IDs.
- Overall source-to-memory completeness remains **PARTIAL**. No merge, app-code modification, database change, or APK build was performed.

## Bounded continuation — narrative/structured event parity — 2026-10-13

This continuation was split into short read-back batches due to intermittent connectivity. Before reading, the current PR branch was checked; PR #22 remained Draft/open/unmerged against `main`.

- At the start of this pass, current HEAD was `f33f290eb5f4778f13d19dc1bf54d2f08399d946`; GitHub Actions `Validate knowledge base` passed on that exact SHA, run #38365561472: https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/38365561472.
- GitHub reports 60 changed files. All 60 paths were enumerated from the PR file-list endpoint. Project and core files were re-read in bounded batches; structured records were separately parsed below.
- Narrative-to-structured event-ID comparison: B77 HTML/PWA 22 narrative IDs / 22 JSONL records, no missing or extra IDs; CARD111 15 / 15, no missing or extra IDs; ORGANISM 7 / 7, no missing or extra IDs.
- RECIPE_MANAGER has 25 structured event records. Every structured event ID appears in its narrative log. Four narrative-only IDs are intentional historical/cross-project pointers: legacy `EVT-20260922-001` and B77 canonical records `EVT-20261012-014/016/019`; they are not new N99 structured events.
- Re-parsed seven canonical JSONL files: RECIPE_MANAGER events 25, B77 events 22, CARD111 events 15, CARD111 lessons 6, ORGANISM events 7, ORGANISM lessons 5, and global lessons 5. All 85 records parsed; IDs were present and unique within each file. This is a structural check, not a claim of full semantic source coverage.
- A current-file-list check and these targeted parity checks did not resolve the outstanding message-by-message reconciliation of mixed N99/B77 source conversations or missing binary artifacts. Source-to-memory completeness remains **PARTIAL**.

Next: continue semantic comparison of source claims against their canonical event/decision/lesson records in small batches; keep source chronology separate from import order and preserve project attribution uncertainty.

## Structured event-link integrity recheck — 2026-10-13

A fresh parse of the four project event JSONL files found 69 event records and 69 unique event IDs across RECIPE_MANAGER (25), B77_HTML_PWA (22), CARD111 (15) and ORGANISM (7). All records parsed; every `related_event_ids` and `created_from_event_ids` reference resolved to a known canonical event ID. No unresolved event links were found. This validates the inspected structured link fields only; it does not validate every prose citation or prove source completeness.

At the immediately preceding checkpoint, CI passed on exact HEAD `0e2a2213742b9e7ee38e7ee916ab42399d7be264`, run #38366704509: https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/38366704509. This commit contains the preceding bounded narrative/structured parity audit. Any subsequent commit requires its own exact-head CI check.


## Scope and stale-gap correction — 2026-10-13

A fresh read-back of `projects/RECIPE_MANAGER/events.jsonl`, `projects/RECIPE_MANAGER/LESSONS.md` and `projects/RECIPE_MANAGER/TASK_STATE.md` confirms that `EVT-20261012-007` and candidate `L-RM-010` are present in the consolidation branch. The earlier statement in section “Specific open completeness issues” that the ID remains unexplained was stale and has been corrected above. The event is recovered from a secondary branch/report, with partial/medium-confidence provenance; the original source message was not found in the inspected archive. Therefore the *record gap* is closed, but primary-source verification and semantic completeness remain PARTIAL.

Current work scope is the memory/experience system in `alexbotleh-oss/agent-knowledge-base`: restore context, preserve event chains and provenance, retain failed attempts and uncertainty, check repository instructions, prevent task drift, and save verifiable continuation points. ORGANISM is a separate deferred project and is not the current implementation target. CARD111 is also deferred for its own later source-reconciliation pass; its existing records are provisional material already present in this consolidation, not proof that the user completed a full transfer. Do not delete those records, but do not expand either deferred project as the main task in this pass.

Next audit step: continue source-to-memory semantic reconciliation in small batches, starting with remaining claims in the extraction-report bundle and comparing each claim to exact canonical event/decision/lesson records. Keep report-copy deduplication separate from event deduplication. Preserve the unresolved 37-versus-74 conversation-object discrepancy and missing binary attachment/source-tail limitations. Re-read changed files and verify validation on the exact current branch head before reporting CI status.
