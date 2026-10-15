import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import continuity_checkpoint_bundle as bundle


class ContinuityCheckpointBundleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.project = Path(self.tmp.name) / "AGENT_MEMORY_SYSTEM"
        self.project.mkdir()
        (self.project / "TASK_STATE.md").write_text(
            "# TASK_STATE\n- Active goal: recoverable checkpoint\n- Next action: test recovery\n",
            encoding="utf-8",
        )
        (self.project / "HANDOFF.md").write_text(
            "# HANDOFF\n- Active goal: recoverable checkpoint\n- Next action: test recovery\n",
            encoding="utf-8",
        )
        (self.project / "events.jsonl").write_text(
            json.dumps({"event_id": "EVT-CHECKPOINT-001", "type": "observation"}) + "\n",
            encoding="utf-8",
        )

    def tearDown(self):
        self.tmp.cleanup()

    def _capture(self, checkpoint_id):
        return bundle.capture(
            self.project,
            checkpoint_id=checkpoint_id,
            summary="checkpoint regression fixture",
            source_head="deadbeef",
            ci_run_id="12345",
        )

    def test_capture_creates_single_commit_pointer_and_verifiable_generation(self):
        result = self._capture("CKPT-TEST-001")
        self.assertEqual(result["status"], "CAPTURED")
        pointer = json.loads((self.project / "CURRENT_CHECKPOINT.json").read_text(encoding="utf-8"))
        self.assertEqual(pointer["checkpoint_id"], "CKPT-TEST-001")
        generation = self.project / pointer["generation_path"]
        self.assertTrue(generation.is_file())
        self.assertEqual(bundle.verify(self.project)["status"], "CURRENT")

    def test_recover_restores_both_projections_after_interruption_after_commit_point(self):
        with mock.patch.object(bundle, "_materialize", side_effect=OSError("simulated interruption")):
            result = self._capture("CKPT-TEST-002")
        self.assertEqual(result["status"], "COMMITTED_PROJECTIONS_PENDING")
        (self.project / "TASK_STATE.md").write_text("partial write", encoding="utf-8")
        (self.project / "HANDOFF.md").write_text("stale handoff", encoding="utf-8")
        recovered = bundle.recover(self.project)
        self.assertEqual(recovered["status"], "RECOVERED")
        self.assertIn("recoverable checkpoint", (self.project / "TASK_STATE.md").read_text(encoding="utf-8"))
        self.assertIn("recoverable checkpoint", (self.project / "HANDOFF.md").read_text(encoding="utf-8"))
        self.assertEqual(bundle.verify(self.project)["status"], "CURRENT")

    def test_exact_checkpoint_replay_is_idempotent(self):
        first = self._capture("CKPT-TEST-006")
        self.assertEqual(first["status"], "CAPTURED")
        replay = self._capture("CKPT-TEST-006")
        self.assertEqual(replay["status"], "ALREADY_CAPTURED")
        self.assertFalse(replay["writes_performed"])

    def test_second_checkpoint_links_to_first_without_rewriting_it(self):
        first = self._capture("CKPT-TEST-003")
        self.assertEqual(first["status"], "CAPTURED")
        first_path = self.project / "checkpoints" / "CKPT-TEST-003.json"
        first_bytes = first_path.read_bytes()
        with (self.project / "TASK_STATE.md").open("a", encoding="utf-8") as stream:
            stream.write("\n- Later verified result: second checkpoint\n")
        with (self.project / "HANDOFF.md").open("a", encoding="utf-8") as stream:
            stream.write("\n- Later verified result: second checkpoint\n")
        second = self._capture("CKPT-TEST-004")
        self.assertEqual(second["status"], "CAPTURED")
        self.assertEqual(first_path.read_bytes(), first_bytes)
        generation = json.loads((self.project / "checkpoints" / "CKPT-TEST-004.json").read_text(encoding="utf-8"))
        self.assertEqual(generation["parent_checkpoint_id"], "CKPT-TEST-003")
        self.assertEqual(bundle.verify(self.project)["chain"], ["CKPT-TEST-003", "CKPT-TEST-004"])

    def test_tampered_generation_fails_closed_before_recovery(self):
        self._capture("CKPT-TEST-005")
        generation_path = self.project / "checkpoints" / "CKPT-TEST-005.json"
        generation_path.write_text(generation_path.read_text(encoding="utf-8").replace("recoverable", "tampered"), encoding="utf-8")
        result = bundle.recover(self.project)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("hash", result["error"])

    def test_missing_checkpoint_pointer_does_not_claim_recovery(self):
        result = bundle.recover(self.project)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("missing", result["error"])


if __name__ == "__main__":
    unittest.main()
