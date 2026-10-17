#!/usr/bin/env python3
"""Static inventory of filesystem/database mutation sites in the memory tools.

This is a review aid, not a proof that a path is safe. New mutation APIs may
require extending MUTATING_METHODS / MUTATING_ATTRS. Exit 2 when a discovered
mutation has no operation contract classification.
"""
from __future__ import annotations

import ast
import argparse
from pathlib import Path

MUTATING_METHODS = {
    "write_text", "write_bytes", "unlink", "mkdir", "rename",
    "write", "writelines", "commit", "executemany", "execute", "truncate",
    "flush",
}
MUTATING_ATTRS = {"replace", "remove", "rename", "unlink", "mkdir", "makedirs"}
PATH_DERIVATION_METHODS = {
    "absolute", "expanduser", "joinpath", "resolve", "with_name",
    "with_suffix", "with_stem",
}
CONTRACTS = {
    "tools/guarded_task_state_update.py": "TASK_STATE checkpoint: trust gate, event evidence, expected hash, lock, atomic replace",
    "tools/branch_result_registry.py": "events.jsonl result/ack append: schema validation, stable ID, replay/conflict handling, journal lock, atomic replace",
    "tools/archive_registry_staging.py": "archive staging: source hash and deterministic records; output staging only; snapshot manifest write requires review",
    "tools/resumable_chat_import.py": "resumable import: immutable source snapshot and SQLite batch/transaction persistence; verify restart/replay contract",
    "tools/validate_memory.py": "validation/reporting: inspect output paths and distinguish report writes from canonical state",
    "tools/reconcile_branch_returns.py": "reconciliation report: derived/read-only report contract; must not mutate canonical task state",
    "tools/archive_temporal_index.py": "derived temporal index: rebuildability and source provenance required",
    "tools/plan_memory_intake.py": "planning output: proposal only; no canonical write authorization",
    "tools/adapt_archive_staging_to_intake.py": "derived intake batch publication: source hashes/counts checked; exclusive temp files, fsync, complete-directory rename; replay/conflict check; no canonical registry writes",
    "tools/source_evidence_registry.py": "metadata-only source registry append: strict target-path guard, source/manifest revalidation under exclusive lock, idempotent key/conflict checks, fsync and atomic replacement; no semantic promotion",
    "tools/semantic_memory_registry.py": "approval-bound semantic memory promotion: exact manifest/artifact/receipt hashes, explicit user decision receipt, strict registry target, OS advisory lock, append-only revisions, idempotency/conflict checks, atomic fsync/replace; receipt integrity does not authenticate author",
    "tools/canonical_memory_index.py": "derived canonical memory index: validate registry hashes and revision chain, lock source registry and index publication, deterministic immutable generation, atomic CURRENT pointer, freshness checks; accepted edge-correction overlays are validated and indexed when present; coverage remains partial until source completeness is proven",
    "tools/edge_correction_registry.py": "append-only edge correction registry: source memory/revision/hash binding, unique relation fingerprint validation, explicit user approval receipt bound to exact correction bytes for accepted entries, source+target advisory locks, replay/conflict guards, atomic fsync/replace; receipt integrity does not authenticate author",
    "tools/memory_pipeline_coordinator.py": "durable stage coordinator: deterministic input-bound run ID, hash-chained append-only event ledger, rebuildable state projection, explicit source-provenance resolution before promotion, idempotent stage replay, and read-only restore summary; ledger is audit evidence, not a transaction spanning all registries",
    "tools/source_ingestion_runner.py": "resumable orchestration ledger: OS advisory run lock, hash-chained transition ledger, atomic state projection, idempotent source-registry reconciliation after uncertain acknowledgement; explicitly stops before semantic promotion/index refresh/restore",
    "tools/continuity_checkpoint_bundle.py": "paired TASK_STATE/HANDOFF checkpoint: immutable generation, hash-verified parent chain, single atomic CURRENT_CHECKPOINT pointer, OS lock, recoverable projections",
    "tools/turn_lifecycle_ledger.py": "protected local append-only turn journal: advisory lock, fsync, exact-input hash, explicit lifecycle states, fail-closed corrupt journal; workspace artifact scan is read-only and ownership remains UNKNOWN",
    "tools/turn_lifecycle_adapter.py": "authenticated local HTTP adapter: request/response socket writes are protocol output, while all durable state changes delegate to the protected turn lifecycle ledger; loopback by default, bearer auth, body/origin validation",
    "tools/experience_outcome_capture.py": "explicit project-event outcome candidate append: exact acceptance-marker check against a real evidence file, SHA-256 provenance, declared-root path confinement, symlink rejection, OS advisory lock, idempotent identity/replay and conflict checks; candidate only, no semantic-memory promotion",
    "tools/verified_task_executor.py": "explicitly invoked reviewed-action runner: bounded timeout, no shell, root-confined action cwd and acceptance artifacts, exact retrieved same-project experience reference, dry-run default, independent artifact acceptance checks, protected checkpoint/event-log hashes, atomic evidence report, and outcome-candidate capture only after all checks pass; no semantic promotion",
    "tools/check_reuse_policy.py": "append-only check-result events in canonical AGENT_MEMORY_SYSTEM journal; input/source/candidate fingerprints bind reuse, idempotent event IDs and lock/atomic persistence; prior PASS is not trusted without verified receipt",
    "tools/dialogue_attention_controller.py": "append-only attention and return-stack events in canonical AGENT_MEMORY_SYSTEM journal; stable event IDs, lock and atomic persistence; lexical turn classification is a proposal and ambiguous turns remain review-needed",
    "tools/trusted_receipt_verifier.py": "temporary files used only to invoke OpenSSL for Ed25519 receipt verification; cleanup is scoped to temporary verification artifacts, no canonical memory writes; trust requires a valid receipt and externally pinned keyring hash",
}
DEFAULT_MUTATING_SUFFIXES = (".md", ".jsonl", ".json", ".sqlite", ".db")


