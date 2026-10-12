#!/usr/bin/env bash
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
P="${1:-.}"
P="$(cd "$P" 2>/dev/null && pwd)" || { echo "ERROR: project path not found: $P" >&2; exit 2; }
source "$ROOT/core/validation_rules.sh"
if [[ -f "$P/package.json" ]] && command -v npm >/dev/null 2>&1; then cd "$P" && npm run lint --if-present; else python3 - "$P" <<'PY'
from pathlib import Path
import sys
files=list(Path(sys.argv[1]).glob("*.html"))
if not files: print("SKIP: no root HTML files"); raise SystemExit(0)
for f in files:
 s=f.read_text(encoding="utf-8",errors="ignore")
 if "<html" not in s.lower(): print(f"WARNING: {f} has no <html> tag")
print(f"Basic HTML scan: {len(files)} file(s)")
PY
fi
