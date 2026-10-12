#!/usr/bin/env bash
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
P="${1:-.}"
P="$(cd "$P" 2>/dev/null && pwd)" || { echo "ERROR: project path not found: $P" >&2; exit 2; }
source "$ROOT/core/validation_rules.sh"
if [[ -f "$P/go.mod" ]] && command -v go >/dev/null 2>&1; then cd "$P" && files="$(find . -name '*.go' -not -path './vendor/*' -print)" && { [[ -z "$files" ]] || test -z "$(gofmt -l $files)"; } && go vet ./...; else skip_check "Go lint" "go/go.mod missing"; fi
