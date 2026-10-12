#!/usr/bin/env bash
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
P="${1:-.}"
P="$(cd "$P" 2>/dev/null && pwd)" || { echo "ERROR: project path not found: $P" >&2; exit 2; }
source "$ROOT/core/validation_rules.sh"
if [[ -f "$P/package.json" ]] && command -v npm >/dev/null 2>&1; then cd "$P" && npm test --if-present; else skip_check "JS tests" "npm/package.json missing"; fi
