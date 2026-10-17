#!/usr/bin/env python3
"""Fail-closed Ed25519 receipt verification for trusted memory judgments and check results.

The verifier trusts no caller-supplied label or receipt by itself. A receipt is
accepted only when its signature validates against a key in a keyring whose
SHA-256 digest is pinned outside the repository (AGMS_TRUSTED_KEYRING_SHA256).
Private signing keys must remain in a separate trusted signer, never in this repo.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HASH_RE = re.compile(r"^[0-9a-f]{64}$")
RECEIPT_TYPES = {"applicability_judgment", "check_result", "owner_acknowledgement"}


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def canonical_receipt_payload(receipt: dict[str, Any]) -> bytes:
    return canonical_json({key: value for key, value in receipt.items() if key != "signature"}).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _read_keyring(path: Path, expected_sha256: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    if not isinstance(expected_sha256, str) or not HASH_RE.fullmatch(expected_sha256):
        return None, {"status": "BLOCKED_TRUST_ROOT_UNCONFIGURED", "reason": "A pinned keyring SHA-256 is required."}
    try:
        raw = path.read_bytes()
    except OSError as exc:
        return None, {"status": "BLOCKED_TRUST_ROOT_UNAVAILABLE", "reason": str(exc)}
    actual = sha256_bytes(raw)
    if actual != expected_sha256:
        return None, {"status": "BLOCKED_TRUST_ROOT_MISMATCH", "expected_sha256": expected_sha256, "actual_sha256": actual}
    try:
        keyring = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return None, {"status": "BLOCKED_KEYRING_INVALID", "reason": str(exc)}
    if not isinstance(keyring, dict) or keyring.get("schema_version") != "1.0" or not isinstance(keyring.get("keys"), list):
        return None, {"status": "BLOCKED_KEYRING_INVALID", "reason": "Expected schema_version 1.0 and a keys array."}
    seen = set()
    for key in keyring["keys"]:
        if not isinstance(key, dict) or not isinstance(key.get("key_id"), str) or not key["key_id"].strip():
            return None, {"status": "BLOCKED_KEYRING_INVALID", "reason": "Every key needs a non-empty key_id."}
        if key["key_id"] in seen:
            return None, {"status": "BLOCKED_KEYRING_INVALID", "reason": f"Duplicate key_id: {key['key_id']}"}
        seen.add(key["key_id"])
    return keyring, None


def _verify_ed25519(public_key_pem: str, payload: bytes, signature: bytes) -> tuple[bool, str | None]:
    openssl = shutil.which("openssl")
    if not openssl:
        return False, "OpenSSL is unavailable; signature verification is blocked."
    try:
        with tempfile.TemporaryDirectory(prefix="agms-receipt-") as tmp:
            root = Path(tmp)
            pub = root / "trusted-public-key.pem"
            data = root / "receipt-payload.json"
            sig = root / "receipt-signature.bin"
            pub.write_text(public_key_pem, encoding="utf-8")
            data.write_bytes(payload)
            sig.write_bytes(signature)
            proc = subprocess.run(
                [openssl, "pkeyutl", "-verify", "-pubin", "-inkey", str(pub),
                 "-rawin", "-in", str(data), "-sigfile", str(sig)],
                capture_output=True, text=True, timeout=8, check=False,
            )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)
    if proc.returncode != 0:
        return False, (proc.stderr or proc.stdout or "Signature verification failed.").strip()
    return True, None


def verify_signed_receipt(
    receipt: Any,
    expected_claim: dict[str, Any],
    *,
    keyring_path: Path | None = None,
    expected_keyring_sha256: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Verify key trust, time, detached signature and exact claim binding."""
    if keyring_path is None or not expected_keyring_sha256:
        return {"status": "BLOCKED_TRUST_ROOT_UNCONFIGURED", "verified": False}
    if not isinstance(receipt, dict) or receipt.get("schema_version") != "1.0":
        return {"status": "INVALID_RECEIPT", "verified": False, "reason": "Receipt schema_version 1.0 is required."}
    if receipt.get("receipt_type") not in RECEIPT_TYPES:
        return {"status": "INVALID_RECEIPT", "verified": False, "reason": "Unknown receipt_type."}
    receipt_id = receipt.get("receipt_id")
    issuer_id = receipt.get("issuer_id")
    key_id = receipt.get("key_id")
    if not all(isinstance(value, str) and value.strip() for value in (receipt_id, issuer_id, key_id)):
        return {"status": "INVALID_RECEIPT", "verified": False, "reason": "receipt_id, issuer_id and key_id are required."}
    issued_at = _timestamp(receipt.get("issued_at"))
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if issued_at is None or (issued_at - current).total_seconds() > 300:
        return {"status": "INVALID_RECEIPT_TIME", "verified": False}
    expires = receipt.get("expires_at")
    # Reusable check-result receipts must be time-bounded; otherwise a signed
    # PASS could be replayed indefinitely while its source fingerprint stays unchanged.
    if receipt.get("receipt_type") == "check_result" and expires is None:
        return {"status": "RECEIPT_EXPIRED_OR_INVALID", "verified": False}
    if expires is not None:
        expires_at = _timestamp(expires)
        if expires_at is None or expires_at <= current or expires_at <= issued_at:
            return {"status": "RECEIPT_EXPIRED_OR_INVALID", "verified": False}
    claim = receipt.get("claim")
    if not isinstance(claim, dict) or not isinstance(expected_claim, dict) or not expected_claim:
        return {"status": "INVALID_RECEIPT_CLAIM", "verified": False}
    # A trusted receipt must describe exactly the claim requested by the caller.
    # Checking only expected keys would accept a signed claim with additional,
    # potentially conflicting fields and weaken the exact-binding contract.
    unexpected = sorted(set(claim) - set(expected_claim))
    if unexpected:
        return {"status": "CLAIM_MISMATCH", "verified": False, "claim_field": unexpected[0]}
    for key, expected in expected_claim.items():
        if key not in claim or canonical_json(claim[key]) != canonical_json(expected):
            return {"status": "CLAIM_MISMATCH", "verified": False, "claim_field": key}
    signature = receipt.get("signature")
    if not isinstance(signature, dict) or signature.get("algorithm") != "Ed25519" or not isinstance(signature.get("value"), str):
        return {"status": "INVALID_RECEIPT_SIGNATURE", "verified": False}
    try:
        signature_bytes = base64.b64decode(signature["value"], validate=True)
    except (ValueError, base64.binascii.Error):
        return {"status": "INVALID_RECEIPT_SIGNATURE", "verified": False}

    keyring, error = _read_keyring(Path(keyring_path), expected_keyring_sha256)
    if error:
        return {**error, "verified": False}
    matches = [key for key in keyring["keys"] if key.get("key_id") == key_id]
    if len(matches) != 1:
        return {"status": "BLOCKED_UNTRUSTED_KEY", "verified": False, "key_id": key_id}
    key = matches[0]
    if (
        key.get("status") != "ACTIVE"
        or key.get("algorithm") != "Ed25519"
        or key.get("issuer_id") != issuer_id
        or receipt["receipt_type"] not in key.get("allowed_receipt_types", [])
        or not isinstance(key.get("public_key_pem"), str)
    ):
        return {"status": "BLOCKED_UNTRUSTED_KEY", "verified": False, "key_id": key_id}
    valid, reason = _verify_ed25519(key["public_key_pem"], canonical_receipt_payload(receipt), signature_bytes)
    if not valid:
        return {"status": "INVALID_RECEIPT_SIGNATURE", "verified": False, "reason": reason}
    return {
        "status": "VERIFIED",
        "verified": True,
        "receipt_id": receipt_id,
        "receipt_type": receipt["receipt_type"],
        "issuer_id": issuer_id,
        "verifier_id": issuer_id,
        "key_id": key_id,
        "issued_at": receipt["issued_at"],
        "claim": claim,
        "source_sha256": claim.get("source_sha256"),
        "basis_ref": claim.get("basis_ref"),
    }


