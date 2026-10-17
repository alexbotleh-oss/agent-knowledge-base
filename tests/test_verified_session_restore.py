import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from verified_session_restore import RemoteEvidenceError, build_verified_session_packet, verify_remote_revision

REPO = "example/memory"
RECORDED = "a" * 40
LIVE = "b" * 40
RUN_ID = 12345
BRANCH = "integration/test"
BRANCH_API = "integration%2Ftest"


class VerifiedSessionRestoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.project = Path(self.tmp.name) / "AGENT_MEMORY_SYSTEM"
        self.project.mkdir()
        (self.project / "CONTINUITY_CHECKPOINT.json").write_text(json.dumps({
            "branch": BRANCH,
            "repository_state": {
                "last_verified_code_head": RECORDED,
                "exact_head_ci_run_id": RUN_ID,
                "exact_head_ci_conclusion": "success",
            },
            "historical_repository_state": {"last_verified_code_head": "c" * 40},
        }), encoding="utf-8")
        (self.project / "TASK_STATE.md").write_text(
            "# TASK_STATE\nGoal: test restore\nEvidence: EVT-TEST-001\n", encoding="utf-8"
        )
        (self.project / "HANDOFF.md").write_text(
            "# HANDOFF\nNext: continue test restore\n", encoding="utf-8"
        )
        (self.project / "events.jsonl").write_text(
            json.dumps({"event_id": "EVT-TEST-001", "summary": "test event"}) + "\n",
            encoding="utf-8",
        )
        self.base_url = f"https://api.github.com/repos/{REPO}"
        self.responses = {
            f"{self.base_url}/branches/{BRANCH_API}": {"commit": {"sha": LIVE}},
            f"{self.base_url}/actions/runs/{RUN_ID}": {
                "head_sha": RECORDED, "status": "completed", "conclusion": "success"
            },
            f"{self.base_url}/compare/{RECORDED}...{LIVE}": {
                "status": "ahead", "merge_base_commit": {"sha": RECORDED},
                "files": [{"filename": "projects/AGENT_MEMORY_SYSTEM/HANDOFF.md"}],
            },
        }

    def tearDown(self):
        self.tmp.cleanup()

    def fake_fetch(self, url):
        if url not in self.responses:
            raise AssertionError(f"Unexpected API request: {url}")
        return self.responses[url]

    def test_metadata_only_descendant_is_verified_and_restore_includes_live_head(self):
        evidence = verify_remote_revision(self.project, REPO, fetch_json=self.fake_fetch)
        self.assertEqual(evidence["status"], "REMOTE_VERIFIED_METADATA_ONLY_AHEAD")
        self.assertEqual(evidence["live_branch_head"], LIVE)
        self.assertEqual(evidence["recorded_code_head"], RECORDED)
        packet = build_verified_session_packet(
            self.project / "TASK_STATE.md", self.project / "HANDOFF.md",
            self.project / "events.jsonl", REPO, fetch_json=self.fake_fetch,
        )
        self.assertEqual(packet["status"], "RESTORED_PACKET")
        self.assertEqual(packet["repository_revision_evidence"]["status"], "OBSERVED_CODE_AND_CI_MATCH")
        self.assertEqual(packet["repository_revision_evidence"]["live_branch_head"], LIVE)
        self.assertEqual(packet["remote_repository_evidence"]["status"], "REMOTE_VERIFIED_METADATA_ONLY_AHEAD")
        self.assertFalse(packet["writes_performed"])

    def test_well_formed_event_records_are_metadata_only_but_unrelated_files_are_not(self):
        compare_url = f"{self.base_url}/compare/{RECORDED}...{LIVE}"
        event_path = (
            "projects/AGENT_MEMORY_SYSTEM/events/"
            "EVT-AGMS-20261017-015-PRE_ACTION.md"
        )
        self.responses[compare_url]["files"] = [{"filename": event_path}]
        evidence = verify_remote_revision(self.project, REPO, fetch_json=self.fake_fetch)
        self.assertEqual(evidence["status"], "REMOTE_VERIFIED_METADATA_ONLY_AHEAD")
        self.assertEqual(evidence["changed_paths"], [event_path])
        self.assertEqual(evidence["unexpected_changed_paths"], [])

        unrelated_path = "projects/AGENT_MEMORY_SYSTEM/events/README.md"
        self.responses[compare_url]["files"] = [{"filename": unrelated_path}]
        evidence = verify_remote_revision(self.project, REPO, fetch_json=self.fake_fetch)
        self.assertEqual(evidence["status"], "CODE_REVISION_DRIFT")
        self.assertEqual(evidence["unexpected_changed_paths"], [unrelated_path])

    def test_exact_code_head_is_verified(self):
        self.responses[f"{self.base_url}/branches/{BRANCH_API}"] = {"commit": {"sha": RECORDED}}
        self.responses[f"{self.base_url}/compare/{RECORDED}...{RECORDED}"] = {
            "status": "identical", "merge_base_commit": {"sha": RECORDED}, "files": []
        }
        evidence = verify_remote_revision(self.project, REPO, fetch_json=self.fake_fetch)
        self.assertEqual(evidence["status"], "REMOTE_VERIFIED_EXACT_CODE_HEAD")

    def test_failed_or_wrong_head_ci_is_rejected(self):
        self.responses[f"{self.base_url}/actions/runs/{RUN_ID}"]["head_sha"] = "d" * 40
        with self.assertRaisesRegex(RemoteEvidenceError, "belongs to"):
            verify_remote_revision(self.project, REPO, fetch_json=self.fake_fetch)
        self.responses[f"{self.base_url}/actions/runs/{RUN_ID}"]["head_sha"] = RECORDED
        self.responses[f"{self.base_url}/actions/runs/{RUN_ID}"]["conclusion"] = "failure"
        with self.assertRaisesRegex(RemoteEvidenceError, "not completed successfully"):
            verify_remote_revision(self.project, REPO, fetch_json=self.fake_fetch)

    def test_unexpected_source_change_fails_closed(self):
        self.responses[f"{self.base_url}/compare/{RECORDED}...{LIVE}"]["files"].append(
            {"filename": "tools/restore_session_packet.py"}
        )
        evidence = verify_remote_revision(self.project, REPO, fetch_json=self.fake_fetch)
        self.assertEqual(evidence["status"], "CODE_REVISION_DRIFT")
        self.assertEqual(evidence["unexpected_changed_paths"], ["tools/restore_session_packet.py"])
        packet = build_verified_session_packet(
            self.project / "TASK_STATE.md", self.project / "HANDOFF.md",
            self.project / "events.jsonl", REPO, fetch_json=self.fake_fetch,
        )
        self.assertEqual(packet["status"], "REVISION_CHECK_BLOCKED")
        self.assertFalse(packet["writes_performed"])

    def test_non_descendant_or_truncated_compare_is_rejected(self):
        compare_url = f"{self.base_url}/compare/{RECORDED}...{LIVE}"
        self.responses[compare_url]["status"] = "diverged"
        with self.assertRaisesRegex(RemoteEvidenceError, "not a clean descendant"):
            verify_remote_revision(self.project, REPO, fetch_json=self.fake_fetch)
        self.responses[compare_url]["status"] = "ahead"
        self.responses[compare_url]["files"] = [{"filename": f"file-{i}.py"} for i in range(300)]
        with self.assertRaisesRegex(RemoteEvidenceError, "truncated"):
            verify_remote_revision(self.project, REPO, fetch_json=self.fake_fetch)

    def test_missing_checkpoint_is_blocked_without_writes(self):
        (self.project / "CONTINUITY_CHECKPOINT.json").unlink()
        packet = build_verified_session_packet(
            self.project / "TASK_STATE.md", self.project / "HANDOFF.md",
            self.project / "events.jsonl", REPO, fetch_json=self.fake_fetch,
        )
        self.assertEqual(packet["status"], "REVISION_CHECK_BLOCKED")
        self.assertFalse(packet["writes_performed"])


if __name__ == "__main__":
    unittest.main()
