#!/usr/bin/env python3
"""Verify remote GitHub revision evidence, then build a source-backed restore packet.

This read-only orchestration entry point fetches the target branch HEAD and the
recorded GitHub Actions run independently, then compares the branch with the
recorded code SHA. Only known metadata-only descendants are accepted without a
new code CI result.
"""
from __future__ import annotations

import argparse
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable

from restore_session_packet import build_session_packet

API_ROOT = "https://api.github.com"
SHA_RE = re.compile(r"^[0-9a-fA-F]{40}$")
METADATA_ONLY_PATHS = {
    "projects/AGENT_MEMORY_SYSTEM/CONTINUITY_CHECKPOINT.json",
    "projects/AGENT_MEMORY_SYSTEM/TASK_STATE.md",
    "projects/AGENT_MEMORY_SYSTEM/HANDOFF.md",
    "projects/AGENT_MEMORY_SYSTEM/events.jsonl",
}

EVENT_RECORD_PATH_RE = re.compile(
    r"^projects/AGENT_MEMORY_SYSTEM/events/EVT-AGMS-[0-9]{8}-[0-9]{3}-[A-Z0-9_-]+\.md$"
)


def _is_metadata_only_path(path: str) -> bool:
    """Allow only explicitly listed state files and well-formed append-only event records."""
    return path in METADATA_ONLY_PATHS or EVENT_RECORD_PATH_RE.fullmatch(path) is not None



class RemoteEvidenceError(RuntimeError):
    """Raised when live remote evidence is missing, inconsistent, or unsafe."""


def request_json(url: str, timeout: int = 15) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "agent-knowledge-base-session-restore",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise RemoteEvidenceError(f"GitHub API request failed for {url}: {exc}") from exc
    if not isinstance(payload, dict):
        raise RemoteEvidenceError(f"GitHub API returned a non-object response for {url}")
    return payload


def _sha(value: Any, field: str) -> str:
    if not isinstance(value, str) or not SHA_RE.fullmatch(value):
        raise RemoteEvidenceError(f"API/checkpoint field {field} is not a full 40-character SHA")
    return value.lower()


def verify_remote_revision(
    project_dir: Path,
    repository: str,
    ref: str | None = None,
    *,
    fetch_json: Callable[[str], dict[str, Any]] = request_json,
) -> dict[str, Any]:
    """Verify the live branch, exact-head CI run, and code-vs-metadata delta."""
    checkpoint_path = Path(project_dir) / "CONTINUITY_CHECKPOINT.json"
    try:
        checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RemoteEvidenceError("CONTINUITY_CHECKPOINT.json is missing") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise RemoteEvidenceError(f"Cannot read checkpoint JSON: {exc}") from exc
    if not isinstance(checkpoint, dict) or not isinstance(checkpoint.get("repository_state"), dict):
        raise RemoteEvidenceError("Checkpoint repository_state is missing or invalid")

    state = checkpoint["repository_state"]
    recorded_sha = _sha(state.get("last_verified_code_head"), "last_verified_code_head")
    run_id = state.get("exact_head_ci_run_id")
    if isinstance(run_id, bool) or not isinstance(run_id, (str, int)) or not str(run_id).isdigit():
        raise RemoteEvidenceError("Checkpoint exact_head_ci_run_id is missing or invalid")
    if state.get("exact_head_ci_conclusion") != "success":
        raise RemoteEvidenceError("Checkpoint does not record a successful exact-head CI conclusion")

    selected_ref = ref or checkpoint.get("branch")
    if not isinstance(selected_ref, str) or not selected_ref.strip():
        raise RemoteEvidenceError("Branch ref is missing; supply --ref or record checkpoint.branch")
    if not re.fullmatch(r"[A-Za-z0-9._/-]+", selected_ref) or ".." in selected_ref:
        raise RemoteEvidenceError("Branch ref contains unsupported characters")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise RemoteEvidenceError("Repository must be owner/repository")

    prefix = f"{API_ROOT}/repos/{repository}"
    encoded_ref = urllib.parse.quote(selected_ref, safe="")
    branch_data = fetch_json(f"{prefix}/branches/{encoded_ref}")
    branch_commit = branch_data.get("commit")
    if not isinstance(branch_commit, dict):
        raise RemoteEvidenceError("GitHub branch response has no commit object")
    live_sha = _sha(branch_commit.get("sha"), "branch.commit.sha")

    run_data = fetch_json(f"{prefix}/actions/runs/{run_id}")
    run_sha = _sha(run_data.get("head_sha"), "workflow_run.head_sha")
    if run_sha != recorded_sha:
        raise RemoteEvidenceError(
            f"CI run {run_id} belongs to {run_sha}, not recorded code SHA {recorded_sha}"
        )
    if run_data.get("status") != "completed" or run_data.get("conclusion") != "success":
        raise RemoteEvidenceError(
            f"Exact-head CI run {run_id} is not completed successfully "
            f"(status={run_data.get('status')!r}, conclusion={run_data.get('conclusion')!r})"
        )

    compare = fetch_json(f"{prefix}/compare/{recorded_sha}...{live_sha}")
    merge_base = compare.get("merge_base_commit")
    merge_base_sha = merge_base.get("sha") if isinstance(merge_base, dict) else None
    compare_status = compare.get("status")
    files = compare.get("files")
    if not isinstance(files, list):
        raise RemoteEvidenceError("GitHub compare response has no complete files list")
    if len(files) >= 300:
        raise RemoteEvidenceError("Compare file list may be truncated; refusing to infer unchanged code")
    changed_paths = sorted(
        item.get("filename") for item in files
        if isinstance(item, dict) and isinstance(item.get("filename"), str)
    )
    if len(changed_paths) != len(files):
        raise RemoteEvidenceError("Compare response contains malformed changed-file entries")

    if live_sha == recorded_sha:
        if compare_status != "identical" or changed_paths:
            raise RemoteEvidenceError("GitHub compare response conflicts with identical branch/code SHA")
        revision_status = "REMOTE_VERIFIED_EXACT_CODE_HEAD"
    else:
        if compare_status != "ahead" or merge_base_sha != recorded_sha:
            raise RemoteEvidenceError(
                "Current branch is not a clean descendant of the recorded code SHA "
                f"(status={compare_status!r}, merge_base={merge_base_sha!r})"
            )
        unexpected = [path for path in changed_paths if not _is_metadata_only_path(path)]
        if unexpected:
            return {
                "status": "CODE_REVISION_DRIFT", "repository": repository, "ref": selected_ref,
                "live_branch_head": live_sha, "recorded_code_head": recorded_sha,
                "recorded_ci_run_id": str(run_id), "ci_head_sha": run_sha,
                "ci_status": run_data.get("status"), "ci_conclusion": run_data.get("conclusion"),
                "compare_status": compare_status, "changed_paths": changed_paths,
                "unexpected_changed_paths": unexpected, "writes_performed": False,
                "reason": "Source/code paths changed after the recorded code SHA; a new exact-head CI result is required.",
            }
        revision_status = "REMOTE_VERIFIED_METADATA_ONLY_AHEAD"

    return {
        "status": revision_status, "repository": repository, "ref": selected_ref,
        "live_branch_head": live_sha, "recorded_code_head": recorded_sha,
        "recorded_ci_run_id": str(run_id), "ci_head_sha": run_sha,
        "ci_status": run_data.get("status"), "ci_conclusion": run_data.get("conclusion"),
        "compare_status": compare_status, "changed_paths": changed_paths,
        "unexpected_changed_paths": [], "writes_performed": False,
    }


