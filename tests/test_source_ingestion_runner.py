import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from archive_registry_staging import build as build_staging
from source_ingestion_runner import _load_events, run_ingestion


class ResumableSourceIngestionRunnerTests(unittest.TestCase):
    def _snapshot(self, root: Path) -> Path:
        source = root / "conversations.json"
        source.write_text(json.dumps([{
            "id": "conversation-run-1",
            "mapping": {
                "node-1": {
                    "parent": None, "children": [],
                    "message": {
                        "id": "message-run-1", "create_time": 1790000000,
                        "author": {"role": "user"},
                        "content": {"content_type": "text", "parts": ["private source text"]},
                        "metadata": {},
                    },
                },
            },
        }]), encoding="utf-8")
        staging = root / "staging"
        build_staging(source, staging, "ARCHIVE-RUNNER-001")
        return staging / "archive_snapshot.json"

    def test_dry_run_persists_hash_chained_state_without_registry_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            snapshot = self._snapshot(root)
            registry = root / "registry" / "source_records.jsonl"
            result = run_ingestion(snapshot, root / "runs", intake_root=root / "intake",
                                   registry_path=registry, apply=False)
            self.assertEqual(result["status"], "READY_FOR_SOURCE_REGISTRATION")
            self.assertFalse(result["writes_performed"] is True and registry.exists())
            self.assertFalse(registry.exists())
            events = _load_events(Path(result["event_ledger_path"]))
            self.assertEqual([event["sequence"] for event in events], list(range(1, len(events) + 1)))
            self.assertEqual(events[-1]["status"], "READY_FOR_SOURCE_REGISTRATION")
            state = json.loads(Path(result["run_state_path"]).read_text(encoding="utf-8"))
            self.assertEqual(state["latest_event_sha256"], events[-1]["event_sha256"])
            self.assertEqual(state["downstream"], "NOT_IMPLEMENTED_BY_THIS_RUNNER")

    def test_apply_and_replay_stop_at_source_registered_downstream_pending(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            snapshot = self._snapshot(root)
            registry = root / "registry" / "source_records.jsonl"
            kwargs = dict(run_root=root / "runs", intake_root=root / "intake",
                          registry_path=registry, apply=True)
            first = run_ingestion(snapshot, **kwargs)
            self.assertEqual(first["status"], "SOURCE_REGISTERED_DOWNSTREAM_PENDING")
            self.assertEqual(first["registration_status"], "APPENDED")
            first_bytes = registry.read_bytes()
            second = run_ingestion(snapshot, **kwargs)
            self.assertEqual(second["status"], "SOURCE_REGISTERED_DOWNSTREAM_PENDING")
            self.assertEqual(second["registration_status"], "ALREADY_REGISTERED")
            self.assertEqual(registry.read_bytes(), first_bytes)
            events = _load_events(Path(second["event_ledger_path"]))
            self.assertEqual(events[-1]["details"]["semantic_promotion"], "NOT_IMPLEMENTED")
            self.assertEqual(events[-1]["details"]["canonical_index_refresh"], "NOT_IMPLEMENTED")
            self.assertEqual(events[-1]["details"]["next_session_restore"], "NOT_VERIFIED")

    def test_crash_after_registry_commit_resumes_via_idempotent_reconciliation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            snapshot = self._snapshot(root)
            run_root, intake_root = root / "runs", root / "intake"
            registry = root / "registry" / "source_records.jsonl"
            script = r'''
import os, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import source_ingestion_runner as runner
original = runner.append_source_records
def commit_then_crash(*args, **kwargs):
    result = original(*args, **kwargs)
    if kwargs.get("apply") and result.get("status") == "APPENDED":
        os._exit(73)
    return result
runner.append_source_records = commit_then_crash
runner.run_ingestion(Path(sys.argv[2]), Path(sys.argv[3]), intake_root=Path(sys.argv[4]), registry_path=Path(sys.argv[5]), apply=True)
'''
            crashed = subprocess.run(
                [sys.executable, "-c", script, str(TOOLS), str(snapshot), str(run_root),
                 str(intake_root), str(registry)],
                capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(crashed.returncode, 73, crashed.stderr)
            self.assertTrue(registry.is_file())
            rows_before = registry.read_bytes()
            resumed = run_ingestion(snapshot, run_root, intake_root=intake_root,
                                    registry_path=registry, apply=True)
            self.assertEqual(resumed["status"], "SOURCE_REGISTERED_DOWNSTREAM_PENDING")
            self.assertEqual(resumed["registration_status"], "ALREADY_REGISTERED")
            self.assertEqual(registry.read_bytes(), rows_before)
            events = _load_events(Path(resumed["event_ledger_path"]))
            self.assertEqual(events[-1]["status"], "SOURCE_REGISTERED_DOWNSTREAM_PENDING")
            self.assertTrue(Path(resumed["run_state_path"]).is_file())

    def test_missing_state_projection_is_rebuilt_from_event_ledger(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            snapshot = self._snapshot(root)
            registry = root / "registry" / "source_records.jsonl"
            kwargs = dict(run_root=root / "runs", intake_root=root / "intake",
                          registry_path=registry, apply=False)
            first = run_ingestion(snapshot, **kwargs)
            state_path = Path(first["run_state_path"])
            state_path.unlink()

            resumed = run_ingestion(snapshot, **kwargs)
            self.assertEqual(resumed["status"], "READY_FOR_SOURCE_REGISTRATION")
            self.assertTrue(state_path.is_file())
            events = _load_events(Path(resumed["event_ledger_path"]))
            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(state["latest_event_sha256"], events[-1]["event_sha256"])
            self.assertEqual(state["latest_sequence"], events[-1]["sequence"])
            self.assertFalse(registry.exists())

    def test_tampered_run_ledger_blocks_before_registry_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            snapshot = self._snapshot(root)
            registry = root / "registry" / "source_records.jsonl"
            first = run_ingestion(snapshot, root / "runs", intake_root=root / "intake",
                                  registry_path=registry, apply=False)
            ledger = Path(first["event_ledger_path"])
            lines = ledger.read_text(encoding="utf-8").splitlines()
            event = json.loads(lines[0])
            event["status"] = "FORGED"
            lines[0] = json.dumps(event)
            ledger.write_text("\n".join(lines) + "\n", encoding="utf-8")
            resumed = run_ingestion(snapshot, root / "runs", intake_root=root / "intake",
                                    registry_path=registry, apply=True)
            self.assertEqual(resumed["status"], "BLOCKED")
            self.assertIn("hash mismatch", resumed["error"])
            self.assertFalse(registry.exists())


if __name__ == "__main__":
    unittest.main()
