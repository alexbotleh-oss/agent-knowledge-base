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
            rows = [json.loads(line) for line in (out / "source_records.jsonl").read_text().splitlines()]
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
            self.assertEqual((one / "source_records.jsonl").read_bytes(), (two / "source_records.jsonl").read_bytes())

if __name__ == "__main__":
    unittest.main()
