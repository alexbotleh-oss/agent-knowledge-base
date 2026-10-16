# Trusted verification receipts: production contract

Status: implementation prototype with fail-closed verification. No production trust root is configured in this repository. A successful unit test with a temporary key is not production trust.

## Trust boundary

A caller-supplied `judged_by`, `recorded_by`, `basis_ref`, `verified: true`, or result label is not authentication. A permissive applicability judgment or a check result that suppresses re-execution is trusted only when a detached Ed25519 receipt verifies against a public key in a keyring whose SHA-256 digest is pinned outside the repository.

The private signing key must live in a separate trusted signer (e.g. a protected CI identity or user-controlled verifier service) and must never be stored in this repository, memory logs, test fixtures or client browser storage. The agent may submit a claim for signing but must not receive the private key.

## Receipt schema

A signed receipt has these top-level fields:

- `schema_version`: `1.0`
- `receipt_id`: globally unique identifier
- `receipt_type`: `applicability_judgment`, `check_result`, or `owner_acknowledgement`
- `issuer_id` and `key_id`: trusted signer identity and key identifier
- `issued_at`: timezone-aware UTC timestamp; no more than five minutes in the future
- `claim`: exact source-bound claim
- `signature`: `{ "algorithm": "Ed25519", "value": "<base64 signature>" }`

The signature covers canonical UTF-8 JSON of every top-level field except `signature`, with keys sorted and compact separators. The keyring record must be ACTIVE, identify the same issuer, use Ed25519, and explicitly allow the receipt type. Revoked or unknown keys fail closed.

For an applicability judgment, the claim binds candidate type/id, criterion, result, basis reference, SHA-256 of the exact candidate source line, and SHA-256 of the local evidence file. External URLs are not resolved by this verifier; they require a separate trusted evidence resolver.

For a check result, the claim binds check key, exact input fingerprint, result status, evidence references, relevant source hashes and candidate fingerprints. A receipt for a different input fingerprint cannot suppress a rerun.

For an owner acknowledgement, the claim binds `result_event_id`, `child_branch_id`, `parent_task_id`, `parent_checkpoint_id`, `decision`, and `owner_ref`. An acknowledgement journal entry without a valid signed `owner_acknowledgement` receipt is audit-only and cannot authorize returning to the parent task. The return controller re-verifies the embedded receipt against the externally pinned keyring at the moment of return; caller-written status fields are not trusted.

## External trust-root configuration

The production process must set all applicable environment variables outside repository-controlled files:

- `AGMS_TRUSTED_KEYRING_PATH`: path to the trusted public-key registry
- `AGMS_TRUSTED_KEYRING_SHA256`: expected SHA-256 of the exact keyring bytes, provisioned out-of-band
- `AGMS_SIGNED_RECEIPTS_PATH`: append-only JSONL store of signed applicability receipts (not needed when a check receipt is embedded in a check event)

If the keyring path/hash is missing, the hash mismatches, a key is revoked, the receipt is malformed/expired, source/evidence bytes changed, or signature verification is unavailable, the verifier returns a blocked/unknown result. It must never downgrade to trusting the unsigned label.

## Receipt store and replay

The receipt store is untrusted storage. Every receipt is verified independently; duplicate receipt IDs or malformed JSONL block the store. Old receipts are usable only while their key remains active and their source/evidence digests still match. Key revocation is controlled by the externally pinned keyring; updating the pin is an operator action and must not be performed by the agent as part of ordinary task execution.

## Current limitation and rollout

The repository has no production key, pinned keyring digest, signed receipt store or trusted signer configured. Therefore `make_applicability_verifier_from_env()` returns `None` unless an operator configures them, and permissive judgments remain UNKNOWN, and owner returns remain blocked until a trusted owner-acknowledgement signer and pinned keyring are configured. This implementation proves the verification mechanism with temporary test keys only; it does not claim production identity, evidence authenticity or safe automatic execution.
