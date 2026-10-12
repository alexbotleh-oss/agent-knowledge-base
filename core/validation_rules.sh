#!/usr/bin/env bash
set -uo pipefail
log() { printf '[%s] %s\n' "$(date -u +'%Y-%m-%dT%H:%M:%SZ')" "$*"; }
run_check() {
  local label="$1"; shift
  log "RUN: $label: $*"
  if "$@"; then log "PASS: $label"; return 0; else local rc=$?; log "FAIL: $label (exit $rc)"; return "$rc"; fi
}
skip_check() {
  local label="$1" reason="${2:-required tool or project configuration not found}"
  log "SKIP: $label — $reason"
  [[ "${STRICT_VALIDATION:-0}" != "1" ]]
}
command_or_skip() {
  local cmd="$1" label="$2"; shift 2
  if command -v "$cmd" >/dev/null 2>&1; then run_check "$label" "$cmd" "$@"; else skip_check "$label" "command '$cmd' not installed"; fi
}
