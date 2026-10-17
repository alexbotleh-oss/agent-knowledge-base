import hashlib
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from resumable_archive_pipeline import run_archive_pipeline


def _conversation(cid: str, mid: str, text: str, timestamp: int) -> dict:
    node_id = f"NODE-{cid}"
    return {
        "id": cid,
        "title": f"synthetic {cid}",
        "mapping": {
            node_id: {
                "parent": None,
                "children": [],
                "message": {
                    "id": mid,
                    "create_time": timestamp,
                    "author": {"role": "user"},
                    "content": {"content_type": "text", "parts": [text]},
                    "metadata": {},
                },
            }
        },
    }


def _write_zip(path: Path, payload: bytes) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("conversations.json", payload)


class ResumableArchivePipelineTests(unittest.TestCase):
    def _source(self, root: Path) -> tuple[Path, list[dict]]:
        source = root / "export.zip"
        conversations = [
            _conversation("CONV-001", "MSG-001", "synthetic first", 1790000000),
            _conversation("CONV-002", "MSG-002", "synthetic second", 1790000001),
        ]
        _write_zip(source, json.dumps(conversations, ensure_ascii=False).encode("utf-8"))
        return source, conversations

    def _run(self, source: Path, root: Path, *, apply: bool = False,
             stop_after_batches: int | None = None) -> dict:
        return run_archive_pipeline(
            source,
            root / "work",
            "ARCHIVE-PIPELINE-TEST",
            registry_path=root / "registry" / "source_records.jsonl",
            batch_size=1,
            apply=apply,
            stop_after_batches=stop_after_batches,
        )

    def test_pause_blocks_downstream_until_raw_import_completes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, _ = self._source(root)

            paused = self._run(source, root, stop_after_batches=1)

            self.assertEqual(paused["status"], "RAW_IMPORT_INCOMPLETE")
            self.assertFalse(paused["downstream_started"])
            self.assertEqual(paused["raw_import"]["status"], "PAUSED")
            self.assertFalse((root / "work" / "staging" / "archive_snapshot.json").exists())
            self.assertFalse((root / "registry" / "source_records.jsonl").exists())

    def test_resume_runs_all_stages_from_the_immutable_snapshot_and_replay_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, conversations = self._source(root)
            original_hash = hashlib.sha256(source.read_bytes()).hexdigest()

            paused = self._run(source, root, stop_after_batches=1)
            self.assertEqual(paused["status"], "RAW_IMPORT_INCOMPLETE")

            dry_run = self._run(source, root)
            self.assertEqual(dry_run["status"], "READY_FOR_SOURCE_REGISTRATION")
            self.assertEqual(dry_run["raw_import"]["status"], "RAW_COMPLETE")
            self.assertEqual(dry_run["raw_import"]["source_sha256"], original_hash)
            self.assertEqual(dry_run["staging"]["raw_sha256"], original_hash)
            self.assertEqual(dry_run["staging"]["source_record_count"], len(conversations))
            self.assertFalse(dry_run["source_ingestion"]["writes_performed"])
            registry = root / "registry" / "source_records.jsonl"
            self.assertFalse(registry.exists())

            applied = self._run(source, root, apply=True)
            self.assertEqual(applied["status"], "SOURCE_REGISTERED_DOWNSTREAM_PENDING")
            self.assertEqual(applied["source_ingestion"]["registration_status"], "APPENDED")
            registry_bytes = registry.read_bytes()

            replayed = self._run(source, root, apply=True)
            self.assertEqual(replayed["status"], "SOURCE_REGISTERED_DOWNSTREAM_PENDING")
            self.assertEqual(replayed["source_ingestion"]["registration_status"], "ALREADY_REGISTERED")
            self.assertEqual(registry.read_bytes(), registry_bytes)
            self.assertEqual(replayed["semantic_promotion"], "NOT_IMPLEMENTED")
            self.assertEqual(replayed["canonical_index_refresh"], "NOT_IMPLEMENTED")
            self.assertEqual(replayed["next_session_restore"], "NOT_VERIFIED")

    def test_truncated_source_stops_before_staging_and_corrected_snapshot_can_resume_as_new_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "export.zip"
            _write_zip(source, b'[{"id":"CONV-BROKEN","mapping":')
            broken_hash = hashlib.sha256(source.read_bytes()).hexdigest()

            failed = self._run(source, root)
            self.assertEqual(failed["status"], "RAW_IMPORT_FAILED")
            self.assertFalse(failed["downstream_started"])
            self.assertFalse((root / "work" / "staging" / "archive_snapshot.json").exists())
            self.assertFalse((root / "registry" / "source_records.jsonl").exists())

            valid = [
                _conversation("CONV-RECOVERED", "MSG-RECOVERED", "synthetic recovered", 1790000002)
            ]
            _write_zip(source, json.dumps(valid, ensure_ascii=False).encode("utf-8"))
            recovered_hash = hashlib.sha256(source.read_bytes()).hexdigest()
            self.assertNotEqual(broken_hash, recovered_hash)

            recovered = self._run(source, root)
            self.assertEqual(recovered["status"], "READY_FOR_SOURCE_REGISTRATION")
            self.assertEqual(recovered["raw_import"]["source_sha256"], recovered_hash)
            self.assertEqual(recovered["staging"]["raw_sha256"], recovered_hash)
            self.assertTrue(recovered["downstream_started"])


if __name__ == "__main__":
    unittest.main()
