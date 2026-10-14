# Reconstructed missing context from chat notes and PDF export — 2026-10-14

## Purpose and method

This document restores context that was flattened or omitted when previous chat reports were transferred into `agent-knowledge-base`. It compares:
1. the four available PDF volumes `История_part001.pdf`–`История_part004.pdf` (text extraction used for locating source passages);
2. the supplied handoff note `Настройка Агента часть 3.txt`;
3. supplied text captures `Вставленный текст(3).txt`–`Вставленный текст(6).txt`;
4. existing repository checkpoint/report material and the user's direct clarifications on 2026-10-14.

This is a bounded reconstruction, not a claim that every chat or attachment payload was present in the PDF export. Source notes and assistant summaries are not automatically treated as primary evidence. Claims are classified as directly supported by PDF text, directly clarified by the user, secondary-report-only, or still unknown.

## A. Recovered project relationships and the missing causal chain

### A1. B77 / LK / Lite Cook / «Что приготовить» APK

**Direct user clarification, 2026-10-14:**
- `LK` is the short repository name for the **whole B77 project**, not a repository dedicated only to Lite Cook.
- B77/LK contains the HTML/WMA direction and had a planned branch for development of the Android APK.
- An agent proposed splitting the application into two directions: a simpler user-facing direction named **Lite Cook / «Лайт Кук»**, and a more technical direction.
- The technical «Что приготовить» APK branch was planned to be unfrozen later and joined with B77/LK into one project. The intended future merge is a plan, not evidence that it happened.
- Development was paused after repeated agent errors. The user chose Lite Cook as a lighter path to make progress.
- The later move to CARD111 was motivated by an expectation that experience from the two recipe projects would help the agent develop faster. Instead, the user experienced severe deterioration in agent performance.

**Direct corroboration in the PDF archive:**
- `История_part002.pdf`, extracted lines approximately 3619–3890: the technical Recipe Manager / «Что приготовить» and Lite Cook are explicitly separated into technical foundation and simpler user-facing layer. The discussion says to stabilize a technical baseline first, then build Lite Cook as a UI layer on top of shared logic.
- Same volume, approximately lines 38435–38459: one SQLite database is described with the technical implementation plus Lite Cook over it; Lite Cook should use the same foundation, not be rewritten from scratch.
- Same volume, approximately lines 42030–42159: HTML prototype, shared database, and the missing internet-import/Food.ru branch are discussed. The transcript explicitly acknowledges that internet recipe import had been dropped from a simplified architecture and restores it to the technical data-ingestion layer.
- Same volume, approximately lines 41441–41445 and 41540–41580: the archive itself calls out the «Техничный + Lite Cook» checkpoint and identifies `Лайт кук.pdf` as a specification source.
- The repository URL `https://github.com/alexbotleh-oss/LK` is present in the archive around extracted lines 68439–68456 (see earlier scope audit). This proves the repository reference, while the repository's whole-project scope is clarified directly by the user.

**Correct model:** B77/LK is the umbrella project; Lite Cook and the technical APK direction are distinct development directions with shared intended foundations and a planned later convergence. Do not collapse this into “LK = Lite Cook only”, and do not assert that the APK and HTML implementation were already merged.

### A2. Why the project sequence matters

The sequence is not a collection of unrelated project names:
1. The recipe application accumulated technical complexity and repeated agent errors.
2. The Lite Cook direction was selected to reduce immediate complexity while preserving the technical foundation and common recipe data.
3. CARD111 was chosen as a more tractable project where experience from both recipe directions might make development faster.
4. The expected acceleration did not occur; the user reports that agent reliability became markedly worse.
5. This experience motivates the current agent-memory project: preserve not only end states and reusable rules, but also why the direction changed, what was expected, what actually happened, and which earlier failures should affect the next decision.

The motivation in steps 2–5 is user-reported/directly clarified context; it should not be rewritten as an independently measured causal diagnosis of model behavior.

## B. Restored main goal and active work

The main goal of «Настройка Агента» is to build a continuous agent workflow that preserves and restores task state across chats and projects, uses shared knowledge without mixing project contexts, and continues from evidence rather than restarting or merely claiming to remember.

The supplied note `Вставленный текст(3).txt` explicitly identifies this chat as the central coordination point and states that checkpoint content must include:
- the overall goal and direction;
- decisions, reasons, and changes in requirements;
- relationships between ideas and contradictions;
- implementation status distinguishing implemented/verified from documented/proposed/unknown;
- the exact return point, open questions, deferred ideas, and next action.

The same note explicitly says this is a working protocol, not proof of automatic cross-chat synchronization. Do not claim that every message is automatically written to the repository.

The current task is not to restart the already completed report review. It is to reconcile the existing report/text captures with the available PDF export and the live repository, restore missing relationships/provenance, then continue implementing and validating the memory-transfer/restore workflow.

