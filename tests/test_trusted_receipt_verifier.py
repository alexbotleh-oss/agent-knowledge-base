import base64
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from trusted_receipt_verifier import (
    canonical_receipt_payload, make_applicability_verifier,
    make_applicability_verifier_from_env, verify_signed_receipt,
)


@unittest.skipUnless(shutil.which("openssl"), "OpenSSL is required for Ed25519 receipt tests")
class TrustedReceiptVerifierTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.private = self.root / "private.pem"
        self.public = self.root / "public.pem"
        subprocess.run(["openssl", "genpkey", "-algorithm", "ED25519", "-out", str(self.private)],
                       check=True, capture_output=True)
        subprocess.run(["openssl", "pkey", "-in", str(self.private), "-pubout", "-out", str(self.public)],
                       check=True, capture_output=True)
        self.keyring = self.root / "trusted-keys.json"
        self.keyring.write_text(json.dumps({
            "schema_version": "1.0",
            "keys": [{
                "key_id": "test-key-1", "issuer_id": "test-signer",
                "algorithm": "Ed25519", "status": "ACTIVE",
                "allowed_receipt_types": ["applicability_judgment", "check_result"],
                "public_key_pem": self.public.read_text(encoding="utf-8"),
            }],
        }, sort_keys=True), encoding="utf-8")
        self.keyring_sha = hashlib.sha256(self.keyring.read_bytes()).hexdigest()
        self.now = datetime.now(timezone.utc).replace(microsecond=0)
        self.receipts = self.root / "signed-receipts.jsonl"

    def tearDown(self):
        self.tmp.cleanup()

    def _sign(self, receipt):
        payload = canonical_receipt_payload(receipt)
        payload_path = self.root / "payload.json"
        signature_path = self.root / "signature.bin"
        payload_path.write_bytes(payload)
        subprocess.run([
            "openssl", "pkeyutl", "-sign", "-inkey", str(self.private),
            "-rawin", "-in", str(payload_path), "-out", str(signature_path),
        ], check=True, capture_output=True)
        receipt["signature"] = {
            "algorithm": "Ed25519",
            "value": base64.b64encode(signature_path.read_bytes()).decode("ascii"),
        }
        return receipt

    def _receipt(self, claim, receipt_type="applicability_judgment"):
        receipt = {
            "schema_version": "1.0", "receipt_id": "RECEIPT-1",
            "receipt_type": receipt_type, "issuer_id": "test-signer",
            "key_id": "test-key-1", "issued_at": self.now.isoformat().replace("+00:00", "Z"),
            "claim": claim,
        }
        return self._sign(receipt)

    def test_valid_signature_and_exact_claim_are_verified(self):
        claim = {
            "candidate_type": "lesson", "candidate_id": "LESSON-1",
            "criterion": "trigger", "result": "MATCH", "basis_ref": "tests/test_trigger.py#case",
            "source_sha256": "a" * 64, "basis_sha256": "b" * 64,
        }
        receipt = self._receipt(claim)
        result = verify_signed_receipt(
            receipt, claim, keyring_path=self.keyring,
            expected_keyring_sha256=self.keyring_sha, now=self.now,
        )
        self.assertEqual(result["status"], "VERIFIED")
        self.assertTrue(result["verified"])
        self.assertEqual(result["verifier_id"], "test-signer")

    def test_changed_claim_or_signature_is_rejected(self):
        claim = {"check_key": "CHECK-1", "input_fingerprint": "a" * 64, "result_status": "PASS"}
        receipt = self._receipt(claim, "check_result")
        mismatch = verify_signed_receipt(
            receipt, {**claim, "input_fingerprint": "b" * 64},
            keyring_path=self.keyring, expected_keyring_sha256=self.keyring_sha, now=self.now,
        )
        self.assertEqual(mismatch["status"], "CLAIM_MISMATCH")
        receipt["claim"]["result_status"] = "FAIL"
        invalid = verify_signed_receipt(
            receipt, receipt["claim"], keyring_path=self.keyring,
            expected_keyring_sha256=self.keyring_sha, now=self.now,
        )
        self.assertEqual(invalid["status"], "INVALID_RECEIPT_SIGNATURE")

    def test_unpinned_or_changed_keyring_fails_closed(self):
        claim = {"check_key": "CHECK-1", "input_fingerprint": "a" * 64, "result_status": "PASS"}
        receipt = self._receipt(claim, "check_result")
        blocked = verify_signed_receipt(receipt, claim, keyring_path=self.keyring, expected_keyring_sha256=None, now=self.now)
        self.assertEqual(blocked["status"], "BLOCKED_TRUST_ROOT_UNCONFIGURED")
        wrong = verify_signed_receipt(receipt, claim, keyring_path=self.keyring, expected_keyring_sha256="0" * 64, now=self.now)
        self.assertEqual(wrong["status"], "BLOCKED_TRUST_ROOT_MISMATCH")

    def test_revoked_key_and_wrong_receipt_type_are_rejected(self):
        claim = {"check_key": "CHECK-1", "input_fingerprint": "a" * 64, "result_status": "PASS"}
        receipt = self._receipt(claim, "check_result")
        keyring = json.loads(self.keyring.read_text(encoding="utf-8"))
        keyring["keys"][0]["status"] = "REVOKED"
        self.keyring.write_text(json.dumps(keyring, sort_keys=True), encoding="utf-8")
        revoked_sha = hashlib.sha256(self.keyring.read_bytes()).hexdigest()
        result = verify_signed_receipt(receipt, claim, keyring_path=self.keyring,
                                       expected_keyring_sha256=revoked_sha, now=self.now)
        self.assertEqual(result["status"], "BLOCKED_UNTRUSTED_KEY")

    def test_applicability_callback_binds_candidate_record_and_basis_file(self):
        lessons = self.root / "lessons.jsonl"
        lessons.write_text(json.dumps({
            "lesson_id": "LESSON-1", "scope": "project", "project_id": "TEST",
            "title": "Trigger lesson",
        }) + "\n", encoding="utf-8")
        basis = self.root / "tests" / "test_trigger.py"
        basis.parent.mkdir(parents=True)
        basis.write_text("def test_trigger():\n    assert True\n", encoding="utf-8")
        line = lessons.read_text(encoding="utf-8").splitlines()[0]
        claim = {
            "candidate_type": "lesson", "candidate_id": "LESSON-1",
            "criterion": "trigger", "result": "MATCH", "basis_ref": "tests/test_trigger.py#test_trigger",
            "source_sha256": hashlib.sha256(line.encode("utf-8")).hexdigest(),
            "basis_sha256": hashlib.sha256(basis.read_bytes()).hexdigest(),
        }
        receipt = self._receipt(claim)
        self.receipts.write_text(json.dumps(receipt) + "\n", encoding="utf-8")
        verifier = make_applicability_verifier(
            repo_root=self.root, keyring_path=self.keyring,
            expected_keyring_sha256=self.keyring_sha, receipt_store_path=self.receipts,
        )
        candidate = {
            "candidate_type": "lesson", "lesson_id": "LESSON-1",
            "source": {"path": str(lessons), "sha256": hashlib.sha256(lessons.read_bytes()).hexdigest(), "line": 1},
        }
        judgment = {"criterion": "trigger", "result": "MATCH", "basis_ref": "tests/test_trigger.py#test_trigger"}
        verified = verifier(candidate, judgment)
        self.assertTrue(verified["verified"])
        self.assertEqual(verified["receipt_id"], "RECEIPT-1")
        basis.write_text("def test_trigger():\n    assert False\n", encoding="utf-8")
        self.assertIsNone(verifier(candidate, judgment))

    def test_environment_factory_is_disabled_without_external_trust_root(self):
        for key in ("AGMS_TRUSTED_KEYRING_PATH", "AGMS_TRUSTED_KEYRING_SHA256", "AGMS_SIGNED_RECEIPTS_PATH"):
            os.environ.pop(key, None)
        self.assertIsNone(make_applicability_verifier_from_env(self.root))


if __name__ == "__main__":
    unittest.main()
