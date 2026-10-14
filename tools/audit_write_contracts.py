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
    "write_text", "write_bytes", "unlink", "mkdir", "rename", "replace",
    "write", "writelines", "commit", "executemany", "execute", "truncate",
    "flush",
}
MUTATING_ATTRS = {"replace", "remove", "rename", "unlink", "mkdir", "makedirs"}
CONTRACTS = {
    "tools/guarded_task_state_update.py": "TASK_STATE checkpoint: trust gate, event evidence, expected hash, lock, atomic replace",
    "tools/branch_result_registry.py": "events.jsonl result/ack append: schema validation, stable ID, replay/conflict handling, journal lock, atomic replace",
    "tools/archive_registry_staging.py": "archive staging: source hash and deterministic records; output staging only; snapshot manifest write requires review",
    "tools/resumable_chat_import.py": "resumable import: immutable source snapshot and SQLite batch/transaction persistence; verify restart/replay contract",
    "tools/validate_memory.py": "validation/reporting: inspect output paths and distinguish report writes from canonical state",
    "tools/reconcile_branch_returns.py": "reconciliation report: derived/read-only report contract; must not mutate canonical task state",
    "tools/archive_temporal_index.py": "derived temporal index: rebuildability and source provenance required",
    "tools/plan_memory_intake.py": "planning output: proposal only; no canonical write authorization",
}
DEFAULT_MUTATING_SUFFIXES = (".md", ".jsonl", ".json", ".sqlite", ".db")


class MutationVisitor(ast.NodeVisitor):
    def __init__(self, path: str):
        self.path = path
        self.function = "<module>"
        self.hits = []

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
            if name in MUTATING_METHODS or name in MUTATING_ATTRS:
                self.hits.append((node.lineno, self.function, name))
        elif isinstance(node.func, ast.Name) and node.func.id in {"open"}:
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
        visitor = MutationVisitor(rel)
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
    return 2 if unclassified else 0


if __name__ == "__main__":
    raise SystemExit(main())
