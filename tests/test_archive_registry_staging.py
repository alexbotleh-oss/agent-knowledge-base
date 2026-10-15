import hashlib, json, sys, tempfile, unittest, zipfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from archive_registry_staging import build

class ArchiveRegistryStagingTests(unittest.TestCase):
    def test_manifest_stable_locators_and_attachment_disclaimer(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            source = tmp / "sample.zip"
            payload = [{"id":"conv-1","title":"sample","mapping":{
                "node-1":{"parent":None,"children":["node-2"],"message":{
                    "id":"msg-1","create_time":1790000000,"author":{"role":"user"},
                    "content":{"content_type":"text","parts":["hello"]},"metadata":{}}},
                "node-2":{"parent":"node-1","children":[],"message":{
                    "id":"msg-2","create_time":1790000001,"author":{"role":"assistant"},
                    "content":{"content_type":"text","parts":["world"]},
                    "metadata":{"attachments":[{"name":"not-read.pdf"}]}}}}}]
            with zipfile.ZipFile(source, "w") as z:
                z.writestr("conversations.json", json.dumps(payload))
            out = tmp / "staging"
            manifest = build(source, out, "ARCHIVE-TEST-001")
            rows = [json.loads(line) for line in (out / manifest["records_file"]).read_text().splitlines()]
            self.assertEqual(manifest["coverage"]["conversation_count"], 1)
            self.assertEqual(manifest["coverage"]["source_record_count"], 2)
            self.assertEqual(len({r["source_locator"] for r in rows}), 2)
            self.assertEqual(rows[0]["source_locator"], "ARCHIVE-TEST-001/conv-1/node-1")
            self.assertFalse(rows[1]["attachment_payloads_inspected"])
            self.assertEqual(manifest["raw_sha256"], hashlib.sha256(source.read_bytes()).hexdigest())

    def test_repeat_build_records_are_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            source = tmp / "conversations.json"
            source.write_text(json.dumps([{"id":"c","mapping":{"n":{
                "parent":None,"children":[],"message":{"id":"m","create_time":1,
                "author":{"role":"user"},"content":{"parts":["same"]},"metadata":{}}}}}]), encoding="utf-8")
            one, two = tmp / "one", tmp / "two"
            build(source, one, "ARCHIVE-TEST-002")
            build(source, two, "ARCHIVE-TEST-002")
            self.assertEqual((one / json.loads((one / "archive_snapshot.json").read_text())["records_file"]).read_bytes(), (two / json.loads((two / "archive_snapshot.json").read_text())["records_file"]).read_bytes())


    def test_failed_manifest_publish_preserves_previous_generation(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            source = tmp / "conversations.json"
            out = tmp / "staging"
            source.write_text(json.dumps([{"id":"c1","mapping":{"node":{"parent":None,"children":[],"message":{"id":"message-c1","create_time":1790000000,"author":{"role":"user"},"content":{"content_type":"text","parts":["old generation"]},"metadata":{}}}}}]), encoding="utf-8")
            first = build(source, out, "ARCHIVE-ATOMIC")
            old_manifest_bytes = (out / "archive_snapshot.json").read_bytes()
            old_records = (out / first["records_file"]).read_bytes()

            source.write_text(json.dumps([{"id":"c2","mapping":{"node":{"parent":None,"children":[],"message":{"id":"message-c2","create_time":1790000000,"author":{"role":"user"},"content":{"content_type":"text","parts":["new generation"]},"metadata":{}}}}}]), encoding="utf-8")
            original_replace = Path.replace
            def fail_manifest_replace(path, target):
                if path.name == "archive_snapshot.json.tmp":
                    raise OSError("injected failure before manifest publication")
                return original_replace(path, target)
            with patch.object(Path, "replace", fail_manifest_replace):
                with self.assertRaises(OSError):
                    build(source, out, "ARCHIVE-ATOMIC")

            self.assertEqual((out / "archive_snapshot.json").read_bytes(), old_manifest_bytes)
            self.assertEqual((out / first["records_file"]).read_bytes(), old_records)
            current = json.loads((out / "archive_snapshot.json").read_text())
            self.assertEqual(current["raw_sha256"], first["raw_sha256"])
            self.assertTrue((out / current["records_file"]).exists())



    def test_same_bytes_with_different_archive_ids_keep_separate_generations(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            source = tmp / "conversations.json"
            source.write_text(json.dumps([{"id":"c","mapping":{"n":{
                "parent":None,"children":[],"message":{"id":"m","create_time":1,
                "author":{"role":"user"},"content":{"parts":["same"]},"metadata":{}}}}}]), encoding="utf-8")
            out = tmp / "staging"
            first = build(source, out, "ARCHIVE-A")
            first_records = (out / first["records_file"]).read_bytes()
            second = build(source, out, "ARCHIVE-B")
            self.assertNotEqual(first["records_file"], second["records_file"])
            self.assertEqual((out / first["records_file"]).read_bytes(), first_records)
            self.assertEqual(json.loads((out / "archive_snapshot.json").read_text())["archive_id"], "ARCHIVE-B")


    def test_process_crash_before_manifest_publish_preserves_old_generation_and_recovers(self):
        import subprocess
        import sys
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "conversations.json"
            out = root / "staging"
            source.write_text(json.dumps([{"id":"c1","mapping":{"node":{"parent":None,"children":[],"message":{"id":"message-c1","create_time":1790000000,"author":{"role":"user"},"content":{"content_type":"text","parts":["old generation"]},"metadata":{}}}}}]), encoding="utf-8")
            first = build(source, out, "ARCHIVE-CRASH-ATOMIC")
            manifest_path = out / "archive_snapshot.json"
            old_manifest = manifest_path.read_bytes()
            old_records_path = out / first["records_file"]
            old_records = old_records_path.read_bytes()

            source.write_text(json.dumps([{"id":"c2","mapping":{"node":{"parent":None,"children":[],"message":{"id":"message-c2","create_time":1790000000,"author":{"role":"user"},"content":{"content_type":"text","parts":["new generation"]},"metadata":{}}}}}]), encoding="utf-8")
            crash_script = r'''
import os
import sys
from pathlib import Path

sys.path.insert(0, sys.argv[1])
from archive_registry_staging import build

original_replace = Path.replace
def crash_before_manifest_publish(path, target):
    if path.name == "archive_snapshot.json.tmp":
        os._exit(73)
    return original_replace(path, target)

Path.replace = crash_before_manifest_publish
build(Path(sys.argv[2]), Path(sys.argv[3]), "ARCHIVE-CRASH-ATOMIC")
'''
            crashed = subprocess.run(
                [sys.executable, "-c", crash_script, str(ROOT / "tools"),
                 str(source), str(out)],
                capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(crashed.returncode, 73, crashed.stderr)

            # The old published pointer and its immutable generation must survive.
            self.assertEqual(manifest_path.read_bytes(), old_manifest)
            self.assertEqual(old_records_path.read_bytes(), old_records)
            old_snapshot = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(old_snapshot["raw_sha256"], first["raw_sha256"])
            self.assertTrue((out / old_snapshot["records_file"]).is_file())

            # A new process can reacquire the OS lock and publish a consistent
            # generation; the interrupted temporary manifest is not authoritative.
            recovered = build(source, out, "ARCHIVE-CRASH-ATOMIC")
            published = json.loads(manifest_path.read_text(encoding="utf-8"))
            published_records = out / published["records_file"]
            self.assertEqual(recovered["raw_sha256"], hashlib.sha256(source.read_bytes()).hexdigest())
            self.assertEqual(published["raw_sha256"], recovered["raw_sha256"])
            self.assertEqual(published["records_sha256"], hashlib.sha256(published_records.read_bytes()).hexdigest())
            self.assertTrue(published_records.is_file())
            self.assertEqual(json.loads(published_records.read_text(encoding="utf-8").splitlines()[0])["conversation_id"], "c2")


if __name__ == "__main__":
    unittest.main()
