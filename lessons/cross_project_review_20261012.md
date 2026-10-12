# Cross-project learning review — 2026-10-12

## Purpose

Compare the two independent ChatGPT projects concerning «Что приготовить» without merging their project histories:

1. **B77 HTML/PWA** — repository `alexbotleh-oss/LK`, `stage14.html`, history including camera/scanner iterations.
2. **RECIPE_MANAGER** — separate project memory for the Flet/Python/Android application, with SQLite, Android startup debugging, and earlier HTML/data regressions.

This is a comparison of currently available records, not a claim that every chat, file, or failure has been recovered. Project facts remain in their own directories. Only prevention patterns are candidates for transfer.

## Evidence reviewed

- B77: `projects/B77_HTML_PWA/EVENT_LOG.md`, `DECISIONS.md`, `LESSONS.md`, plus [LK continuity report](https://github.com/alexbotleh-oss/LK/blob/main/reports/PROJECT_CONTINUITY_20261005.md) and cited Git commits.
- RECIPE_MANAGER: `projects/RECIPE_MANAGER/EVENT_LOG.md`, `DECISIONS.md`, `LESSONS.md`, `HANDOFF.md` on branch `handoff/recipe-manager-20261012`.
- User's explicit priority in the current conversation (2026-10-12): learn from both real projects now; accept partial history; never confuse memory-recording time with event order.

## Comparison matrix

| Pattern | B77 evidence | RECIPE_MANAGER evidence | Current status |
|---|---|---|---|
| Chat-to-chat context can be lost; restore known context before rediscovery | Explicit incident: assistant asked for repository information already available in the project context; LK report and commit `ded2288` | Project handoff records missing source chats/artifacts and incomplete current-state recovery; user reports repeated context/history loss across both projects | **Cross-project candidate, high relevance.** Test on the next real handoff. |
| Preserve chronology independently from the date a fragment is imported | Dated Git commits, snapshots, and rollback; late-found history is a stated user concern | Event log explicitly says it is a partial reconstruction and that dates must not be invented | **Required memory rule.** The formal event/source/recording-time fields are proposed in PR #4, not yet part of `main` at the time of this review. |
| Keep a known-good baseline, bound the change, and preserve rollback evidence | Immutable WP/pre-camera snapshots; Data Matrix addition followed by rollback | Decision record requires one minimal diagnostic patch and protection of data/resources; the exact current Android baseline remains unknown | **Cross-project candidate.** Good process evidence exists; full efficacy is not yet demonstrated across both projects. |
| Separate code/edit status from actual runtime status | Scanner commits and diagnostics exist, but this record lacks complete device-level acceptance for every change | `py_compile` was reported for a candidate while Android runtime remains unconfirmed; black-screen cause unknown | **Strong shared rule.** Claim only the exact check actually performed. |
| Preserve existing business logic when adding an input/UI layer | Camera must feed the existing `Core.findQR → Products/Shopping/QR` chain; no parallel Core | Android UI is frozen until startup debugging is complete; recipe/data functions must be preserved | **Shared architectural principle, different implementation details.** Do not copy code-level assumptions between projects. |
| Verify final data and adjacent user-visible behavior after changes | Scanner chain must preserve QR/EAN result handling; complete runtime regression evidence is partial | Recipe list/CRUD/KБЖУ regressions were reported; actual database contents and adjacent functions must be checked | **Cross-project candidate.** Test real outcomes, not just absence of exceptions. |
| Check environment/API assumptions before patching | Camera behavior was associated with `content://` vs HTTPS secure context; device/API evidence should be checked | Flet constructor rejected `text` for `PopupMenuItem`; exact installed API version needs checking | **Cross-project candidate.** Diagnose runtime environment/API first, but don't assume these are the cause of unrelated errors. |
| Preserve failed attempts and do not repeat a failed change unchanged | Data Matrix change was rolled back; precise technical cause remains unknown | Flet/API and recipe regressions are logged, but some final patches and results are missing | **Required recording rule; effectiveness pending.** A rollback is evidence, not noise to delete. |

## Initial transferable rules

These are the first rules to apply in actual work. They are not claims that every rule has already been experimentally validated across both projects.

1. **Recover before acting.** Read the project handoff, latest state, source artifacts, and repository checkpoint before asking for information or making changes.
2. **Track three times separately when possible:** event time, source time, and recording/import time. Insert a late-discovered old event at its historical position, preserve its provenance, and link it to later fixes/rollbacks. Never infer chronology from import order alone.
3. **One bounded change per iteration.** Record baseline SHA and backup; state the hypothesis and acceptance test; make the smallest relevant patch; inspect the diff; run the test that can falsify the hypothesis; perform targeted regression; record PASS/BLOCKED/FAIL with evidence.
4. **Separate validation levels.** Syntax, unit tests, build, installation, device/browser runtime, visual behavior, and data/function regression are distinct claims.
5. **Protect known-working paths and user data.** New UI/input code should call established business logic; don't rewrite Core or replace a working reference without a verified reason and rollback.
6. **Preserve negative experience.** Record failed attempt, conditions, exact symptom, evidence, rollback, and known/unknown cause. Do not retry the same approach unless the new attempt tests a materially different hypothesis.
7. **Keep project histories separate.** Shared product domain does not make B77 and RECIPE_MANAGER the same codebase. Transfer only the prevention rule, not branch names, implementation details, statuses, or chronology.

## Practical validation plan

For each next real task in either project, add a short learning record with:
- the historical event/source time and the date the record was added;
- baseline and change boundary;
- expected result and a falsifiable test;
- observed result and evidence;
- whether the change prevented recurrence;
- applicability limits and any counterexample.

After at least one real iteration in each project, update the status of each candidate to `validated`, `disputed`, or `still candidate`. Do not raise confidence solely because multiple AI summaries repeat the same statement.

## Important boundary

This review does not diagnose the current B77 or Android failure, does not assert either app is working, and does not modify either application's code. Its deliverable is the first practical learning layer built from the available project evidence.
