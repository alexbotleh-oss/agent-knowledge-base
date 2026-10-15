import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from adapt_archive_staging_to_intake import adapt_archive_staging_to_intake
from archive_registry_staging import build as build_staging
from source_evidence_registry import append_source_records


class SourceIngestionWriteContractTests(unittest.TestCase):
    def _make_staging(self, root: Path) -> Path:
        source = root / "conversations.json"
        source.write_text(json.dumps([{
            "id": "conversation-1",
            "title": "PRIVATE CONVERSATION TITLE",
            "mapping": {
                "node-1": {
                    "parent": None,
                    "children": [],
                    "message": {
                        "id": "message-1",
                        "create_time": 1790000000,
                        "author": {"role": "user", "name": "PRIVATE AUTHOR"},
                        "content": {"content_type": "text", "parts": ["PRIVATE MESSAGE TEXT"]},
                        "metadata": {},
                    },
                },
            },
        }]), encoding="utf-8")
        staging_root = root / "staging"
        build_staging(source, staging_root, "ARCHIVE-CONTRACT-001")
        return staging_root / "archive_snapshot.json"

    def test_adapter_publishes_metadata_only_batch_and_exact_replay_is_noop(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            snapshot = self._make_staging(root)
            output = root / "intake"
            first = adapt_archive_staging_to_intake(snapshot, output)
            self.assertEqual(first["status"], "ADAPTED")
            batch_dir = Path(first["manifest_path"]).parent
            manifest = json.loads(Path(first["manifest_path"]).read_text(encoding="utf-8"))
            records_bytes = (batch_dir / "source_records.jsonl").read_bytes()
            self.assertEqual(manifest["source"]["project_id"], "unknown")
            self.assertNotIn(b"PRIVATE MESSAGE TEXT", records_bytes)
            self.assertNotIn(b"PRIVATE CONVERSATION TITLE", records_bytes)
            self.assertNotIn(b"PRIVATE AUTHOR", records_bytes)
            self.assertEqual(manifest["artifacts"][0]["record_count"], 1)

            replay = adapt_archive_staging_to_intake(snapshot, output)
            self.assertEqual(replay["status"], "ALREADY_ADAPTED")
            self.assertFalse(replay["writes_performed"])
            self.assertEqual((batch_dir / "source_records.jsonl").read_bytes(), records_bytes)

    def test_adapter_rejects_tampered_staging_records_before_publication(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            snapshot = self._make_staging(root)
            metadata = json.loads(snapshot.read_text(encoding="utf-8"))
            records = snapshot.parent / metadata["records_file"]
            records.write_bytes(records.read_bytes() + b"{}\n")
            with self.assertRaisesRegex(ValueError, "records_sha256 mismatch"):
                adapt_archive_staging_to_intake(snapshot, root / "intake")
            self.assertFalse((root / "intake").exists())

    def test_registry_dry_run_apply_and_replay_preserve_single_revision(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            snapshot = self._make_staging(root)
            adapted = adapt_archive_staging_to_intake(snapshot, root / "intake")
            manifest = Path(adapted["manifest_path"])
            registry = root / "registry" / "source_records.jsonl"

            dry_run = append_source_records(manifest, registry, apply=False)
            self.assertEqual(dry_run["status"], "DRY_RUN_READY")
            self.assertFalse(dry_run["writes_performed"])
            self.assertFalse(registry.exists())

            applied = append_source_records(manifest, registry, apply=True)
            self.assertEqual(applied["status"], "APPENDED")
            self.assertTrue(applied["writes_performed"])
            first_bytes = registry.read_bytes()
            rows = [json.loads(line) for line in first_bytes.splitlines()]
            self.assertEqual(len(rows), 1)
            self.assertNotIn("project_id", rows[0])

            replay = append_source_records(manifest, registry, apply=True)
            self.assertEqual(replay["status"], "ALREADY_REGISTERED")
            self.assertFalse(replay["writes_performed"])
            self.assertEqual(registry.read_bytes(), first_bytes)
            self.assertFalse(registry.with_name(registry.name + ".lock").exists())

    def test_registry_lock_contention_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            snapshot = self._make_staging(root)
            adapted = adapt_archive_staging_to_intake(snapshot, root / "intake")
            manifest = Path(adapted["manifest_path"])
            registry = root / "registry" / "source_records.jsonl"
            registry.parent.mkdir(parents=True)
            lock = registry.with_name(registry.name + ".lock")
            lock.write_text("test lock", encoding="utf-8")

            result = append_source_records(manifest, registry, apply=True)
            self.assertEqual(result["status"], "LOCKED")
            self.assertFalse(result["writes_performed"])
            self.assertFalse(registry.exists())
            self.assertTrue(lock.exists())


if __name__ == "__main__":
    unittest.main()
