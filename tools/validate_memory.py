#!/usr/bin/env python3
"""Dependency-free structural checks for memory records and handoff files."""
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ERRORS = []
ARTIFACT_KINDS = {
    "raw_source_reference", "source_inventory", "source_records", "memory_records",
    "event_records", "lesson_records", "decision_records", "task_state", "handoff",
    "relation_records", "other",
}
EVIDENCE_STATUSES = {"reported", "observed", "inferred", "verified", "unknown"}
LIFECYCLE_STATUSES = {"candidate", "accepted", "disputed", "superseded", "deprecated", "not_applicable"}
APPROVAL_STATUSES = {"not_requested", "pending", "user_approved", "user_rejected"}


def fail(message):
    ERRORS.append(message)


def check_json(path):
    try:
        json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"{path.relative_to(ROOT)}: invalid JSON: {exc}")


def check_jsonl(path, required):
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        try:
            value = json.loads(line)
        except Exception as exc:
            fail(f"{path.relative_to(ROOT)}:{number}: invalid JSON: {exc}")
            continue
        if not isinstance(value, dict):
            fail(f"{path.relative_to(ROOT)}:{number}: each record must be an object")
            continue
        missing = [key for key in required if key not in value]
        if missing:
            fail(f"{path.relative_to(ROOT)}:{number}: missing keys: {', '.join(missing)}")


def _has_timezone(value):
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        return parsed.tzinfo is not None
    except ValueError:
        return False


