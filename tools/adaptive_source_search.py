#!/usr/bin/env python3
"""Plan and execute capability-aware discovery across explicitly configured local sources.

Known constraints determine search order, not permanent exclusion: sources with conflicting
metadata are searched only in the emergency tier after compatible/unknown sources fail.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from relocation_aware_discovery import discover

PLAN_VERSION = "adaptive-source-search-v1"


def _strings(value: Any) -> set[str]:
    if isinstance(value, str):
        return {value} if value else set()
    if isinstance(value, list):
        return {item for item in value if isinstance(item, str) and item}
    return set()


def _profile_relation(source: dict, request: dict) -> tuple[str, list[str], list[str]]:
    """Return preferred/fallback/emergency and explain every constraint comparison."""
    conflicts: list[str] = []
    unknowns: list[str] = []
    checks = (
        ("source_type", "source_types"),
        ("format", "formats"),
        ("project_id", "project_ids"),
        ("required_capabilities", "capabilities"),
    )
    for request_key, source_key in checks:
        requested = _strings(request.get(request_key) if request_key != "required_capabilities"
                             else request.get(request_key))
        if not requested:
            continue
        known = _strings(source.get(source_key))
        if not known:
            unknowns.append(f"{source_key}:unknown")
        elif request_key == "required_capabilities":
            missing = requested - known
            if missing:
                conflicts.append(f"missing_capabilities:{','.join(sorted(missing))}")
        elif not (requested & known):
            conflicts.append(f"{source_key}:no_overlap")

    size = request.get("size_bytes")
    if size is not None:
        max_size = source.get("max_item_size_bytes")
        min_size = source.get("min_item_size_bytes", 0)
        if not isinstance(max_size, int) or isinstance(max_size, bool):
            unknowns.append("max_item_size_bytes:unknown")
        elif size > max_size:
            conflicts.append("item_exceeds_source_max_size")
        if not isinstance(min_size, int) or isinstance(min_size, bool):
            unknowns.append("min_item_size_bytes:unknown")
        elif size < min_size:
            conflicts.append("item_below_source_min_size")

    if source.get("accessible") is False:
        conflicts.append("source_marked_inaccessible")
    if conflicts:
        return "emergency", conflicts, unknowns
    if unknowns:
        return "fallback", conflicts, unknowns
    return "preferred", conflicts, unknowns


def build_plan(sources: list[dict], request: dict) -> dict:
    """Create a deterministic tiered plan without touching source data."""
    if not isinstance(sources, list) or not sources:
        return {"status": "INVALID_INPUT", "plan_version": PLAN_VERSION, "tiers": [],
                "reason": "at least one source profile is required", "writes_performed": False}
    if not isinstance(request, dict):
        return {"status": "INVALID_INPUT", "plan_version": PLAN_VERSION, "tiers": [],
                "reason": "request must be an object", "writes_performed": False}
    if not any(request.get(k) for k in ("identity", "expected_sha256", "query")):
        return {"status": "INVALID_INPUT", "plan_version": PLAN_VERSION, "tiers": [],
                "reason": "identity, expected_sha256, or query is required", "writes_performed": False}
    if request.get("size_bytes") is not None and (
        isinstance(request["size_bytes"], bool) or not isinstance(request["size_bytes"], int)
        or request["size_bytes"] < 0
    ):
        return {"status": "INVALID_INPUT", "plan_version": PLAN_VERSION, "tiers": [],
                "reason": "size_bytes must be a non-negative integer", "writes_performed": False}

    seen: set[str] = set()
    planned = []
    for position, source in enumerate(sources):
        if not isinstance(source, dict):
            continue
        source_id = source.get("source_id")
        root = source.get("root")
        if not isinstance(source_id, str) or not source_id.strip() or source_id in seen:
            continue
        if not isinstance(root, str) or not root.strip():
            continue
        seen.add(source_id)
        tier, conflicts, unknowns = _profile_relation(source, request)
        try:
            priority = int(source.get("priority", 100))
        except (ValueError, TypeError, OverflowError):
            priority = 100
        planned.append({
            "source_id": source_id,
            "root": root,
            "expected_path": source.get("expected_path"),
            "tier": tier,
            "priority": priority,
            "configuration_order": position,
            "constraint_conflicts": conflicts,
            "unknown_constraints": unknowns,
        })

    rank = {"preferred": 0, "fallback": 1, "emergency": 2}
    planned.sort(key=lambda item: (
        rank[item["tier"]], item["priority"], item["configuration_order"], item["source_id"]
    ))
    tiers = []
    for tier in ("preferred", "fallback", "emergency"):
        entries = [item for item in planned if item["tier"] == tier]
        tiers.append({
            "tier": tier,
            "reason": {
                "preferred": "Known profile matches requested constraints.",
                "fallback": "No known conflict, but some source capabilities or limits are unknown.",
                "emergency": "Known metadata conflicts or marks this source inaccessible; search only if earlier tiers do not verify the target.",
            }[tier],
            "sources": entries,
        })
    return {
        "status": "PLAN_READY" if planned else "NO_VALID_SOURCES",
        "plan_version": PLAN_VERSION,
        "request": request,
        "tiers": tiers,
        "source_count": len(planned),
        "policy": {
            "never_discard_only_by_rank": True,
            "unknown_metadata_is_not_a_conflict": True,
            "fallback_expands_only_after_no_verified_identity_match": True,
            "text_similarity_is_not_identity_proof": True,
        },
        "writes_performed": False,
    }


def execute_search(plan: dict, request: dict, expected_path: str, *,
                   max_files: int = 2000, max_file_bytes: int = 2 * 1024 * 1024) -> dict:
    """Search tiers in order; stop only on a verified identity/hash result."""
    if plan.get("status") != "PLAN_READY":
        return {"status": "INVALID_PLAN", "coverage_status": "UNKNOWN",
                "plan": plan, "searches": [], "writes_performed": False}
    searches = []
    for tier in plan["tiers"]:
        tier_results = []
        for source in tier["sources"]:
            result = discover(
                source.get("expected_path") or expected_path, [Path(source["root"])],
                identity=request.get("identity"),
                expected_sha256=request.get("expected_sha256"),
                query=request.get("query"),
                max_files=max_files, max_file_bytes=max_file_bytes,
            )
            item = {
                "source_id": source["source_id"],
                "tier": tier["tier"],
                "priority": source["priority"],
                "result": result,
            }
            searches.append(item)
            tier_results.append(item)
            if result.get("status") in {"FOUND_AT_EXPECTED_PATH", "FOUND_ELSEWHERE_IDENTITY_MATCH"}:
                return {
                    "status": "VERIFIED_MATCH_FOUND",
                    "coverage_status": "STOPPED_AFTER_VERIFIED_MATCH",
                    "matched_source_id": source["source_id"],
                    "matched_tier": tier["tier"],
                    "searches": searches,
                    "unsearched_tiers": [t["tier"] for t in plan["tiers"]
                                         if {"preferred": 0, "fallback": 1, "emergency": 2}[t["tier"]]
                                         > {"preferred": 0, "fallback": 1, "emergency": 2}[tier["tier"]]],
                    "writes_performed": False,
                    "automatic_relocation_performed": False,
                }
        # A lexical candidate is not enough to stop; expand to the next tier.
    incomplete = any(
        item["result"].get("coverage_status") != "COMPLETE_WITHIN_CONFIGURED_BOUNDS"
        for item in searches
    )
    any_candidates = any(item["result"].get("candidates") for item in searches)
    return {
        "status": "SEARCH_INCOMPLETE" if incomplete else (
            "UNVERIFIED_CANDIDATES_ONLY" if any_candidates else "NO_MATCH_IN_CONFIGURED_SOURCES"
        ),
        "coverage_status": "PARTIAL" if incomplete else "ALL_CONFIGURED_TIERS_SCANNED",
        "searches": searches,
        "writes_performed": False,
        "automatic_relocation_performed": False,
        "interpretation": "A no-match applies only to configured sources and scan limits; it does not prove global absence.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, required=True,
                        help="JSON file containing a sources array of local source profiles")
    parser.add_argument("--request", type=Path, required=True,
                        help="JSON file describing identity/query and optional source constraints")
    parser.add_argument("--expected-path", required=True,
                        help="Path relative to each source root")
    parser.add_argument("--plan-only", action="store_true",
                        help="Print ordered tiers without reading source files")
    parser.add_argument("--max-files", type=int, default=2000)
    parser.add_argument("--max-file-bytes", type=int, default=2 * 1024 * 1024)
    args = parser.parse_args()
    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    request = json.loads(args.request.read_text(encoding="utf-8"))
    sources = catalog.get("sources") if isinstance(catalog, dict) else None
    if isinstance(sources, list):
        catalog_root = args.catalog.resolve().parent
        normalized_sources = []
        for source in sources:
            if not isinstance(source, dict):
                continue
            item = dict(source)
            root = item.get("root")
            if isinstance(root, str) and root and not Path(root).is_absolute():
                item["root"] = str((catalog_root / root).resolve())
            normalized_sources.append(item)
        sources = normalized_sources
    plan = build_plan(sources, request)
    result = plan if args.plan_only else execute_search(
        plan, request, args.expected_path,
        max_files=args.max_files, max_file_bytes=args.max_file_bytes,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") in {
        "PLAN_READY", "VERIFIED_MATCH_FOUND", "UNVERIFIED_CANDIDATES_ONLY"
    } else 1


if __name__ == "__main__":
    raise SystemExit(main())
