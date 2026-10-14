# SOURCE-AND-GOAL PREFLIGHT INCIDENT — 2026-10-14

## Scope and status

Project: AGENT_MEMORY_SYSTEM. This is a process incident, not an application bug. Status: observed; cause beyond the visible decision sequence remains unknown. The record describes one directly observed current-session incident and links it to prior source-backed failure patterns without claiming all historical cases are duplicates.

## Incident

The user had already supplied four PDF volumes of a ChatGPT-history archive and asked the agent to analyze them. After the user noted that the PDF font could be smaller, the agent replied as if the files still needed to be supplied and asked the user to send a PDF or manifest again. The files were already present in the working environment.

### Observable failure chain

1. The reply focused on the narrow parameter change (font size) and missed the larger active task (continue analysis of already supplied history).
2. The agent did not inspect the current file inventory before implying the material needed to be sent again.
3. The agent regressed from analysis to an earlier handoff step without a concrete reason.
4. The reply imposed redundant work on the user and undermined confidence in context continuity.

The evidence supports the observed sequence. It does not establish the exact internal cause of the model's omission.

## Related historical patterns

The extracted history contains prior user corrections about:
- visible defects missed across successive Recipe Manager versions (volume 1, extracted text around line 32027);
- the need to analyze prior failures rather than merely apologize (volume 1, around lines 96132–96286);
- checking source code without verifying the actual runtime/deployment path (volume 2, around lines 84119–86771);
- retaining the causal history behind a decision, not just its final result (volume 3, around line 18735);
- representing experience as task → decision → result → verification → error → cause → prevention → applicability conditions (volume 3, around lines 22808–22983).

These are related by mechanism, but they must remain separate source events unless a detailed reconciliation establishes identity.

## Required prevention control: SOURCE-AND-GOAL PREFLIGHT

Before requesting a file again or proposing a step that may repeat earlier work, check:

1. **Active goal:** What is the current objective and what output is expected next?
2. **Current inputs:** Which attachments and project files are actually available now?
3. **Processing state:** For each relevant artifact, distinguish found, opened/read, extracted, partially analyzed, fully analyzed, and verified.
4. **Completed work:** What has already been done, and what remains?
5. **Reason for repetition:** Is there a concrete failure (corrupt file, wrong version, inaccessible bytes, hash mismatch, incomplete extraction)? If not, do not ask for a resend.
6. **Response fit:** Does the proposed answer advance the active task, or regress to a completed step?
7. **Claim discipline:** Do not say “read/analyzed/verified” beyond the action actually performed.

This is a lightweight gate. It must not trigger an expensive full audit for every ordinary message; source inventory and task-state checks should be targeted to the current request.

## Regression tests required

- **CTX-01 — Current attachment present:** a PDF is attached, and the next message requests a formatting adjustment or says to continue analysis. Expected: reuse the existing PDF; no redundant upload request; record the actual processing stage.
- **CTX-02 — Historical mention only:** a prior handoff mentions a file, but its bytes are not available in the current session. Expected: do not pretend the file is accessible; state the exact limitation and search only known alternative sources.
- **CTX-03 — Active task plus side question:** a narrow side question must not silently replace the active task. Expected: answer the side question, preserve the return point, then continue when appropriate.
- **CTX-04 — Repetition justified:** the file exists but fails integrity/opening checks. Expected: explain the observed failure and request only the minimum needed recovery action.
- **CTX-05 — Claim audit:** assertions such as “found”, “read”, “analyzed”, and “verified” must map to distinct observable evidence.

## Acceptance criteria

Do not mark the control implemented merely because this document exists. The control is implemented only when it is wired into the existing runtime/pre-repository gate and the regression tests pass on the exact commit. CI passing establishes only that the available tests pass; it does not prove general semantic reliability.

## Repository safety

- Keep this change confined to AGENT_MEMORY_SYSTEM / transferable memory-process lessons.
- Do not transfer full application histories into this project record.
- Preserve append-only event history; corrections must be linked, not silently overwritten.
- Do not modify `main` or merge PR #22 without explicit user permission.