def _load_receipt_store(path: Path) -> tuple[list[dict[str, Any]] | None, dict[str, Any] | None]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return None, {"status": "BLOCKED_RECEIPT_STORE_UNAVAILABLE", "reason": str(exc)}
    receipts = []
    seen = set()
    for number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            receipt = json.loads(line)
        except json.JSONDecodeError as exc:
            return None, {"status": "BLOCKED_RECEIPT_STORE_INVALID", "reason": f"line {number}: {exc}"}
        if not isinstance(receipt, dict) or not isinstance(receipt.get("receipt_id"), str):
            return None, {"status": "BLOCKED_RECEIPT_STORE_INVALID", "reason": f"line {number}: receipt_id required"}
        if receipt["receipt_id"] in seen:
            return None, {"status": "BLOCKED_RECEIPT_STORE_INVALID", "reason": f"duplicate receipt_id at line {number}"}
        seen.add(receipt["receipt_id"])
        receipts.append(receipt)
    return receipts, None


def _repo_file(repo_root: Path, reference: str) -> Path | None:
    """Resolve a local evidence reference; external URLs need a separate trusted resolver."""
    path_text = reference.split("#", 1)[0]
    if not path_text or "://" in path_text or path_text.startswith("sha256:"):
        return None
    root = repo_root.resolve()
    path = Path(path_text)
    resolved = path.resolve() if path.is_absolute() else (root / path).resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        return None
    return resolved if resolved.is_file() else None


