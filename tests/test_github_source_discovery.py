import base64
import json
import sys
import unittest
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from github_source_discovery import discover_github_source
from verified_session_restore import API_ROOT, RemoteEvidenceError


REPO = "example/agent-knowledge-base"
SHA_A = "a" * 40
SHA_B = "b" * 40
SHA_C = "c" * 40


def api_file(raw, blob_sha="d" * 40):
    return {
        "type": "file",
        "sha": blob_sha,
        "size": len(raw),
        "encoding": "base64",
        "content": base64.b64encode(raw).decode("ascii"),
    }


class GithubSourceDiscoveryTests(unittest.TestCase):
    def test_expected_path_identity_match_is_verified_and_ref_rechecked(self):
        raw = json.dumps({"memory_id": "MEM-EXACT-1", "revision_id": "r1"}).encode()
        def fetch(url):
            if url.endswith("/branches/expected"):
                return {"commit": {"sha": SHA_A}}
            if f"/contents/registry/memory_records.jsonl?ref={SHA_A}" in url:
                return api_file(raw)
            raise RemoteEvidenceError("HTTP Error 404: Not Found")
        result = discover_github_source(
            REPO, "registry/memory_records.jsonl", ["expected"],
            identity="MEM-EXACT-1", fetch_json=fetch,
        )
        self.assertEqual(result["status"], "FOUND_AT_EXPECTED_PATH")
        self.assertEqual(result["matches"][0]["commit_sha"], SHA_A)
        self.assertEqual(result["matches"][0]["matched_identity_field"], "memory_id")
        self.assertTrue(result["matches"][0]["ref_stable_at_return"])
        self.assertFalse(result["writes_performed"])

    def test_expected_path_miss_finds_identity_in_alternate_ref_and_path(self):
        raw = (json.dumps({"source_record_id": "SRC-ALTERNATE-1"}) + "\n").encode()
        def fetch(url):
            if url.endswith("/branches/expected"):
                return {"commit": {"sha": SHA_A}}
            if url.endswith("/branches/alternate"):
                return {"commit": {"sha": SHA_B}}
            if f"?ref={SHA_A}" in url or f"/contents/registry/memory_records.jsonl?ref={SHA_B}" in url:
                raise RemoteEvidenceError("HTTP Error 404: Not Found")
            if f"/contents/projects/AGENT_MEMORY_SYSTEM/events.jsonl?ref={SHA_B}" in url:
                return api_file(raw, "e" * 40)
            raise RemoteEvidenceError("HTTP Error 404: Not Found")
        result = discover_github_source(
            REPO, "registry/memory_records.jsonl", ["expected", "alternate"],
            identity="SRC-ALTERNATE-1",
            candidate_paths=["projects/AGENT_MEMORY_SYSTEM/events.jsonl"],
            fetch_json=fetch,
        )
        self.assertEqual(result["status"], "FOUND_ELSEWHERE_IDENTITY_MATCH")
        match = result["matches"][0]
        self.assertEqual(match["ref"], "alternate")
        self.assertEqual(match["path"], "projects/AGENT_MEMORY_SYSTEM/events.jsonl")
        self.assertEqual(match["blob_sha"], "e" * 40)
        self.assertEqual(match["matched_identity_field"], "source_record_id")

    def test_text_mention_is_only_unverified_candidate(self):
        raw = b'{"summary":"a prose mention of SRC-ONLY-TEXT"}\n'
        def fetch(url):
            if url.endswith("/branches/expected"):
                return {"commit": {"sha": SHA_A}}
            if f"/contents/registry/memory_records.jsonl?ref={SHA_A}" in url:
                raise RemoteEvidenceError("HTTP Error 404: Not Found")
            if f"/contents/projects/AGENT_MEMORY_SYSTEM/events.jsonl?ref={SHA_A}" in url:
                return api_file(raw)
            raise RemoteEvidenceError("HTTP Error 404: Not Found")
        result = discover_github_source(
            REPO, "registry/memory_records.jsonl", ["expected"],
            identity="SRC-ONLY-TEXT",
            candidate_paths=["projects/AGENT_MEMORY_SYSTEM/events.jsonl"],
            fetch_json=fetch,
        )
        self.assertEqual(result["status"], "CANDIDATES_UNVERIFIED")
        self.assertEqual(result["candidates"][0]["candidate_reason"], "TEXT_MENTION_ONLY_NOT_IDENTITY_PROOF")
        self.assertEqual(result["matches"], [])

    def test_access_denied_marks_search_incomplete_not_absent(self):
        def fetch(url):
            if url.endswith("/branches/expected"):
                return {"commit": {"sha": SHA_A}}
            if url.endswith("/branches/private"):
                raise RemoteEvidenceError("HTTP Error 403: Forbidden")
            raise RemoteEvidenceError("HTTP Error 404: Not Found")
        result = discover_github_source(
            REPO, "registry/memory_records.jsonl", ["expected", "private"],
            identity="MEM-NOT-FOUND", fetch_json=fetch,
        )
        self.assertEqual(result["status"], "SEARCH_INCOMPLETE")
        self.assertTrue(any("ACCESS_DENIED" in reason for reason in result["coverage"]["incomplete_reasons"]))
        self.assertIn("not global absence", result["scope_note"])

    def test_branch_movement_during_search_returns_incomplete_with_exact_commit_evidence(self):
        raw = b'{"event_id":"EVT-STALE-REF-1"}\n'
        branch_calls = 0
        def fetch(url):
            nonlocal branch_calls
            if url.endswith("/branches/expected"):
                branch_calls += 1
                return {"commit": {"sha": SHA_A if branch_calls == 1 else SHA_C}}
            if f"/contents/registry/memory_records.jsonl?ref={SHA_A}" in url:
                return api_file(raw)
            raise RemoteEvidenceError("HTTP Error 404: Not Found")
        result = discover_github_source(
            REPO, "registry/memory_records.jsonl", ["expected"],
            identity="EVT-STALE-REF-1", fetch_json=fetch,
        )
        self.assertEqual(result["status"], "SEARCH_INCOMPLETE")
        self.assertEqual(result["matches"][0]["commit_sha"], SHA_A)
        self.assertIn("REF_MOVED_DURING_SEARCH:expected", result["coverage"]["incomplete_reasons"])

    def test_invalid_ref_and_path_are_rejected(self):
        result = discover_github_source(
            REPO, "../secrets.json", ["../main"], identity="MEM-1",
            fetch_json=lambda _: {},
        )
        self.assertEqual(result["status"], "INVALID_INPUT")
        self.assertFalse(result["writes_performed"])


if __name__ == "__main__":
    unittest.main()