def _is_path_expression(node: ast.AST, names: set[str]) -> bool:
    """Conservatively recognize common pathlib values without treating str.replace as a write."""
    if isinstance(node, ast.Name):
        return node.id in names
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        return _is_path_expression(node.left, names)
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id in {"Path", "PurePath"}:
            return True
        if isinstance(node.func, ast.Attribute):
            return (
                node.func.attr in PATH_DERIVATION_METHODS
                and _is_path_expression(node.func.value, names)
            )
        return False
    if isinstance(node, ast.Attribute):
        if node.attr == "parent":
            return _is_path_expression(node.value, names)
        if node.attr in PATH_DERIVATION_METHODS:
            return _is_path_expression(node.value, names)
    return False


def _path_names(tree: ast.AST) -> set[str]:
    """Infer obvious pathlib names from annotations and assignments for .replace classification."""
    names: set[str] = set()
    nodes = list(ast.walk(tree))
    for node in nodes:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for arg in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs):
                if isinstance(arg.annotation, ast.Name) and arg.annotation.id in {"Path", "PurePath"}:
                    names.add(arg.arg)
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            annotation = node.annotation
            if isinstance(annotation, ast.Name) and annotation.id in {"Path", "PurePath"}:
                names.add(node.target.id)
    changed = True
    while changed:
        changed = False
        for node in nodes:
            if isinstance(node, ast.Assign) and _is_path_expression(node.value, names):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id not in names:
                        names.add(target.id)
                        changed = True
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                if node.value is not None and _is_path_expression(node.value, names) and node.target.id not in names:
                    names.add(node.target.id)
                    changed = True
    return names


class MutationVisitor(ast.NodeVisitor):
    def __init__(self, path: str, tree: ast.AST):
        self.path = path
        self.function = "<module>"
        self.hits = []
        self.path_names = _path_names(tree)

    def visit_FunctionDef(self, node):
        prior = self.function
        self.function = node.name
        self.generic_visit(node)
        self.function = prior

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Call(self, node):
        name = ""
        if isinstance(node.func, ast.Attribute):
            name = node.func.attr
            receiver = node.func.value
            receiver_is_os = isinstance(receiver, ast.Name) and receiver.id == "os"
            receiver_is_path = _is_path_expression(receiver, self.path_names)
            if (
                name in MUTATING_METHODS
                or (name in MUTATING_ATTRS and name != "replace")
                or (name == "replace" and (receiver_is_os or receiver_is_path))
            ):
                self.hits.append((node.lineno, self.function, name))
        elif isinstance(node.func, ast.Name) and node.func.id == "open":
            mode = ""
            if len(node.args) > 1 and isinstance(node.args[1], ast.Constant):
                mode = str(node.args[1].value)
            if any(flag in mode for flag in ("w", "a", "x", "+")):
                self.hits.append((node.lineno, self.function, f"open({mode})"))
        self.generic_visit(node)


def audit(root: Path) -> tuple[list[dict], list[str]]:
    findings, unclassified = [], []
    for path in sorted((root / "tools").glob("*.py")):
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(path))
        except (OSError, SyntaxError) as exc:
            unclassified.append(f"{path.relative_to(root)}: cannot inspect: {exc}")
            continue
        rel = path.relative_to(root).as_posix()
        visitor = MutationVisitor(rel, tree)
        visitor.visit(tree)
        for line, function, operation in visitor.hits:
            contract = CONTRACTS.get(rel)
            finding = {
                "path": rel, "line": line, "function": function,
                "operation": operation, "contract": contract or "UNCLASSIFIED",
            }
            findings.append(finding)
            if not contract:
                unclassified.append(f"{rel}:{line} {function} -> {operation}")
    return findings, unclassified


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--json", action="store_true", help="emit JSON")
    parser.add_argument("--strict", action="store_true", help="exit 2 when any mutation site lacks a contract entry")
    args = parser.parse_args(argv)
    findings, unclassified = audit(args.root.resolve())
    if args.json:
        import json
        print(json.dumps({"findings": findings, "unclassified": unclassified}, ensure_ascii=False, indent=2))
    else:
        for item in findings:
            print(f"{item['path']}:{item['line']} [{item['function']}] {item['operation']} — {item['contract']}")
        print(f"\nMutation sites: {len(findings)}; unclassified: {len(unclassified)}")
        for item in unclassified:
            print("UNCLASSIFIED:", item)
    return 2 if args.strict and unclassified else 0


if __name__ == "__main__":
    raise SystemExit(main())