def _candidate_record_digest(candidate: dict[str, Any], repo_root: Path) -> str | None:
    source = candidate.get("source")
    if not isinstance(source, dict) or not isinstance(source.get("path"), str):
        return None
    root = repo_root.resolve()
    path = Path(source["path"])
    path = path.resolve() if path.is_absolute() else (root / path).resolve()
    try:
        path.relative_to(root)
    except ValueError:
        return None
    try:
        raw = path.read_bytes()
    except OSError:
        return None
    if source.get("sha256") != sha256_bytes(raw):
        return None
    line = source.get("line")
    try:
        records = raw.decode("utf-8").splitlines()
        if not isinstance(line, int) or line < 1 or line > len(records):
            return None
        record = json.loads(records[line - 1])
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    candidate_type = candidate.get("candidate_type", "lesson" if "lesson_id" in candidate else "event")
    candidate_id = candidate.get("lesson_id", candidate.get("event_id"))
    expected_id = record.get("lesson_id" if candidate_type == "lesson" else "event_id") if isinstance(record, dict) else None
    if candidate_id != expected_id:
        return None
    return sha256_bytes(records[line - 1].encode("utf-8"))


def make_applicability_verifier(
    *, repo_root: Path, keyring_path: Path, expected_keyring_sha256: str,
    receipt_store_path: Path,
):
    """Return a verifier callback, or None if the trust root is not configured."""
    if not expected_keyring_sha256 or not Path(keyring_path).is_file() or not Path(receipt_store_path).is_file():
        return None
    def verify(candidate: dict[str, Any], judgment: dict[str, Any]):
        source_digest = _candidate_record_digest(candidate, Path(repo_root))
        basis_ref = judgment.get("basis_ref")
        basis_path = _repo_file(Path(repo_root), basis_ref) if isinstance(basis_ref, str) else None
        if source_digest is None or basis_path is None:
            return None
        try:
            basis_digest = sha256_bytes(basis_path.read_bytes())
        except OSError:
            return None
        candidate_type = candidate.get("candidate_type", "lesson" if "lesson_id" in candidate else "event")
        candidate_id = candidate.get("lesson_id", candidate.get("event_id"))
        identity = {
            "candidate_type": candidate_type, "candidate_id": candidate_id,
            "criterion": judgment.get("criterion"), "basis_ref": basis_ref,
            "source_sha256": source_digest, "basis_sha256": basis_digest,
        }
        receipts, error = _load_receipt_store(Path(receipt_store_path))
        if error or receipts is None:
            return None
        verified = []
        for receipt in receipts:
            if receipt.get("receipt_type") != "applicability_judgment":
                continue
            claim = receipt.get("claim")
            if not isinstance(claim, dict) or any(
                canonical_json(claim.get(key)) != canonical_json(value) for key, value in identity.items()
            ):
                continue
            result_claim = claim.get("result")
            expected = {**identity, "result": result_claim}
            check = verify_signed_receipt(
                receipt, expected, keyring_path=Path(keyring_path),
                expected_keyring_sha256=expected_keyring_sha256,
            )
            if check.get("verified") is not True:
                return None
            verified.append((result_claim, check))
        results = {result for result, _ in verified}
        if len(results) != 1 or judgment.get("result") not in results:
            return None
        _, receipt_check = verified[0]
        return {
            "verified": True,
            "candidate_id": candidate_id,
            "candidate_type": candidate_type,
            "criterion": judgment.get("criterion"),
            "result": judgment.get("result"),
            "basis_ref": basis_ref,
            "verifier_id": receipt_check["verifier_id"],
            "source_sha256": source_digest,
            "receipt_id": receipt_check["receipt_id"],
        }
    return verify


def make_applicability_verifier_from_env(repo_root: Path | None = None):
    root = Path(repo_root or Path(__file__).resolve().parents[1])
    keyring_path = os.environ.get("AGMS_TRUSTED_KEYRING_PATH")
    keyring_sha = os.environ.get("AGMS_TRUSTED_KEYRING_SHA256")
    receipts_path = os.environ.get("AGMS_SIGNED_RECEIPTS_PATH")
    if not keyring_path or not keyring_sha or not receipts_path:
        return None
    return make_applicability_verifier(
        repo_root=root, keyring_path=Path(keyring_path),
        expected_keyring_sha256=keyring_sha, receipt_store_path=Path(receipts_path),
    )


def make_check_receipt_verifier_from_env():
    keyring_path = os.environ.get("AGMS_TRUSTED_KEYRING_PATH")
    keyring_sha = os.environ.get("AGMS_TRUSTED_KEYRING_SHA256")
    if not keyring_path or not keyring_sha:
        return None
    def verify(receipt: Any, expected_claim: dict[str, Any]):
        return verify_signed_receipt(
            receipt, expected_claim, keyring_path=Path(keyring_path),
            expected_keyring_sha256=keyring_sha,
        )
    return verify
