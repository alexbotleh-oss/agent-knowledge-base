# LESSONS — B77 HTML/PWA

Status labels: **validated** means the described event/result is supported by a source; it does not automatically mean the prevention rule has been tested across projects. **candidate** means a useful prevention rule that still needs a deliberate trial in later work.

## B77-L-001 — Restore project context before rediscovering
- **Status:** validated incident; prevention rule to be exercised in future transitions.
- **Evidence:** [context-continuity incident report](https://github.com/alexbotleh-oss/LK/blob/main/reports/PROJECT_CONTINUITY_20261005.md), commit [ded2288](https://github.com/alexbotleh-oss/LK/commit/ded22885e28773b12ccd0fb8c494af5d2991af55).
- **Observed failure:** a new chat treated a known connected repository as unknown and asked the user to repeat its identity.
- **Prevention rule:** at task start, inspect project instructions, recent project chats/files if accessible, connected repository, latest verified checkpoint, frozen boundaries, and unresolved task. Ask only for a genuinely unavailable detail.
- **Transfer candidate:** likely applies to both B77 and RECIPE_MANAGER; verify against the second project's source history.

## B77-L-002 — Record event chronology independently from memory-import order
- **Status:** candidate grounded in the user's explicit requirement and the observed cross-chat loss problem.
- **Evidence:** user statement, 2026-10-12; B77 report and Git history.
- **Risk:** a source discovered or pasted late can be mistaken for a new event, corrupting cause/effect and the next-step decision.
- **Prevention rule:** retain separate event time, source time, and record/ingestion time where available. Insert late-found events at their historical position and link them to evidence; do not silently reorder or overwrite later outcomes.
- **Validation needed:** apply this rule when merging real fragments from both ChatGPT projects, including at least one late-arriving older source.

## B77-L-003 — Snapshot before changing a sensitive or working area
- **Status:** validated that snapshots were created; effectiveness of each backup under restoration has not been tested by this record.
- **Evidence:** [WP backup](https://github.com/alexbotleh-oss/LK/commit/6d9038eb0b37f53698074be7ea1a0dc3b1eb77eb), [pre-camera main backup](https://github.com/alexbotleh-oss/LK/commit/7e911a97dd95df6d08efb24b2eb39846efa0ce1c), [scanner binding snapshot](https://github.com/alexbotleh-oss/LK/commit/162442d1fbccf6e41e536ffed3fc5882eef7e2be), [format snapshot](https://github.com/alexbotleh-oss/LK/commit/2af27cd62e87376d3409ba30a298fe7a3512a22c).
- **Prevention rule:** before a risky change, name the baseline SHA, recovery point, intended files, and regression checks. After the change, compare the reverse diff and retain a clear rollback path.
- **Exception:** a snapshot alone is not proof that the correct state can be restored; restoration must be checked when required.

## B77-L-004 — A rollback is experience, not noise to erase
- **Status:** validated event; exact technical reason for rollback remains unknown here.
- **Evidence:** Data Matrix format addition [456b420](https://github.com/alexbotleh-oss/LK/commit/456b4208e94b9e2130ffa2a4a29d0041d9be7679) followed by [rollback d5a77c1](https://github.com/alexbotleh-oss/LK/commit/d5a77c141e268bd2275af8748c2c4e5db2fec27a).
- **Prevention rule:** preserve the attempted change, evidence of failure, rollback, and reason if known. Do not reapply the same change without a new hypothesis and a test that distinguishes it from the failed attempt.

## B77-L-005 — Keep input/UI changes on the existing business path
- **Status:** validated project constraint; end-to-end runtime result must be checked separately.
- **Evidence:** [B77 continuity report](https://github.com/alexbotleh-oss/LK/blob/main/reports/PROJECT_CONTINUITY_20261005.md).
- **Rule:** camera input feeds the established `openScanner → scanSubmit → Core.findQR → Products/Shopping/QR` path. Avoid duplicate handlers/Core and avoid changing business logic to compensate for an input-layer issue without evidence.
- **Applicability:** architectural integrations where a new interface/input method should reuse established business logic.

## B77-L-006 — Diagnose the environment before patching the feature
- **Status:** candidate, with a reported secure-context case.
- **Evidence:** project history reports QR/camera trouble when opened via `content://` rather than HTTPS; supporting commit history includes an HTTPS diagnostic harness: [d60cbae](https://github.com/alexbotleh-oss/LK/commit/d60cbae0a0aa3d2bffe0511f83534a94853551f).
- **Rule:** before changing scanner logic, verify deployment URL, secure-context eligibility, permissions, API availability, and actual error output on the target device.
- **Limit:** this is not a universal explanation for every scanner failure.

## B77-L-007 — Separate change existence from runtime success
- **Status:** validated as a reporting rule; broader cross-project validation pending.
- **Evidence:** repository records contain commits and diagnostic changes, while this memory does not contain a complete device test record for every change.
- **Rule:** state separately what was edited, statically checked, deployed, and actually exercised on the target device. Do not call a feature PASS from a commit, syntax check, or successful CI alone.

## B77-L-008 — Compare every HTML candidate against the known working reference
- **Status:** validated as a required prevention rule from repeated user-reported regressions; latest candidate outcome remains unverified.
- **Evidence:** EVT-B77-20260922-002, EVT-B77-20260922-003 and EVT-20261012-014; the user repeatedly reported that database import, recipe deletion and kcal/100 g / BJU display disappeared in later HTML candidates despite being present in a reference.
- **Rule:** name the exact working baseline and candidate; compare the final saved artifact and test SQLite import/add, edit, delete, nutrition display, ingredient matching and persistence. Syntax checks, a link, or a claim that a function exists are not runtime evidence.
- **Limit:** do not attribute this HTML regression to N99 Android/Flet without separate source evidence.

## B77-L-009 — Trace a visible-but-ineffective control through the existing event chain
- **Status:** validated user-reported symptom; code-level root cause remains unknown.
- **Evidence:** EVT-B77-20261004-001 and EVT-20261012-016; Products category/sort options were visible, but choosing them did not apply the filter/sort. Shopping sorting also had a reported unit-display side effect before a narrow recovery was reported.
- **Rule:** trace control → handler → state/key → filter/sort → render. Verify the resulting list, each option, reset-to-all behavior and unchanged quantity/unit values. Do not add another listener or declare success merely because the option highlights.
- **Limit:** this is a diagnostic method, not a claim that the original code cause was found.

## B77-L-010 — Camera video is not proof of successful code decoding
- **Status:** validated distinction from user reports; decoder root cause remains unknown.
- **Evidence:** EVT-B77-20261005-002, EVT-B77-20261005-004 and EVT-20261012-019; camera access/video appeared in browser/PWA contexts, but the code was not recognized or saved.
- **Rule:** verify separately: secure context and permission → video/frame availability → decoder invocation → decoded value and symbology → callback/business handler → persistence → stop behavior after a successful decode. Do not diagnose a stop-after-success failure when no successful decode was observed.
- **Limit:** the browser/PWA pipeline is distinct from the native N99/Flet scanner.

## Cross-project candidates to compare against RECIPE_MANAGER
1. Context recovery should precede new work.
2. One bounded change per iteration, followed by a reverse-diff and regression checks.
3. Keep syntax/build/CI/runtime/UI validation as separate claims.
4. Preserve user data, working checkpoints, and rollback paths.
5. Record failed attempts and their evidence, not only successful versions.
6. Keep event chronology separate from the date a fragment is imported.
7. Promote a project-specific lesson to global memory only after checking that the second project supports it and documenting applicability/limits.
