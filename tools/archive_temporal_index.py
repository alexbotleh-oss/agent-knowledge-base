#!/usr/bin/env python3
"""Read-only bidirectional index for ChatGPT conversations.json exports.

Examples:
  python tools/archive_temporal_index.py conversations.zip --stats
  python tools/archive_temporal_index.py conversations.zip --search "black screen" --context 2
  python tools/archive_temporal_index.py conversations.zip --at 2026-09-21T12:00:00Z --window-minutes 30
  python tools/archive_temporal_index.py conversations.zip --repeat-terms "не работает;пропала;ошибка" --min-hits 2

The archive is read locally; this tool never uploads conversation text.
"""
from __future__ import annotations
import argparse
import datetime as dt
import json
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any

UTC = dt.timezone.utc


def iso_time(value: Any) -> str | None:
    if not isinstance(value, (int, float)):
        return None
    return dt.datetime.fromtimestamp(value, UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def parse_time(value: str) -> float:
    parsed = dt.datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.timestamp()


def part_text(parts: Any) -> str:
    if not isinstance(parts, list):
        return ""
    return "\n".join(part for part in parts if isinstance(part, str)).strip()


def load_archive(path: str) -> tuple[list[dict], list[dict]]:
    source = Path(path)
    if source.suffix.lower() == ".zip":
        with zipfile.ZipFile(source) as archive:
            candidates = [name for name in archive.namelist() if name.endswith("conversations.json")]
            if not candidates:
                raise ValueError("ZIP does not contain conversations.json")
            raw = json.loads(archive.read(candidates[0]))
    else:
        raw = json.loads(source.read_text(encoding="utf-8"))

    conversations, messages = [], []
    for conv in raw:
        cid = conv.get("id") or conv.get("conversation_id")
        mapping = conv.get("mapping") or {}
        conversations.append({
            "conversation_id": cid, "title": conv.get("title") or "",
            "create_time": conv.get("create_time"), "update_time": conv.get("update_time"),
            "node_count": len(mapping),
        })
        for node_id, node in mapping.items():
            msg = node.get("message")
            if not isinstance(msg, dict):
                continue
            content = msg.get("content") or {}
            author = msg.get("author") or {}
            messages.append({
                "conversation_id": cid, "conversation_title": conv.get("title") or "",
                "node_id": node_id, "message_id": msg.get("id"),
                "parent_node_id": node.get("parent"), "child_node_ids": node.get("children") or [],
                "timestamp": msg.get("create_time"), "timestamp_utc": iso_time(msg.get("create_time")),
                "role": author.get("role"), "author_name": author.get("name"),
                "content_type": content.get("content_type"), "text": part_text(content.get("parts")),
                "has_attachments": bool((msg.get("metadata") or {}).get("attachments")),
            })
    messages.sort(key=lambda item: (item["timestamp"] is None, item["timestamp"] or 0))
    return conversations, messages


def context_for(row: dict, by_node: dict, radius: int) -> list[dict]:
    result, seen, cursor = [], set(), row
    for _ in range(radius):
        parent = by_node.get((row["conversation_id"], cursor.get("parent_node_id")))
        if not parent:
            break
        result.append(parent)
        seen.add(parent["node_id"])
        cursor = parent
    result.reverse()
    result.append(row)
    seen.add(row["node_id"])
    for child_id in row.get("child_node_ids", [])[:radius]:
        child = by_node.get((row["conversation_id"], child_id))
        if child and child["node_id"] not in seen:
            result.append(child)
            seen.add(child["node_id"])
    parent = by_node.get((row["conversation_id"], row.get("parent_node_id")))
    if parent:
        for sibling_id in parent.get("child_node_ids", []):
            sibling = by_node.get((row["conversation_id"], sibling_id))
            if sibling and sibling["node_id"] not in seen and len(result) < radius * 2 + 1:
                result.append(sibling)
                seen.add(sibling["node_id"])
    return result


def show_row(row: dict, by_node: dict, radius: int = 0) -> None:
    context = context_for(row, by_node, radius) if radius else [row]
    print(f'[{row["timestamp_utc"] or "NO_TIMESTAMP"}] {row["role"]} | {row["conversation_title"]}')
    print(f'conversation_id={row["conversation_id"]} message_id={row["message_id"]} node_id={row["node_id"]}')
    for item in context:
        marker = ">>" if item["node_id"] == row["node_id"] else "  "
        body = item["text"].replace("\n", " / ")
        if len(body) > 700:
            body = body[:700] + "…"
        print(f'  {marker} [{item["timestamp_utc"] or "NO_TIMESTAMP"}] {item["role"]}: {body or "[non-text/empty content]"}')
    print()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive")
    parser.add_argument("--stats", action="store_true")
    parser.add_argument("--search", help="case-insensitive substring in textual message parts")
    parser.add_argument("--at", help="ISO timestamp; accepts Z or explicit offset")
    parser.add_argument("--window-minutes", type=float, default=30)
    parser.add_argument("--context", type=int, default=1, help="branch context radius")
    parser.add_argument("--repeat-terms", help="semicolon-separated candidate failure/lesson terms")
    parser.add_argument("--min-hits", type=int, default=2)
    parser.add_argument("--limit", type=int, default=30)
    args = parser.parse_args(argv)

    conversations, messages = load_archive(args.archive)
    by_node = {(item["conversation_id"], item["node_id"]): item for item in messages}
    timed = [item for item in messages if isinstance(item["timestamp"], (int, float))]
    if args.stats:
        print(json.dumps({
            "conversations": len(conversations), "message_nodes": len(messages),
            "text_messages": sum(bool(item["text"]) for item in messages),
            "timed_messages": len(timed), "missing_timestamps": len(messages) - len(timed),
            "first_utc": min((item["timestamp_utc"] for item in timed), default=None),
            "last_utc": max((item["timestamp_utc"] for item in timed), default=None),
        }, ensure_ascii=False, indent=2))
    if args.search:
        hits = [item for item in messages if args.search.casefold() in item["text"].casefold()]
        print(f'SEARCH {args.search!r}: {len(hits)} hit(s)')
        for item in hits[:args.limit]:
            show_row(item, by_node, max(0, args.context))
    if args.at:
        center, delta = parse_time(args.at), args.window_minutes * 60
        hits = [item for item in timed if abs(item["timestamp"] - center) <= delta]
        print(f'TIME {args.at} ±{args.window_minutes:g} min: {len(hits)} hit(s)')
        for item in hits[:args.limit]:
            show_row(item, by_node, max(0, args.context))
    if args.repeat_terms:
        for term in (term.strip() for term in args.repeat_terms.split(";") if term.strip()):
            hits = [item for item in messages if term.casefold() in item["text"].casefold()]
            conversation_count = len({item["conversation_id"] for item in hits})
            if len(hits) >= args.min_hits:
                print(f'REPEAT CANDIDATE term={term!r} message_hits={len(hits)} conversations={conversation_count}')
                for item in hits[:args.limit]:
                    show_row(item, by_node, max(0, args.context))
    if not (args.stats or args.search or args.at or args.repeat_terms):
        parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