## C. Memory architecture requirements that must survive summarization

The source material supports the following requirements as established design direction, not all as fully implemented capabilities:

1. **Capture before interpretation.** First preserve source messages and attachments, their identifiers, timestamps and reply/thread relationships. Do not run expensive semantic deduplication or summarization in the first import pass.
2. **Separate importer and analyzer.** The importer should quickly and resumably preserve original records; the analyzer can later derive events, decisions, failed attempts, consequences, causal links and lessons.
3. **Chronology is not report order.** Reports gathered from several chats/tabs may overlap and arrive out of sequence. Distinguish source event time, export time, ingestion time, and later correction time.
4. **Deduplicate copies, not independent recurrences.** Repeated report text is a copy-level duplicate candidate; it does not prove repeated underlying incidents are one event. Keep distinct recurrences and new outcomes as separate linked events.
5. **Provenance is mandatory.** Every derived event/lesson should point back to source message/file/log where possible, and preserve evidence level and uncertainty.
6. **Preserve the causal chain.** A memory record must not only store the final answer. Capture context/problem → alternatives/hypotheses → decision and reason → action/attempt → result → verification → error/correction → applicability and next step.
7. **Project identity boundaries.** Similar feature names do not prove the same implementation. B77 HTML/WMA, the technical APK/Flet direction, CARD111 and ORGANISM must retain their own source chains; transferable lessons may link them without merging their histories.
8. **Resumability and idempotence.** Store a confirmed cursor/checkpoint, record counts, parser version and operation status. A repeated import must not duplicate already confirmed source records. Recovery after interrupted writes must verify persisted data before retrying.
9. **A checkpoint must lead to action.** Restoring context is incomplete unless the agent recovers the current goal, last completed step, restrictions, pending return from side branches, and one evidence-based next step.
10. **Written rules are not proof of behavior.** Passing a documentation-contract test or CI does not prove live model compliance, complete history coverage, correct semantic reconstruction, or end-to-end session restoration.

These requirements align with the supplied note `Настройка Агента часть 3.txt`, the central checkpoint in `Вставленный текст(3).txt`, and the PDF passages about lost causal history (part003, approximately line 18735) and the required experience unit (part003, approximately lines 22808–22983). The line locations are navigation aids within the extracted PDF text, not claims that the entire archive has been exhaustively audited.

## D. Reconciliation findings: what had been flattened or misrepresented

### Corrected now
- The relationship of B77, LK, Lite Cook and the technical APK branch is restored as above.
- The absence of an exact chat title «Что приготовить-лайт» is not evidence against the two-direction development history; a branch name and a chat title are different kinds of identifiers.
- LK must not be classified as a Lite-Cook-only repository.
- Planned later integration of the APK direction must not be described as completed.
- Internet recipe import must remain in the technical/shared data-ingestion architecture; simplifying the Lite Cook UI must not erase the import requirement.
- The choice to switch to CARD111 and the disappointment after expecting faster development are part of the causal history, not incidental conversation.

### Still partial / unknown
- The available PDF export is a text rendering with attachment payloads excluded; filenames/metadata are not the same as attachment bytes.
- The archive snapshot is bounded in time. It cannot independently establish events or edits made after its export.
- Exact Git branch/commit evidence is required to determine whether a planned APK/HTML integration ever happened. The current discussion does not establish that it did.
- Reports from other chats remain secondary sources unless their original message records or artifacts are available.
- The mechanism behind the model's deterioration is not established by the project history. Preserve the observed failures and their effects; do not invent a single technical root cause.

## E. Source coverage and archive-count caution

Existing repository reports say the inspected `conversations.zip` snapshot contains 37 conversation objects and 10,034 distinct message IDs across 2026-09-21 through 2026-10-07 UTC; the earlier “74 chats” count is unresolved/unsubstantiated against that snapshot. The four PDF volumes are a rendering of available export material, not a guarantee of every message or attachment payload. Keep the 37-object count scoped to that ZIP snapshot and do not treat it as the total number of chats ever involved in the work.

## F. Where this belongs and next actions

This reconstruction belongs under `projects/AGENT_MEMORY_SYSTEM/` because it restores context and source-provenance rules for the memory-transfer project. The B77-specific project state should eventually reference this document or receive a concise, separately scoped update; do not move raw B77 history into the direct-scope memory PR without a scope decision.

Next:
1. Read this document back from GitHub and verify its content.
2. Link it from the canonical AGMS task state and handoff.
3. Update the path-disposition manifest with this reconstruction file.
4. Continue scope-cleaning PR #22 only after preserving out-of-scope source/history material.
5. Check validation and CI against the exact resulting commit SHA.
6. Keep PR #22 open/Draft/unmerged and do not modify `main` without explicit authorization.
