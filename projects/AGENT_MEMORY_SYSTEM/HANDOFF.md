# HANDOFF — AGENT_MEMORY_SYSTEM

Updated: 2026-10-18

## Active goal
Continue building a reliable, resumable raw-history intake and memory-evolution pipeline. Preserve source bytes, chronology, provenance, conflicts and unknowns. Keep raw import separate from later semantic analysis.

## Live baseline
- Repository: `alexbotleh-oss/agent-knowledge-base`.
- Branch: `export/cross-project-experience-rollup-20261012`.
- PR #22: [open / Draft / unmerged](https://github.com/alexbotleh-oss/agent-knowledge-base/pull/22).
- `main` last verified at `a0c12ba849a3416f50e1289d8f0dd20844e1e51f`; do not modify or merge without explicit permission.
- Earlier exact-head CI passed at `825f71bda46078ef9e0864b55af094784eb29b4b` in [run #39124375760](https://github.com/alexbotleh-oss/agent-knowledge-base/actions/runs/39124375760), with 79 unittest tests and memory validation. Later code, validator, docs and checkpoint commits were added after that run. **Verify CI for the current exact HEAD before reporting current state as verified.**

## Current implementation state
- `tools/resumable_chat_import.py` is an existing local-first prototype. It preserves a SHA-256-verified immutable source snapshot, incrementally parses one conversation object at a time, stages opaque payloads in SQLite, journals batches/checkpoints transactionally, and supports JSON/ZIP input with resumable/idempotent runs.
- `_verify_staged_integrity()` validates staged payload JSON, payload SHA-256 and contiguous source ordinals before resume, before marking `RAW_COMPLETE`, and before returning `ALREADY_COMPLETE`. Corruption sets `FAILED`, appends `INTEGRITY_FAILED`, and raises.
- `import_export()` acquires an OS-managed exclusive lock for its output directory. A second writer should fail visibly; the OS releases the lock when the process exits. Linux/Unix `fcntl` is the CI path; Windows and network filesystems are not independently verified.
- `immutable_snapshot()` fsyncs copied file contents before publishing the final content-addressed name, then attempts directory fsync where supported. A failure-injection test checks that file-fsync failure does not publish the final name.
- `tools/temporal_memory_model.py::validate_temporal_relations(records, trusted_order)` validates `preceded_by` / `followed_by` against explicit trusted ordering, applies `edge_corrections` overlays in memory, and refuses to guess when order evidence is missing. Tests cover a wrong-direction edge, the correction case EVT-AGMS-20261018-003, preservation of source rows, and missing chronology.
- Temporal validation is currently a tested library primitive, **not** a mandatory pre-write hook. A single event append path that invokes it before writing is still needed.
- Append-only events `EVT-AGMS-20261018-001..005` document integrity hardening, writer locking, the relation-direction correction, snapshot durability and the temporal validator. Do not rewrite historical events or remove correction overlays.

## Verification boundary
- Exact-head CI for the newest code/docs/event/checkpoint commits is pending in this handoff revision.
- A real archive run was not possible in the previous session: the Library file service refused raw-byte materialization of the selected ZIP. Do not claim real-source verification.
- The importer stages conversation JSON only. Manifest reconciliation, binary attachment inventory, full external chat coverage, SQLite commit-boundary failure injection and automatic live ChatGPT capture remain unverified or unimplemented.
- The PR contains 135 changed paths and unrelated project-history scope; it is not scope-clean or merge-ready.

## Immediate next actions
1. Re-fetch branch HEAD, `main`, PR metadata and Actions; verify exact-head CI. Read back changed code and check JSONL parseability, unique event IDs and correction overlays.
2. Build a single append-only event-writing entry point that refuses to append if temporal relations fail validation or lack trusted chronology. Do not derive chronology from journal line order.
3. Add failure injection around SQLite commit/checkpoint boundaries; test Windows lock behavior separately if Windows is a target.
4. Obtain authorized local raw bytes for the intended export; run the importer and record source hash, archive structure, counts and gaps without uploading private content to GitHub.
5. Reconcile manifest entries and attachment payload availability separately. The importer does not prove attachment completeness.
6. Continue PR scope cleanup only with a verified preservation destination for out-of-scope history.

## Operating rules
- Preserve raw source separately from extracted/candidate/canonical memory.
- Never treat a summary as a replacement for source history or import time as event time.
- A passing CI run does not prove complete chat/attachment coverage, multi-process safety on every filesystem, or live ChatGPT integration.
- Keep PR #22 Draft/open/unmerged. Do not modify `main`, delete history or merge without explicit user permission.
