import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXT = ROOT / "clients" / "chatgpt-web-extension"


class ChatGPTWebExtensionContractTests(unittest.TestCase):
    def test_manifest_is_mv3_and_limits_host_access_to_chatgpt_and_loopback_bridge(self):
        manifest = json.loads((EXT / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["manifest_version"], 3)
        self.assertEqual(set(manifest["host_permissions"]), {
            "https://chatgpt.com/*", "https://chat.openai.com/*", "http://127.0.0.1:8766/*"
        })
        self.assertIn("storage", manifest["permissions"])
        self.assertEqual(manifest["background"]["service_worker"], "background.js")
        for relative in [
            manifest["background"]["service_worker"],
            manifest["action"]["default_popup"],
            *manifest["content_scripts"][0]["js"],
        ]:
            self.assertTrue((EXT / relative).is_file(), relative)

    def test_extension_journal_is_local_and_send_is_gated(self):
        background = (EXT / "background.js").read_text(encoding="utf-8")
        content = (EXT / "content_script.js").read_text(encoding="utf-8")
        self.assertIn('indexedDB.open(DB_NAME, DB_VERSION)', background)
        self.assertIn('"TURN_RECEIVED"', background)
        self.assertIn('await sendWorker({ action: "REGISTER_TURN", payload })', content)
        self.assertIn('await sendWorker({\n        action: "RECORD_EVENT", turn_id: turnId, event_type: "WORK_STARTED"', content)
        self.assertIn('freshButton.click()', content)
        self.assertIn('Сообщение НЕ отправлено', content)
        self.assertNotIn("fetch(", background)
        self.assertNotIn("fetch(", content)

    def test_recovery_popup_exports_local_journal_and_copies_recovery_prompt(self):
        popup = (EXT / "popup.js").read_text(encoding="utf-8")
        self.assertIn('action: "LIST_INCOMPLETE"', popup)
        self.assertIn('action: "EXPORT_LEDGER"', popup)
        self.assertIn("Скопировать запрос восстановления", popup)
        self.assertIn("createObjectURL", popup)

    def test_attachment_popup_requires_explicit_project_and_links_reference_only(self):
        popup = (EXT / "popup.js").read_text(encoding="utf-8")
        background = (EXT / "background.js").read_text(encoding="utf-8")
        docs = (EXT / "README.md").read_text(encoding="utf-8")
        self.assertIn('http://127.0.0.1:8766/v1/attachments', popup)
        self.assertIn('"X-Rima-Project-ID": projectId', popup)
        self.assertIn('action: "LINK_ATTACHMENT"', popup)
        self.assertIn('case "LINK_ATTACHMENT"', background)
        self.assertIn("manual second selection", docs)
        self.assertIn("Never log file bytes", (ROOT / "tools" / "project_attachment_adapter.py").read_text(encoding="utf-8"))

    def test_docs_state_live_browser_validation_is_pending(self):
        docs = (EXT / "README.md").read_text(encoding="utf-8")
        self.assertIn("Not yet validated in a live browser", docs)
        self.assertIn("does not send messages to an external server", docs)


if __name__ == "__main__":
    unittest.main()
