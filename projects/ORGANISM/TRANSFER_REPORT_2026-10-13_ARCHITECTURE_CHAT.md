# ORGANISM architecture-chat experience transfer report — 2026-10-13

## Status
**Coverage: PARTIAL.** This report preserves architecture decisions, requirements, source-state corrections and lessons available in the current ORGANISM conversation. It is not a complete extraction of the full chat history and does not claim the architecture proposal is implemented.

## A. Sources and coverage

### Directly available and reviewed
- Current visible conversation: user clarified that ORGANISM should mediate input into an embedded provider web UI, read responses where supported, retain chat history, restore context when chat limits/transitions occur, use accumulated experience to improve prompts, detect repeated no-progress loops, and maximize autonomy within constraints. Exact stable message IDs/timestamps are not available.
- ORGANISM_CURRENT_STATE_v0.1_2026-10-08.md: project purpose, architecture baseline and implementation sequence.
- ОРГАНИЗМ_МАСТЕР_АРХИТЕКТУРА_v0.3_СВОД_5_РЕШЕНИЙ.txt (dated 2026-10-07).
- ORGANISM_SOLUTION_v0.2.md (dated 2026-10-07).
- OUR_DEVELOPMENT_MEMORY_HISTORY_PIPELINE_v1.0.docx (dated 2026-10-07).
- MEMORY_EXPERIENCE_SYSTEM_TZ_v0_1.docx.
- Организм_непрерывного_агента_v0.1_описание.docx.
- #ОРГАНИЗМНЕПРЕРКВЕН.docx (dated 2026-10-08).
- ORGANISM_TASK_INDEPENDENT_DESIGN_KNOWLEDGE_EXPERIENCE_PIPELINE_v1.0.txt.
- ORGANISM_ROUND_2_ARCHITECTURE_ATTACK_v1.0.txt (dated 2026-10-08).
- Live GitHub reads from ORGANISM branches, project instructions, continuity handoff, work log and the current WebView source file.

### Not fully available / not exhaustively inspected
- No complete raw chronological export of every message in this chat with stable message IDs and exact timestamps.
- Not every uploaded attachment was read end-to-end. ORGANISM_MOBILE_v0_1.zip, ORGANISM_PWA_v0.1.zip, chat-archive ZIPs and several independent-model packs were present but were not exhaustively unpacked/audited in this transfer.
- No local developer checkout was available, so its checked-out branch and uncommitted changes are unknown.
- No APK was built and no physical-device test was run during this transfer.
- The round-2 architecture attack and independent pipeline task files are prompts/specifications, not evidence that every requested experiment was executed.

## B. Project binding and repository state

**Source project:** https://github.com/alexbotleh-oss/organism

