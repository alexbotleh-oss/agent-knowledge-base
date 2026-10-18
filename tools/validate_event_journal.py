"""Read-only preflight report for temporal edges in an event JSONL journal."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from append_memory_event import read_event_journal
from temporal_memory_model import validate_temporal_relations


def validate_event_journal(journal_path: Path, trusted_order_path: Path) -> dict[str, Any]:
    """Validate a journal without changing it and return a machine-readable report."""
    journal_path = Path(journal_path)
    trusted_order_path = Path(trusted_order_path)
    records = read_event_journal(journal_path)
    trusted_order = json.loads(trusted_order_path.read_text(encoding="utf-8"))
    if not isinstance(trusted_order, dict):
        raise ValueError("trusted-order file must contain a JSON object")
    errors = validate_temporal_relations(records, trusted_order)
    return {
        "status": "PASS" if not errors else "NEEDS_RECONCILIATION",
        "journal": str(journal_path),
        "record_count": len(records),
        "temporal_edge_count": sum(
            1 for record in records
            for edge in record.get("relations", [])
            if isinstance(edge, dict) and edge.get("type") in {"preceded_by", "followed_by"}
        ),
        "errors": errors,
        "writes_performed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--journal", required=True, type=Path)
    parser.add_argument("--trusted-order", required=True, type=Path)
    parser.add_argument(
        "--allow-unresolved",
        action="store_true",
        help="Exit successfully after emitting a NEEDS_RECONCILIATION report; for diagnostic CI only.",
    )
    args = parser.parse_args()
    report = validate_event_journal(args.journal, args.trusted_order)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["status"] == "PASS" or args.allow_unresolved:
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
