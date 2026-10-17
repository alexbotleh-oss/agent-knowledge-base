import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import project_attachment_library as library


class ProjectAttachmentLibraryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.source = self.root / "incoming" / "report.txt"
        self.source.parent.mkdir()
        self.source.write_bytes(b"private attachment bytes\n")
        self.library_root = self.root / "private-library"

    def tearDown(self):
        self.tmp.cleanup()

    def register(self, *, project="AGENT_MEMORY_SYSTEM", conversation="CHAT-1", message="MSG-1"):
        return library.register_attachment(
            self.source, self.library_root, project_id=project,
            conversation_id=conversation, source_message_id=message,
            original_name="report.txt", media_type="text/plain",
        )

    def rows(self, path):
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]

    def test_registers_one_content_object_and_stable_reference(self):
        first = self.register()
        second = self.register()
        self.assertEqual(first["status"], "REGISTERED")
        self.assertEqual(second["status"], "ALREADY_REGISTERED")
        self.assertEqual(first["attachment_id"], second["attachment_id"])
        self.assertEqual(first["library_ref"], second["library_ref"])
        self.assertEqual(first["sha256"], second["sha256"])
        self.assertEqual(len(self.rows(self.library_root / "objects.jsonl")), 1)
        self.assertEqual(len(self.rows(self.library_root / "references.jsonl")), 1)
        stored = self.library_root / "objects" / "AGENT_MEMORY_SYSTEM" / first["sha256"][:2] / first["sha256"]
        self.assertTrue(stored.is_file())
        self.assertEqual(stored.read_bytes(), self.source.read_bytes())

    def test_same_content_in_two_messages_reuses_object_but_keeps_occurrences(self):
        first = self.register(message="MSG-1")
        second = self.register(message="MSG-2")
        self.assertEqual(first["library_ref"], second["library_ref"])
        self.assertNotEqual(first["attachment_id"], second["attachment_id"])
        self.assertEqual(len(self.rows(self.library_root / "objects.jsonl")), 1)
        self.assertEqual(len(self.rows(self.library_root / "references.jsonl")), 2)

    def test_project_boundaries_create_distinct_library_objects(self):
        first = self.register(project="PROJECT_A")
        second = self.register(project="PROJECT_B")
        self.assertNotEqual(first["library_ref"], second["library_ref"])
        self.assertEqual(len(self.rows(self.library_root / "objects.jsonl")), 2)

    def test_registry_contains_references_and_hashes_not_attachment_bytes(self):
        self.register()
        serialized = (self.library_root / "references.jsonl").read_text(encoding="utf-8")
        self.assertNotIn("private attachment bytes", serialized)
        row = self.rows(self.library_root / "references.jsonl")[0]
        self.assertTrue(row["library_ref"].startswith("project-library://"))
        self.assertEqual(row["sha256"], library.sha256_file(self.source))

    def test_missing_source_and_invalid_project_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "missing"):
            library.register_attachment(
                self.root / "missing.bin", self.library_root,
                project_id="PROJECT_A", conversation_id="CHAT-1", source_message_id="MSG-1",
            )
        with self.assertRaisesRegex(ValueError, "unsupported characters"):
            self.register(project="../outside")

    def test_stable_reference_resolves_only_after_provenance_and_hash_checks(self):
        registered = self.register()
        resolved = library.resolve_attachment(
            self.library_root, attachment_id=registered["attachment_id"],
            library_ref=registered["library_ref"],
        )
        self.assertEqual(resolved["status"], "AVAILABLE")
        self.assertEqual(resolved["sha256"], registered["sha256"])
        self.assertEqual(resolved["conversation_id"], "CHAT-1")
        with self.assertRaisesRegex(ValueError, "mismatch"):
            library.resolve_attachment(
                self.library_root, attachment_id=registered["attachment_id"],
                library_ref="project-library://OTHER/objects/sha256/" + registered["sha256"],
            )

    def test_missing_or_tampered_library_object_is_not_reported_available(self):
        registered = self.register()
        Path(registered["storage_locator"]).write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            library.resolve_attachment(self.library_root, attachment_id=registered["attachment_id"])

        Path(registered["storage_locator"]).unlink()
        missing = library.resolve_attachment(self.library_root, attachment_id=registered["attachment_id"])
        self.assertEqual(missing["status"], "UNAVAILABLE")

    def test_corrupt_registry_fails_closed(self):
        self.library_root.mkdir(parents=True)
        (self.library_root / "objects.jsonl").write_text("{broken\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "corrupt library object registry"):
            self.register()
        self.assertFalse((self.library_root / "objects").exists())


if __name__ == "__main__":
    unittest.main()
