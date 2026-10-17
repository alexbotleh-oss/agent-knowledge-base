#!/usr/bin/env python3
"""Locate expected memory/source material across known roots when its canonical path misses.

Read-only by design: this tool discovers and classifies candidates. It never moves files,
rewrites indexes, or treats a bounded no-match as proof of global absence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

DEFAULT_EXTENSIONS = {
    ".md", ".txt", ".json", ".jsonl", ".yaml", ".yml", ".toml", ".csv",
    ".py", ".sh", ".xml", ".html", ".js", ".ts",
}
SKIP_DIRS = {
    ".git", ".github", "node_modules", ".venv", "venv", "__pycache__",
    "dist", "build", ".idea", ".next",
}


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _normalise(value: str) -> str:
    return " ".join(value.casefold().split())


def _identity_present(text: str, identity: str) -> bool:
    # A textual mention is a candidate, not proof that this file owns the identity.
    return re.search(r"(?<![A-Za-z0-9_.:/-])" + re.escape(identity) +
                     r"(?![A-Za-z0-9_.:/-])", text) is not None


IDENTITY_FIELDS = {
    "memory_id", "source_record_id", "source_id", "event_id", "record_id",
    "conversation_id", "message_id", "source_node_id", "archive_id",
}


def _structured_identity_present(path: Path, text: str, identity: str) -> bool:
    """Verify an ID in a declared identity field, not merely in prose or provenance."""
    if path.suffix.lower() not in {".json", ".jsonl"}:
        return False

    def contains(value: Any) -> bool:
        if isinstance(value, dict):
            for key, child in value.items():
                if key in IDENTITY_FIELDS and child == identity:
                    return True
                if contains(child):
                    return True
        elif isinstance(value, list):
            return any(contains(item) for item in value)
        return False

    try:
        if path.suffix.lower() == ".jsonl":
            for line in text.splitlines():
                if line.strip() and contains(json.loads(line)):
                    return True
            return False
        return contains(json.loads(text))
    except (json.JSONDecodeError, TypeError):
        return False


def discover(
    expected_path: str,
    search_roots: list[Path],
    *,
    identity: str | None = None,
    expected_sha256: str | None = None,
    query: str | None = None,
    max_files: int = 2000,
    max_file_bytes: int = 2 * 1024 * 1024,
) -> dict[str, Any]:
    """Search bounded, explicitly supplied roots and return evidence-backed candidates."""
    if not expected_path or not search_roots:
        return {"status": "INVALID_INPUT", "coverage_status": "UNKNOWN",
                "reason": "expected_path and at least one search root are required",
                "candidates": [], "writes_performed": False}
    if not any((identity, expected_sha256, query)):
        return {"status": "INVALID_INPUT", "coverage_status": "UNKNOWN",
                "reason": "provide identity, expected_sha256, or query",
                "candidates": [], "writes_performed": False}
    if isinstance(max_files, bool) or not isinstance(max_files, int) or max_files < 1:
        return {"status": "INVALID_INPUT", "coverage_status": "UNKNOWN",
                "reason": "max_files must be a positive integer",
                "candidates": [], "writes_performed": False}
    if expected_sha256 and not re.fullmatch(r"[0-9a-fA-F]{64}", expected_sha256):
        return {"status": "INVALID_INPUT", "coverage_status": "UNKNOWN",
                "reason": "expected_sha256 must be a 64-character SHA-256 hex digest",
                "candidates": [], "writes_performed": False}

    roots: list[Path] = []
    for raw_root in search_roots:
        root = Path(raw_root).expanduser().resolve()
        if root.is_dir() and root not in roots:
            roots.append(root)
    if not roots:
        return {"status": "NO_VALID_ROOTS", "coverage_status": "UNKNOWN",
                "reason": "none of the supplied search roots is an accessible directory",
                "candidates": [], "writes_performed": False}

    expected = Path(expected_path)
    expected_locations = []
    for root in roots:
        path = (root / expected).resolve()
        if root == path or root not in path.parents:
            continue
        if path.exists():
            expected_locations.append(path)

    candidates: list[dict[str, Any]] = []
    scanned = 0
    incomplete_reasons: list[str] = []
    seen: set[Path] = set()
    normal_query = _normalise(query) if query else None

    def inspect(path: Path, root: Path) -> None:
        nonlocal scanned
        if path in seen or not path.is_file():
            return
        seen.add(path)
        if path.suffix.lower() not in DEFAULT_EXTENSIONS:
            return
        if scanned >= max_files:
            incomplete_reasons.append("MAX_FILES_REACHED")
            return
        try:
            size = path.stat().st_size
            if size > max_file_bytes:
                incomplete_reasons.append("OVERSIZED_FILE_SKIPPED")
                return
            data = path.read_bytes()
            scanned += 1
            text = data.decode("utf-8")
        except (OSError, UnicodeDecodeError):
            incomplete_reasons.append("UNREADABLE_OR_NON_UTF8_FILE")
            return

        actual_sha = _sha(data)
        hash_match = bool(expected_sha256 and actual_sha.lower() == expected_sha256.lower())
        identity_token_match = bool(identity and _identity_present(text, identity))
        structured_identity_match = bool(identity and _structured_identity_present(path, text, identity))
        query_match = bool(normal_query and normal_query in _normalise(text))
        if not (hash_match or identity_token_match or query_match):
            return
        try:
            relative = path.relative_to(root).as_posix()
        except ValueError:
            relative = str(path)
        evidence = []
        if hash_match:
            evidence.append("EXACT_SHA256")
        if identity_token_match:
            evidence.append("EXACT_IDENTITY_TOKEN")
        if structured_identity_match:
            evidence.append("STRUCTURED_IDENTITY_FIELD")
        if query_match:
            evidence.append("NORMALIZED_TEXT_MATCH")
        candidates.append({
            "path": str(path),
            "root": str(root),
            "relative_path": relative,
            "sha256": actual_sha,
            "size_bytes": size,
            "evidence": evidence,
            "identity_verified": hash_match or structured_identity_match,
            "canonical_path": path in expected_locations,
        })

    # Inspect expected locations first, then search every other known location.
    for path in expected_locations:
        root = next(r for r in roots if r == path or r in path.parents)
        inspect(path, root)
    for root in roots:
        for path in root.rglob("*"):
            if any(part in SKIP_DIRS for part in path.parts):
                continue
            if path in seen:
                continue
            inspect(path, root)
            if scanned >= max_files:
                incomplete_reasons.append("MAX_FILES_REACHED")
                break
        if scanned >= max_files:
            break

    candidates.sort(key=lambda c: (
        not c["canonical_path"], not c["identity_verified"],
        "EXACT_SHA256" not in c["evidence"], c["path"]
    ))
    canonical_match = next((c for c in candidates if c["canonical_path"] and c["identity_verified"]), None)
    elsewhere_match = next((c for c in candidates if not c["canonical_path"] and c["identity_verified"]), None)
    if canonical_match:
        status = "FOUND_AT_EXPECTED_PATH"
    elif elsewhere_match:
        status = "FOUND_ELSEWHERE_IDENTITY_MATCH"
    elif candidates:
        status = "CANDIDATES_UNVERIFIED"
    elif incomplete_reasons:
        status = "SEARCH_INCOMPLETE"
    else:
        status = "NOT_FOUND_WITHIN_SEARCH_SCOPE"

    coverage = "COMPLETE_WITHIN_CONFIGURED_BOUNDS" if not incomplete_reasons else "PARTIAL"
    if status == "NOT_FOUND_WITHIN_SEARCH_SCOPE" and incomplete_reasons:
        status = "SEARCH_INCOMPLETE"
    return {
        "status": status,
        "coverage_status": coverage,
        "expected_path": expected_path,
        "expected_path_exists": bool(expected_locations),
        "identity": identity,
        "expected_sha256": expected_sha256,
        "query": query,
        "search_roots": [str(root) for root in roots],
        "files_scanned": scanned,
        "max_files": max_files,
        "max_file_bytes": max_file_bytes,
        "incomplete_reasons": sorted(set(incomplete_reasons)),
        "candidates": candidates[:100],
        "candidate_count": len(candidates),
        "interpretation": {
            "FOUND_AT_EXPECTED_PATH": "Identity evidence was found at the expected path.",
            "FOUND_ELSEWHERE_IDENTITY_MATCH": "Identity evidence was found elsewhere; inspect provenance before repairing pointers or moving data.",
            "CANDIDATES_UNVERIFIED": "Text candidates exist, but identity was not verified.",
            "NOT_FOUND_WITHIN_SEARCH_SCOPE": "No match in the fully scanned configured scope; this does not prove global absence.",
            "SEARCH_INCOMPLETE": "Some locations were not fully examined; absence cannot be concluded.",
        }.get(status, "Input or scope needs review."),
        "writes_performed": False,
        "automatic_relocation_performed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-path", required=True, help="Expected path relative to each supplied root")
    parser.add_argument("--root", action="append", required=True, help="Explicit directory to search; repeatable")
    parser.add_argument("--identity", help="Stable record/source ID to find exactly")
    parser.add_argument("--expected-sha256", help="Expected SHA-256 of the source bytes")
    parser.add_argument("--query", help="Normalized text to find as a fallback candidate")
    parser.add_argument("--max-files", type=int, default=2000)
    parser.add_argument("--max-file-bytes", type=int, default=2 * 1024 * 1024)
    args = parser.parse_args()
    result = discover(
        args.expected_path, [Path(p) for p in args.root],
        identity=args.identity, expected_sha256=args.expected_sha256,
        query=args.query, max_files=args.max_files, max_file_bytes=args.max_file_bytes,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] in {"FOUND_AT_EXPECTED_PATH", "FOUND_ELSEWHERE_IDENTITY_MATCH", "CANDIDATES_UNVERIFIED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
