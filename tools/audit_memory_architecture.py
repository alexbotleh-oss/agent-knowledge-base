#!/usr/bin/env python3
"""Build a read-only, evidence-based map of memory-system tools and storage.

The report is derived from repository contents and Python imports. It distinguishes
observed code paths from documentation claims and missing expected locations.
"""
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "memory-architecture-audit-v1"
EXPECTED_ENTRYPOINTS = (
    "core/agent_bootstrap.md",
    "core/agent_runtime_protocol.md",
    "core/session_handoff.md",
    "core/source_ingestion_protocol.md",
    "core/memory_model.md",
    "core/memory_registry_and_multidimensional_index.md",
    "core/unified_memory_control_loop.md",
)
PATH_NAME_HINTS = ("REGISTRY", "INDEX", "ROOT", "LEDGER", "STATE", "MANIFEST", "CORRECTION")


def _relative(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path)


def _resolve_static_path(node: ast.AST, root: Path, env: dict[str, Any]) -> str | None:
    """Resolve a deliberately small safe subset of Python path expressions."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name):
        value = env.get(node.id)
        return str(value) if isinstance(value, Path) else None
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        left = _resolve_static_path(node.left, root, env)
        right = _resolve_static_path(node.right, root, env)
        if left is not None and right is not None:
            return str((Path(left) / right).resolve()) if Path(left).is_absolute() else str(Path(left) / right)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        # Recognize Path(__file__).resolve().parents[N] without evaluating code.
        if node.func.attr == "resolve" and isinstance(node.func.value, ast.Call):
            inner = node.func.value
            if isinstance(inner.func, ast.Name) and inner.func.id == "Path":
                if inner.args and isinstance(inner.args[0], ast.Name) and inner.args[0].id == "__file__":
                    return str(root.resolve())
    if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute):
        if node.value.attr == "parents" and isinstance(node.value.value, ast.Call):
            resolved = _resolve_static_path(node.value.value, root, env)
            if resolved is not None and isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, int):
                base = Path(resolved)
                for _ in range(node.slice.value + 1):
                    base = base.parent
                return str(base)
    return None


def _module_name(path: Path, tools_root: Path) -> str:
    return path.relative_to(tools_root).with_suffix("").as_posix().replace("/", ".")


def _scan_python(path: Path, repo_root: Path, tools_root: Path, known_modules: set[str]) -> dict:
    rel = _relative(path, repo_root)
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=rel)
    except (OSError, UnicodeDecodeError, SyntaxError) as exc:
        return {"path": rel, "parse_status": "ERROR", "error": str(exc),
                "imports": [], "storage_paths": [], "cli_entrypoint": False}

    module = _module_name(path, tools_root)
    imports: set[str] = set()
    storage_paths = []
    env: dict[str, Any] = {"ROOT": repo_root.resolve()}
    assignments = [node for node in tree.body if isinstance(node, (ast.Assign, ast.AnnAssign))]
    for node in assignments:
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        value = node.value
        for target in targets:
            if not isinstance(target, ast.Name):
                continue
            name = target.id
            if name == "ROOT":
                env[name] = repo_root.resolve()
                continue
            resolved = _resolve_static_path(value, repo_root, env)
            if resolved is not None and "://" not in resolved and (
                any(hint in name.upper() for hint in PATH_NAME_HINTS)
                or name.upper().startswith("DEFAULT_")
            ):
                path_value = Path(resolved)
                if not path_value.is_absolute():
                    path_value = repo_root / path_value
                try:
                    stored = path_value.resolve().relative_to(repo_root.resolve()).as_posix()
                except ValueError:
                    stored = str(path_value)
                storage_paths.append({
                    "constant": name,
                    "path": stored,
                    "exists_in_current_checkout": (repo_root / stored).exists() if not Path(stored).is_absolute() else Path(stored).exists(),
                    "evidence": "static_path_expression",
                })
                env[name] = path_value
            elif resolved is not None and name in {"ROOT", "REPO_ROOT"}:
                env[name] = Path(resolved)

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for item in node.names:
                candidate = item.name
                if candidate in known_modules:
                    imports.add(candidate)
        elif isinstance(node, ast.ImportFrom) and node.module:
            candidate = node.module.lstrip(".")
            if candidate in known_modules:
                imports.add(candidate)
        elif isinstance(node, ast.If):
            test = ast.dump(node.test)
            if "__name__" in test and "__main__" in test:
                pass

    cli_entrypoint = any(
        isinstance(node, ast.If)
        and isinstance(node.test, ast.Compare)
        and "__name__" in ast.dump(node.test)
        and "__main__" in ast.dump(node.test)
        for node in tree.body
    )
    return {
        "path": rel,
        "module": module,
        "parse_status": "OK",
        "imports": sorted(imports),
        "storage_paths": sorted(storage_paths, key=lambda item: (item["path"], item["constant"])),
        "cli_entrypoint": cli_entrypoint,
        "source_sha256": __import__("hashlib").sha256(source.encode("utf-8")).hexdigest(),
    }


def build_audit(repo_root: Path, expected_paths: tuple[str, ...] = EXPECTED_ENTRYPOINTS) -> dict:
    repo_root = Path(repo_root).resolve()
    tools_root = repo_root / "tools"
    if not repo_root.is_dir():
        return {"schema_version": SCHEMA_VERSION, "status": "INVALID_ROOT",
                "repo_root": str(repo_root), "components": [], "storage_paths": [],
                "expected_locations": [], "writes_performed": False}
    python_files = sorted(tools_root.rglob("*.py")) if tools_root.is_dir() else []
    known_modules = {_module_name(path, tools_root) for path in python_files}
    components = [_scan_python(path, repo_root, tools_root, known_modules) for path in python_files]
    path_to_module = {item["path"]: item.get("module") for item in components}
    storage_paths = []
    for component in components:
        for item in component.get("storage_paths", []):
            storage_paths.append({
                "owner": component["path"],
                "module": component.get("module"),
                **item,
            })
    expected = []
    for rel in expected_paths:
        target = repo_root / rel
        expected.append({
            "path": rel,
            "status": "PRESENT" if target.exists() else "EXPECTED_BUT_ABSENT",
            "evidence": "filesystem_check",
        })
    # These edges are direct Python imports, not inferred semantic relationships.
    edges = [
        {"from": item["module"], "to": target, "type": "imports"}
        for item in components if item.get("module")
        for target in item.get("imports", [])
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "COMPLETE_SCAN" if all(c.get("parse_status") == "OK" for c in components) else "PARTIAL_SCAN",
        "repo_root": str(repo_root),
        "component_count": len(components),
        "components": components,
        "dependency_edges": sorted(edges, key=lambda item: (item["from"], item["to"])),
        "storage_paths": sorted(storage_paths, key=lambda item: (item["path"], item["owner"], item["constant"])),
        "expected_locations": expected,
        "limitations": [
            "Imports establish code dependencies, not proof that a function is called in the live ChatGPT session.",
            "Static path detection intentionally handles only a limited subset of Python expressions.",
            "Runtime data files may be absent from Git while existing in another runtime or branch.",
            "Documentation claims and runtime behavior must be verified separately.",
            "This audit does not search other branches, remote archives, connected apps, or devices.",
        ],
        "writes_performed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    report = build_audit(args.repo_root)
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    print(payload, end="")
    return 0 if report["status"] in {"COMPLETE_SCAN", "PARTIAL_SCAN"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
