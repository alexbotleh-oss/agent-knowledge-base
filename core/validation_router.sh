#!/usr/bin/env bash
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT="${1:-.}"
PROJECT="$(cd "$PROJECT" 2>/dev/null && pwd)" || { echo "ERROR: project path not found" >&2; exit 2; }
REGISTRY="${STACK_REGISTRY:-$ROOT/core/stack_registry.json}"
source "$ROOT/core/validation_rules.sh"
command -v python3 >/dev/null 2>&1 || { echo "ERROR: python3 required to read stack registry" >&2; exit 2; }
mapfile -t STACKS < <(python3 - "$REGISTRY" "$PROJECT" <<'PY'
import json,pathlib,sys
reg,root=sys.argv[1],pathlib.Path(sys.argv[2])
with open(reg,encoding="utf-8") as f: data=json.load(f)
def matches(e):
 if any((root/p).exists() for p in e.get("path_exists",[])): return True
 if any(any(root.glob(g)) for g in e.get("glob_exists",[])): return True
 for rule in e.get("content_contains",[]):
  for p in root.glob(rule["file_glob"]):
   if not p.is_file() or any(x in p.parts for x in (".git","node_modules",".venv")): continue
   try: s=p.read_text(encoding="utf-8",errors="ignore")
   except OSError: continue
   pat=rule["pattern"]
   if pat=="import flet|from flet":
    if "import flet" in s or "from flet" in s: return True
   elif pat in s: return True
 return False
for e in sorted((e for e in data["stacks"] if matches(e)),key=lambda e:(-e.get("priority",0),e["id"])): print(e["id"])
PY
) || exit 2
if (("${#STACKS[@]}" == 0)); then log "No registered stack detected; generic checks only."; exit 0; fi
status=0
for stack in "${STACKS[@]}"; do
 dir="$ROOT/stacks/$stack"
 if [[ ! -d "$dir" ]]; then log "FAIL: missing adapter directory: $stack"; status=1; continue; fi
 log "Detected stack: $stack"
 for stage in lint test build; do
  script="$dir/$stage.sh"
  if [[ ! -f "$script" ]]; then log "FAIL: missing adapter $script"; status=1; continue; fi
  if bash "$script" "$PROJECT"; then :; else rc=$?; log "FAIL: $stack/$stage (exit $rc)"; status=1; fi
 done
done
exit "$status"
