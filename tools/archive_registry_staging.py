#!/usr/bin/env python3
"""Build local staging records from a ChatGPT export; never uploads source text."""
from __future__ import annotations
import argparse, hashlib, json, zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def iso_utc(value: Any) -> str | None:
    if not isinstance(value, (int, float)):
        return None
    return datetime.fromtimestamp(value, timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")

def extract_text(content: Any) -> str:
    if not isinstance(content, dict):
        return ""
    parts = content.get("parts")
    if not isinstance(parts, list):
        return ""
    out = []
    for part in parts:
        if isinstance(part, str):
            out.append(part)
        elif isinstance(part, dict):
            out.append("[structured content: " + ",".join(sorted(part.keys())) + "]")
    return "\n".join(out).strip()

def load_export(source: Path) -> tuple[bytes, list[dict]]:
    raw = source.read_bytes()
    if source.suffix.lower() == ".zip":
        with zipfile.ZipFile(source) as archive:
            names = [name for name in archive.namelist() if name.endswith("conversations.json")]
            if len(names) != 1:
                raise ValueError(f"Expected exactly one conversations.json in ZIP; found {len(names)}")
            payload = json.loads(archive.read(names[0]).decode("utf-8"))
    else:
        payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Export root must be a JSON array")
    return raw, payload

def build(source: Path, output: Path, archive_id: str) -> dict:
    raw, conversations = load_export(source)
    digest = sha256(raw)
    records, timestamps, seen = [], [], set()
    missing_ids = attachment_count = 0
    for conv in conversations:
        if not isinstance(conv, dict):
            continue
        cid = conv.get("id") or conv.get("conversation_id")
        if not cid:
            cid = "conversation-unknown-" + sha256(json.dumps(conv, sort_keys=True, ensure_ascii=False).encode())[:16]
        mapping = conv.get("mapping") or {}
        if not isinstance(mapping, dict):
            continue
        for node_id, node in mapping.items():
            if not isinstance(node, dict) or not isinstance(node.get("message"), dict):
                continue
            msg = node["message"]
            created = msg.get("create_time")
            if isinstance(created, (int, float)):
                timestamps.append(created)
            mid = msg.get("id")
            missing_ids += int(not bool(mid))
            metadata = msg.get("metadata") or {}
            attachments = metadata.get("attachments") or []
            has_attachments = bool(attachments)
            attachment_count += int(has_attachments)
            content = msg.get("content") or {}
            locator = f"{archive_id}/{cid}/{node_id}"
            if locator in seen:
                raise ValueError("Duplicate stable source locator: " + locator)
            seen.add(locator)
            text = extract_text(content)
            author = msg.get("author") or {}
            records.append({
                "source_record_id": "SRC-" + sha256(locator.encode())[:24],
                "archive_id": archive_id, "conversation_id": str(cid),
                "conversation_title": conv.get("title") or "",
                "source_message_id": mid, "source_node_id": str(node_id),
                "source_locator": locator, "parent_node_id": node.get("parent"),
                "child_node_ids": node.get("children") or [],
                "event_time": iso_utc(created),
                "event_time_unix": created if isinstance(created, (int, float)) else None,
                "role": author.get("role"), "author_name": author.get("name"),
                "content_type": content.get("content_type") if isinstance(content, dict) else None,
                "text": text, "text_sha256": sha256(text.encode()),
                "has_attachments": has_attachments,
                "attachment_count": len(attachments) if isinstance(attachments, list) else None,
                "attachment_payloads_inspected": False if has_attachments else None,
            })
    records.sort(key=lambda x: (x["event_time_unix"] is None, x["event_time_unix"] or 0, x["source_locator"]))
    output.mkdir(parents=True, exist_ok=True)
    record_path = output / "source_records.jsonl"
    tmp_path = output / "source_records.jsonl.tmp"
    with tmp_path.open("w", encoding="utf-8", newline="\n") as stream:
        for record in records:
            stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    tmp_path.replace(record_path)
    manifest = {
        "archive_id": archive_id, "source_name": source.name, "source_kind": "chat_export",
        "raw_sha256": digest, "byte_size": len(raw),
        "format": "zip+json" if source.suffix.lower() == ".zip" else "json",
        "parser_version": "source-registry-staging-v1",
        "coverage": {
            "status": "partial" if missing_ids or attachment_count else "unknown",
            "conversation_count": len(conversations), "source_record_count": len(records),
            "message_id_missing_count": missing_ids, "records_with_attachment_markers": attachment_count,
            "first_source_time": iso_utc(min(timestamps)) if timestamps else None,
            "last_source_time": iso_utc(max(timestamps)) if timestamps else None,
            "limitations": [
                "Binary attachment payloads are not extracted or verified by this tool.",
                "Structural records are not semantic lessons, decisions, or verified claims.",
                "Coverage must be reviewed against export scope before it can be marked complete."
            ]
        },
        "records_file": record_path.name, "records_sha256": sha256(record_path.read_bytes()),
        "immutability": "raw-input-read-only; derived-output-rebuildable",
        "notes": "Local staging only. Do not commit private raw message text to a public repository."
    }
    (output / "archive_snapshot.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--archive-id", required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.source, args.out, args.archive_id), ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