def build_verified_session_packet(
    task_state: Path, handoff: Path, event_log: Path, repository: str, ref: str | None = None,
    *, fetch_json: Callable[[str], dict[str, Any]] = request_json, max_chars: int = 12000,
) -> dict[str, Any]:
    try:
        remote = verify_remote_revision(Path(task_state).parent, repository, ref, fetch_json=fetch_json)
    except RemoteEvidenceError as exc:
        return {
            "status": "REVISION_CHECK_BLOCKED", "reason": str(exc),
            "repository_revision_evidence": {
                "status": "REMOTE_EVIDENCE_UNAVAILABLE", "reason": str(exc), "writes_performed": False
            },
            "writes_performed": False,
        }
    if remote["status"] == "CODE_REVISION_DRIFT":
        return {
            "status": "REVISION_CHECK_BLOCKED", "reason": remote["reason"],
            "repository_revision_evidence": remote, "writes_performed": False,
        }

    # Pass only the recorded code SHA whose exact CI run and unchanged-code
    # ancestry were independently checked. Keep the live branch tip separate.
    packet = build_session_packet(
        task_state, handoff, event_log, max_chars=max_chars,
        observed_code_head=remote["recorded_code_head"],
        observed_ci_run_id=remote["recorded_ci_run_id"],
    )
    packet["remote_repository_evidence"] = remote
    packet["repository_revision_evidence"]["verification_method"] = (
        "live GitHub branch + compare + exact workflow-run API"
    )
    packet["repository_revision_evidence"]["live_branch_head"] = remote["live_branch_head"]
    packet["repository_revision_evidence"]["recorded_code_head_is_current"] = True
    return packet


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task_state", type=Path)
    parser.add_argument("handoff", type=Path)
    parser.add_argument("event_log", type=Path)
    parser.add_argument("--repository", required=True, help="GitHub owner/repository")
    parser.add_argument("--ref", help="Branch to verify; defaults to checkpoint.branch")
    parser.add_argument("--max-chars", type=int, default=12000)
    args = parser.parse_args(argv)
    packet = build_verified_session_packet(
        args.task_state, args.handoff, args.event_log,
        args.repository, args.ref, max_chars=args.max_chars,
    )
    print(json.dumps(packet, ensure_ascii=False, indent=2))
    return 0 if packet.get("status") == "RESTORED_PACKET" else 2


if __name__ == "__main__":
    raise SystemExit(main())