Observed refs fetched on 2026-10-13:
- main: 6835e00ba03a3bef3206eb49c924f80604c1da17 — “Parse ChatGPT HTML exports into individual messages (#9)”, 2026-10-09T11:10:06Z.
- fix/oauth-diagnostic-trace-20261009: 2f67f6b817b065acaa8b9f4bd0e0a77e6b73d7ce — “Log ChatGPT download filename fix”, 2026-10-10T08:03:12Z.
- fix/zip-import-crash-and-archive-restore: c201c730604575bd799971accff486ff0e51bb22 — “docs: hand off OAuth diagnostic instrumentation”, 2026-10-09T15:28:36Z.

The repository's PROJECT_INSTRUCTIONS/handoff text names fix/zip-import-crash-and-archive-restore as the working branch, but the observed refs show a later commit on fix/oauth-diagnostic-trace-20261009. These facts are retained as a conflict. GitHub refs cannot prove the user's local checkout branch.

Historical build evidence: [Android build run 37987076157](https://github.com/alexbotleh-oss/organism/actions/runs/37987076157) succeeded for source SHA 08cb9dafdbc2eae918808886adfa310b178d5a6e; artifact ID 11642818226. This is an older source SHA, not the current source branch HEAD and not evidence of later device verification.

Current source readback: [PlatformWebActivity.java at inspected branch](https://github.com/alexbotleh-oss/organism/blob/fix/oauth-diagnostic-trace-20261009/app/src/main/java/com/organism/app/PlatformWebActivity.java), blob SHA 64719a041ac899884bb6abb462b2e536a8088528. The inspected source contains a separate composer that copies prompt text to the clipboard. It sets content access true. The source readback does not establish an automated provider send/receive loop.

**Target repository:** https://github.com/alexbotleh-oss/agent-knowledge-base  
**Base memory branch:** [memory/organism-current-chat-20261013](https://github.com/alexbotleh-oss/agent-knowledge-base/tree/memory/organism-current-chat-20261013), base HEAD at start adbd68938539ff59bf67a0b451207d22d6b896de. This branch already contains the separate OAuth/attachment transfer and PR #23; this transfer does not overwrite that branch's history directly.
**Dedicated delta branch:** memory/organism-architecture-chat-20261013, created from the above base. A separate review PR should target the existing memory branch, not main.

## C. Contents of this transfer

### Events appended
- **E-ORG-011:** architecture v0.3 synthesized continuity-first, RAW/provenance, SQLite-first, append-only event history, Context/Resume, CORE/MEMORY separation and replaceable model.
- **E-ORG-012:** history/experience pipeline and adversarial-review requirements documented; specification prompts are explicitly not counted as completed experiments.
- **E-ORG-013:** user requirement for browser-mediated input/output, persistent history, context recovery, experience-informed prompting and loop detection.
- **E-ORG-014:** assistant's Kotlin/Room recommendation was premature because the existing source was not inspected first; proposal not accepted or implemented.
- **E-ORG-015:** current source readback shows Java modules, clipboard-based prompt flow and setAllowContentAccess(true); this corrects the older mutable-branch-path observation without erasing it.
- **E-ORG-016:** observed branch refs conflict with the working-branch pointer in project documentation; local checkout remains unknown.

### Decision and lessons
- Added **D-ORG-008** as a user requirement that supplements existing platform decision D-ORG-001; it is not recorded as a completed feature.
- Added **L-ORG-008–L-ORG-010**: inspect the current implementation before proposing a new stack; don't equate embedded web UI with automated send/receive; pin source observations to immutable commit/blob identifiers.
- No new global lesson was promoted because the design artifacts do not establish runtime success; the three lessons are kept in ORGANISM's project lesson chain as portable candidates, with their evidence and boundaries.

### State and source records
- Appended architecture-chat addenda to PROJECT_STATE, TASK_STATE and HANDOFF without removing earlier OAuth/attachment history.
- Appended source IDs S-ORG-017–S-ORG-031, including the exact current source blob and the limitations of the available chat/files.
- Created this separate report rather than overwriting the existing TRANSFER_REPORT_2026-10-13.md for the OAuth/attachment conversation.
- No ORGANISM application source code or user data was changed.

## D. Chronology, causality and corrections

1. **2026-10-07:** architecture synthesis document v0.3 records the continuity-first direction. This is a design decision in a document, not proof of implementation.
2. **2026-10-08:** current-state and memory pipeline/attack specifications define RAW/provenance, extraction/audit, loss coverage, claim/verification separation, applicability and negative experience. The attack prompt itself does not prove a completed attack test.
3. **2026-10-13:** user clarifies the intended Android/browser-mediated system and autonomy boundary.
4. **2026-10-13:** the assistant proposes Kotlin + Room without inspecting the live source. Current GitHub source tree confirms a Java Android application. This is recorded as an assistant process error, not a user decision.
5. **2026-10-13:** a fresh read of the mutable branch path shows setAllowContentAccess(true), whereas an earlier transfer recorded false. The correct resolution is to preserve both observations with their source time/blob boundary; do not rewrite the earlier record and do not treat the old value as current.
6. **Branch chronology conflict:** fix/oauth-diagnostic-trace-20261009 has a later observed commit timestamp than the branch named by PROJECT_INSTRUCTIONS/handoff. The repository does not establish the local checkout, so the report does not invent one.

Causal links are stated only where directly supported. In particular, no claim is made that a WebView setting caused the upload problem or that automatic browser interaction has been solved.

## E. Verification plan and results

### Completed in this transfer
- Read project instructions, continuity handoff, continuity protocol and work log from the inspected ORGANISM branch.
- Read source repository metadata, branch refs, commit metadata, current source tree and the current PlatformWebActivity file.
- Inspected the existing target branch and project-memory files before adding records.
- Created a dedicated delta branch based on the existing ORGANISM memory branch.

### Required after write
- Re-read every changed file from the target branch.
- Parse each non-empty line in SOURCES.jsonl as JSON and check unique source IDs.
- Check that every newly appended event's source IDs exist and that event IDs do not duplicate existing IDs.
- Inspect the exact branch head and PR diff.
- Check GitHub Actions validation for the exact resulting commit. If the PR workflow does not run, report that as BLOCKED/NOT RUN rather than PASS.

### Not done / not claimed
- No full raw-chat extraction.
- No Android build, APK generation, device test, OAuth trace or attachment retest.
- No implementation of automated WebView send/receive.
- No merge to target main.
- Independent review has not been performed by this agent and is not claimed.

## F. Control checklist

- **DONE:** recovered the available architecture lineage; distinguished project scope from general memory-system work; fetched actual source branch refs; identified an existing target memory branch and avoided overwriting its separate PR.
- **PARTIAL:** chat/source coverage; not every attachment or historical message was available or exhaustively read.
- **PARTIAL:** architecture state; the design baseline is recorded, but many components are not proven implemented.
- **NOT TESTED:** Android runtime, provider send/receive automation, context recovery acceptance tests, loop detection acceptance tests.
- **BLOCKED / PENDING:** exact target branch write/readback and CI checks until this report is committed and verified.
- **Next step:** verify the transfer branch's exact commit, read back all changed files, run available validators/CI and open a review PR against memory/organism-current-chat-20261013. Do not merge to main.


## Post-write verification addendum — 2026-10-13

- **Payload commit:** 7f3301cb33ed7f00434cfe33ba1f19fc53bc4147 — https://github.com/alexbotleh-oss/agent-knowledge-base/commit/7f3301cb33ed7f00434cfe33ba1f19fc53bc4147
- **Readback:** all eight changed files were fetched again from the dedicated branch. Their resulting blob SHAs matched the blobs created for the commit.
- **Structural checks:** SOURCES.jsonl has 31 non-empty JSON records; all parse; source IDs are unique. Event, decision and lesson IDs are unique. Every source ID referenced by the appended events exists in SOURCES.jsonl.
- **Diff integrity:** comparison against base adbd68938539ff59bf67a0b451207d22d6b896de reports one commit ahead, eight changed files, 251 additions and zero deletions. Existing records were appended to; the earlier transfer report was not overwritten.
- **CI for the payload commit:** GitHub Actions run 38457405842 (pull_request event) completed with conclusion SUCCESS: https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/38457405842 . Both “Validate memory protocol and records” and “Validate knowledge base and detected stacks” passed for commit 7f3301cb33ed7f00434cfe33ba1f19fc53bc4147.
- **Review PR:** draft PR #24, https://github.com/alexbotleh-oss/agent-knowledge-base/pull/24, targets the existing memory branch memory/organism-current-chat-20261013. It remains unmerged. Existing PR #23 was not modified.
- **Main/data safety:** target main remains at a0c12ba849a3416f50e1289d8f0dd20844e1e51f in the observed ref; no merge or deletion was performed. No ORGANISM application code or user data was changed.
- **Remaining:** source/chat coverage is PARTIAL; the final report-only follow-up commit still requires its own CI status check; independent review has not occurred.


## Additional source verification — 2026-10-13

A subsequent direct read of [Db.java](https://github.com/alexbotleh-oss/organism/blob/fix/oauth-diagnostic-trace-20261009/app/src/main/java/com/organism/app/Db.java) found blob SHA 8c3936cfa3726c792cca068a4545d61e0dfde233. The class extends SQLiteOpenHelper and defines a substantial existing schema covering projects/states/tasks, sources, events/actions/results/verifications, memory objects/search/tags, relations, experiences, rejected paths, loss coverage, sessions, availability and change logs. This strengthens the correction in E-ORG-014: do not propose Kotlin/Room or a database redesign without first evaluating the existing implementation. Schema declarations are source evidence, not runtime verification. No application code or database was changed.
