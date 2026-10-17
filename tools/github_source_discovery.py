#!/usr/bin/env python3
"""Bounded, read-only source discovery across explicitly configured GitHub refs.

A missing path at one ref is not global absence. Results retain the exact ref
commit, file blob SHA, content digest, access status and search coverage.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import urllib.parse
from pathlib import PurePosixPath
from typing import Any, Callable

from verified_session_restore import API_ROOT, RemoteEvidenceError, request_json

SCHEMA_VERSION = "github-source-discovery-v1"
SHA_RE = re.compile(r"^[0-9a-fA-F]{40}$")
IDENTITY_FIELDS = {
    "memory_id", "source_record_id", "source_id", "event_id", "record_id",
    "conversation_id", "message_id", "source_node_id", "archive_id",
}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _api_error_kind(exc: Exception) -> str:
    message = str(exc).casefold()
    if "404" in message or "not found" in message:
        return "NOT_FOUND"
    if "403" in message or "401" in message or "forbidden" in message or "unauthorized" in message:
        return "ACCESS_DENIED"
    return "SOURCE_UNAVAILABLE"


def _valid_ref(value: Any) -> bool:
    return (
        isinstance(value, str) and bool(value.strip())
        and bool(re.fullmatch(r"[A-Za-z0-9._/-]+", value))
        and ".." not in value and "\\" not in value
    )


def _resolve_ref(repository: str, ref: str, fetch_json: Callable[[str], dict[str, Any]]) -> dict[str, Any]:
    prefix = f"{API_ROOT}/repos/{repository}"
    if SHA_RE.fullmatch(ref):
        commit_sha = ref.lower()
        response = fetch_json(f"{prefix}/commits/{commit_sha}")
        actual = response.get("sha")
        if not isinstance(actual, str) or actual.lower() != commit_sha:
            raise RemoteEvidenceError("COMMIT_REF_MISMATCH")
        return {"ref": ref, "commit_sha": commit_sha, "ref_kind": "commit"}
    encoded = urllib.parse.quote(ref, safe="")
    response = fetch_json(f"{prefix}/branches/{encoded}")
    commit = response.get("commit")
    commit_sha = commit.get("sha") if isinstance(commit, dict) else None
    if not isinstance(commit_sha, str) or not SHA_RE.fullmatch(commit_sha):
        raise RemoteEvidenceError(f"INVALID_BRANCH_HEAD:{ref}")
    return {"ref": ref, "commit_sha": commit_sha.lower(), "ref_kind": "branch"}


def _read_file(repository: str, commit_sha: str, path: str,
               fetch_json: Callable[[str], dict[str, Any]]) -> dict[str, Any]:
    prefix = f"{API_ROOT}/repos/{repository}"
    encoded_path = urllib.parse.quote(path, safe="/")
    url = f"{prefix}/contents/{encoded_path}?ref={commit_sha}"
    payload = fetch_json(url)
    if payload.get("type") != "file":
        raise RemoteEvidenceError("PATH_IS_NOT_FILE")
    blob_sha = payload.get("sha")
    if not isinstance(blob_sha, str) or not SHA_RE.fullmatch(blob_sha):
        raise RemoteEvidenceError("INVALID_BLOB_SHA")
    if payload.get("encoding") != "base64" or not isinstance(payload.get("content"), str):
        raise RemoteEvidenceError("FILE_CONTENT_UNAVAILABLE_OR_TOO_LARGE")
    try:
        raw = base64.b64decode(payload["content"], validate=False)
    except Exception as exc:
        raise RemoteEvidenceError(f"INVALID_BASE64_CONTENT:{exc}") from exc
    if len(raw) != payload.get("size"):
        raise RemoteEvidenceError("FILE_SIZE_MISMATCH")
    return {
        "path": path,
        "blob_sha": blob_sha.lower(),
        "content_sha256": _sha256(raw),
        "size_bytes": len(raw),
        "raw": raw,
    }


def _identity_matches(raw: bytes, identity: str) -> tuple[bool, str | None]:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return False, None
    candidates = []
    try:
        parsed = json.loads(text)
        candidates = parsed if isinstance(parsed, list) else [parsed]
    except json.JSONDecodeError:
        for line in text.splitlines():
            if not line.strip():
                continue
            try:
                candidates.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    for item in candidates:
        if not isinstance(item, dict):
            continue
        for field in IDENTITY_FIELDS:
            value = item.get(field)
            if isinstance(value, str) and value == identity:
                return True, field
    return False, None


def _query_matches(raw: bytes, query: str | None) -> bool:
    if not isinstance(query, str) or not query.strip():
        return False
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return False
    normalized_text = " ".join(text.casefold().split())
    normalized_query = " ".join(query.casefold().split())
    return bool(normalized_query) and normalized_query in normalized_text


def discover_github_source(
    repository: str,
    expected_path: str,
    refs: list[str],
    *,
    identity: str | None = None,
    expected_sha256: str | None = None,
    expected_blob_sha: str | None = None,
    query: str | None = None,
    candidate_paths: list[str] | None = None,
    max_refs: int = 20,
    max_files: int = 200,
    fetch_json: Callable[[str], dict[str, Any]] = request_json,
) -> dict[str, Any]:
    """Search the expected path first, then explicitly known alternate refs/paths.

    The first ref is the expected ref. Search scope is exactly the provided refs
    and paths; the function never claims repository-wide/global absence.
    """
    invalid = []
    if not isinstance(repository, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        invalid.append("repository must be owner/repository")
    if not isinstance(expected_path, str) or not expected_path.strip() or expected_path.startswith("/") or ".." in PurePosixPath(expected_path).parts:
        invalid.append("expected_path must be a safe repository-relative path")
    if not isinstance(refs, list) or not refs or any(not _valid_ref(ref) for ref in refs):
        invalid.append("refs must be a non-empty list of safe branch names or full commit SHAs")
    if isinstance(max_refs, bool) or not isinstance(max_refs, int) or not 1 <= max_refs <= 100:
        invalid.append("max_refs must be between 1 and 100")
    if isinstance(max_files, bool) or not isinstance(max_files, int) or not 1 <= max_files <= 1000:
        invalid.append("max_files must be between 1 and 1000")
    if expected_sha256 is not None and not re.fullmatch(r"[0-9a-fA-F]{64}", str(expected_sha256)):
        invalid.append("expected_sha256 must be a 64-character SHA-256")
    if expected_blob_sha is not None and not SHA_RE.fullmatch(str(expected_blob_sha)):
        invalid.append("expected_blob_sha must be a 40-character Git blob SHA")
    if identity is not None and (not isinstance(identity, str) or not identity.strip()):
        invalid.append("identity must be a non-empty string when supplied")
    if query is not None and (not isinstance(query, str) or not query.strip()):
        invalid.append("query must be a non-empty string when supplied")
    if not any((identity, expected_sha256, expected_blob_sha, query)):
        invalid.append("identity, expected hash, or query is required")
    paths = [expected_path]
    for path in candidate_paths or []:
        if not isinstance(path, str) or not path.strip() or path.startswith("/") or ".." in PurePosixPath(path).parts:
            invalid.append(f"unsafe candidate path: {path!r}")
        elif path not in paths:
            paths.append(path)
    if invalid:
        return {
            "schema_version": SCHEMA_VERSION, "status": "INVALID_INPUT",
            "errors": invalid, "matches": [], "candidates": [],
            "coverage": {"requested_refs": [], "searched_refs": [], "paths_attempted": [], "incomplete_reasons": []},
            "writes_performed": False,
        }

    requested_refs = refs[:max_refs]
    incomplete_reasons = []
    if len(refs) > max_refs:
        incomplete_reasons.append("REF_LIMIT_REACHED")
    resolved_refs = []
    for ref in requested_refs:
        try:
            resolved_refs.append(_resolve_ref(repository, ref, fetch_json))
        except Exception as exc:
            incomplete_reasons.append(f"REF_UNAVAILABLE:{ref}:{_api_error_kind(exc)}")
    searched_refs = []
    paths_attempted = []
    matches = []
    candidates = []
    read_count = 0
    expected_ref = refs[0]

    # Two passes enforce ordering: expected path across refs first, then known alternate paths.
    ordered_attempts = [(resolved, expected_path) for resolved in resolved_refs]
    ordered_attempts += [
        (resolved, path) for resolved in resolved_refs for path in paths[1:]
    ]
    seen = set()
    for resolved, path in ordered_attempts:
        key = (resolved["commit_sha"], path)
        if key in seen:
            continue
        seen.add(key)
        if read_count >= max_files:
            incomplete_reasons.append("FILE_LIMIT_REACHED")
            break
        paths_attempted.append({"ref": resolved["ref"], "commit_sha": resolved["commit_sha"], "path": path})
        if resolved["ref"] not in searched_refs:
            searched_refs.append(resolved["ref"])
        try:
            file = _read_file(repository, resolved["commit_sha"], path, fetch_json)
        except Exception as exc:
            kind = _api_error_kind(exc)
            if kind == "NOT_FOUND":
                continue
            incomplete_reasons.append(f"FILE_UNAVAILABLE:{resolved['ref']}:{path}:{kind}")
            continue
        read_count += 1
        verified = False
        match_kind = None
        matched_field = None
        if expected_sha256 and file["content_sha256"].casefold() == expected_sha256.casefold():
            verified, match_kind = True, "CONTENT_SHA256_MATCH"
        elif expected_blob_sha and file["blob_sha"].casefold() == expected_blob_sha.casefold():
            verified, match_kind = True, "GIT_BLOB_SHA_MATCH"
        elif identity:
            verified, matched_field = _identity_matches(file["raw"], identity)
            if verified:
                match_kind = "STRUCTURED_IDENTITY_MATCH"
        result = {k: v for k, v in file.items() if k != "raw"}
        result.update({
            "ref": resolved["ref"],
            "commit_sha": resolved["commit_sha"],
            "ref_kind": resolved["ref_kind"],
            "expected_ref": expected_ref,
            "expected_path": expected_path,
            "match_kind": match_kind,
            "matched_identity_field": matched_field,
            "verified_identity": verified,
        })
        if verified:
            if resolved["ref_kind"] == "branch":
                try:
                    live_ref = _resolve_ref(repository, resolved["ref"], fetch_json)
                except Exception as exc:
                    incomplete_reasons.append(
                        f"REF_RECHECK_FAILED:{resolved['ref']}:{_api_error_kind(exc)}"
                    )
                    result["ref_stable_at_return"] = False
                    matches.append(result)
                    return {
                        "schema_version": SCHEMA_VERSION, "status": "SEARCH_INCOMPLETE",
                        "matches": matches, "candidates": candidates,
                        "coverage": {
                            "requested_refs": refs, "searched_refs": searched_refs,
                            "paths_attempted": paths_attempted, "files_read": read_count,
                            "incomplete_reasons": incomplete_reasons,
                        },
                        "writes_performed": False, "automatic_relocation_performed": False,
                        "scope_note": "Identity was found at an exact commit, but the branch could not be revalidated after the read.",
                    }
                if live_ref["commit_sha"] != resolved["commit_sha"]:
                    incomplete_reasons.append(f"REF_MOVED_DURING_SEARCH:{resolved['ref']}")
                    result["ref_stable_at_return"] = False
                    matches.append(result)
                    return {
                        "schema_version": SCHEMA_VERSION, "status": "SEARCH_INCOMPLETE",
                        "matches": matches, "candidates": candidates,
                        "coverage": {
                            "requested_refs": refs, "searched_refs": searched_refs,
                            "paths_attempted": paths_attempted, "files_read": read_count,
                            "incomplete_reasons": incomplete_reasons,
                        },
                        "writes_performed": False, "automatic_relocation_performed": False,
                        "scope_note": "Identity was found at an exact historical commit, but the branch moved during discovery.",
                    }
            result["ref_stable_at_return"] = True
            matches.append(result)
            if resolved["ref"] == expected_ref and path == expected_path:
                status = "FOUND_AT_EXPECTED_PATH"
            else:
                status = "FOUND_ELSEWHERE_IDENTITY_MATCH"
            return {
                "schema_version": SCHEMA_VERSION, "status": status,
                "matches": matches, "candidates": candidates,
                "coverage": {
                    "requested_refs": refs, "searched_refs": searched_refs,
                    "paths_attempted": paths_attempted, "files_read": read_count,
                    "incomplete_reasons": incomplete_reasons,
                },
                "writes_performed": False, "automatic_relocation_performed": False,
            }
        if (identity and _query_matches(file["raw"], identity)) or _query_matches(file["raw"], query):
            result["candidate_reason"] = "TEXT_MENTION_ONLY_NOT_IDENTITY_PROOF"
            candidates.append(result)

    status = (
        "SEARCH_INCOMPLETE" if incomplete_reasons else
        "CANDIDATES_UNVERIFIED" if candidates else
        "NOT_FOUND_WITHIN_SEARCH_SCOPE"
    )
    return {
        "schema_version": SCHEMA_VERSION, "status": status,
        "matches": matches, "candidates": candidates,
        "coverage": {
            "requested_refs": refs, "searched_refs": searched_refs,
            "paths_attempted": paths_attempted, "files_read": read_count,
            "incomplete_reasons": incomplete_reasons,
        },
        "writes_performed": False, "automatic_relocation_performed": False,
        "scope_note": "No-match applies only to the configured refs and candidate paths; it is not global absence.",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--expected-path", required=True)
    parser.add_argument("--ref", action="append", required=True, help="expected ref first, then alternate branches/commit SHAs")
    parser.add_argument("--identity")
    parser.add_argument("--expected-sha256")
    parser.add_argument("--expected-blob-sha")
    parser.add_argument("--query")
    parser.add_argument("--candidate-path", action="append", default=[])
    parser.add_argument("--max-refs", type=int, default=20)
    parser.add_argument("--max-files", type=int, default=200)
    args = parser.parse_args(argv)
    result = discover_github_source(
        args.repository, args.expected_path, args.ref, identity=args.identity,
        expected_sha256=args.expected_sha256, expected_blob_sha=args.expected_blob_sha,
        query=args.query, candidate_paths=args.candidate_path,
        max_refs=args.max_refs, max_files=args.max_files,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] in {"FOUND_AT_EXPECTED_PATH", "FOUND_ELSEWHERE_IDENTITY_MATCH", "CANDIDATES_UNVERIFIED", "NOT_FOUND_WITHIN_SEARCH_SCOPE"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
