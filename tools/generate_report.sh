#!/usr/bin/env bash
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT="${1:-.}"
OUT="${2:-$PROJECT/validation-report.md}"
mkdir -p "$(dirname "$OUT")"
TMP="$(mktemp)"; trap 'rm -f "$TMP"' EXIT
if bash "$ROOT/tools/validate_project.sh" "$PROJECT" >"$TMP" 2>&1; then rc=0; else rc=$?; fi
{
 echo "# Validation report"; echo
 echo "- Timestamp (UTC): $(date -u +'%Y-%m-%dT%H:%M:%SZ')"
 echo "- Project: `$PROJECT`"
 if [[ $rc -eq 0 ]]; then echo "- Overall: **PASS**"; else echo "- Overall: **FAIL** (exit $rc)"; fi
 echo; echo ' ```text'; cat "$TMP"; echo ' ```'
} > "$OUT"
echo "Report written to: $OUT"
exit "$rc"
