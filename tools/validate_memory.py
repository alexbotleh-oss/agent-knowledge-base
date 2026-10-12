#!/usr/bin/env python3
"""Dependency-free structural checks for memory records and handoff files."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ERRORS = []

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
    print("Checked core protocol files and JSON/JSONL example records.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