def validate_intake_manifest(manifest_path, repo_root=None):
    """Validate v1 intake metadata and referenced artifact bytes without executing them."""
    manifest_path = Path(manifest_path)
    root = Path(repo_root) if repo_root else ROOT
    errors = []
    try:
        value = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"{manifest_path}: invalid JSON: {exc}"]
    if not isinstance(value, dict):
        return [f"{manifest_path}: manifest must be a JSON object"]

    allowed = {"schema_version", "command", "batch_id", "created_at", "payload_classification", "source", "observed_context", "artifacts", "notes"}
    unknown = sorted(set(value) - allowed)
    if unknown:
        errors.append(f"{manifest_path}: unknown top-level fields: {', '.join(unknown)}")
    if value.get("schema_version") != "1.0":
        errors.append(f"{manifest_path}: unsupported schema_version (expected 1.0)")
    if value.get("command") != "IMPORT_READY":
        errors.append(f"{manifest_path}: command must be IMPORT_READY")
    if not isinstance(value.get("batch_id"), str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{2,127}", value.get("batch_id", "")):
        errors.append(f"{manifest_path}: invalid batch_id")
    if not _has_timezone(value.get("created_at")):
        errors.append(f"{manifest_path}: created_at must be ISO-8601 with timezone")
    if value.get("payload_classification") not in {"public", "sanitized", "private_reference_only"}:
        errors.append(f"{manifest_path}: invalid payload_classification")

    source = value.get("source")
    source_fields = {"source_type", "source_id", "project_id", "conversation_ids", "source_locator", "captured_at", "scope_status"}
    if not isinstance(source, dict):
        errors.append(f"{manifest_path}: source must be an object")
    else:
        extra = sorted(set(source) - source_fields)
        if extra:
            errors.append(f"{manifest_path}: unknown source fields: {', '.join(extra)}")
        if source.get("source_type") not in {"chat_summary", "structured_export", "project_artifact", "mixed", "manual"}:
            errors.append(f"{manifest_path}: invalid source.source_type")
        for key in ("source_id", "project_id"):
            if not isinstance(source.get(key), str) or not source[key].strip():
                errors.append(f"{manifest_path}: source.{key} must be a non-empty string; use unknown rather than guessing")
        if source.get("scope_status") not in {"COMPLETE", "PARTIAL", "UNKNOWN"}:
            errors.append(f"{manifest_path}: invalid source.scope_status")
        captured = source.get("captured_at")
        if captured != "unknown" and not _has_timezone(captured):
            errors.append(f"{manifest_path}: source.captured_at must be timezone-aware ISO-8601 or unknown")
        ids = source.get("conversation_ids", [])
        if not isinstance(ids, list) or any(not isinstance(x, str) or not x for x in ids) or len(ids) != len(set(ids)):
            errors.append(f"{manifest_path}: source.conversation_ids must be unique non-empty strings")
        if "source_locator" in source and (not isinstance(source["source_locator"], str) or not source["source_locator"].strip()):
            errors.append(f"{manifest_path}: source.source_locator must be a non-empty string")

    context = value.get("observed_context", {})
    if not isinstance(context, dict) or set(context) - {"languages", "tools", "task_types"}:
        errors.append(f"{manifest_path}: observed_context may contain only languages, tools, task_types")
    else:
        for dimension in ("languages", "tools", "task_types"):
            tags = context.get(dimension, [])
            if not isinstance(tags, list):
                errors.append(f"{manifest_path}: observed_context.{dimension} must be an array")
                continue
            for i, tag in enumerate(tags):
                if not isinstance(tag, dict) or set(tag) - {"value", "evidence_status", "source_refs", "basis"}:
                    errors.append(f"{manifest_path}: observed_context.{dimension}[{i}] has invalid shape")
                    continue
                if not isinstance(tag.get("value"), str) or not tag["value"].strip():
                    errors.append(f"{manifest_path}: observed_context.{dimension}[{i}].value is required")
                if tag.get("evidence_status") not in EVIDENCE_STATUSES:
                    errors.append(f"{manifest_path}: observed_context.{dimension}[{i}].evidence_status is invalid")
                refs = tag.get("source_refs")
                if not isinstance(refs, list) or not refs or any(not isinstance(ref, str) or not ref for ref in refs):
                    errors.append(f"{manifest_path}: observed_context.{dimension}[{i}].source_refs must be non-empty")

    artifacts = value.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        errors.append(f"{manifest_path}: artifacts must be a non-empty array")
        return errors
    seen_ids = set()
    base = manifest_path.resolve().parent
    for i, artifact in enumerate(artifacts):
        label = f"{manifest_path}: artifacts[{i}]"
        if not isinstance(artifact, dict):
            errors.append(f"{label} must be an object")
            continue
        allowed_artifact = {"artifact_id", "kind", "path", "sha256", "record_count", "lifecycle_status", "evidence_status", "approval_status", "approval_evidence", "notes"}
        extra = sorted(set(artifact) - allowed_artifact)
        if extra:
            errors.append(f"{label} has unknown fields: {', '.join(extra)}")
        aid = artifact.get("artifact_id")
        if not isinstance(aid, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{2,127}", aid):
            errors.append(f"{label}.artifact_id is invalid")
        elif aid in seen_ids:
            errors.append(f"{label}.artifact_id is duplicated: {aid}")
        else:
            seen_ids.add(aid)
        if artifact.get("kind") not in ARTIFACT_KINDS:
            errors.append(f"{label}.kind is invalid")
        if artifact.get("lifecycle_status") not in LIFECYCLE_STATUSES:
            errors.append(f"{label}.lifecycle_status is invalid")
        if artifact.get("evidence_status") not in EVIDENCE_STATUSES:
            errors.append(f"{label}.evidence_status is invalid")
        approval = artifact.get("approval_status")
        if approval not in APPROVAL_STATUSES:
            errors.append(f"{label}.approval_status is invalid")
        if artifact.get("lifecycle_status") == "accepted" and (approval != "user_approved" or not artifact.get("approval_evidence")):
            errors.append(f"{label}: accepted records require user_approved and approval_evidence")
        if approval == "user_approved" and not artifact.get("approval_evidence"):
            errors.append(f"{label}: user_approved requires approval_evidence")

        relpath = artifact.get("path")
        if not isinstance(relpath, str) or not relpath.strip():
            errors.append(f"{label}.path is required")
            continue
        candidate = Path(relpath)
        if candidate.is_absolute() or ".." in candidate.parts or "\\" in relpath:
            errors.append(f"{label}.path must be a safe relative path without traversal")
            continue
        full_path = (base / candidate).resolve()
        try:
            full_path.relative_to(base)
        except ValueError:
            errors.append(f"{label}.path escapes the manifest directory")
            continue
        if not full_path.is_file():
            errors.append(f"{label}.path does not exist: {relpath}")
            continue
        digest = hashlib.sha256(full_path.read_bytes()).hexdigest()
        if not isinstance(artifact.get("sha256"), str) or digest.lower() != artifact.get("sha256", "").lower():
            errors.append(f"{label}.sha256 does not match referenced artifact")
        count = artifact.get("record_count")
        if count is not None and (not isinstance(count, int) or isinstance(count, bool) or count < 0):
            errors.append(f"{label}.record_count must be a non-negative integer")
    return errors


def main():
    registry = ROOT / "core/stack_registry.json"
    if registry.exists():
        check_json(registry)
    event_example = ROOT / "templates/event_record.jsonl.example"
    lesson_example = ROOT / "templates/lesson_record.jsonl.example"
    if event_example.exists():
        check_jsonl(event_example, ["event_id", "project_id", "type", "summary", "status", "evidence", "confidence"])
    if lesson_example.exists():
        check_jsonl(lesson_example, ["lesson_id", "scope", "title", "trigger", "status", "prevention_rule"])
    schema = ROOT / "schemas/memory_intake_manifest.schema.json"
    if schema.exists():
        check_json(schema)
    intake_root = ROOT / "incoming"
    if intake_root.exists():
        for manifest in sorted(intake_root.rglob("manifest.json")):
            for error in validate_intake_manifest(manifest, ROOT):
                fail(error)
    required_docs = [
        "core/guardrails.md", "core/universal_instructions.md",
        "core/agent_runtime_protocol.md", "core/memory_model.md",
        "core/session_handoff.md", "core/context_interpretation.md",
        "core/autonomy_policy.md", "core/visual_diagnostics.md",
        "templates/project_state.md", "templates/task_state.md",
    ]
    for name in required_docs:
        path = ROOT / name
        if not path.is_file() or not path.read_text(encoding="utf-8").strip():
            fail(f"{name}: missing or empty")
    if ERRORS:
        print("MEMORY VALIDATION: FAIL")
        for error in ERRORS:
            print(f"- {error}")
        return 1
    print("MEMORY VALIDATION: PASS")
    print("Checked core protocol files, JSON/JSONL examples, and incoming memory manifests.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
